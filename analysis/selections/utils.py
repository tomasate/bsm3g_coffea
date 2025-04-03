import awkward as ak

def trigger_match(leptons: ak.Array, trigobjs: ak.Array, trigger_path: str):
    """
    Returns DeltaR matched trigger objects

    leptons:
        electrons or muons arrays
    trigobjs:
        trigger objects array
    trigger_path:
        trigger to match {IsoMu27, Ele35_WPTight_Gsf}

    https://twiki.cern.ch/twiki/bin/viewauth/CMS/EgammaNanoAOD#Trigger_bits_how_to
    """
    match_configs = {
        "IsoMu24": {
            "pt": trigobjs.pt > 22,
            "filterbit": (trigobjs.filterBits & 8) > 0,
            "id": abs(trigobjs.id) == 13
        },
        "IsoMu27": {
            "pt": trigobjs.pt > 25,
            "filterbit": (trigobjs.filterBits & 8) > 0,
            "id": abs(trigobjs.id) == 13
        },
        "Mu50": {
            "pt": trigobjs.pt > 45,
            "filterbit": (trigobjs.filterBits & 1024) > 0,
            "id": abs(trigobjs.id) == 13
        },
        "OldMu100": {
            "pt": trigobjs.pt > 95,
            "filterbit": (trigobjs.filterBits & 2048) > 0,
            "id": abs(trigobjs.id) == 13
        },
        # same as OldMu100?
        # https://github.com/cms-sw/cmssw/blob/CMSSW_10_6_X/PhysicsTools/NanoAOD/python/triggerObjects_cff.py#L79
        "TkMu100": {
            "pt": trigobjs.pt > 95,
            "filterbit": (trigobjs.filterBits & 2048) > 0,
            "id": abs(trigobjs.id) == 13
        },
        "Ele35_WPTight_Gsf": {
            "pt": trigobjs.pt > 33,
            "filterbit": (trigobjs.filterBits & 2) > 0,
            "id": abs(trigobjs.id) == 11
        },
        "Ele32_WPTight_Gsf": {
            "pt": trigobjs.pt > 30,
            "filterbit": (trigobjs.filterBits & 2) > 0,
            "id": abs(trigobjs.id) == 11
        },
        "Ele27_WPTight_Gsf": {
            "pt": trigobjs.pt > 25,
            "filterbit": (trigobjs.filterBits & 2) > 0,
            "id": abs(trigobjs.id) == 11
        },
        "Photon175": {
            "pt": trigobjs.pt > 25,
            "filterbit": (trigobjs.filterBits & 8192) > 0,
            "id": abs(trigobjs.id) == 11
        },
        "Photon200": {
            "pt": trigobjs.pt > 25,
            "filterbit": (trigobjs.filterBits & 8192) > 0,
            "id": abs(trigobjs.id) == 11
        },
        "IsoTkMu24": {
            "pt": trigobjs.pt > 22,
            "filterbit": (trigobjs.filterBits & 8) > 0,
            "id": abs(trigobjs.id) == 13
        },
    }
    pass_pt = match_configs[trigger_path]["pt"]
    pass_id = match_configs[trigger_path]["id"]
    pass_filterbit = match_configs[trigger_path]["filterbit"]
    trigger_cands = trigobjs[pass_pt & pass_id & pass_filterbit]
    delta_r = leptons.metric_table(trigger_cands)
    pass_delta_r = delta_r < 0.1
    n_of_trigger_matches = ak.sum(pass_delta_r, axis=2)
    trig_matched_locs = n_of_trigger_matches >= 1
    return trig_matched_locs


def delta_r_mask(first, second, threshold=0.4):
    """select objects from 'first' which are at least 'threshold' away from all objects in 'second'."""
    mval = first.metric_table(second)
    return ak.all(mval > threshold, axis=-1)