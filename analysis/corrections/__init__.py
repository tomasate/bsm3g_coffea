from analysis.corrections.tau import TauCorrector
from analysis.corrections.btag import BTagCorrector
from analysis.corrections.muon import MuonCorrector
from analysis.corrections.lhepdf import add_lhepdf_weight
from analysis.corrections.pileup import add_pileup_weight
from analysis.corrections.jec import apply_jet_corrections
from analysis.corrections.electron import ElectronCorrector
from analysis.corrections.pujetid import add_pujetid_weight
from analysis.corrections.lhescale import add_scalevar_weight
from analysis.corrections.l1prefiring import add_l1prefiring_weight
from analysis.corrections.partonshower import add_partonshower_weight
from analysis.corrections.rochester import apply_rochester_corrections
from analysis.corrections.tau_energy import apply_tau_energy_scale_corrections
from analysis.corrections.met import apply_met_phi_corrections
from analysis.corrections.muon_highpt import MuonHighPtCorrector
from analysis.corrections.corrections_manager import (
    object_corrector_manager,
    weight_manager,
)


