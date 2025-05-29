import copy
import correctionlib
import awkward as ak
from pathlib import Path


def add_electron_boost_weight(events, weights, year, variation):
    # get input values
    met_pt = events.selected_met.pt
    electrons_pt = ak.firsts(events.selected_electrons).pt

    bjets = events.selected_bjets
    leading_bjet_pt = ak.pad_none(bjets, target=2)[:, 0].pt
    subleading_bjet_pt = ak.pad_none(bjets, target=2)[:, 1].pt

    st = electrons_pt + met_pt + leading_bjet_pt + subleading_bjet_pt
    njet = ak.num(events.selected_jets)

    in_binning = (st > 196.4) & (st < 1000.0) & (njet > 1) & (njet < 9)
    selected_st = st.mask[in_binning]
    selected_njet = njet.mask[in_binning]
    selected_st = ak.fill_none(selected_st, 500.0)
    selected_njet = ak.fill_none(selected_njet, 2.0)

    # load correction set
    json_path = f"{Path.cwd()}/analysis/data/{year}_2b1e_boost_weight.json.gz"
    cset = correctionlib.CorrectionSet.from_file(json_path)

    # compute weight
    sf = cset["boost_weight"].evaluate(selected_st, selected_njet)
    weight = ak.where(in_binning, sf, ak.ones_like(sf))
    weights.add(
        name="boost_weight",
        weight=weight,
    )