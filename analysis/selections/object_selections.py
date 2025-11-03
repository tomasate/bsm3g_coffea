import vector
import numpy as np
import awkward as ak
from analysis.working_points import working_points
from analysis.selections import delta_r_mask, select_dileptons, select_dileptons_qcd


class ObjectSelector:

    def __init__(self, object_selection_config, year, run):
        self.object_selection_config = object_selection_config
        self.year = year
        self.run = run

    def select_objects(self, events):
        self.objects = {}
        self.events = events

        for obj_name, obj_config in self.object_selection_config.items():
            # check if object is defined from events or user defined function
            if "events" in obj_config["field"]:
                self.objects[obj_name] = eval(obj_config["field"])
            else:
                selection_function = getattr(self, obj_config["field"])
                selection_function(obj_name)
            if "add_cut" in obj_config:
                for field_to_add in obj_config["add_cut"]:
                    selection_mask = self.get_selection_mask(
                        events=events,
                        obj_name=obj_name,
                        cuts=obj_config["add_cut"][field_to_add],
                    )
                    self.objects[obj_name][field_to_add] = selection_mask
            if "add_field" in obj_config:
                for field_name, field_to_add in obj_config["add_field"].items():
                    self.objects[obj_name][field_name] = eval(field_to_add)
            if "cuts" in obj_config:
                selection_mask = self.get_selection_mask(
                    events=events, obj_name=obj_name, cuts=obj_config["cuts"]
                )
                self.objects[obj_name] = self.objects[obj_name][selection_mask]
        return self.objects

    def get_selection_mask(self, events, obj_name, cuts):
        # bring objects and year to local scope
        objects = self.objects
        year = self.year
        # initialize selection mask
        selection_mask = ak.ones_like(self.objects[obj_name].pt, dtype=bool)
        # iterate over all cuts
        for str_mask in cuts:
            mask = eval(str_mask)
            selection_mask = np.logical_and(selection_mask, mask)
        return selection_mask

    # --------------------------------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------------------------------
    def select_dimuons(self, obj_name):
        if "muons" not in self.objects:
            raise ValueError(f"'muons' object has not been defined!")
        self.objects[obj_name] = select_dileptons(self.objects, "muons")

    def select_dielectrons(self, obj_name):
        if "electrons" not in self.objects:
            raise ValueError(f"'electrons' object has not been defined!")
        self.objects[obj_name] = select_dileptons(self.objects, "electrons")

    def select_met(self, obj_name):
        if self.run == "2":
            met = self.events.MET
        else:
            met = self.events.PuppiMET
        self.objects[obj_name] = met

    def select_dimuons_qcd(self, obj_name):
        if "muons" not in self.objects:
            raise ValueError(f"'muons' object has not been defined!")
        self.objects[obj_name] = select_dileptons_qcd(self.objects, "muons")

    def select_dielectrons_qcd(self, obj_name):
        if "electrons" not in self.objects:
            raise ValueError(f"'electrons' object has not been defined!")
        self.objects[obj_name] = select_dileptons_qcd(self.objects, "electrons")

    # --------------------------------------------------------------------------------
    # SUSY VBF
    # --------------------------------------------------------------------------------
    def select_dijets(self, obj_name):
        # create pair combinations with all jets (VBF selection)
        dijets = ak.combinations(self.objects["jets"], 2, fields=["j1", "j2"])
        # add dijet 4-momentum field
        dijets["p4"] = dijets.j1 + dijets.j2
        dijets["pt"] = dijets.p4.pt
        self.objects[obj_name] = dijets

    def select_max_mass_dijet(self, obj_name):
        self.objects[obj_name] = ak.max(self.objects["dijets"].p4.mass, axis=1)

    def select_max_mass_dijet_eta(self, obj_name):
        dijets_idx = ak.local_index(self.objects["dijets"], axis=1)
        max_mass_idx = ak.argmax(self.objects["dijets"].p4.mass, axis=1)
        max_mass_dijet = self.objects["dijets"][max_mass_idx == dijets_idx]
        self.objects[obj_name] = ak.firsts(
            np.abs(max_mass_dijet.j1.eta - max_mass_dijet.j2.eta)
        )

    def select_ztojets_met(self, obj_name):
        # add muons pT to MET to simulate a 0-lepton final state
        all_muons = ak.sum(self.objects["muons"], axis=1)
        muons2D = ak.zip(
            {
                "pt": all_muons.pt,
                "phi": all_muons.phi,
            },
            with_name="Momentum2D",
            behavior=vector.backends.awkward.behavior,
        )
        if self.run == "2":
            met = self.events.MET
        else:
            met = self.events.PuppiMET
        met2D = ak.zip(
            {
                "pt": met.pt,
                "phi": met.phi,
            },
            with_name="Momentum2D",
            behavior=vector.backends.awkward.behavior,
        )
        self.objects[obj_name] = met2D + muons2D
