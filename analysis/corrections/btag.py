import re
import json
import glob
import pathlib
import correctionlib
import numpy as np
import awkward as ak
import importlib.resources
from coffea import util
from typing import Type
from coffea.analysis_tools import Weights
from analysis.working_points import working_points
from analysis.corrections.utils import get_pog_json


class BTagCorrector:
    """
    BTag corrector class.

    https://twiki.cern.ch/twiki/bin/viewauth/CMS/BtagRecommendation

    Parameters:
    -----------
        events:
            Events collection
        weights:
            Weights container from coffea.analysis_tools
        sf_type:
            scale factors type to use {mujets, comb}
            For the working point corrections the SFs in 'mujets' and 'comb' are for b/c jets.
            The 'mujets' SFs contain only corrections derived in QCD-enriched regions.
            The 'comb' SFs contain corrections derived in QCD and ttbar-enriched regions.
            Hence, 'comb' SFs can be used everywhere, except for ttbar-dileptonic enriched analysis regions.
            For the ttbar-dileptonic regions the 'mujets' SFs should be used.
        worging_point:
            worging point {loose, medium, tight}
        tagger:
            tagger model {deepJet}
        year:
            dataset year {2016preVFP, 2016postVFP, 2017, 2018}
        variation:
            if 'nominal' (default) add 'nominal', 'up' and 'down' variations to weights container. else, add only 'nominal' weights.
        full_run:
            False (default) if only one year is analized,
            True if the fullRunII data is analyzed.
            If False, the 'up' and 'down' systematics are be used.
            If True, 'up/down_correlated' and 'up/down_uncorrelated'
            systematics are used instead of the 'up/down' ones,
            which are supposed to be correlated/decorrelated
            between the different data years
    """

    def __init__(
        self,
        events,
        weights: Type[Weights],
        sf_type: str = "comb",
        worging_point: str = "medium",
        tagger: str = "deepJet",
        year: str = "2017",
        variation: str = "nominal",
        full_run: bool = False,
    ) -> None:
        self._sf = sf_type
        self._year = year
        self._wp = worging_point
        self._weights = weights
        self._full_run = full_run
        self._variation = variation
        self._tagger = "deepJet"

        # check available btag SFs
        self._taggers = {"deepJet": {"tight": "T", "medium": "M", "loose": "L"}}
        if self._wp not in self._taggers[self._tagger]:
            raise ValueError(
                f"There are no available b-tag SFs for the working point. Please specify {self._taggers[self._tagger]}"
            )

        # check available btag efficiencies (btag_eff_<tagger>_<wp>_<year>.coffea)
        cwd = pathlib.Path().cwd()
        data_dir = cwd / "analysis/data"
        file_paths = glob.glob(f"{str(data_dir)}/btag_eff*")
        wps = set()
        years = set()
        for path in file_paths:
            wp_match = re.search(rf"{self._tagger}_(.*?)_", path)
            year_match = re.search(r"_(\d{4}(?:preVFP|postVFP)?)\.coffea", path)
            if wp_match:
                wps.add(wp_match.group(1))
            if year_match:
                years.add(year_match.group(1))
        if self._wp not in wps:
            raise ValueError(
                f"There are no b-tag efficiency for {self._wp} working point. Please specify {wps}"
            )
        if self._year not in years:
            raise ValueError(
                f"There are no b-tag efficiency for year {self._year}. Please specify {years}"
            )
        # load efficiency lookup table (only for deepJet)
        # efflookup(pt, |eta|, flavor)
        with importlib.resources.path(
            "analysis.data",
            f"btag_eff_deepJet_{self._wp}_{year}.coffea",
        ) as filename:
            self._efflookup = util.load(str(filename))

        # define correction set
        self._cset = correctionlib.CorrectionSet.from_file(
            get_pog_json(json_name="btag", year=year)
        )

        # select bc and light jets
        # hadron flavor definition: 5=b, 4=c, 0=udsg
        self._bc_jets = events.selected_jets[events.selected_jets.hadronFlavour >= 4]
        self._light_jets = events.selected_jets[events.selected_jets.hadronFlavour == 0]
        self._jet_map = {"bc": self._bc_jets, "light": self._light_jets}
        self._jet_pass_btag = {
            "bc": working_points.jets_deepjet_b(events, self._wp, year)[
                events.selected_jets.hadronFlavour >= 4
            ],
            "light": working_points.jets_deepjet_b(events, self._wp, year)[
                events.selected_jets.hadronFlavour == 0
            ],
        }

        self.var_naming_map = {
            "bc": "CMS_btag_heavy",
            "light": "CMS_btag_light",
        }

    def add_btag_weights(self, flavor: str) -> None:
        """
        Add b-tagging weights (nominal, up and down) to weights container for bc or light jets

        Parameters:
        -----------
            flavor:
                hadron flavor {'bc', 'light'}
        """
        # efficiencies
        eff = self.efficiency(flavor=flavor)

        # mask with events that pass the btag working point
        passbtag = self._jet_pass_btag[flavor]

        # nominal scale factors
        jets_sf = self.get_scale_factors(flavor=flavor, syst="central")

        # nominal weights
        jets_weight = self.get_btag_weight(eff, jets_sf, passbtag)

        if self._variation == "nominal":
            # systematics
            if self._full_run:
                # If the fullRunII data is analyzed, 'up/down_correlated' and 'up/down_uncorrelated' systematics are provided to be used instead of the 'up/down' ones, which are supposed to be correlated/decorrelated between the different data years
                for var in ["correlated", "uncorrelated"]:
                    # up and down scale factors
                    jets_sf_up = self.get_scale_factors(flavor=flavor, syst=f"up_{var}")
                    jets_sf_down = self.get_scale_factors(
                        flavor=flavor, syst=f"down_{var}"
                    )

                    jets_weight_up = self.get_btag_weight(eff, jets_sf_up, passbtag)
                    jets_weight_down = self.get_btag_weight(eff, jets_sf_down, passbtag)

                    # add weights to Weights container
                    self._weights.add(
                        name=f"{self.var_naming_map[flavor]}_{var}_{self._year}",
                        weight=jets_weight,
                        weightUp=jets_weight_up,
                        weightDown=jets_weight_down,
                    )
            else:
                syst_up = "up"
                syst_down = "down"
                # up and down scale factors
                jets_sf_up = self.get_scale_factors(flavor=flavor, syst=syst_up)
                jets_sf_down = self.get_scale_factors(flavor=flavor, syst=syst_down)

                jets_weight_up = self.get_btag_weight(eff, jets_sf_up, passbtag)
                jets_weight_down = self.get_btag_weight(eff, jets_sf_down, passbtag)

                # add weights to Weights container
                self._weights.add(
                    name=self.var_naming_map[flavor],
                    weight=jets_weight,
                    weightUp=jets_weight_up,
                    weightDown=jets_weight_down,
                )
        else:
            self._weights.add(
                name=self.var_naming_map[flavor],
                weight=jets_weight,
            )

    def efficiency(self, flavor: str, fill_value=1) -> ak.Array:
        """compute the btagging efficiency for 'njets' jets"""
        return self._efflookup(
            self._jet_map[flavor].pt,
            np.abs(self._jet_map[flavor].eta),
            self._jet_map[flavor].hadronFlavour,
        )

    def get_scale_factors(self, flavor: str, syst="central", fill_value=1) -> ak.Array:
        """
        compute jets scale factors
        """
        return self.get_sf(flavor=flavor, syst=syst)

    def get_sf(self, flavor: str, syst: str = "central") -> ak.Array:
        """
        compute the scale factors for bc or light jets

        Parameters:
        -----------
            flavor:
                hadron flavor {'bc', 'light'}
            syst:
                Name of the systematic {'central', 'down', 'down_correlated', 'down_uncorrelated', 'up', 'up_correlated'}
        """
        cset_keys = {
            "bc": f"{self._tagger}_{self._sf}",
            "light": f"{self._tagger}_incl",
        }
        # until correctionlib handles jagged data natively we have to flatten and unflatten
        j, nj = ak.flatten(self._jet_map[flavor]), ak.num(self._jet_map[flavor])

        # get 'in-limits' jets
        jet_eta_mask = np.abs(j.eta) < 2.499
        in_jet_mask = jet_eta_mask
        in_jets = j.mask[in_jet_mask]

        # get jet transverse momentum, abs pseudorapidity and hadron flavour (replace None values with some 'in-limit' value)
        jets_pt = ak.fill_none(in_jets.pt, 0.0)
        jets_eta = ak.fill_none(np.abs(in_jets.eta), 0.0)
        jets_hadron_flavour = ak.fill_none(
            in_jets.hadronFlavour, 5 if flavor == "bc" else 0
        )

        sf = self._cset[cset_keys[flavor]].evaluate(
            syst,
            self._taggers[self._tagger][self._wp],
            np.array(jets_hadron_flavour),
            np.array(jets_eta),
            np.array(jets_pt),
        )
        sf = ak.where(in_jet_mask, sf, ak.ones_like(sf))
        return ak.unflatten(sf, nj)

    @staticmethod
    def get_btag_weight(eff: ak.Array, sf: ak.Array, passbtag: ak.Array) -> ak.Array:
        """
        compute b-tagging weights

        see: https://twiki.cern.ch/twiki/bin/viewauth/CMS/BTagSFMethods

        Parameters:
        -----------
            eff:
                btagging efficiencies
            sf:
                jets scale factors
            passbtag:
                mask with jets that pass the b-tagging working point
        """
        # tagged SF = SF * eff / eff = SF
        tagged_sf = ak.prod(sf.mask[passbtag], axis=-1)

        # untagged SF = (1 - SF * eff) / (1 - eff)
        untagged_sf = ak.prod(((1 - sf * eff) / (1 - eff)).mask[~passbtag], axis=-1)

        return ak.fill_none(tagged_sf * untagged_sf, 1.0)
