import logging
from pathlib import Path
from coffea.util import save, load
from analysis.workflows import WorkflowConfigBuilder
from analysis.postprocess.root_plotter import ROOTPlotter
from analysis.postprocess.root_postprocessor import ROOTPostprocessor
from analysis.postprocess.coffea_plotter import CoffeaPlotter
from analysis.postprocess.coffea_postprocessor import CoffeaPostprocessor
from analysis.postprocess.utils import (
    print_header,
    setup_logger,
    clear_output_directory,
)

from coffea import processor as cp

def coffea_postprocess(
    postprocess: bool,
    plot: bool,
    workflow: str,
    year: str,
    yratio_limits: tuple,
    log: bool,
    extension: str,
):
    # load and save workflow config
    config_builder = WorkflowConfigBuilder(workflow=workflow)
    workflow_config = config_builder.build_workflow_config()

    output_dir = Path.cwd() / "outputs" / workflow / year
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    clear_output_directory(str(output_dir), "txt")
    setup_logger(output_dir)

    if year in ["2022", "2023"]:
        aux_map = {
            "2022": ["2022preEE", "2022postEE"],
            "2023": ["2023preBPix", "2023postBPix"]
        }
        pre_file = Path.cwd() / "outputs" / workflow / aux_map[year][0] / f"{workflow}_{aux_map[year][0]}_processed_histograms.coffea"
        pos_file = Path.cwd() / "outputs" / workflow / aux_map[year][1] / f"{workflow}_{aux_map[year][1]}_processed_histograms.coffea"
        processed_histograms = cp.accumulate([load(pre_file), load(pos_file)])

    if postprocess:
        logging.info(workflow_config.to_yaml())
        # process (group and accumulate) outputs
        postprocessor = CoffeaPostprocessor(
            workflow=workflow,
            year=year,
            output_dir=output_dir,
        )
        processed_histograms = postprocessor.histograms
        save(
            processed_histograms,
            f"{output_dir}/{workflow}_{year}_processed_histograms.coffea",
        )

    if plot:
        if not postprocess:
            if year not in ["2022", "2023"]:
                postprocess_path = Path(
                    f"{output_dir}/{workflow}_{year}_processed_histograms.coffea"
                )
                if not postprocess_path.exists():
                    postprocess_cmd = f"python3 run_postprocess.py --workflow {workflow} --year {year} --output_format coffea --postprocess --plot"
                    raise ValueError(
                        f"Postprocess dict have not been generated. Please run '{postprocess_cmd}'"
                    )
                processed_histograms = load(postprocess_path)
        # plot processed histograms
        print_header("Plots")
        plotter = CoffeaPlotter(
            workflow=workflow,
            processed_histograms=processed_histograms,
            year=year,
            output_dir=output_dir,
        )
        for category in workflow_config.event_selection["categories"]:
            logging.info(f"plotting histograms for category: {category}")
            for variable in workflow_config.histogram_config.variables:
                logging.info(variable)
                plotter.plot_histograms(
                    variable=variable,
                    category=category,
                    yratio_limits=yratio_limits,
                    log=log,
                    extension=extension,
                )


def root_postprocess(
    postprocess: bool,
    plot: bool,
    workflow: str,
    year: str,
    yratio_limits: tuple,
    log: bool,
    extension: str,
):
    # load workflow config
    config_builder = WorkflowConfigBuilder(workflow=workflow, year=year)
    workflow_config = config_builder.build_workflow_config()
    # do postprocessing for each selection category
    for category in workflow_config.event_selection["categories"]:
        output_dir = Path.cwd() / "outputs" / workflow / year / category
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        clear_output_directory(str(output_dir), "txt")
        setup_logger(str(output_dir))
        if postprocess:
            logging.info(workflow_config.to_yaml())
            clear_output_directory(output_dir, "pkl")
            clear_output_directory(output_dir.parent, "root")
            postprocessor = ROOTPostworkflow(
                workflow=processor,
                year=year,
                category=category,
                output_dir=output_dir,
            )
            postprocessor.run_postprocess()
            processed_histograms = postprocessor.proccesed_histograms
            save(
                processed_histograms,
                f"{output_dir}/{category}_{workflow}_{year}_processed_histograms.coffea",
            )

        if plot:
            if not postprocess:
                postprocess_path = Path(
                    f"{output_dir}/{category}_{workflow}_{year}_processed_histograms.coffea"
                )
                if not postprocess_path.exists():
                    postprocess_cmd = f"python3 run_postprocess.py --workflow {workflow} --year {year} --output_format root --postprocess --plot"
                    raise ValueError(
                        f"Postprocess dict have not been generated. Please run '{postprocess_cmd}'"
                    )
                processed_histograms = load(postprocess_path)
            plotter = ROOTPlotter(
                workflow=workflow,
                year=year,
                processed_histograms=processed_histograms,
                output_dir=output_dir,
            )
            print_header("Plots")
            logging.info(f"plotting histograms for category: {category}")
            for variable in workflow_config.histogram_config.variables:
                has_variable = False
                for v in processed_histograms["Data"]:
                    if variable in v:
                        has_variable = True
                        break
                if has_variable:
                    logging.info(variable)
                    plotter.plot_histograms(
                        variable=variable,
                        category=category,
                        yratio_limits=yratio_limits,
                        log=log,
                        extension=extension,
                    )
