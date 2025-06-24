# BSM3G Coffea

[![Codestyle](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Python package that uses a columnar framework to process input tree-based [NanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD) files using the [coffea](https://coffeateam.github.io/coffea/) and [scikit-hep](https://scikit-hep.org) Python libraries.

- [Input filesets](#Input-filesets)
- [Workflows](#Workflows)
- [Submit Condor jobs](#Submit-Condor-jobs)
- [Postprocessing](#Postprocessing)


### Input filesets
 

Each year/campaign has a config file in [`analysis/filesets/<year>_<nano version>.yaml`](https://github.com/deoache/wprimeplusb/tree/main/analysis/filesets) from which the input filesets are built. 

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

The workflows (selections, variables, output histograms, triggers, etc) are defined through a configuration file located in `analysis/workflows`. [Here](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/README.md) you can find a detailed description on how to create the config file.

The available workflows are:

* [ztomumu](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/ztomumu.yaml)
* [ztoee](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/ztoee.yaml)
* W'+b
    * $t\bar{t}$ estimation
        * [2b1mu](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/2b1mu.yaml)
        * [2b1e](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/2b1e.yaml)
        * [1b1mu1e](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/1b1mu1e.yaml)
        * [1b1e1mu](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/1b1e1mu.yaml)
    * QCD estimation
        * [qcd_mu](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/qcd_mu.yaml)
        * [qcd_cr1T_mu](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/qcd_cr1T_mu.yaml)
        * [qcd_cr2T_mu](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/qcd_cr2T_mu.yaml)
        * [qcd_ele](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/qcd_ele.yaml)
        * [qcd_cr1T_ele](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/qcd_cr1T_ele.yaml)
        * [qcd_cr2T_ele](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/qcd_cr2T_ele.yaml)
* VBF SUSY
    * [ztojets](https://github.com/deoache/wprimeplusb/blob/main/analysis/workflows/ztojets.yaml)


### Submit Condor jobs

First connect to lxplus and clone the repository (if you have not done it yet)
```
ssh <your_username>@lxplus.cern.ch

git clone https://github.com/deoache/wprimeplusb.git
cd wprimeplusb
```
You need to have a valid grid proxy in the CMS VO. (see [here](https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideLcgAccess) for details on how to register in the CMS VO). The needed grid proxy is obtained via the usual command
```
voms-proxy-init --voms cms
```

Jobs are submitted via the [runner.py](https://github.com/deoache/higgscharm/blob/lxplus/runner.py) script. It can be used to submit all jobs (MC + data) of a workflow/year
```
python3 runner.py --workflow ztomumu --year 2017 --submit --eos
``` 

**Note**: It's recommended to add the `--eos` flag to save the outputs in your `/eos` area, so the postprocessing step can be done from [SWAN](https://swan-k8s.cern.ch/hub/spawn). **In this case, you will need to clone the repo also in [SWAN](https://swan-k8s.cern.ch/hub/spawn) (select the 105a release) in order to be able to run the postprocess**.

After submitting the jobs you can watch their status by typing:
```
watch condor_q
```
You can use the `jobs_status.py` script to see which jobs are still to be executed, build new datasets in case there are xrootd OS errors, update and resubmit condor jobs.
```
python3 jobs_status.py --workflow ztomumu --year 2017 --eos
```

### Postprocessing

Once all jobs are done for a processor/year, you can get the results using the `run_postprocess.py` script:
```
python3 run_postprocess.py --workflow ztomumu --year 2017 --postprocess --plot --log
``` 
Results will be saved to the same directory as the output files