import yaml
import numpy as np
import awkward as ak
import importlib.resources
from analysis.filesets.utils import get_dataset_key


def get_hltpaths_from_flag(flag, year):
    if year.startswith("2016"):
        year = "2016"
    elif year.startswith("2022"):
        year = "2022"
    elif year.startswith("2023"):
        year = "2023"
    with importlib.resources.open_text(
        f"analysis.selections", f"trigger_flags.yaml"
    ) as file:
        hlt_paths = yaml.safe_load(file)
    return hlt_paths[int(year)][flag]


def trigger_from_flag(events, flag, year):
    hlt_paths = get_hltpaths_from_flag(flag, year)
    trigger_mask = np.zeros(len(events), dtype="bool")
    for hlt_path in hlt_paths:
        trigger_mask = trigger_mask | events.HLT[hlt_path]
    return trigger_mask


def trigger_mask(events, hlt_paths, dataset, year):
    dataset_key = get_dataset_key(dataset)
    # compute all trigger masks based on the flags in hlt_paths
    trigger_flags = {}
    for dataset_flags in hlt_paths.values():
        for flag in dataset_flags:
            trigger_flags[flag] = trigger_from_flag(events, flag, year)

    # compute the combined OR of all flags (for background)
    all_combined_mask = np.zeros(len(events), dtype="bool")
    for flag in trigger_flags:
        all_combined_mask = all_combined_mask | trigger_flags[flag]

    dataset_masks = {}
    for dataset, flags in hlt_paths.items():
        # OR of all flags for this dataset
        mask = np.zeros(len(events), dtype="bool")
        for flag in flags:
            mask = mask | trigger_flags[flag]

        if dataset_masks:
            # exclude other datasets flags
            other_masks = np.zeros(len(events), dtype="bool")
            for other_dataset in dataset_masks:
                for flag in hlt_paths[other_dataset]:
                    other_masks = other_masks | trigger_flags[flag]
            mask = mask & ~other_masks
        dataset_masks[dataset] = mask

    return dataset_masks.get(dataset_key, all_combined_mask)


def trigger_match(leptons: ak.Array, trigobjs: ak.Array, hlt_path: str, year: str):
    """
    Returns DeltaR matched trigger objects

    leptons:
        electrons or muons arrays
    trigobjs:
        trigger objects array
    hlt_path:
        trigger to match
    year:
        dataset year {2016preVFP, 2016postVFP, 2017, 2018, 2022preEE, 2022postEE, 2023preBPix, 2023postBPix}

    https://twiki.cern.ch/twiki/bin/viewauth/CMS/EgammaNanoAOD#Trigger_bits_how_to
    """
    match_configs = {
        "Run2": {
            "IsoMu24": {
                "pt": trigobjs.pt > 22,
                "id": abs(trigobjs.id) == 13,
                "filterbit": (trigobjs.filterBits & 8) > 0,
            },
            "IsoMu27": {
                "pt": trigobjs.pt > 25,
                "filterbit": (trigobjs.filterBits & 8) > 0,
                "id": abs(trigobjs.id) == 13,
            },
            "Mu50": {
                "pt": trigobjs.pt > 45,
                "filterbit": (trigobjs.filterBits & 1024) > 0,
                "id": abs(trigobjs.id) == 13,
            },
            "OldMu100": {
                "pt": trigobjs.pt > 95,
                "filterbit": (trigobjs.filterBits & 2048) > 0,
                "id": abs(trigobjs.id) == 13,
            },
            "TkMu100": {
                "pt": trigobjs.pt > 95,
                "filterbit": (trigobjs.filterBits & 2048) > 0,
                "id": abs(trigobjs.id) == 13,
            },
            "Ele35_WPTight_Gsf": {
                "pt": trigobjs.pt > 33,
                "filterbit": (trigobjs.filterBits & 2) > 0,
                "id": abs(trigobjs.id) == 11,
            },
            "Ele32_WPTight_Gsf": {
                "pt": trigobjs.pt > 30,
                "filterbit": (trigobjs.filterBits & 2) > 0,
                "id": abs(trigobjs.id) == 11,
            },
            "Ele27_WPTight_Gsf": {
                "pt": trigobjs.pt > 25,
                "filterbit": (trigobjs.filterBits & 2) > 0,
                "id": abs(trigobjs.id) == 11,
            },
            "Photon175": {
                "pt": trigobjs.pt > 25,
                "filterbit": (trigobjs.filterBits & 8192) > 0,
                "id": abs(trigobjs.id) == 11,
            },
            "Photon200": {
                "pt": trigobjs.pt > 25,
                "filterbit": (trigobjs.filterBits & 8192) > 0,
                "id": abs(trigobjs.id) == 11,
            },
            "IsoTkMu24": {
                "pt": trigobjs.pt > 22,
                "filterbit": (trigobjs.filterBits & 8) > 0,
                "id": abs(trigobjs.id) == 13,
            },
        },
        "Run3": {
            # filterbit: 3 => 1mu
            # id: 13 => mu
            "IsoMu24": {
                "pt": trigobjs.pt > 23,
                "id": abs(trigobjs.id) == 13,
                "filterbit": trigobjs.filterBits & (0x1 << 3) > 0,
            },
            # filterbit: 0 => TrkIsoVVL
            # id: 13 => mu
            "Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": {
                "pt": trigobjs.pt > 7,
                "id": abs(trigobjs.id) == 13,
                "filterbit": trigobjs.filterBits & (0x1 << 0) > 0,
            },
            # filterbit: 1 => 1e (WPTight)
            # id: 11 => ele
            "Ele30_WPTight_Gsf": {
                "pt": trigobjs.pt > 28,
                "id": abs(trigobjs.id) == 11,
                "filterbit": trigobjs.filterBits & (0x1 << 1) > 0,
            },
        },
    }
    run_key = (
        "Run2" if year in ["2016preVFP", "2016postVFP", "2017", "2018"] else "Run3"
    )
    pass_pt = match_configs[run_key][hlt_path]["pt"]
    pass_id = match_configs[run_key][hlt_path]["id"]
    pass_filterbit = match_configs[run_key][hlt_path]["filterbit"]
    trigger_cands = trigobjs[pass_pt & pass_id & pass_filterbit]
    delta_r = leptons.metric_table(trigger_cands)
    pass_delta_r = delta_r < 0.1
    n_of_trigger_matches = ak.sum(pass_delta_r, axis=2)
    trig_matched_locs = n_of_trigger_matches >= 1
    return trig_matched_locs


def trigger_match_mask(events, hlt_paths, year, leptons):
    trigger_match_mask = np.zeros(len(events), dtype="bool")
    for dataset_flags in hlt_paths.values():
        for flag in dataset_flags:
            for hlt_path in get_hltpaths_from_flag(flag, year):
                trig_obj_mask = trigger_match(
                    leptons=leptons,
                    trigobjs=events.TrigObj,
                    hlt_path=hlt_path,
                    year=year,
                )
                trigger_match_mask = trigger_match_mask | trig_obj_mask
    return trigger_match_mask
