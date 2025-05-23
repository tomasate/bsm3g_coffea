import correctionlib
import numpy as np
import awkward as ak
from typing import Tuple
from analysis.corrections.utils import get_pog_json


def apply_met_phi_corrections(
    events: ak.Array,
    year: str,
) -> Tuple[ak.Array, ak.Array]:
    """
    Apply MET phi modulation corrections

    Parameters:
    -----------
        events:
            Events array
        year:
            Year of the dataset  {'2016preVFP', '2016postVFP', '2017', '2018'}

    Returns:
    --------
        corrected MET pt and phi
    """
    cset = correctionlib.CorrectionSet.from_file(
        get_pog_json(json_name="met", year=year)
    )
    events["MET", "pt_raw"] = ak.ones_like(events.MET.pt) * events.MET.pt
    events["MET", "phi_raw"] = ak.ones_like(events.MET.phi) * events.MET.phi

    # make sure to not cross the maximum allowed value for uncorrected met
    met_pt = events.MET.pt_raw
    met_pt = np.clip(met_pt, 0.0, 6499.0)
    met_phi = events.MET.phi_raw
    met_phi = np.clip(met_phi, -3.5, 3.5)

    # use correct run ranges when working with data, otherwise use uniform run numbers in an arbitrary large window
    run_ranges = {
        "2016preVFP": [272007, 278771],
        "2016postVFP": [278769, 284045],
        "2017": [297020, 306463],
        "2018": [315252, 325274],
    }
    data_kind = "mc" if hasattr(events, "genWeight") else "data"
    if data_kind == "mc":
        run = np.random.randint(
            run_ranges[year][0], run_ranges[year][1], size=len(met_pt)
        )
    else:
        run = events.run
    try:
        events["MET", "pt"] = cset[f"pt_metphicorr_pfmet_{data_kind}"].evaluate(
            met_pt.to_numpy(), met_phi.to_numpy(), events.PV.npvsGood.to_numpy(), run
        )
        events["MET", "phi"] = cset[f"phi_metphicorr_pfmet_{data_kind}"].evaluate(
            met_pt.to_numpy(), met_phi.to_numpy(), events.PV.npvsGood.to_numpy(), run
        )
    except:
        pass


def corrected_polar_met(
    met_pt,
    met_phi,
    other_phi,
    other_pt_old,
    other_pt_new,
    positive=None,
    dx=None,
    dy=None,
) -> tuple:
    """
    helper function to compute new MET polar components after some other object pT correction.

    https://github.com/CoffeaTeam/coffea/blob/master/src/coffea/jetmet_tools/CorrectedMETFactory.py#L6
    """
    sin, cos = np.sin(other_phi), np.cos(other_phi)
    met_px = met_pt * np.cos(met_phi) + ak.sum(
        (other_pt_new - other_pt_old) * cos, axis=1
    )
    met_py = met_pt * np.sin(met_phi) + ak.sum(
        (other_pt_new - other_pt_old) * sin, axis=1
    )
    if positive is not None and dx is not None and dy is not None:
        met_px = met_px + dx if positive else x - dx
        met_py = met_py + dy if positive else y - dy

    corrected_met_pt = np.hypot(met_px, met_py)
    corrected_met_phi = np.arctan2(met_py, met_px)
    return corrected_met_pt, corrected_met_phi
