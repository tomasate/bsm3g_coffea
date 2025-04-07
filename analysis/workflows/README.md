### Workflow config

Workflow's selection, variables, output histograms, triggers, among other features are defined through a yaml configuration file:


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
      - (objects['dimuons'].p4.mass > 60.0) & (objects['dimuons'].p4.mass <
        120.0)
```
With `field` you define how to select the object, either through a NanoAOD field (`events.Muon`) or a custom object-selection function (`select_dimuons`) defined as a method of the [ObjectSelector](https://github.com/deoache/wprimeplusb/blob/main/analysis/selections/object_selections.py) class. Each object is added sequentially to a dictionary called `objects`, which can later be used to access the already selected objects.

`cuts` defines the set of object-level cuts to apply. Similarly, you can use NanoAOD fields (`events.Muon.pt > 24`) to define a cut or any valid expression (`objects['dimuons'].p4.mass < 120.0`). Alternatively, you can also use a working point function (`working_points.muons_iso(events, 'tight')`) defined in the [WorkingPoints class](https://github.com/deoache/wprimeplusb/blob/main/analysis/working_points/working_points.py). 

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
    - IsoMu27
  selections:
    trigger: get_trigger_mask(events, hlt_paths, dataset, year)
    lumimask: get_lumi_mask(events, year)
    atleast_one_goodvertex: events.PV.npvsGood > 0
    electron_veto: ak.num(objects['electrons']) == 0
    two_muons: ak.num(objects['muons']) == 2
    one_dimuon: ak.num(objects['dimuons']) == 1
  categories:
    base:
      - trigger
      - lumimask
      - atleast_one_goodvertex
      - electron_veto
      - two_muons
      - one_dimuon
```
First, you define which trigger(s) to apply with `hlt_paths`. Then, you define all event-level cuts in `selections`. Similarly to the object selection, you can use any valid expression from a NanoAOD field or a custom event-selection function defined in [`analysis/selections/event_selections.py`](https://github.com/deoache/wprimeplusb/blob/main/analysis/selections/event_selections.py). Then, you can define one or more categories in `categories` by listing the cuts you want to include for each category. Histograms will be filled for each category.


* `corrections`: Contains the object-level corrections and event-level weights to apply:

```yaml
corrections:
  objects:
    - jets
    - muons
    - met
    - jets_veto
  event_weights:
    genWeight: true
    pileupWeight: true
    l1prefiring: true
    pujetid:
      - id: tight
    btagging: false
    electron:
      - id: false
      - reco: false
    muon:
      - id: tight
      - iso: tight
      - reco: true
      - trigger: true
```

The corrections are managed [here](https://github.com/deoache/wprimeplusb/blob/main/analysis/corrections/corrections_manager.py).

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
    jet_flav:
      type: IntCategory
      categories:
        - 0
        - 4
        - 5
      label: HadronFlavour
      expression: objects['jets'].hadronFlavour
    npvs:
      type: Integer
      start: 0
      stop: 60
      label: npvs
      expression: events.PV.npvsGood
  layout:
    muon:
      - muon_pt
      - muon_eta
      - muon_phi
    zcandidate:
      - dimuon_mass
    vertex:
      - npvs
```
Note that the variable associated with the axis must be included through the `expression` field using the `objects` dictionary. Output histogram's layout is defined with the `layout` field. In the example above, our output dictionary will contain two histograms labelled `muon` and `zcandidate`, the first with the `muon_pt`, `muon_eta` and `muon_phi` axes, and the second only with the `dimuon_mass` axis (make sure to include axis with the same dimensions within a histogram). If you set `layout: individual` then the output dictionary will contain a histogram for each axis. Note that if you set `add_syst_axis: true`, a StrCategory axis `{"variable_name": {"type": "StrCategory", "categories": [], "growth": True}}` to store systematic variations will be added to each histogram.