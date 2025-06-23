import copy
import numpy as np
import awkward as ak
from coffea import processor
from coffea.analysis_tools import PackedSelection, Weights
from analysis.workflows.config import WorkflowConfigBuilder
from analysis.histograms import HistBuilder, fill_histograms
from analysis.corrections import (
    object_corrector_manager,
    weight_manager,
)
from analysis.selections import (
    ObjectSelector,
    get_lumi_mask,
    get_trigger_mask,
    get_trigger_match_mask,
    get_metfilters_mask,
    get_stitching_mask,
    get_hemcleaning_mask,
)
from analysis.corrections.jetvetomaps import apply_jetvetomaps


def update(events, collections):
    """Return a shallow copy of events array with some collections swapped out"""
    out = events
    for name, value in collections.items():
        out = ak.with_field(out, value, name)
    return out


class BaseProcessor(processor.ProcessorABC):
    def __init__(
        self,
        workflow: str,
        year: str = "2017",
    ):
        year_key_map = {
            "2016preVFP": "2016",
            "2016postVFP": "2016",
            "2022preEE": "2022",
            "2022postEE": "2022",
            "2023preBPix": "2023",
            "2023postBPix": "2023",
        }
        self.year = year
        self.year_key = year_key_map.get(year, year)
        self.run_key = "Run3" if self.year_key in ["2022", "2023"] else "Run2"

        config_builder = WorkflowConfigBuilder(workflow=workflow)
        self.workflow_config = config_builder.build_workflow_config()
        self.histogram_config = self.workflow_config.histogram_config
        self.histograms = HistBuilder(self.workflow_config).build_histogram()

        self.flow = self.histogram_config.flow
        self.apply_obj_syst = self.workflow_config.corrections_config["apply_obj_syst"]

    def process(self, events):
        # correct objects
        object_corrector_manager(
            events=events,
            year=self.year,
            workflow_config=self.workflow_config,
            dataset=events.metadata["dataset"],
        )
        # check if sample is MC
        self.is_mc = hasattr(events, "genWeight")
        if not self.is_mc:
            return self.process_shift(events, shift_name="nominal")

        # define object-level shifts
        shifts = [({"Jet": events.Jet, "MET": events.MET, "Muon": events.Muon, "Tau": events.Tau}, "nominal")]
        if self.apply_obj_syst:
            if self.run_key == "Run2":
                shifts.extend(
                    [
                        ({"Jet": events.Jet, "MET": events.MET.rochester.up, "Muon": events.Muon.rochester.up, "Tau": events.Tau}, f"CMS_rochester_{self.year_key}Up"),
                        ({"Jet": events.Jet, "MET": events.MET.rochester.down, "Muon": events.Muon.rochester.down, "Tau": events.Tau}, f"CMS_rochester_{self.year_key}Down"),
                        ({"Jet": events.Jet.JES_jes.up, "MET": events.MET.JES_jes.up, "Muon": events.Muon, "Tau": events.Tau}, f"CMS_scale_j_{self.year_key}Up"),
                        ({"Jet": events.Jet.JES_jes.down, "MET": events.MET.JES_jes.down, "Muon": events.Muon, "Tau": events.Tau}, f"CMS_scale_j_{self.year_key}Down"),
                        ({"Jet": events.Jet.JER.up, "MET": events.MET.JER.up, "Muon": events.Muon, "Tau": events.Tau}, f"CMS_res_j_{self.year_key}Up"),
                        ({"Jet": events.Jet.JER.down, "MET": events.MET.JER.down, "Muon": events.Muon, "Tau": events.Tau}, f"CMS_res_j_{self.year_key}Down"),
                        ({"Jet": events.Jet, "MET": events.MET.MET_UnclusteredEnergy.up, "Muon": events.Muon, "Tau": events.Tau}, f"CMS_met_unclustered_{self.year_key}Up"),
                        ({"Jet": events.Jet, "MET": events.MET.MET_UnclusteredEnergy.down, "Muon": events.Muon, "Tau": events.Tau}, f"CMS_met_unclustered_{self.year_key}Down"),
                        ({"Jet": events.Jet, "MET": events.MET.tau_energy.up, "Muon": events.Muon, "Tau": events.Tau.tau_energy.up}, f"CMS_t_energy_{self.year_key}Up"),
                        ({"Jet": events.Jet, "MET": events.MET.tau_energy.down, "Muon": events.Muon, "Tau": events.Tau.tau_energy.down}, f"CMS_t_energy_{self.year_key}Down"),
                    ]
                )
        return processor.accumulate(
            self.process_shift(update(events, collections), name)
            for collections, name in shifts
        )

    def process_shift(self, events, shift_name):
        year = self.year
        is_mc = self.is_mc
        # get number of events
        nevents = len(events)
        # get dataset name
        dataset = events.metadata["dataset"]
        # get object and event selection configs
        object_selection = self.workflow_config.object_selection
        event_selection = self.workflow_config.event_selection
        hlt_paths = event_selection["hlt_paths"]
        # create copies of histogram objects
        histograms = copy.deepcopy(self.histograms)
        # initialize output dictionary
        output = {}
        output["metadata"] = {}
        if shift_name == "nominal":
            # save sum of weights before object_selection
            sumw = ak.sum(events.genWeight) if is_mc else len(events)
            output["metadata"].update({"sumw": sumw})

        # -------------------------------------------------------------
        # object selection
        # -------------------------------------------------------------
        if "jets_veto" in self.workflow_config.corrections_config["objects"]:
            # apply jet veto maps and update missing energy
            apply_jetvetomaps(events, year)

        object_selector = ObjectSelector(object_selection, year)
        objects = object_selector.select_objects(events)
        # -------------------------------------------------------------
        # event selection
        # -------------------------------------------------------------
        # itinialize selection manager
        selection_manager = PackedSelection()
        # add all selections to selector manager
        for selection, mask in event_selection["selections"].items():
            selection_manager.add(selection, eval(mask))
        # --------------------------------------------------------------
        # Histogram filling
        # --------------------------------------------------------------
        categories = event_selection["categories"]
        for category, category_cuts in categories.items():
            # get selection mask by category
            category_mask = selection_manager.all(*category_cuts)
            nevents_after = ak.sum(category_mask)
            if nevents_after > 0:
                # get pruned events
                pruned_ev = events[category_mask]
                # add each selected object to 'pruned_ev' as a new field
                for obj in objects:
                    pruned_ev[f"selected_{obj}"] = objects[obj][category_mask]
                # get weights container
                weights_container = weight_manager(
                    pruned_ev=pruned_ev,
                    year=year,
                    workflow_config=self.workflow_config,
                    variation=shift_name,
                    dataset=dataset,
                )
                if shift_name == "nominal":
                    # save cutflow to metadata
                    output["metadata"][category] = {"cutflow": {"initial": sumw}}
                    selections = []
                    for cut_name in category_cuts:
                        selections.append(cut_name)
                        current_selection = selection_manager.all(*selections)
                        pruned_ev_cutflow = events[current_selection]
                        for obj in objects:
                            pruned_ev_cutflow[f"selected_{obj}"] = objects[obj][
                                current_selection
                            ]
                        weights_container_cutflow = weight_manager(
                            pruned_ev=pruned_ev_cutflow,
                            year=year,
                            workflow_config=self.workflow_config,
                            variation="nominal",
                            dataset=dataset,
                        )
                        output["metadata"][category]["cutflow"][cut_name] = ak.sum(
                            weights_container_cutflow.weight()
                        )
                    # save number of events after selection to metadata
                    weighted_final_nevents = ak.sum(weights_container.weight())
                    output["metadata"][category].update(
                        {"weighted_final_nevents": weighted_final_nevents}
                    )
                # get analysis variables and fill histograms
                variables_map = {}
                for variable, axis in self.histogram_config.axes.items():
                    variables_map[variable] = eval(axis.expression)[category_mask]
                fill_histograms(
                    histogram_config=self.histogram_config,
                    weights_container=weights_container,
                    variables_map=variables_map,
                    histograms=histograms,
                    shift_name=shift_name,
                    category=category,
                    is_mc=is_mc,
                    flow=self.flow,
                )
        # define output dictionary accumulator
        output["histograms"] = histograms
        return output

    def postprocess(self, accumulator):
        return accumulator
