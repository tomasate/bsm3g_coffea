import copy
import correctionlib
import numpy as np
import awkward as ak
from analysis.corrections.utils import get_pog_json
from analysis.corrections.met import corrected_polar_met

# ----------------------------------------------------------------------------------- #
# -- The tau energy scale (TES) corrections for taus are provided  ------------------ #
# --  to be applied to reconstructed tau_h Lorentz vector ----------------------------#
# --  It should be applied to a genuine tau -> genmatch = 5 --------------------------#
# -----------  (pT, mass and energy) in simulated data -------------------------------#
# tau_E  *= tes
# tau_pt *= tes
# tau_m  *= tes
# https://github.com/cms-tau-pog/TauIDsfs/tree/master
# ----------------------------------------------------------------------------------- #


def mask_energy_corrections(tau):
    # https://github.com/cms-tau-pog/TauFW/blob/4056e9dec257b9f68d1a729c00aecc8e3e6bf97d/PicoProducer/python/analysis/ETauFakeRate/ModuleETau.py#L320
    # https://gitlab.cern.ch/cms-tau-pog/jsonpog-integration/-/blob/TauPOG_v2/POG/TAU/scripts/tau_tes.py

    tau_mask_gm = (
        (tau.genPartFlav == 5)  # Genuine tau
        | (tau.genPartFlav == 1)  # e -> fake
        | (tau.genPartFlav == 2)  # mu -> fake
        | (tau.genPartFlav == 6)  # unmached
    )
    tau_mask_dm = (
        (tau.decayMode == 0)
        | (tau.decayMode == 1)  # 1 prong
        | (tau.decayMode == 2)  # 1 prong
        | (tau.decayMode == 10)  # 1 prong
        | (tau.decayMode == 11)  # 3 prongs  # 3 prongs
    )
    tau_eta_mask = (tau.eta >= 0) & (tau.eta < 2.5)
    tau_mask = tau_mask_gm & tau_mask_dm  # & tau_eta_mask
    return tau_mask


def apply_tau_energy_scale_corrections(events, year):
    # define tau pt_raw field
    events["Tau", "pt_raw"] = ak.ones_like(events.Tau.pt) * events.Tau.pt
    events["Tau", "mass_raw"] = ak.ones_like(events.Tau.mass) * events.Tau.mass

    # corrections works with flatten values
    out = ak.flatten(events.Tau)
    counts = ak.num(events.Tau)
    fields = ak.fields(events.Tau)
    out_dict = dict({field: out[field] for field in fields})

    # it is defined the taus will be corrected with the energy scale factor: Only a subset of the initial taus.
    mask = mask_energy_corrections(out)
    taus_filter = out.mask[mask]

    # fill None values with valid entries
    pt = ak.fill_none(taus_filter.pt_raw, 0)
    eta = ak.fill_none(taus_filter.eta, 0)
    dm = ak.fill_none(taus_filter.decayMode, 0)
    genmatch = ak.fill_none(taus_filter.genPartFlav, 2)

    # define correction set
    cset = correctionlib.CorrectionSet.from_file(
        get_pog_json(json_name="tau", year=year)
    )
    # get scale factors
    sf = cset["tau_energy_scale"].evaluate(
        pt, eta, dm, genmatch, "DeepTau2017v2p1", "nom"
    )
    sf_up = cset["tau_energy_scale"].evaluate(
        pt, eta, dm, genmatch, "DeepTau2017v2p1", "up"
    )
    sf_down = cset["tau_energy_scale"].evaluate(
        pt, eta, dm, genmatch, "DeepTau2017v2p1", "down"
    )
    # set new (pT, mass) values using the scale factor
    out_dict["pt"] = ak.where(mask, taus_filter.pt_raw * sf, out.pt_raw)
    out_dict["mass"] = ak.where(mask, taus_filter.mass_raw * sf, out.mass_raw)

    # Compute variations
    up = ak.flatten(events.Tau)
    up = ak.with_field(
        up, ak.where(mask, taus_filter.pt_raw * sf_up, out.pt_raw), where="pt"
    )
    up = ak.with_field(
        up, ak.where(mask, taus_filter.mass_raw * sf_up, out.mass_raw), where="mass"
    )

    down = ak.flatten(events.Tau)
    down = ak.with_field(
        down, ak.where(mask, taus_filter.pt_raw * sf_down, out.pt_raw), where="pt"
    )
    down = ak.with_field(
        down, ak.where(mask, taus_filter.mass_raw * sf_down, out.mass_raw), where="mass"
    )

    # Combine up/down shifts
    out_dict["tau_energy"] = ak.zip(
        {"up": up, "down": down}, depth_limit=1, with_name="TauSystematic"
    )
    # Attach systematic field
    out_parms = out._layout.parameters
    out = ak.zip(out_dict, depth_limit=1, parameters=out_parms, behavior=out.behavior)
    events["Tau"] = ak.unflatten(out, counts)

    # propagate tau pT corrections to MET
    corrected_met_pt, corrected_met_phi = corrected_polar_met(
        met_pt=events.MET.pt,
        met_phi=events.MET.phi,
        other_phi=events.Tau.phi,
        other_pt_old=events.Tau.pt_raw,
        other_pt_new=events.Tau.pt,
    )
    # update MET fields
    events["MET", "pt"] = corrected_met_pt
    events["MET", "phi"] = corrected_met_phi

    # Propagate muon pt shifts to MET
    met_up_pt, met_up_phi = corrected_polar_met(
        events.MET.pt_raw,
        events.MET.phi_raw,
        events.Tau.phi,
        events.Tau.pt_raw,
        events.Tau.tau_energy.up.pt,
    )
    met_down_pt, met_down_phi = corrected_polar_met(
        events.MET.pt_raw,
        events.MET.phi_raw,
        events.Tau.phi,
        events.Tau.pt_raw,
        events.Tau.tau_energy.down.pt,
    )
    # Apply MET pt and phi shifts
    met_up = ak.with_field(events.MET, met_up_pt, where="pt")
    met_up = ak.with_field(met_up, met_up_phi, where="phi")

    met_down = ak.with_field(events.MET, met_down_pt, where="pt")
    met_down = ak.with_field(met_down, met_down_phi, where="phi")

    # Combine into METSystematic structure
    met_tau_systematics = ak.zip(
        {"up": met_up, "down": met_down}, depth_limit=1, with_name="METSystematic"
    )
    # Attach to events.MET
    events["MET"] = ak.with_field(events.MET, met_tau_systematics, where="tau_energy")