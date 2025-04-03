import numpy as np
import awkward as ak
from analysis.selections import delta_r_mask
from analysis.working_points import working_points


class ObjectSelector:

    def __init__(self, object_selection_config, year):
        self.object_selection_config = object_selection_config
        self.year = year

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