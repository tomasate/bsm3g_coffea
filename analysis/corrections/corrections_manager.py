import numpy as np
from coffea.analysis_tools import Weights
from analysis.corrections import (
    TauCorrector,
    BTagCorrector,
    MuonCorrector,
    ElectronCorrector,
    MuonHighPtCorrector,
    add_pileup_weight,
    add_pujetid_weight,
    apply_jet_corrections,
    add_l1prefiring_weight,
    apply_met_phi_corrections,
    apply_rochester_corrections,
    apply_tau_energy_scale_corrections,
)


def object_corrector_manager(events, year, processor_config, variation="nominal"):
    """apply object level corrections"""
    objcorr_config = processor_config.corrections_config["objects"]
    if "jets" in objcorr_config:
        # apply JEC/JER corrections to jets (in data, the corrections are already applied)
        apply_jet_corrections(events, year)
    if "muons" in objcorr_config:
        # apply rochester corretions to muons
        apply_rochester_corrections(events=events, year=year, variation=variation)
    if "taus" in objcorr_config:
        if hasattr(events, "genWeight"):
            # apply energy corrections to taus (only to MC)
            apply_tau_energy_scale_corrections(
                events=events, year=year, variation=variation
            )
    if "met" in objcorr_config:
        # apply MET phi modulation corrections
        apply_met_phi_corrections(
            events=events,
            year=year,
        )


def weight_manager(pruned_ev, year, processor_config, variation="nominal"):
    """apply event level corrections (weights)"""
    # get weights config info
    weights_config = processor_config.corrections_config["event_weights"]
    # initialize weights container
    weights_container = Weights(len(pruned_ev), storeIndividual=True)
    # add weights
    if hasattr(pruned_ev, "genWeight"):
        if weights_config["genWeight"]:
            weights_container.add("genweight", pruned_ev.genWeight)

        if weights_config["l1prefiring"]:
            add_l1prefiring_weight(pruned_ev, weights_container, year, variation)

        if weights_config["pileupWeight"]:
            add_pileup_weight(pruned_ev, weights_container, year, variation)

        if weights_config["pujetid"]:
            add_pujetid_weight(
                events=pruned_ev,
                weights=weights_container,
                year=year,
                working_point=weights_config["pujetid"]["id"],
                variation=variation,
            )
        if weights_config["btagging"]:
            btag_corrector = BTagCorrector(
                events=pruned_ev,
                weights=weights_container,
                sf_type="comb",
                worging_point=weights_config["btagging"]["id"],
                year=year,
                full_run=weights_config["btagging"]["full_run"],
                variation=variation,
            )
            if weights_config["btagging"]["bc"]:
                btag_corrector.add_btag_weights(flavor="bc")
            if weights_config["btagging"]["light"]:
                btag_corrector.add_btag_weights(flavor="light")

        if "electron" in weights_config:
            if "selected_electrons" in pruned_ev.fields:
                electron_corrector = ElectronCorrector(
                    events=pruned_ev,
                    weights=weights_container,
                    year=year,
                )
                if "id" in weights_config["electron"]:
                    if weights_config["electron"]["id"]:
                        electron_corrector.add_id_weight(
                            id_working_point=weights_config["electron"]["id"]
                        )
                if "reco" in weights_config["electron"]:
                    if weights_config["electron"]["reco"]:
                        electron_corrector.add_reco_weight("RecoAbove20")
                        electron_corrector.add_reco_weight("RecoBelow20")

        if "muon" in weights_config:
            if "selected_muons" in pruned_ev.fields:
                muon_corrector_args = {
                    "events": pruned_ev,
                    "weights": weights_container,
                    "year": year,
                    "variation": variation,
                    "id_wp": weights_config["muon"]["id"],
                    "iso_wp": weights_config["muon"]["iso"],
                }
                muon_corrector = (
                    MuonHighPtCorrector(**muon_corrector_args)
                    if weights_config["muon"]["id"] == "highpt"
                    else MuonCorrector(**muon_corrector_args)
                )
                if "id" in weights_config["muon"]:
                    if weights_config["muon"]["id"]:
                        muon_corrector.add_id_weight()
                if "reco" in weights_config["muon"]:
                    if weights_config["muon"]["reco"]:
                        muon_corrector.add_reco_weight()
                if "iso" in weights_config["muon"]:
                    if weights_config["muon"]["iso"]:
                        muon_corrector.add_iso_weight()
                if "trigger" in weights_config["muon"]:
                    if weights_config["muon"]["trigger"]:
                        muon_corrector.add_triggeriso_weight(
                            processor_config.event_selection["hlt_paths"]
                        )

        if "tau" in weights_config:
            if "selected_taus" in pruned_ev.fields:
                tau_corrector = TauCorrector(
                    events=pruned_ev,
                    weights=weights_container,
                    year=year,
                    tau_vs_jet=weights_config["tau"]["taus_vs_jet"],
                    tau_vs_ele=weights_config["tau"]["taus_vs_ele"],
                    tau_vs_mu=weights_config["tau"]["taus_vs_mu"],
                    variation=variation,
                )
                if "taus_vs_jet" in weights_config["tau"]:
                    if weights_config["tau"]["taus_vs_jet"]:
                        tau_corrector.add_id_weight_deeptauvsjet()
                if "taus_vs_ele" in weights_config["tau"]:
                    if weights_config["tau"]["taus_vs_ele"]:
                        tau_corrector.add_id_weight_deeptauvse()
                if "taus_vs_mu" in weights_config["tau"]:
                    if weights_config["tau"]["taus_vs_mu"]:
                        tau_corrector.add_id_weight_deeptauvsmu()

    else:
        weights_container.add("weight", np.ones(len(pruned_ev)))
    return weights_container
