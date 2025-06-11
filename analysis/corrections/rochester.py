import numpy as np
import awkward as ak
from analysis.corrections.met import corrected_polar_met
from coffea.lookup_tools import txt_converters, rochester_lookup


def apply_rochester_corrections(events, year):
    # https://twiki.cern.ch/twiki/bin/viewauth/CMS/RochcorMuon
    rochester_data = txt_converters.convert_rochester_file(
        f"analysis/data/RoccoR{year}UL.txt", loaduncs=True
    )
    rochester = rochester_lookup.rochester_lookup(rochester_data)

    if hasattr(events, "genWeight"):
        hasgen = ~np.isnan(ak.fill_none(events.Muon.matched_gen.pt, np.nan))
        mc_rand = np.random.rand(*ak.to_numpy(ak.flatten(events.Muon.pt)).shape)
        mc_rand = ak.unflatten(mc_rand, ak.num(events.Muon.pt, axis=1))
        corrections = np.array(ak.flatten(ak.ones_like(events.Muon.pt)))
        mc_kspread = rochester.kSpreadMC(
            events.Muon.charge[hasgen],
            events.Muon.pt[hasgen],
            events.Muon.eta[hasgen],
            events.Muon.phi[hasgen],
            events.Muon.matched_gen.pt[hasgen],
        )
        mc_ksmear = rochester.kSmearMC(
            events.Muon.charge[~hasgen],
            events.Muon.pt[~hasgen],
            events.Muon.eta[~hasgen],
            events.Muon.phi[~hasgen],
            events.Muon.nTrackerLayers[~hasgen],
            mc_rand[~hasgen],
        )
        hasgen_flat = np.array(ak.flatten(hasgen))
        corrections[hasgen_flat] = np.array(ak.flatten(mc_kspread))
        corrections[~hasgen_flat] = np.array(ak.flatten(mc_ksmear))
        corrections = ak.unflatten(corrections, ak.num(events.Muon.pt, axis=1))

        errors = np.array(ak.flatten(ak.ones_like(events.Muon.pt)))
        errspread = rochester.kSpreadMCerror(
            events.Muon.charge[hasgen],
            events.Muon.pt[hasgen],
            events.Muon.eta[hasgen],
            events.Muon.phi[hasgen],
            events.Muon.matched_gen.pt[hasgen],
        )
        errsmear = rochester.kSmearMCerror(
            events.Muon.charge[~hasgen],
            events.Muon.pt[~hasgen],
            events.Muon.eta[~hasgen],
            events.Muon.phi[~hasgen],
            events.Muon.nTrackerLayers[~hasgen],
            mc_rand[~hasgen],
        )
        errors[hasgen_flat] = np.array(ak.flatten(errspread))
        errors[~hasgen_flat] = np.array(ak.flatten(errsmear))
        errors = ak.unflatten(errors, ak.num(events.Muon.pt, axis=1))
    else:
        corrections = rochester.kScaleDT(
            events.Muon.charge, events.Muon.pt, events.Muon.eta, events.Muon.phi
        )
        errors = rochester.kScaleDTerror(
            events.Muon.charge, events.Muon.pt, events.Muon.eta, events.Muon.phi
        )

    # Backup original pt and MET values
    events["Muon", "pt_raw"] = events.Muon.pt
    events["MET", "pt_raw"] = events.MET.pt
    events["MET", "phi_raw"] = events.MET.phi

    muons, counts, fields = events.Muon, ak.num(events.Muon), ak.fields(events.Muon)
    out = ak.flatten(muons)
    out_dict = dict({field: out[field] for field in fields})

    # Apply nominal correction
    corrected_pt = out.pt_raw * ak.flatten(corrections)
    out_dict["pt"] = corrected_pt

    # Compute Rochester-shifted pt values
    up = ak.flatten(muons)
    pt_up = up.pt_raw * ak.flatten(corrections) + ak.flatten(errors)
    up = ak.with_field(up, pt_up, where="pt")

    down = ak.flatten(muons)
    pt_down = down.pt_raw * ak.flatten(corrections) - ak.flatten(errors)
    down = ak.with_field(down, pt_down, where="pt")

    # Combine up/down shifts into RochesterSystematic structure
    out_dict["rochester"] = ak.zip(
        {"up": up, "down": down}, depth_limit=1, with_name="RochesterSystematic"
    )
    # Attach systematic field
    out_parms = out._layout.parameters
    out = ak.zip(out_dict, depth_limit=1, parameters=out_parms, behavior=out.behavior)
    events["Muon"] = ak.unflatten(out, counts)

    # Propagate corrections to MET
    met_pt, met_phi = corrected_polar_met(
        events.MET.pt_raw,
        events.MET.phi_raw,
        events.Muon.phi,
        events.Muon.pt_raw,
        events.Muon.pt,
    )
    events["MET", "pt"] = met_pt
    events["MET", "phi"] = met_phi

    # Propagate muon pt shifts to MET
    met_up_pt, met_up_phi = corrected_polar_met(
        events.MET.pt_raw,
        events.MET.phi_raw,
        events.Muon.phi,
        events.Muon.pt_raw,
        events.Muon.rochester.up.pt,
    )
    met_down_pt, met_down_phi = corrected_polar_met(
        events.MET.pt_raw,
        events.MET.phi_raw,
        events.Muon.phi,
        events.Muon.pt_raw,
        events.Muon.rochester.down.pt,
    )
    # Apply MET pt and phi shifts
    met_up = ak.with_field(events.MET, met_up_pt, where="pt")
    met_up = ak.with_field(met_up, met_up_phi, where="phi")

    met_down = ak.with_field(events.MET, met_down_pt, where="pt")
    met_down = ak.with_field(met_down, met_down_phi, where="phi")

    # Combine into METSystematic structure
    met_rochester_systematics = ak.zip(
        {"up": met_up, "down": met_down}, depth_limit=1, with_name="METSystematic"
    )
    # Attach to events.MET
    events["MET"] = ak.with_field(
        events.MET, met_rochester_systematics, where="rochester"
    )
