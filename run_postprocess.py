import gc
import yaml
import glob
import logging
import argparse
import subprocess
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from coffea.util import save, load
from coffea.processor import accumulate
from analysis.workflows.config import WorkflowConfigBuilder
from analysis.postprocess.coffea_plotter import CoffeaPlotter
from analysis.postprocess.coffea_postprocessor import (
    save_process_histograms_by_process,
    save_process_histograms_by_sample,
    load_processed_histograms,
    get_results_report,
    get_cutflow,
)
from analysis.postprocess.utils import (
    print_header,
    setup_logger,
    clear_output_directory,
    combine_event_tables,
    combine_cutflows,
    df_to_latex,
)


OUTPUT_DIR = Path.cwd() / "outputs"
FILE_EXTENSION = ".coffea"
TXT_EXT = "txt"


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run postprocessing and plotting for specified workflow and year."
    )
    parser.add_argument(
        "-w",
        "--workflow",
        required=True,
        choices=["2b1e", "2b1mu", "ztomumu", "ztoee"],
        help="Workflow config to run",
    )
    parser.add_argument(
        "-y",
        "--year",
        required=True,
        choices=["2016", "2016preVFP", "2016postVFP", "2017", "2018"],
        help="Dataset year",
    )
    parser.add_argument(
        "--log", action="store_true", help="Enable log scale for y-axis"
    )
    parser.add_argument(
        "--yratio_limits",
        type=float,
        nargs=2,
        default=(0.5, 1.5),
        help="Set y-axis ratio limits (e.g., --yratio_limits 0 2)",
    )
    parser.add_argument(
        "--postprocess", action="store_true", help="Enable postprocessing"
    )
    parser.add_argument("--plot", action="store_true", help="Enable plotting")
    parser.add_argument(
        "--extension",
        type=str,
        default="pdf",
        choices=["pdf", "png"],
        help="File extension for plots",
    )
    parser.add_argument(
        "--output_format",
        type=str,
        default="coffea",
        choices=["coffea", "root"],
        help="Format of output histograms",
    )
    return parser.parse_args()


def build_process_sample_map(dataset_configs):
    process_map = defaultdict(list)
    for sample, config in dataset_configs.items():
        process_map[config["process"]].append(sample)
    return process_map


def load_2016_histograms(workflow):
    aux_map = {
        "2016": ["2016preVFP", "2016postVFP"],
    }
    pre_year, post_year = aux_map["2016"]
    base_path = OUTPUT_DIR / workflow

    pre_file = base_path / pre_year / f"{pre_year}_processed_histograms{FILE_EXTENSION}"
    post_file = (
        base_path / post_year / f"{post_year}_processed_histograms{FILE_EXTENSION}"
    )
    return accumulate([load(pre_file), load(post_file)])


def load_histogram_file(path: Path):
    if not path.exists():
        return None
    return load(path)


def uncertainty_table(processed_histograms, workflow, year):
    to_accumulate = []
    for process in processed_histograms:
        if process != "Data":
            to_accumulate.append(processed_histograms[process])
    helper_histo = accumulate(to_accumulate)
    for key in helper_histo:
        for var in helper_histo[key].axes.name:
            if var != "variation":
                helper_key = var
                break
        break
    helper_histo = helper_histo[key].project(var, "variation")

    # get histogram per variation
    variation_hists = {}
    for variation in helper_histo.axes["variation"]:
        if variation == "nominal":
            nominal = helper_histo[{"variation": variation}]
        else:
            variation_hists[variation] = helper_histo[{"variation": variation}]

    # get variations names
    variations_keys = []
    for variation in variation_hists:
        if variation == "nominal":
            continue
        # get variation key
        variation_key = variation.replace("Up", "").replace("Down", "")
        if variation_key not in variations_keys:
            variations_keys.append(variation_key)

    variation_impact = {}
    nom = nominal.values()
    for variation in variations_keys:
        # up/down yields by bin
        varup = variation_hists[f"{variation}Up"].values()
        vardown = variation_hists[f"{variation}Down"].values()
        # concatenate σxup−nominal, σxdown−nominal, and 0
        up_and_down = np.stack([varup - nom, vardown - nom, np.zeros_like(nom)], axis=0)
        # max(σxup−nominal, σxdown−nominal, 0.) / nominal
        max_up_and_down = np.max(up_and_down, axis=0) / nom
        # min(σxup−nominal,σ xdown−nominal,0.) / nominal
        min_up_and_down = np.min(up_and_down, axis=0) / nom
        # integate over all bins
        variation_impact[variation] = [
            np.sqrt(np.sum(max_up_and_down**2)),
            np.sqrt(np.sum(min_up_and_down**2)),
        ]

    syst_df = pd.DataFrame(variation_impact).T * 100
    syst_df = syst_df.rename({0: "Up", 1: "Down"}, axis=1)
    return syst_df


if __name__ == "__main__":
    args = parse_arguments()

    output_dir = OUTPUT_DIR / args.workflow / args.year
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    clear_output_directory(str(output_dir), TXT_EXT)
    setup_logger(output_dir)

    config_builder = WorkflowConfigBuilder(workflow=args.workflow)
    workflow_config = config_builder.build_workflow_config()
    event_selection = workflow_config.event_selection
    categories = workflow_config.event_selection["categories"]
    processed_histograms = None

    if args.year == "2016":
        # load and accumulate processed 2016preVFP and 2016postVFP histograms
        processed_histograms = load_2016_histograms(args.workflow)
        identifier = "VFP"

        print_header(f"Systematic uncertainty impact")
        syst_df = uncertainty_table(processed_histograms, args.workflow, args.year)
        print(f"{OUTPUT_DIR / args.workflow / args.year}/uncertainty_table.csv")
        syst_df.to_csv(
            f"{OUTPUT_DIR / args.workflow / args.year}/uncertainty_table.csv"
        )
        logging.info(syst_df)
        logging.info("\n")

        for category in categories:
            logging.info(f"category: {category}")
            # load and combine results tables
            results_pre = pd.read_csv(
                OUTPUT_DIR
                / args.workflow
                / f"{args.year}pre{identifier}"
                / category
                / f"results_{category}.csv",
                index_col=0,
            )
            results_post = pd.read_csv(
                OUTPUT_DIR
                / args.workflow
                / f"{args.year}post{identifier}"
                / category
                / f"results_{category}.csv",
                index_col=0,
            )
            combined_results = combine_event_tables(results_pre, results_post)

            print_header(f"Results")
            logging.info(
                combined_results.applymap(lambda x: f"{x:.5f}" if pd.notnull(x) else "")
            )
            logging.info("\n")

            category_dir = OUTPUT_DIR / args.workflow / args.year / category
            if not category_dir.exists():
                category_dir.mkdir(parents=True, exist_ok=True)
            combined_results.to_csv(category_dir / f"results_{category}.csv")

            # save latex table
            latex_table = df_to_latex(combined_results)
            with open(category_dir / f"results_{category}.txt", "w") as f:
                f.write(latex_table)

            # load and combine cutflow tables
            print_header(f"Cutflow")
            cutflow_pre = pd.read_csv(
                OUTPUT_DIR
                / args.workflow
                / f"{args.year}pre{identifier}"
                / category
                / f"cutflow_{category}.csv",
                index_col=0,
            )
            cutflow_post = pd.read_csv(
                OUTPUT_DIR
                / args.workflow
                / f"{args.year}post{identifier}"
                / category
                / f"cutflow_{category}.csv",
                index_col=0,
            )
            combined_cutflow = combine_cutflows(cutflow_pre, cutflow_post)
            combined_cutflow.to_csv(category_dir / f"cutflow_{category}.csv")
            logging.info(
                combined_cutflow.applymap(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
            )

    if args.postprocess:
        logging.info(workflow_config.to_yaml())

        fileset_path = Path.cwd() / "analysis/filesets" / f"{args.year}_nanov9.yaml"
        with open(fileset_path, "r") as f:
            dataset_configs = yaml.safe_load(f)

        print_header(f"Reading outputs from: {output_dir}")

        extension = ".coffea"
        output_files = [
            i
            for i in glob.glob(f"{output_dir}/*/*{extension}", recursive=True)
            if not i.split("/")[-1].startswith("cutflow")
        ]
        process_samples_map = build_process_sample_map(dataset_configs)

        # group output file paths by sample name
        grouped_outputs = {}
        for output_file in output_files:
            sample_name = output_file.split("/")[-1].split(extension)[0]
            if sample_name.rsplit("_")[-1].isdigit():
                sample_name = "_".join(sample_name.rsplit("_")[:-1])
            sample_name = sample_name.replace(f"{args.year}_", "")
            if sample_name in grouped_outputs:
                grouped_outputs[sample_name].append(output_file)
            else:
                grouped_outputs[sample_name] = [output_file]

        for sample in grouped_outputs:
            save_process_histograms_by_sample(
                year=args.year,
                output_dir=output_dir,
                sample=sample,
                grouped_outputs=grouped_outputs,
                categories=categories,
            )
            gc.collect()

        for process in process_samples_map:
            save_process_histograms_by_process(
                year=args.year,
                output_dir=output_dir,
                process_samples_map=process_samples_map,
                process=process,
                categories=categories,
            )
            gc.collect()

        processed_histograms = load_processed_histograms(
            year=args.year,
            output_dir=output_dir,
            process_samples_map=process_samples_map,
        )

        print_header(f"Systematic uncertainty impact")
        syst_df = uncertainty_table(processed_histograms, args.workflow, args.year)
        syst_df.to_csv(f"{output_dir}/uncertainty_table.csv")
        logging.info(syst_df)
        logging.info("\n")

        for category in categories:
            logging.info(f"category: {category}")
            category_dir = Path(f"{output_dir}/{category}")

            print_header(f"Cutflow")
            cutflow_df = pd.DataFrame()
            for process in process_samples_map:
                cutflow_file = category_dir / f"cutflow_{category}_{process}.csv"
                cutflow_df = pd.concat(
                    [cutflow_df, pd.read_csv(cutflow_file, index_col=[0])], axis=1
                )

            cutflow_df["Total Background"] = cutflow_df.drop(columns="Data").sum(axis=1)

            cutflow_index = event_selection["categories"][category]
            cutflow_df = cutflow_df.loc[cutflow_index]

            cutflow_df = cutflow_df[
                ["Data", "Total Background"]
                + [
                    process
                    for process in cutflow_df.columns
                    if process not in ["Data", "Total Background"]
                ]
            ]
            logging.info(
                f'{cutflow_df.applymap(lambda x: f"{x:.3f}" if pd.notnull(x) else "")}\n'
            )
            cutflow_df.to_csv(f"{category_dir}/cutflow_{category}.csv")
            logging.info("\n")

            print_header(f"Results")
            results_df = get_results_report(processed_histograms, category)
            logging.info(
                results_df.applymap(lambda x: f"{x:.5f}" if pd.notnull(x) else "")
            )
            logging.info("\n")
            results_df.to_csv(f"{category_dir}/results_{category}.csv")

            latex_table = df_to_latex(results_df)
            with open(category_dir / f"results_{category}.txt", "w") as f:
                f.write(latex_table)

    if args.plot:
        if not args.postprocess and args.year != "2016":
            postprocess_file = (
                output_dir / f"{args.year}_processed_histograms{FILE_EXTENSION}"
            )
            processed_histograms = load_histogram_file(postprocess_file)
            if processed_histograms is None:
                cmd = f"python3 run_postprocess.py -w {args.workflow} -y {args.year} --postprocess"
                raise ValueError(
                    f"Postprocess file not found. Please run:\n  '{cmd}' first"
                )

        print_header("Plots")
        plotter = CoffeaPlotter(
            workflow=args.workflow,
            processed_histograms=processed_histograms,
            year=args.year,
            output_dir=output_dir,
        )

        for category in workflow_config.event_selection["categories"]:
            logging.info(f"Plotting histograms for category: {category}")
            for variable in workflow_config.histogram_config.variables:
                logging.info(variable)
                plotter.plot_histograms(
                    variable=variable,
                    category=category,
                    yratio_limits=args.yratio_limits,
                    log=args.log,
                    extension=args.extension,
                )
            subprocess.run(
                f"tar -zcvf {output_dir}/{category}/{args.workflow}_{args.year}_plots.tar.gz {output_dir}/{category}/*.{args.extension}",
                shell=True,
            )
