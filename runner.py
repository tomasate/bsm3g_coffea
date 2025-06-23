import argparse
import subprocess
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w",
        "--workflow",
        dest="workflow",
        type=str,
        choices=[
            f.stem for f in (Path.cwd() / "analysis" / "workflows").glob("*.yaml")
        ],
        help="workflow to run",
    )
    parser.add_argument(
        "-y",
        "--year",
        dest="year",
        type=str,
        choices=[
            "2016preVFP",
            "2016postVFP",
            "2017",
            "2018",
            "2022preEE",
            "2022postEE",
            "2023preBPix",
            "2023postBPix",
        ],
        help="dataset year",
    )
    parser.add_argument(
        "--nfiles",
        dest="nfiles",
        type=int,
        default=10,
        help="number of root files to include in each dataset partition (default 10)",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Enable Condor job submission. If not provided, it just builds condor files",
    )
    parser.add_argument(
        "--eos",
        action="store_true",
        help="Enable saving outputs to /eos",
    )
    parser.add_argument(
        "--output_format",
        type=str,
        default="coffea",
        choices=["coffea"],
        help="format of output histogram",
    )
    args = parser.parse_args()

    muon_datasets = {
        "2016preVFP": [
            "SingleMuonv1B",
            "SingleMuonv2B",
            "SingleMuonC",
            "SingleMuonD",
            "SingleMuonE",
            "SingleMuonF",
        ],
        "2016postVFP": ["SingleMuonF", "SingleMuonG", "SingleMuonH"],
        "2017": [
            "SingleMuonB",
            "SingleMuonC",
            "SingleMuonD",
            "SingleMuonE",
            "SingleMuonF",
        ],
        "2018": ["SingleMuonA", "SingleMuonB", "SingleMuonC", "SingleMuonD"],
        "2022preEE": ["MuonC", "MuonD"],
        "2022postEE": ["MuonE", "MuonF", "MuonG"],
        "2023preBPix": [
            "Muon0v1C",
            "Muon0v2C",
            "Muon0v3C",
            "Muon0v4C",
            "Muon1v1C",
            "Muon1v2C",
            "Muon1v3C",
            "Muon1v4C",
        ],
        "2023postBPix": ["Muon0v1D", "Muon0v2D", "Muon1v1D", "Muon1v2D"],
    }
    electron_datasets = {
        "2016preVFP": [
            "SingleElectronv1B",
            "SingleElectronv2B",
            "SingleElectronC",
            "SingleElectronD",
            "SingleElectronE",
            "SingleElectronF",
        ],
        "2016postVFP": ["SingleElectronF", "SingleElectronG", "SingleElectronH"],
        "2017": [
            "SingleElectronB",
            "SingleElectronC",
            "SingleElectronD",
            "SingleElectronE",
            "SingleElectronF",
        ],
        "2018": [
            "SingleElectronA",
            "SingleElectronB",
            "SingleElectronC",
            "SingleElectronD",
        ],
        "2022preEE": ["EGammaC", "EGammaD"],
        "2022postEE": ["EGammaE", "EGammaF", "EGammaG"],
        "2023preBPix": [
            "EGamma0v1C",
            "EGamma0v2C",
            "EGamma0v3C",
            "EGamma0v4C",
            "EGamma1v1C",
            "EGamma1v2C",
            "EGamma1v3C",
            "EGamma1v4C",
        ],
        "2023postBPix": ["EGamma0v1D", "EGamma0v2D", "EGamma1v1D", "EGamma1v2D"],
    }
    dy_inclusive = {
        "run2": ["DYJetsToLL_inclusive_10to50", "DYJetsToLL_inclusive_50"],
        "run3": ["DYJetsToLL_inclusive_10to50", "DYJetsToLL_inclusive_50"],
    }
    singletop = {
        "run2": [
            "ST_s-channel_4f_leptonDecays",
            "ST_t-channel_antitop_4f_InclusiveDecays",
            "ST_t-channel_top_4f_InclusiveDecays",
            "ST_tW_antitop_5f_inclusiveDecays",
            "ST_tW_top_5f_inclusiveDecays",
        ],
        "run3": [
            "TWminusto2L2Nu",
            "TWminusto4Q",
            "TWminustoLNu2Q",
            "TbarBQ",
            "TbarWplusto2L2Nu",
            "TbarWplusto4Q",
            "TbarWplustoLNu2Q",
            "TBbarQ",
        ],
    }
    tt = {
        "run2": [
            "TTTo2L2Nu",
            "TTToHadronic",
            "TTToSemiLeptonic",
        ],
        "run3": ["TTTo2L2Nu", "TTto4Q", "TTtoLNu2Q"],
    }
    wjets_inclusive = {"run2": ["WJetsToLNu_inclusive"], "run3": []}
    wjets_ht = {
        "run2": [
            "WJetsToLNu_HT-100To200",
            "WJetsToLNu_HT-1200To2500",
            "WJetsToLNu_HT-200To400",
            "WJetsToLNu_HT-2500ToInf",
            "WJetsToLNu_HT-400To600",
            "WJetsToLNu_HT-600To800",
            "WJetsToLNu_HT-800To1200",
        ],
        "run3": [],
    }
    diboson = {"run2": ["WW", "WZ", "ZZ"], "run3": ["WW", "WZ", "ZZ"]}
    ewk = {
        "run2": [
            "EWKWMinus2Jets_WToLNu",
            "EWKWPlus2Jets_WToLNu",
            "EWKZ2Jets_ZToLL",
            "EWKZ2Jets_ZToNuNu",
        ],
        "run3": [],
    }
    higgs = {
        "run2": ["GluGluHToWWToLNuQQ", "VBFHToWWTo2L2Nu", "VBFHToWWToLNuQQ"],
        "run3": [],
    }
    qcd_mu = {
        "run2": [
            "QCD_Pt-15To20_MuEnriched",
            "QCD_Pt-20To30_MuEnriched",
            "QCD_Pt-30To50_MuEnriched",
            "QCD_Pt-50To80_MuEnriched",
            "QCD_Pt-80To120_MuEnriched",
            "QCD_Pt-120To170_EMEnriched",
            "QCD_Pt-170To300_MuEnriched",
            "QCD_Pt-300To470_MuEnriched",
            "QCD_Pt-470To600_MuEnriched",
            "QCD_Pt-600To800_MuEnriched",
            "QCD_Pt-800To1000_MuEnriched",
            "QCD_Pt-1000_MuEnriched",
        ],
        "run3": [],
    }
    qcd_ele = {
        "run2": [
            "QCD_Pt-15To20_EMEnriched",
            "QCD_Pt-20To30_EMEnriched",
            "QCD_Pt-30To50_EMEnriched",
            "QCD_Pt-50To80_EMEnriched",
            "QCD_Pt-80To120_EMEnriched",
            "QCD_Pt-120To170_EMEnriched",
            "QCD_Pt-170To300_EMEnriched",
            "QCD_Pt-300ToInf_EMEnriched",
        ],
        "run3": [],
    }
    qcd_ht = {
        "run2": [
            "QCD_HT50to100",
            "QCD_HT100to200" "QCD_HT200to300",
            "QCD_HT300to500",
            "QCD_HT500to700",
            "QCD_HT700to1000",
            "QCD_HT1000to1500",
            "QCD_HT1500to2000",
            "QCD_HT2000toInf",
        ],
        "run3": [],
    }
    run_key = "run3" if (year.startswith("2022") or year.startswith("2023")) else "run2"
    data_samples = {
        "1b1mu1e": muon_datasets,
        "1b1e1mu": electron_datasets,
        "2b1mu": muon_datasets,
        "2b1e": electron_datasets,
        "ztomumu": muon_datasets,
        "ztoee": electron_datasets,
        "qcd_mu": muon_datasets,
        "qcd_ele": electron_datasets,
        "qcd_cr1T_mu": None,
        "qcd_cr2T_mu": None,
        "qcd_cr1T_ele": None,
        "qcd_cr2T_ele": None,
        "ztojets": muon_datasets,
    }
    mc_samples = {
        "1b1mu1e": dy_inclusive[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "1b1e1mu": dy_inclusive[run_key][run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "2b1mu": dy_inclusive[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "2b1e": dy_inclusive[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "ztomumu": dy_inclusive[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "ztoee": dy_inclusive[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "qcd_mu": dy_inclusive[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_inclusive[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "qcd_ele": dy_inclusive[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_inclusive[run_key]
        + wjets_ht[run_key]
        + diboson[run_key],
        "qcd_cr1T_mu": wjets_inclusive[run_key] + wjets_ht[run_key],
        "qcd_cr2T_mu": wjets_inclusive[run_key] + wjets_ht[run_key],
        "qcd_cr1T_ele": wjets_inclusive[run_key] + wjets_ht[run_key],
        "qcd_cr2T_ele": wjets_inclusive[run_key] + wjets_ht[run_key],
        "ztojets": dy_inclusive[run_key]
        + dy_ht[run_key]
        + singletop[run_key]
        + tt[run_key]
        + wjets_inclusive[run_key]
        + wjets_ht[run_key],
    }
    # check if the fileset for the given year exists, generate it otherwise
    filesets_path = Path.cwd() / "analysis" / "filesets"
    fileset_file = filesets_path / f"fileset_{args.year}_NANO_lxplus.json"
    if not fileset_file.exists():
        cmd = f"python3 fetch.py --year {args.year}"
        subprocess.run(cmd, shell=True)

    if fileset_file.exists():
        # submit (or prepare) a job for each dataset using the given arguments
        to_run = mc_samples[args.workflow]
        if data_samples[args.workflow]:
            to_run += data_samples[args.workflow][args.year]
        cmd = ["python3", "submit_condor.py"]
        for dataset in to_run:
            cmd_args = [
                "--workflow",
                args.workflow,
                "--year",
                args.year,
                "--dataset",
                dataset,
                "--nfiles",
                str(args.nfiles),
                "--output_format",
                args.output_format,
            ]
            if args.submit:
                cmd_args.append("--submit")
            if args.eos:
                cmd_args.append("--eos")
            subprocess.run(cmd + cmd_args)
    else:
        print("Input dataset could not be found!")
