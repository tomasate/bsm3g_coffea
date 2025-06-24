import json
import argparse
import subprocess
from pathlib import Path
from analysis.filesets.utils import get_datasets_to_run, fileset_checker


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

    data_samples = {
        "1b1mu1e": "muon",
        "1b1e1mu": "electron",
        "2b1mu": "muon",
        "2b1e": "electron",
        "ztomumu": "muon",
        "ztoee": "electron",
        "qcd_mu": "muon",
        "qcd_ele": "electron",
        "qcd_cr1T_mu": None,
        "qcd_cr2T_mu": None,
        "qcd_cr1T_ele": None,
        "qcd_cr2T_ele": None,
        "ztojets": "muon",
    }
    mc_samples = {
        "1b1mu1e": ["dy_inclusive", "singletop", "tt", "wjets_ht", "diboson"],
        "1b1e1mu": ["dy_inclusive", "singletop", "tt", "wjets_ht", "diboson"],
        "2b1mu": ["dy_inclusive", "singletop", "tt", "wjets_ht", "diboson"],
        "2b1e": ["dy_inclusive", "singletop", "tt", "wjets_ht", "diboson"],
        "ztomumu": ["dy_inclusive", "singletop", "tt", "wjets_ht", "diboson"],
        "ztoee": ["dy_inclusive", "singletop", "tt", "wjets_ht", "diboson"],
        "qcd_mu": ["dy_inclusive", "singletop", "tt", "wjets_ht", "wjets_inclusive", "diboson"],
        "qcd_ele": ["dy_inclusive", "singletop", "tt", "wjets_ht", "wjets_inclusive", "diboson"],
        "qcd_cr1T_mu": ["wjets_ht", "wjets_inclusive"],
        "qcd_cr2T_mu": ["wjets_ht", "wjets_inclusive"],
        "qcd_cr1T_ele": ["wjets_ht", "wjets_inclusive"],
        "qcd_cr2T_ele": ["wjets_ht", "wjets_inclusive"],
        "ztojets": ["dy_inclusive", "dy_ht", "singletop", "tt", "wjets_ht", "wjets_inclusive", "diboson", "ewk", "higgs"],
    }
    datasets_to_run = get_datasets_to_run(
        args.workflow, args.year, data_samples, mc_samples
    )
    fileset_checker(datasets_to_run, args.year)

    # submit (or prepare) a job for each dataset using the given arguments
    cmd = ["python3", "submit_condor.py"]
    for dataset in datasets_to_run:
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