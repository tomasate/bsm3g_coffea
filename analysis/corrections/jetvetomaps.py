import correctionlib
import numpy as np
import awkward as ak
from analysis.corrections.utils import get_pog_json


def apply_jetvetomaps(events: ak.Array, year: str, mapname: str = "jetvetomap"):
    """
    These are the jet veto maps showing regions with an excess of jets (hot zones) and lack of jets
    (cold zones). Using the phi-symmetry of the CMS detector, these areas with detector and or
    calibration issues can be pinpointed.

    Non-zero value indicates that the region is vetoed
    """
    hname = {
        "2016preVFP": "Summer19UL16_V1",
        "2016postVFP": "Summer19UL16_V1",
        "2017": "Summer19UL17_V1",
        "2018": "Summer19UL18_V1",
        "2022preEE": "Summer22_23Sep2023_RunCD_V1",
        "2022postEE": "Summer22EE_23Sep2023_RunEFG_V1",
        "2023preBPix": "Summer23Prompt23_RunC_V1",
        "2023postBPix": "Summer23BPixPrompt23_RunD_V1",
    }
    # select veto jets
    jets = events.Jet
    j, n = ak.flatten(jets), ak.num(jets)
    jet_eta_mask = np.abs(j.eta) < 5.19
    jet_phi_mask = np.abs(j.phi) < 3.14
    in_jet_mask = jet_eta_mask & jet_phi_mask
    in_jets = j.mask[in_jet_mask]
    jets_eta = ak.fill_none(in_jets.eta, 0.0)
    jets_phi = ak.fill_none(in_jets.phi, 0.0)
    cset = correctionlib.CorrectionSet.from_file(get_pog_json("jetvetomaps", year))
    vetomaps = cset[hname[year]].evaluate(mapname, jets_eta, jets_phi)
    vetomaps = ak.unflatten(vetomaps, n) == 0
    jets_veto = events.Jet[vetomaps]

    # update MET
    met_key = (
        "PuppiMET" if (year.startswith("2022") or year.startswith("2023")) else "MET"
    )
    met_pt = events[met_key].pt
    met_phi = events[met_key].phi
    # Jet veto pt(x,y) per event
    jet_veto_pt_x = jets_veto.pt * np.cos(jets_veto.phi)
    jet_veto_pt_y = jets_veto.pt * np.sin(jets_veto.phi)
    jet_pt_x = events.Jet.pt * np.cos(events.Jet.phi)
    jet_pt_y = events.Jet.pt * np.sin(events.Jet.phi)
    # get x and y changes
    delta_x = ak.sum(jet_pt_x, axis=-1) - ak.sum(jet_veto_pt_x, axis=-1)
    delta_y = ak.sum(jet_pt_y, axis=-1) - ak.sum(jet_veto_pt_y, axis=-1)
    # propagate changes to MET (x, y) components
    met_px = met_pt * np.cos(met_phi) - delta_x
    met_py = met_pt * np.sin(met_phi) - delta_y
    # propagate changes to MET (pT, phi) components
    new_met_pt = np.sqrt((met_px**2.0 + met_py**2.0))
    new_met_phi = np.arctan2(met_py, met_px)

    # update fields
    events["Jet"] = jets_veto
    events[met_key, "pt"] = new_met_pt
    events[met_key, "phi"] = new_met_phi
