### Workflow config

Workflow's selection, variables, output histograms, triggers, among other features are defined through a yaml configuration file:

* `datasets`: Data and MC datasets to process

```yaml
datasets:
  data: 
    - muon
  mc:
    - dy_inclusive
    - singletop
    - tt
    - wjets_ht
    - diboson
```
Each item (e.g. muon, dy_inclusive, tt) corresponds to a key in the fileset YAML file.

* `object_selection`: Contains the information required for object selection:
```yaml
object_selection:
  muons:
    field: events.Muon
    cuts:
      - events.Muon.pt > 35
      - np.abs(events.Muon.eta) < 2.4
      - working_points.muons_id(events, 'tight')
      - working_points.muons_iso(events, 'tight')
  dimuons:
    field: select_dimuons
    cuts:
      - objects['dimuons'].l1.delta_r(objects['dimuons'].l2) > 0.3
      - objects['dimuons'].l1.charge * objects['dimuons'].l2.charge < 0
      - (objects['dimuons'].p4.mass > 60.0) & (objects['dimuons'].p4.mass < 120.0)
```
With `field` you define how to select the object, either through a NanoAOD field (`events.Muon`) or a custom object-selection function (`select_dimuons`) defined as a method of the [ObjectSelector](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/selections/object_selections.py) class. Each object is added sequentially to a dictionary called `objects`, which can later be used to access the already selected objects.

`cuts` defines the set of object-level cuts to apply. Similarly, you can use NanoAOD fields (`events.Muon.pt > 24`) to define a cut or any valid expression (`objects['dimuons'].p4.mass < 120.0`). Alternatively, you can also use a working point function (`working_points.muons_iso(events, 'tight')`) defined in the [WorkingPoints class](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/working_points/working_points.py). 

You can also use `add_cut` to define masks that will be added to the object and can be accessed later in the workflow:

```yaml
muons:
    field: events.Muon
    add_cut:
      is_loose:
        - events.Muon.pt > 5
        - np.abs(events.Muon.eta) < 2.4
        - np.abs(events.Muon.dxy) < 0.5
        - np.abs(events.Muon.dz) < 1
        - events.Muon.isGlobal | (events.Muon.isTracker & (events.Muon.nStations > 0))
      is_relaxed:
        - objects['muons'].is_loose
        - np.abs(events.Muon.sip3d) < 4
      is_tight:
        - objects['muons'].is_loose
        - objects['muons'].is_relaxed
        - events.Muon.isPFcand | ((events.Muon.highPtId > 0) & (events.Muon.pt > 200))
    cuts:
      - objects['muons'].is_tight
```

* `event_selection`: Contains the HLT paths and event-level cuts:
```yaml
event_selection:
  hlt_paths:
    muon:
      - SingleMu
  selections:
    trigger: get_trigger_mask(events, hlt_paths, dataset, year)
    trigger_match: get_trigger_match_mask(events, hlt_paths, year, events.Muon)
    lumi: get_lumi_mask(events, year)
    goodvertex: events.PV.npvsGood > 0
    two_muons: ak.num(objects['muons']) == 2
    one_dimuon: ak.num(objects['dimuons']) == 1
    leading_muon_pt: ak.firsts(objects['muons'].pt) > 30
    subleading_muon_pt: ak.pad_none(objects['muons'], target=2)[:, 1].pt > 15
  categories:
    base:
      - goodvertex
      - lumi
      - trigger
      - trigger_match
      - two_muons
      - leading_muon_pt
      - subleading_muon_pt
      - one_dimuon
```
First, you define which trigger(s) to apply with `hlt_paths`. The first-level key (`muon`) refers to the dataset key as defined in the fileset config. The values (e.g. `SingleMu`) are trigger flags. These map to specific HLT paths (like `HLT_IsoMu24`, `HLT_Mu50`, etc.) and are defined [here](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/selections/trigger_flags.yaml). 

The event-level cuts are defined in `selections`. Similarly to the object selection, you can use any valid expression from a NanoAOD field or a custom event-selection function defined in [`analysis/selections/event_selections.py`](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/selections/event_selections.py). Then, you can define one or more categories in `categories` by listing the cuts you want to include for each category. Histograms will be filled for each category.


* `corrections`: Contains the object-level corrections and event-level weights to apply:

```yaml
corrections:
  objects:
    - jets
    - jets_veto
    - muons
    - electrons
    - taus
    - met
  apply_obj_syst: false
  event_weights:
    genWeight: true
    pileupWeight: true
    l1prefiringWeight: true
    lhepdfWeight: false
    lhescaleWeight: false
    partonshowerWeight: true
    muon:
      - id: tight
      - iso: tight
      - reco: true
      - trigger: true
```

The corrections are managed [here](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/corrections/corrections_manager.py).

* `histogram_config`: Use to define processor's output histograms (more info on Hist histograms [here](https://hist.readthedocs.io/en/latest/)). Here you define the histogram axes associated with the variables you want to include in the analysis. 
```yaml
histogram_config:
  add_syst_axis: true
  add_weight: true
  axes:
    muon_pt:
      type: Regular
      bins: 50
      start: 30
      stop: 300
      label: $p_T(\mu)$ [GeV]
      expression: objects['muons'].pt
    muon_eta:
      type: Regular
      bins: 50
      start: -2.5
      stop: 2.5
      label: $\eta(\mu)$
      expression: objects['muons'].eta
    muon_phi:
      type: Regular
      bins: 50
      start: -3.14159
      stop: 3.14159
      label: $\phi(\mu)$
      expression: objects['muons'].phi
    dimuon_mass:
      type: Regular
      bins: 100
      start: 10
      stop: 150
      label: $m(\mu\mu)$ [GeV]
      expression: objects['dimuons'].p4.mass
    jet_pt:
      type: Variable
      edges:
        - 20
        - 60
        - 90
        - 120
        - 150
        - 180
        - 210
        - 240
        - 300
        - 500
      label: $p_T(j)$ [GeV]
      expression: objects['jets'].pt
    jet_flav:
      type: IntCategory
      categories:
        - 0
        - 4
        - 5
      label: HadronFlavour
      expression: objects['jets'].hadronFlavour
    vertex_multiplicity:
      type: Integer
      start: 0
      stop: 60
      label: vertex multiplicity
      expression: events.PV.npvsGood
  layout:
    muon:
      - muon_pt
      - muon_eta
      - muon_phi
    zcandidate:
      - dimuon_mass
    jet:
      - jet_pt
      - jet_flav
    vertex_multiplicity:
      - vertex_multiplicity
```
Note that the variable associated with the axis must be included through the `expression` field using the `objects` dictionary. Output histogram's layout is defined with the `layout` field. In the example above, our output dictionary will contain four histograms labelled `muon`, `zcandidate`, `jet` and `vertex_multiplicity` (make sure to include axis with the same dimensions within a histogram). If you set `layout: individual` then the output dictionary will contain a histogram for each axis. Note that if you set `add_syst_axis: true`, a StrCategory axis `{"variable_name": {"type": "StrCategory", "categories": [], "growth": True}}` to store systematic variations will be added to each histogram.