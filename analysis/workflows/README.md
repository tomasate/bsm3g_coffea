### Workflow config

Workflow's selection, variables, output histograms, triggers, among other features are defined through a yaml configuration file:

### `datasets`

Data and MC datasets to process

```yaml
datasets:
  data:               # List of dataset keys corresponding to real data
    - muon
  mc:                 # List of dataset keys corresponding to Monte Carlo samples
    - dy_inclusive
    - singletop
    - tt
    - wjets_ht
    - diboson
```
- Each item refers to the `key` field defined in the fileset YAML
- This section is used by job submission script `runner.py` to determine which samples to run over

### `object_selection`

Contains the information required for object selection:
```yaml
object_selection:
  muons:                           # Logical name for the object (used as objects['muons'])    
    field: events.Muon             # Source collection
    cuts:                          # List of selection expressions for this object
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
- The `field` can be a NanoAOD field (`events.Muon`) or a custom object-selection function (`select_dimuons`) defined as a method of the [ObjectSelector](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/selections/object_selections.py) class. Each object is added sequentially to a dictionary called `objects`, which can later be used to access the already selected objects.
- `cuts` defines the set of object-level cuts to apply. You can use NanoAOD fields (`events.Muon.pt > 24`) or any valid expression (`objects['dimuons'].p4.mass < 120.0`). Alternatively, you can also use a working point function (`working_points.muons_iso(events, 'tight')`) defined in the [WorkingPoints class](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/working_points/working_points.py). 
- You can also use `add_cut` to define masks that will be added to the object and could be accessed later in the workflow:
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

### `event_selection`

Defines event-level selections and analysis regions (categories)
```yaml
event_selection:
  hlt_paths:
    muon:                        # Dataset key (as defined in the fileset YAML)
      - SingleMu                 # Trigger flag (defined in analysis/selections/trigger_flags.yaml)
  selections:                    # Event-level selections
    trigger: get_trigger_mask(events, hlt_paths, dataset, year)
    trigger_match: get_trigger_match_mask(events, hlt_paths, year, events.Muon)
    lumi: get_lumi_mask(events, year)
    goodvertex: events.PV.npvsGood > 0
    two_muons: ak.num(objects['muons']) == 2
    one_dimuon: ak.num(objects['dimuons']) == 1
    leading_muon_pt: ak.firsts(objects['muons'].pt) > 30
    subleading_muon_pt: ak.pad_none(objects['muons'], target=2)[:, 1].pt > 15
  categories:
    base:                        # Named selection region
      - goodvertex
      - lumi
      - trigger
      - trigger_match
      - two_muons
      - leading_muon_pt
      - subleading_muon_pt
      - one_dimuon
```
- `hlt_paths`: This section associates each dataset key (e.g. `muon`, `electron`) with one or more trigger flags. The [available trigger flags](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/selections/trigger_flags.yaml) are:
    | Year   | `SingleMu`               | `SingleEle`                       |
    |--------|--------------------------|-----------------------------------|
    | 2016   | IsoMu24 OR IsoTkMu24     | Ele27_WPTight_Gsf OR Photon175    |
    | 2017   | IsoMu27                  | Ele35_WPTight_Gsf OR Photon200    |
    | 2018   | IsoMu24                  | Ele32_WPTight_Gsf                 |
    | 2022   | IsoMu24                  | Ele30_WPTight_Gsf                 |
    | 2023   | IsoMu24                  | Ele30_WPTight_Gsf                 |

  
- `selections`: Here you define all event-level cuts. Similarly to object selection, you can use any valid expression from a NanoAOD field or a custom event-selection function defined in [`analysis/selections/event_selections.py`](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/selections/event_selections.py).

  For **data**, only the trigger flags listed under `hlt_paths` for the corresponding dataset key are applied. For **MC**, all trigger flags across all datasets are combined with a logical OR (via `get_trigger_mask()`). In addition, lepton–trigger object matching is enforced (via `get_trigger_match_mask()`) to ensure selected leptons are consistent with the fired HLT paths.

- `categories`: Named combinations of selection cuts. Each category defines a region for histogram filling and postprocessing

### `corrections`

Contains the object-level corrections and event-level weights to apply:

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
    MuBoostWeight: false
    pujetid: 
      - id: tight
    btagging: 
      - id: medium
      - bc: true
      - light: true
      - full_run: false
    muon:
      - id: tight
      - iso: tight
      - reco: true
      - trigger: true
    electron:
      - id: wp80iso
      - reco: true
      - trigger: false
    tau: false
```

- `objects`: List of physics objects to apply corrections to. Variations are included if `apply_obj_syst: true`


| Object      | Applied Corrections                              | Notes                                                                 |
|-------------|---------------------------------------------------|-----------------------------------------------------------------------|
| `jets`      | JES, JER                                          | Run2: uses JEC/JER. Run3: uses JERC framework. |
| `muons`     | Rochester corrections                             | Run2: `apply_rochester_corrections_run2`. Run3: `apply_rochester_corrections_run3` |
| `electrons` | Energy scale/shift corrections                    | Only in Run3, via `apply_electron_ss_corrections`.                    |
| `taus`      | Tau energy scale corrections                      | Run2 only. Applied only to MC          |
| `met`       | MET phi modulation corrections                    | Run-dependent. No variations added.                        |
| `jets_veto` | Jet veto map application (HEM, noisy regions, etc.) | Applies mask to jets and modifies MET accordingly.                   |


- `event_weights`: Defines event-level weights to apply to MC samples


| Field               | Description                                             | Notes                                                                 |
|---------------------|---------------------------------------------------------|-----------------------------------------------------------------------|
| `genWeight`         | Generator event weight                                  | Always applied if present.                                            |
| `pileupWeight`      | Pileup reweighting using data/MC distributions          | Requires PU profiles for data and MC.                                |
| `l1prefiringWeight` | ECAL L1 prefiring correction                            | Run2 only. Not applied in Run3.                                       |
| `partonshowerWeight`| ISR/FSR variation weights from `PSWeight`               | Applied only if `PSWeight` is present.                               |
| `lhepdfWeight`      | PDF uncertainty weights from `LHEPdfWeight`             | Applied only if `LHEPdfWeight` is available in NanoAOD.              |
| `lhescaleWeight`    | Renormalization/factorization scale variations          | Requires `LHEScaleWeight`.                                           |
| `pujetid`           | Jet ID scale factors                                    | Only in Run2. Requires `id` working point (e.g. loose, tight).       |
| `btagging`          | B-tagging SFs for jets                                  | Requires `id` (e.g. medium), `full_run`, `bc`, `light` flags.        |
| `MuBoostWeight`     | Custom muon reweighting for tt regions                  | Optional. Applied only if defined.                                   |
| `EleBoostWeight`    | Custom electron reweighting for tt regions              | Optional. Applied only if defined.                                   |
| `muon`              | Muon SFs for ID, ISO, reco, and trigger                 | Requires selected muons. Supports: `id`, `iso`, `reco`, `trigger`.   |
| `electron`          | Electron SFs for ID, reco, and trigger                  | Requires selected electrons. Reco split by `pt` region in Run2/Run3. |
| `tau`               | Tau ID SFs for DeepTau discriminators                   | Requires selected taus. Supports: `taus_vs_jet`, `taus_vs_ele`, `taus_vs_mu`. |



The corrections are managed [here](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/corrections/corrections_manager.py).

### `histogram_config`

This section defines the output histograms to be produced by the processor. This includes which variables to histogram, their binning, labels, and expression to evaluate them. The configuration is structured as follows:

```yaml
histogram_config:
  add_syst_axis: true        # Add a "variation" axis to include systematic uncertainties
  add_weight: true           # Use weighted histograms (hist.storage.Weight)
  flow: true                 # Whether to include underflow/overflow bins
  axes:                      # Dictionary of axis definitions (one per variable)
    <axis_name>:
      type: <AxisType>       # One of: Regular, Variable, Integer, IntCategory, StrCategory
      ...                    # Parameters depending on the type
      label: <str>           # Axis label for plots
      expression: <str>      # Python expression evaluated using objects or events
  layout:                    # Defines how axes are grouped into histograms
    <histogram_name>:
      - <axis_name_1>
      - <axis_name_2>
```
- If `add_syst_axis: true`, each histogram will include an additional axis named `"variation"` (of type `StrCategory`) to store systematic uncertainty shifts (`nominal`, `pileupUp`, `pileupDown`, etc.).
- If `add_weight: true`, histograms use `hist.storage.Weight` to track statistical uncertainties from weighted events.
- Supported axis types are:

| Type          | Description                                                                                     | Required Fields                                      |
|---------------|-------------------------------------------------------------------------------------------------|------------------------------------------------------|
| `Regular`     | Fixed-width bins over a continuous range                                                        | `bins`, `start`, `stop`                              |
| `Variable`    | Custom bin edges over a continuous range                                                        | `edges`                                              |
| `Integer`     | Integer range for discrete binning (e.g. multiplicities)                                        | `start`, `stop`                                      |
| `IntCategory` | Discrete categories (e.g. 0, 4, 5 for jet flavor), optionally with growing capability            | `categories`, `growth` (optional, default `false`)   |
| `StrCategory` | String-labeled categories, typically for systematics or selections                              | `categories`, `growth` (optional, default `false`)   |

- Each axis must define an `expression`, which is a Python expression evaluated using `objects` or `events` (you can also use expressions using numpy (np) or/and awkward (ak)). For example: `objects['muons'].pt` or `events.PV.npvsGood`.

- The `layout` field controls how axes are grouped into histograms:
  - If set to `"individual"`, each axis is turned into a separate 1D histogram.
  - If a dictionary is provided, e.g:
    ```yaml
    layout:
      muon:
        - muon_pt
        - muon_eta
        - muon_phi
    ```
    a multi-dimensional histogram is built (make sure the axes have the same dimensionality)

More info on Hist histograms [here](https://hist.readthedocs.io/en/latest/)