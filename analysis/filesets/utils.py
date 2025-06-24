import re
import glob
import yaml
import subprocess
from pathlib import Path
from analysis.workflows.config import WorkflowConfigBuilder


def get_rootfiles(year: str, dataset: str):
    main_dir = Path.cwd()
    fileset_path = Path(f"{main_dir}/analysis/filesets")
    with open(f"{fileset_path}/{year}_fileset.yaml", "r") as f:
        dataset_config = yaml.safe_load(f)[dataset]

    # check for .root files in the specified path
    root_files = glob.glob(f"{dataset_config['path']}/*.root")
    if not root_files:
        # if no files found, check in the subdirectories
        root_files = glob.glob(f"{dataset_config['path']}/*/*.root")
    elif not root_files:
        raise FileNotFoundError(
            f"No .root files found in {dataset_config['path']} or its subdirectories."
        )
    return root_files


def divide_list(lst: list, nfiles: int = 20) -> list:
    """Divide a list into sublists such that each sublist has at least 20 elements."""
    if len(lst) < nfiles:
        return [lst]

    # Dynamically calculate the number of sublists such that each has at least 20 elements
    n = len(lst) // nfiles  # This gives the number of groups with at least 20 elements
    if len(lst) % nfiles != 0:
        n += 1  # Increase n by 1 if there is a remainder, to accommodate extra elements

    # Divide the list into 'n' sublists
    size = len(lst) // n
    remainder = len(lst) % n
    result = []
    start = 0

    for i in range(n):
        if i < remainder:
            end = start + size + 1
        else:
            end = start + size
        result.append(lst[start:end])
        start = end
    return result


def get_dataset_key(dataset):
    datasets = ["SingleMuon", "SingleElectron"]
    for dataset_key in datasets:
        if dataset.startswith(dataset_key):
            return dataset_key
    return "MC"


def get_dataset_era(dataset, year):
    fileset_path = Path(f"{Path.cwd()}/analysis/filesets")
    run_key = "Run3" if year.startswith("2022") or year.startswith("2023") else "Run2"
    nano_version = "nanov9" if run_key == "Run2" else "nanov12"
    with open(f"{fileset_path}/{year}_{nano_version}.yaml", "r") as f:
        dataset_config = yaml.safe_load(f)
    for dataset_key in dataset_config:
        if dataset.startswith(dataset_key):
            return dataset_config[dataset_key]["era"]


def modify_site_list(year: str, site: str, status: str) -> None:
    """
    Move a given site to the specified status list ("white" or "black")

    Parameters:
    -----------
        site: The site identifier to modify.
        status: Desired list to move the site to ("white" or "black").
    """
    yaml_file = Path.cwd() / "analysis" / "filesets" / f"{year}_sites.yaml"
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)

    if status == "white":
        if site not in data["white"]:
            data["white"].append(site)
        if site in data["black"]:
            data["black"].remove(site)
    else:
        if site not in data["black"]:
            data["black"].append(site)
        if site in data["white"]:
            data["white"].remove(site)

    with open(yaml_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def extract_xrootd_errors(error_files: list) -> set:
    """
    Extract xrootd URLs from a list of Condor error log files.

    Parameters:
    -----------
        error_files: (list of str or Path): Paths to error log files.

    Returns:
    --------
        set: A set of unique xrootd endpoints found in the logs.
    """
    xrootd_errs = set()
    for error_file in error_files:
        with open(error_file, "r") as f:
            err_content = f.read()
        xrootd_matches = re.findall(r"root://[a-zA-Z0-9\-.]+(?:[:]\d+)?", err_content)
        xrootd_errs.update(xrootd_matches)
    return xrootd_errs


def get_datasets_map(year: str):
    run_key = "Run3" if year.startswith("2022") or year.startswith("2023") else "Run2"
    nano_version = "nanov9" if run_key == "Run2" else "nanov12"
    fileset_path = Path.cwd() / "analysis" / "filesets" / f"{year}_{nano_version}.yaml"
    with open(fileset_path) as f:
        fileset_config = yaml.safe_load(f)
    datasets_map = {}
    for sample in fileset_config:
        key = fileset_config[sample]["key"]
        if key in datasets_map:
            datasets_map[key] += [sample]
        else:
            datasets_map[key] = [sample]
    return datasets_map


def get_datasets_to_run(workflow: str, year: str):
    config_builder = WorkflowConfigBuilder(workflow=workflow)
    workflow_config = config_builder.build_workflow_config()
    mc_samples = workflow_config.datasets["mc"]
    data_samples = workflow_config.datasets["data"]

    datasets_map = get_datasets_map(year)
    samples_keys_to_run = mc_samples
    if data_samples:
        samples_keys_to_run += data_samples
    datasets_to_run = []
    for key in samples_keys_to_run:
        if key not in datasets_map:
            print(f"\n{key} not availabe for {year}!")
            continue
        datasets_to_run += datasets_map[key]
    return datasets_to_run


def fileset_checker(samples: list, year: str):
    """check if the fileset for the given year exists, generate it otherwise"""

    filesets_path = Path.cwd() / "analysis" / "filesets"
    fileset_file = filesets_path / f"fileset_{year}_NANO_lxplus.json"

    build_input_fileset = False
    if not fileset_file.exists():
        build_input_fileset = True
    else:
        with open(fileset_file, "r") as f:
            filesets = json.load(f)
        build_input_fileset = not any(ds not in filesets for ds in samples)

    if build_input_fileset:
        print("\nBuilding input filesets for:")
        print(yaml.dump(samples, default_flow_style=False, sort_keys=False, indent=2))
        cmd = f"python3 fetch.py --year {year} --samples {' '.join(samples)}"
        subprocess.run(cmd, shell=True)
