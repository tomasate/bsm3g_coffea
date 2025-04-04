import argparse
import subprocess
from pathlib import Path

DATA_SAMPLES = {
    "2b1mu": {
        "2016preVFP": [
            "SingleMuonBver1",
            "SingleMuonBver2",
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
    },
    "2b1e": {
        "2016preVFP": [
            "SingleElectronBver1",
            "SingleElectronBver2",
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
    },
}
MC_SAMPLES = [
    # DYJetsToLL
    "DYJetsToLL_inclusive_10to50",
    "DYJetsToLL_inclusive_50",
    # SingleTop
    "ST_s-channel_4f_leptonDecays",
    "ST_t-channel_antitop_4f_InclusiveDecays",
    "ST_t-channel_top_4f_InclusiveDecays",
    "ST_tW_antitop_5f_inclusiveDecays",
    "ST_tW_top_5f_inclusiveDecays",
    # tt
    "TTTo2L2Nu",
    "TTToHadronic",
    "TTToSemiLeptonic",
    # WJetsToLNu
    "WJetsToLNu_HT-100To200",
    "WJetsToLNu_HT-1200To2500",
    "WJetsToLNu_HT-200To400",
    "WJetsToLNu_HT-2500ToInf",
    "WJetsToLNu_HT-400To600",
    "WJetsToLNu_HT-600To800",
    "WJetsToLNu_HT-800To1200",,
    # Diboson
    "WW",
    "WZ",
    "ZZ",
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w",
        "--workflow",
        dest="workflow",
        type=str,
        choices=["2b1e", "2b1mu"],
        help="workflow config to run",
    )
    parser.add_argument(
        "-y",
        "--year",
        dest="year",
        type=str,
        choices=["2016preVFP", "2016postVFP", "2017", "2018"],
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
        choices=["coffea", "root"],
        help="format of output histogram",
    )
    args = parser.parse_args()

    # check if the fileset for the given year exists, generate it otherwise
    filesets_path = Path.cwd() / "analysis" / "filesets"
    fileset_file = filesets_path / f"fileset_{args.year}_NANO_lxplus.json"
    if not fileset_file.exists():
        cmd = f"python3 fetch.py --year {args.year}"
        subprocess.run(cmd, shell=True)

    # submit (or prepare) a job for each dataset using the given arguments
    to_run = MC_SAMPLES + DATA_SAMPLES[args.workflow][args.year]
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
