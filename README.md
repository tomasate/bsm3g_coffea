# BSM3G Coffea

[![Codestyle](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Python package that uses a columnar framework to process input tree-based [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) files using the [coffea](https://coffeateam.github.io/coffea/) and [scikit-hep](https://scikit-hep.org) Python libraries.

- [Input filesets](#Input-filesets)
- [Workflows](#Workflows)
- [Submit Condor jobs](#Submit-Condor-jobs)
- [Postprocessing](#Postprocessing)


### Input filesets
 

Each data-taking year or campaign has a corresponding config file in [`analysis/filesets/<year>_<nano version>.yaml`](https://github.com/deoache/bsm3g_coffea/tree/main/analysis/filesets), which defines the input datasets to process

```yaml
SingleMuonF:
  era: F
  process: Data
  key: muon
  query: SingleMuon/Run2017F-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
  xsec: null
DYJetsToLL_inclusive_50:
  era: MC
  process: DYJetsToLL
  key: dy_inclusive
  query: DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v2/NANOAODSIM
  xsec: 6025.6
```

- **`era`**: Dataset era. For data, this is typically the run letter (e.g. `B`, `F`, etc.). For Monte Carlo datasets, use `"MC"`.
- **`process`**: Logical process name used during postprocessing to group multiple datasets (e.g. different HT bins) into the same physical process.
- **`key`**: Label that associates the dataset with a group defined in the workflow configuration under `datasets` (see next section).
- **`query`**: DAS path used to fetch the files for this dataset.
- **`xsec`**: Cross section in picobarns (pb). Should be `null` for data. Required for Monte Carlo samples in order to compute event weights.

### Workflows

Workflows define the configuration of an analysis: object and event selections, triggers, corrections and histograms. They are stored as YAML files in the [`analysis/workflows`](https://github.com/deoache/bsm3g_coffea/tree/main/analysis/workflows) directory. 

Each workflow also specifies which data and MC samples to run over for a given workflow through the `datasets` field:
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
These entries (e.g. `muon`, `dy_inclusive`, etc) refer directly to the key fields defined in the input fileset configuration. **You can find a detailed explanation of the structure of a workflow** [here](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/README.md) 

The available workflows are:

* [ztomumu](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/ztomumu.yaml)
* [ztoee](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/ztoee.yaml)
* W'+b
    * $t\bar{t}$ estimation
        * [2b1mu](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/2b1mu.yaml)
        * [2b1e](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/2b1e.yaml)
        * [1b1mu1e](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/1b1mu1e.yaml)
        * [1b1e1mu](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/1b1e1mu.yaml)
    * QCD estimation
        * [qcd_mu](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/qcd_mu.yaml)
        * [qcd_cr1T_mu](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/qcd_cr1T_mu.yaml)
        * [qcd_cr2T_mu](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/qcd_cr2T_mu.yaml)
        * [qcd_ele](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/qcd_ele.yaml)
        * [qcd_cr1T_ele](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/qcd_cr1T_ele.yaml)
        * [qcd_cr2T_ele](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/qcd_cr2T_ele.yaml)
* VBF SUSY
    * [ztojets](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/ztojets.yaml)



### Submit Condor jobs

**1. Log in to lxplus and clone the repository**
   
If you haven't done so already:
```bash
ssh <your_username>@lxplus.cern.ch

git clone https://github.com/deoache/bsm3g_coffea.git
cd bsm3g_coffea
```

**2. Initialize a valid CMS grid proxy**

To access remote datasets via xrootd, you need a valid grid proxy.

To generate the proxy:
```bash
voms-proxy-init --voms cms
```
If you're not registered in the CMS VO, follow these [instructions](https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideLcgAccess) to request access.


**3. Submit all datasets from a workflow**

Use [runner.py](https://github.com/deoache/higgscharm/blob/lxplus/runner.py) to submit jobs for a specific workflow and campaign/year. 
```bash
python3 runner.py --workflow <workflow> --year <campaign> --submit --eos
``` 

**Note**: It's recommended to add the `--eos` flag to save the outputs to your `/eos` area, so the postprocessing step can be done from [SWAN](https://swan-k8s.cern.ch/hub/spawn). In this case, **you need to clone the repo before submitting jobs** in [SWAN](https://swan-k8s.cern.ch/hub/spawn) (select the 105a release) in order to be able to run the postprocess.

You could use [submit_condor.py](https://github.com/deoache/bsm3g_coffea/blob/main/submit_condor.py) to submit jobs for a specific dataset:
```bash
python3 submit_condor.py --workflow <workflow> --dataset <dataset> --year <campaign> --submit --eos
```

**4. Monitor job status**

To continuously monitor your Condor jobs:
```bash
watch condor_q
```
To get a summary of missing, failed, or incomplete jobs, and optionally resubmit them, use:
```bash
python3 jobs_status.py --workflow <workflow> --year <campaign> --eos
```
It can also regenerate filesets and resubmit jobs if needed.


### Postprocessing

Once the Condor jobs are completed and all outputs are saved under the `outputs/` directory, you can run `run_postprocess.py` to aggregate results, compute cutflows, and generate plots
```bash
python3 run_postprocess.py --workflow <workflow> --year <campaign> --postprocess --plot --log
``` 
For years with split campaigns (e.g. year 2016 with campaigns 2016preVFP and 2016postVFP), run
```bash
python3 run_postprocess.py --workflow <workflow> --year <year> --plot --log
```
to automatically combine both campaigns and compute joint results and plots.

Results will be saved to the same directory as the output files