import yaml
import glob
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from coffea.util import load
from coffea.processor import accumulate
from analysis.workflows import WorkflowConfigBuilder
from analysis.postprocess.utils import print_header, df_to_latex




def get_variations_keys(processed_histograms):
    variations = {}
    for process, histogram_dict in processed_histograms.items():
        for feature in histogram_dict:
            helper_histogram = histogram_dict[feature]
            variations = [
                var
                for var in helper_histogram.axes["variation"]
                if var != "nominal"
            ]
            break
        break
    variations = list(
        set([var.replace("Up", "").replace("Down", "") for var in variations])
    )
    return variations



class CoffeaPostprocessor:
    def __init__(
        self,
        workflow: str,
        year: str,
        output_dir: str,
    ):
        self.workflow = workflow
        self.year = year
        self.output_dir = output_dir

        # get datasets configs
        main_dir = Path.cwd()
        fileset_path = Path(f"{main_dir}/analysis/filesets")
        with open(f"{fileset_path}/{year}_nanov9.yaml", "r") as f:
            self.dataset_config = yaml.safe_load(f)
        # get categories
        config_builder = WorkflowConfigBuilder(workflow=workflow)
        workflow_config = config_builder.build_workflow_config()
        self.categories = workflow_config.event_selection["categories"]
        # run postprocessor
        self.run_postprocess()

    def run_postprocess(self):
        print_header("grouping outputs by sample")
        self.group_outputs()

        print_header("scaling outputs by sample")
        self.set_lumixsec_weights()
        self.scale_histograms()
        self.scale_cutflow()

        print_header("grouping outputs by process")
        self.histograms = self.group_by_process(self.scaled_histograms)
        logging.info(
            yaml.dump(self.process_samples, sort_keys=False, default_flow_style=False)
        )

        print_header(f"Cutflow")
        for category in self.categories:
            output_path = Path(f"{self.output_dir}/{category}")
            if not output_path.exists():
                output_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"category: {category}")
            processed_cutflow = self.group_by_process(self.scaled_cutflow[category])
            self.cutflow_df = pd.DataFrame(processed_cutflow)
            # add total background events to cutflow
            self.cutflow_df["Total Background"] = self.cutflow_df.drop(
                columns="Data"
            ).sum(axis=1)
            # sort cutflow to show 'Data' and 'Total Background' first
            self.cutflow_df = self.cutflow_df[
                ["Data", "Total Background"]
                + [
                    process
                    for process in self.cutflow_df.columns
                    if process not in ["Data", "Total Background"]
                ]
            ]
            logging.info(
                f'{self.cutflow_df.applymap(lambda x: f"{x:.3f}" if pd.notnull(x) else "")}\n'
            )
            self.cutflow_df.to_csv(f"{output_path}/cutflow_{category}.csv")

        print_header(f"Results")
        for category in self.categories:
            output_path = Path(f"{self.output_dir}/{category}")
            logging.info(f"category: {category}")
            results_df = self.get_results_report(category)
            logging.info(
                results_df.applymap(lambda x: f"{x:.5f}" if pd.notnull(x) else "")
            )
            logging.info("\n")
            results_df.to_csv(f"{output_path}/results_{category}.csv")
            #latex_table = df_to_latex(results_df)
            #with open(f"{output_path}/results_latex_{category}.txt", "w") as f:
            #    f.write(latex_table)

    def group_outputs(self):
        """
        group and accumulate output files by sample
        """
        logging.info(f"reading outputs from {self.output_dir}")
        extension = ".coffea"
        output_files = glob.glob(f"{self.output_dir}/*/*{extension}", recursive=True)
        n_output_files = len(output_files)
        assert n_output_files != 0, "No output files found"

        # group output file paths by sample name
        grouped_outputs = {}
        for output_file in output_files:
            sample_name = output_file.split("/")[-1].split(extension)[0]
            if sample_name.rsplit("_")[-1].isdigit():
                sample_name = "_".join(sample_name.rsplit("_")[:-1])
            sample_name = sample_name.replace(f"{self.year}_", "")
            if sample_name in grouped_outputs:
                grouped_outputs[sample_name].append(output_file)
            else:
                grouped_outputs[sample_name] = [output_file]

        logging.info(f"{n_output_files} output files were found:")
        n_grouped_outputs = {}

        # open output dictionaries with layout:
        #      {<sample>_<i-th>: {"histograms": {"pt": Hist(...), ...}, "metadata": {"sumw": x, ...}}})
        # group and accumulate histograms and metadata by <sample>
        self.metadata = {}
        self.histograms = {}
        grouped_metadata = {}
        grouped_histograms = {}
        print_header("Reading and accumulating outputs by sample")
        for sample in grouped_outputs:
            logging.info(f"{sample}...")
            grouped_histograms[sample] = []
            grouped_metadata[sample] = {}
            for fname in grouped_outputs[sample]:
                output = load(fname)
                if output:
                    # group histograms by sample
                    grouped_histograms[sample].append(output["histograms"])
                    # group metadata by sample
                    for meta_key in output["metadata"]:
                        if meta_key in grouped_metadata[sample]:
                            grouped_metadata[sample][meta_key].append(
                                output["metadata"][meta_key]
                            )
                        else:
                            grouped_metadata[sample][meta_key] = [
                                output["metadata"][meta_key]
                            ]
            # accumulate histograms and metadata by sample
            self.histograms[sample] = accumulate(grouped_histograms[sample])
            self.metadata[sample] = {}
            for meta_key in grouped_metadata[sample]:
                self.metadata[sample][meta_key] = accumulate(
                    grouped_metadata[sample][meta_key]
                )

    def set_lumixsec_weights(self):
        print_header("Computing lumi-xsec weights")
        # load luminosities
        with open(f"{Path.cwd()}/analysis/postprocess/luminosity.yaml", "r") as f:
            self.luminosities = yaml.safe_load(f)
        logging.info(f"luminosity [/pb] {self.luminosities[self.year]}")
        # compute lumi-xsec weights
        self.weights = {}
        self.xsecs = {}
        self.sumw = {}
        for sample, metadata in self.metadata.items():
            self.weights[sample] = 1
            self.xsecs[sample] = self.dataset_config[sample]["xsec"]
            self.sumw[sample] = metadata["sumw"]
            if self.dataset_config[sample]["is_mc"]:
                self.weights[sample] = (
                    self.luminosities[self.year] * self.xsecs[sample]
                ) / self.sumw[sample]
        scale_info = pd.DataFrame(
            {
                "xsec [pb]": self.xsecs,
                "sumw": self.sumw,
                "weight": self.weights,
            }
        )
        logging.info(scale_info.applymap(lambda x: f"{x}" if pd.notnull(x) else ""))

    def scale_histograms(self):
        """scale histograms to lumi-xsec"""
        self.scaled_histograms = {}
        for sample, variables in self.histograms.items():
            # scale histograms
            self.scaled_histograms[sample] = {}
            for variable in variables:
                self.scaled_histograms[sample][variable] = (
                    self.histograms[sample][variable] * self.weights[sample]
                )

    def scale_cutflow(self):
        """scale cutflow to lumi-xsec"""
        self.scaled_cutflow = {}
        for category in self.categories:
            self.scaled_cutflow[category] = {}
            for sample, variables in self.histograms.items():
                self.scaled_cutflow[category][sample] = {}
                if category in self.metadata[sample]:
                    for cut, nevents in self.metadata[sample][category][
                        "cutflow"
                    ].items():
                        self.scaled_cutflow[category][sample][cut] = (
                            nevents * self.weights[sample]
                        )

    def group_by_process(self, to_group):
        """group and accumulate histograms by process"""
        group = {}
        self.process_samples = {}
        for sample in to_group:
            process = self.dataset_config[sample]["process"]
            if process not in group:
                group[process] = [to_group[sample]]
                self.process_samples[process] = [sample]
            else:
                group[process].append(to_group[sample])
                self.process_samples[process].append(sample)

        for process in group:
            group[process] = accumulate(group[process])

        return group

    def get_results_report(self, category):
        nominal = {}
        for process in self.histograms:
            for kin in self.histograms[process]:
                helper_hist = self.histograms[process][kin]
                nominal_hist = helper_hist[{"variation":"nominal"}]
                for variable in nominal_hist.axes.name:
                    helper_variable = variable
                    nominal[process] = nominal_hist.project(helper_variable)
                    break
                break
        
        variations = {}
        mcstat_err = {}
        bin_error_up = {}
        bin_error_down = {}
        for process in self.histograms:
            if process == "Data":
                continue
            mcstat_err[process] = {}
            bin_error_up[process] = {}
            bin_error_down[process] = {}
            nom = nominal[process].values()
            mcstat_err2 = nominal[process].variances()
            mcstat_err[process] = np.sum(np.sqrt(mcstat_err2))
            err2_up = mcstat_err2
            err2_down = mcstat_err2
            for variation in get_variations_keys(self.histograms):
                var_cats = [v for v in helper_hist.axes["variation"]]
                if not f"{variation}Up" in var_cats:
                    continue
                var_up = helper_hist[{"variation": f"{variation}Up"}].project(helper_variable).values()
                var_down = helper_hist[{"variation": f"{variation}Down"}].project(helper_variable).values()
                # Compute the uncertainties corresponding to the up/down variations
                err_up = var_up -nom
                err_down = var_down - nom
                # Compute the flags to check which of the two variations (up and down) are pushing the nominal value up and down
                up_is_up = err_up > 0
                down_is_down = err_down < 0
                # Compute the flag to check if the uncertainty is one-sided, i.e. when both variations are up or down
                is_onesided = up_is_up ^ down_is_down
                # Sum in quadrature of the systematic uncertainties taking into account if the uncertainty is one- or double-sided
                err2_up_twosided = np.where(up_is_up, err_up**2, err_down**2)
                err2_down_twosided = np.where(up_is_up, err_down**2, err_up**2)
                err2_max = np.maximum(err2_up_twosided, err2_down_twosided)
                err2_up_onesided = np.where(is_onesided & up_is_up, err2_max, 0)
                err2_down_onesided = np.where(is_onesided & down_is_down, err2_max, 0)
                err2_up_combined = np.where(is_onesided, err2_up_onesided, err2_up_twosided)
                err2_down_combined = np.where(
                    is_onesided, err2_down_onesided, err2_down_twosided
                )
                # Sum in quadrature of the systematic uncertainty corresponding to a MC sample
                err2_up += err2_up_combined
                err2_down += err2_down_combined
                
            bin_error_up[process] = np.sum(np.sqrt(err2_up))
            bin_error_down[process] = np.sum(np.sqrt(err2_down))
        
        mcs = []
        results = {}
        for process in nominal:
            results[process] = {}
            
            results[process]["events"] = np.sum(nominal[process].values())
            if process == "Data":
                results[process]["stat err"] = np.sqrt(np.sum(nominal[process].values()))
            else:
                mcs.append(process)
                results[process]["stat err"] = mcstat_err[process]
                results[process]["syst err"] = (bin_error_up[process] + bin_error_down[process]) / 2
        df = pd.DataFrame(results)
        df["Total background"] = df.loc[["events"], mcs].sum(axis=1)
        df.loc["stat err", "Total background"] = np.sqrt(np.sum(df.loc["stat err", mcs]**2))
        df.loc["syst err", "Total background"] = np.sqrt(np.sum(df.loc["syst err", mcs]**2))
        df = df.T
        df.loc["Data/Total background"] = df.loc["Data", ["events"]] / df.loc["Total background", ["events"]]
        return df
