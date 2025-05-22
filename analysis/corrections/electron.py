import json
import copy
import correctionlib
import numpy as np
import awkward as ak
import importlib.resources
from typing import Type
from pathlib import Path
from .utils import unflat_sf
from coffea.analysis_tools import Weights
from analysis.corrections.utils import pog_years, get_pog_json


# ----------------------------------
# lepton scale factors
# -----------------------------------
#
# Electron
#    - ID: wp80noiso?
#    - Recon: RecoAbove20?
#    - Trigger: ?
#
# working points: (Loose, Medium, RecoAbove20, RecoBelow20, Tight, Veto, wp80iso, wp80noiso, wp90iso, wp90noiso)
#
class ElectronCorrector:
    """
    Electron corrector class

    Parameters:
    -----------
    events:
        events collection
    weights:
        Weights object from coffea.analysis_tools
    year:
        Year of the dataset {'2016', '2017', '2018'}
    variation:
        if 'nominal' (default) add 'nominal', 'up' and 'down'
        variations to weights container. else, add only 'nominal' weights.
    """

    def __init__(
        self,
        events: ak.Array,
        weights: Type[Weights],
        year: str = "2017",
        variation: str = "nominal",
    ) -> None:
        self.electrons = events.selected_electrons
        self.variation = variation

        # flat electrons array
        self.e, self.n = ak.flatten(events.selected_electrons), ak.num(
            events.selected_electrons
        )

        # weights container
        self.weights = weights

        # define correction set
        self.cset = correctionlib.CorrectionSet.from_file(
            get_pog_json(json_name="electron", year=year)
        )
        self.year = year
        self.pog_year = pog_years[year]

    def add_id_weight(self, id_working_point: str) -> None:
        """
        add electron identification scale factors to weights container

        Parameters:
        -----------
            id_working_point:
                Working point {'Loose', 'Medium', 'Tight', 'wp80iso', 'wp80noiso', 'wp90iso', 'wp90noiso'}
        """
        # get 'in-limits' electrons
        electron_pt_mask = (self.e.pt > 10.0) & (
            self.e.pt < 499.999
        )  # potential problems with pt > 500 GeV
        in_electron_mask = electron_pt_mask
        in_electrons = self.e.mask[in_electron_mask]

        # get electrons transverse momentum and pseudorapidity (replace None values with some 'in-limit' value)
        electron_pt = ak.fill_none(in_electrons.pt, 10.0)
        electron_eta = ak.fill_none(in_electrons.eta, 0.0)

        # remove '_UL' from year
        year = self.pog_year.replace("_UL", "")

        # get nominal scale factors
        nominal_sf = unflat_sf(
            self.cset["UL-Electron-ID-SF"].evaluate(
                year, "sf", id_working_point, electron_eta, electron_pt
            ),
            in_electron_mask,
            self.n,
        )
        if self.variation == "nominal":
            # get 'up' and 'down' scale factors
            up_sf = unflat_sf(
                self.cset["UL-Electron-ID-SF"].evaluate(
                    year, "sfup", id_working_point, electron_eta, electron_pt
                ),
                in_electron_mask,
                self.n,
            )
            down_sf = unflat_sf(
                self.cset["UL-Electron-ID-SF"].evaluate(
                    year, "sfdown", id_working_point, electron_eta, electron_pt
                ),
                in_electron_mask,
                self.n,
            )
            # add scale factors to weights container
            self.weights.add(
                name=f"electron_id_{id_working_point}",
                weight=nominal_sf,
                weightUp=up_sf,
                weightDown=down_sf,
            )
        else:
            self.weights.add(
                name=f"electron_id_{id_working_point}",
                weight=nominal_sf,
            )

    def add_reco_weight(self, reco: str) -> None:
        """
        add electron reconstruction scale factors to weights container

        reco: {RecoAbove20, RecoBelow20}
        """
        electron_pt_mask = {
            "RecoAbove20": (self.e.pt > 20) & (self.e.pt < 499.999),
            "RecoBelow20": (self.e.pt > 10) & (self.e.pt < 20),
        }
        # get 'in-limits' electrons
        in_electron_mask = electron_pt_mask[reco]
        in_electrons = self.e.mask[in_electron_mask]

        # get electrons transverse momentum and pseudorapidity (replace None values with some 'in-limit' value)
        electrons_pt_limits = {"RecoAbove20": 21, "RecoBelow20": 15}
        electron_pt = ak.fill_none(in_electrons.pt, electrons_pt_limits[reco])
        electron_eta = ak.fill_none(in_electrons.eta, 0.0)

        # remove _UL from year
        year = self.pog_year.replace("_UL", "")

        # get nominal scale factors
        nominal_sf = unflat_sf(
            self.cset["UL-Electron-ID-SF"].evaluate(
                year, "sf", reco, electron_eta, electron_pt
            ),
            in_electron_mask,
            self.n,
        )
        if self.variation == "nominal":
            # get 'up' and 'down' scale factors
            up_sf = unflat_sf(
                self.cset["UL-Electron-ID-SF"].evaluate(
                    year, "sfup", reco, electron_eta, electron_pt
                ),
                in_electron_mask,
                self.n,
            )
            down_sf = unflat_sf(
                self.cset["UL-Electron-ID-SF"].evaluate(
                    year, "sfdown", reco, electron_eta, electron_pt
                ),
                in_electron_mask,
                self.n,
            )
            # add scale factors to weights container
            self.weights.add(
                name=f"electron_{reco}",
                weight=nominal_sf,
                weightUp=up_sf,
                weightDown=down_sf,
            )
        else:
            self.weights.add(
                name=f"electron_{reco}",
                weight=nominal_sf,
            )