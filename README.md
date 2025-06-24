# BSM3G Coffea

[![Codestyle](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Python package that uses a columnar framework to process input tree-based [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) files using the [coffea](https://coffeateam.github.io/coffea/) and [scikit-hep](https://scikit-hep.org) Python libraries.

- [Input filesets](#Input-filesets)
- [Workflows](#Workflows)
- [Submit Condor jobs](#Submit-Condor-jobs)
- [Postprocessing](#Postprocessing)


### Input filesets
 

Each data-taking year or campaign has a corresponding config file in [`analysis/filesets/<year>_<nano version>.yaml`](https://github.com/deoache/bsm3g_coffea/tree/main/analysis/filesets), which defines the input datasets to process.

Each entry in the fileset configuration includes the following fields:

- **`era`**: Dataset era. For data, this is typically the run letter (e.g. `B`, `F`, etc.). For Monte Carlo datasets, use `"MC"`.
- **`process`**: Logical process name used during postprocessing to group multiple datasets (e.g. different HT bins) into the same physical process.
- **`key`**: Label that associates the dataset with a group defined in the workflow configuration under `datasets` (see next section). This key is used in the Condor submitter script to determine which datasets to run for a given workflow and year.
- **`query`**: DAS path used to fetch the files for this dataset.
- **`xsec`**: Cross section in picobarns (pb). Should be `null` for data. Required for Monte Carlo samples in order to compute event weights.

example:
```yaml
SingleMuonF:
  era: F
  process: Data
  key: muon
  query: SingleMuon/Run2017F-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
  xsec: null
  
DYJetsToLL_M-4to50_HT-100to200:
  era: MC
  process: DYJetsToLL
  key: dy_ht
  query: DYJetsToLL_M-4to50_HT-100to200_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v2/NANOAODSIM
  xsec: 224.2
```


### Workflows

Workflows define the analysis configuration: selections, histograms, triggers, corrections, and output structure. They are stored as YAML files in the [`analysis/workflows`](https://github.com/deoache/bsm3g_coffea/tree/main/analysis/workflows) directory. You can find a detailed explanation of the structure of a workflow [here](https://github.com/deoache/bsm3g_coffea/blob/main/analysis/workflows/README.md) 

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

**3. (Optional) build the input fileset**

Before submitting jobs, you can manually generate the input fileset for a given campaign/year. This step will query DAS based on the YAML config file
```bash
python3 fecth.py -y <campaign>
```
If you skip this step, the job submission script will automatically try to generate missing filesets on demand.

**4. Submit jobs**

There are two main ways to submit jobs: per dataset or entire workflow.

**A. Submit a single dataset**

Use [submit_condor.py](https://github.com/deoache/bsm3g_coffea/blob/main/submit_condor.py) to submit jobs for a specific workflow, dataset and campaign/year:
```bash
python3 submit_condor.py --workflow <workflow> --dataset <dataset> --year <campaign> --submit --eos
```

**B. Submit all datasets from a workflow**

The easiest and recommended method is using [runner.py](https://github.com/deoache/higgscharm/blob/lxplus/runner.py), which reads the `datasets` section in the workflow YAML and submits jobs for all listed data and MC samples
```bash
python3 runner.py --workflow <workflow> --year <campaign> --submit --eos
``` 

Use `--nfiles <N>` to control how many root files are used per job (default is 10).

**Note**: It's recommended to add the `--eos` flag to save the outputs to your `/eos` area, so the postprocessing step can be done from [SWAN](https://swan-k8s.cern.ch/hub/spawn). **In this case, you will need to clone the repo also in [SWAN](https://swan-k8s.cern.ch/hub/spawn) (select the 105a release) in order to be able to run the postprocess**.

**5. Monitor job status**

To continuously monitor your Condor jobs:
```bash
watch condor_q
```
To get a summary of missing, failed, or incomplete jobs, and optionally resubmit them, use:
```bash
python3 jobs_status.py --workflow <workflow> --year <campaign> --eos
```
It can also regenerate filesets and resubmit jobs if needed


### Postprocessing

Once all jobs are done, you can get the results (plots + tables) using `run_postprocess.py`:
```bash
python3 run_postprocess.py --workflow <workflow> --year <campaign> --postprocess --plot --log
``` 
Results will be saved to the same directory as the output files