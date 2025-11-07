import correctionlib


def get_btag_mask(jets, year, wp):
    """
    Parameters:
    -----------
      jets: Jet collection
      year: {2016preVFP, 2016postVFP, 2017, 2018, 2022preEE, 2022postEE, 2023preBPix, 2023postBPix}
      wp: {loose, medium, tight}
    """
    # https://cms-analysis-corrections.docs.cern.ch/corrections/BTV/
    btagging_files = {
        "2016preVFP": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run2-2016preVFP-UL-NanoAODv9/2025-08-19/btagging.json.gz",
        "2016postVFP": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run2-2016postVFP-UL-NanoAODv9/2025-08-19/btagging.json.gz",
        "2017": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run2-2017-UL-NanoAODv9/2025-08-19/btagging.json.gz",
        "2018": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run2-2018-UL-NanoAODv9/2025-08-19/btagging.json.gz",
        "2022preEE": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run3-22CDSep23-Summer22-NanoAODv12/2025-08-20/btagging.json.gz",
        "2022postEE": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run3-22EFGSep23-Summer22EE-NanoAODv12/2025-08-20/btagging.json.gz",
        "2023preBPix": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run3-23CSep23-Summer23-NanoAODv12/2025-08-20/btagging.json.gz",
        "2023postBPix": "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run3-23DSep23-Summer23BPix-NanoAODv12/2025-08-20/btagging.json.gz",
    }
    # set working points mapping
    wp_map = {"loose": "L", "medium": "M", "tight": "T"}
    # select tagger according to run era
    tagger = "deepJet" if year.startswith("201") else "particleNet"
    tagger_map = {
        "deepJet": "deepJet_wp_values",
        "particleNet": "particleNet_wp_values",
    }
    # load correction set with working points
    cset = correctionlib.CorrectionSet.from_file(btagging_files[year])
    btag_wp = cset[tagger_map[tagger]].evaluate(wp_map[wp])

    if tagger == "deepJet":
        pass_btag_wp = jets.btagDeepFlavB > btag_wp
    elif tagger == "particleNet":
        pass_btag_wp = jets.btagPNetB > btag_wp
    return pass_btag_wp
