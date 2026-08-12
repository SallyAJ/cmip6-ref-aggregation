# Spatially averaged (population-weighted) climate variables from downscaled CMIP6 models and observational references

## Repository and Publication

This repository stores a simplified version of the Python and R code used to reproduce the generation of spatially 
averaged (population-weighted) climate variables presented in:

**Jahn et al. (2026)**: *Quasi-global, land-only, high-resolution and spatially averaged climate variables from 
downscaled CMIP6 models for climate impact research*, Scientific Data [``DOI``].

All relevant information on original data sources, methods, processing, and data archiving is provided in the associated
publication. To effectively use this repository, please read the following information carefully.

---
## Description
The dataset covers information on historical as well as future climate model outputs under the SSP2-4.5 and SSP5-8.5 
scenarios. It is based on six global climate models (GCMs) from the Coupled Model Intercomparison Project Phase 6 (CMIP6). 
The data have been statistically downscaled to a high spatial resolution of 0.1°, using ERA5-Land reanalysis data and 
the CHIRPS observational precipitation dataset as the reference climatology.

This repository provides guidance on downloading and processing the datasets used as reference climatology (ERA5-Land, 
CHIRPS). These datasets, alongside the bias-corrected and downscaled CMIP6 models presented in the above publication, 
are used to derive spatially aggregated (population-weighted) information for different countries (administrative 
unit levels 0-2), with the spatial aggregation presented here applied to the original data sources, reference 
climatology, and the bias-corrected and downscaled CMIP6 model outputs.

For further details, users are referred to the publication.

---
## Dependencies and Setup

### General Setup
#### Python 

##### Copyright and Corresponding Author
Copyright © 2026 Sally Jahn (GitHubID: SallyAJ).

##### General
The main code was developed using Python 3.11 in a Linux (Ubuntu) environment.

To run this repo, create the environment with ``conda env create -f environment.yml``. Make sure to update the placeholder
environment name in the YAML file! Then activate the environment with: ``conda activate <environment name>``. This 
installs all required dependencies, including the Climate Data Operators (CDO) system binary. 
Files can be executed from the terminal as Python modules using the -m flag. The general pattern is ``python3 -m 
src.<folder>.<script>``, and commands should be run from the project root directory.

Scripts in `src/global` must be executed first, as they perform the download, preprocessing, and validation of all 
underlying data sources. Subsequently, scripts in `src/countries` focus on generating spatially averaged (population-
weighted) estimates for more than 100 countries. Within each directory, scripts are numerically prefixed and should be 
executed sequentially in ascending order.

Please replace the placeholders in the attributes of the functions `conventions_obs` and `conventions_esm` by setting 
`AUTHOR_NAME`, `AUTHOR_ORCID`, and `INSTITUTION_NAME` before running the code in `src/utils/data_helper.py`.

In `src/config/data_catalog`, the path to the grid directory defining the underlying spatial grids used in this workflow 
is specified. As an example, a `grids` folder is provided in this repository, which can be integrated into the respective
path structure in a local workflow.

##### CDO and CDS
This repository provides Python interfaces (wrappers) for workflows originally implemented using Climate Data Operators 
(CDO) in a Linux terminal environment. While many operations have been translated into Python using CDO’s scripting 
interface, running CDO commands directly in the terminal is still recommended for efficiency and flexibility.

CDO is used for various data processing tasks, such as adjusting and harmonizing model grid types. More information on 
using CDO with Python is available here:  
https://code.mpimet.mpg.de/projects/cdo/wiki/Cdo%7Brbpy%7D

The workflow also relies on access to the Copernicus Climate Data Store (CDS) API for downloading ERA5-Land data. Setup 
instructions can be found here:  
https://cds.climate.copernicus.eu/api-how-to

##### Environment Variables

Configuration is managed via a `.env` file in the project root. Copy `.env.template` to `.env` and fill in the values:

```
cp .env.template .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `DATA_DIR_CENTRE` | Absolute path to the shared/cluster data storage root | `./data` *(required)* |
| `CDS_API_RC_PATH` | Path to the CDS API credentials file | `~/.cdsapirc` *(required)* |
| `CDS_API_KEY` | Your personal CDS API key. Obtain it at https://cds.climate.copernicus.eu/ | *(required)* |
| `CDS_API_URL` | Base URL for the CDS API | `https://cds.climate.copernicus.eu/api` |
| `CHIRPS_URL` | Base URL for CHIRPS daily data downloads | `CHIRPS_URL=https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/netcdf/byMonth/` |



#### R

##### Copyright and Corresponding Authors
Copyright © 2026 Wes Hinsley and Neil Ferguson (GitHubIDs: weshinsley and NeilFerguson).

##### General
Part of the code was developed using the statistical programming language R, within the RStudio integrated development 
environment (IDE) on a Windows operating system. Running the R code provides spatially aggregated area-weighted and 
population-weighted area-level estimates, in addition to those generated based on the simple cosine-of-latitude weighting 
approach (via the Python workflow described above). 
For further details on methods and overall workflows, please refer to the accompanying manuscript.

For generating spatially aggregated (area- and population-weighted) estimates from the observational datasets,
run `avg_obs.R`. For generating spatially aggregated (area- and population-weighted) estimates from the climate-model 
outputs, run `run_all_proj_regions.R`.

##### Configure Input Paths
Before running either script, update the placeholder paths under `TODO` in `avg_obs.R` and `avg_proj.R` so that they 
point to the corresponding output directories generated by the Python workflow, as described in each respective script.
Furthermore, the data build is based on the workflow under `global` in the Python repository provided here. The outlined
population datasets are pre-downloaded and stored externally in the respective shares. Information on the source, 
version, and download path for these datasets is provided in the accompanying manuscript cited above.

##### Required Packages
Required R packages:

```text
terra, sf, exactextractr, data.table, ggplot2, scales,
ncdf4, dplyr, arrow, rhdf5, rhdf5filters
```
The CRAN packages can be installed with:

```r
install.packages(c("terra", "sf", "exactextractr", "data.table",
                   "ggplot2", "scales", "ncdf4", "dplyr", "arrow"))
```
The Bioconductor packages can be installed with:

```r
if (!require("BiocManager", quietly = TRUE))
  install.packages("BiocManager")

BiocManager::install(c("rhdf5", "rhdf5filters"))
```

---
## Citations and Acknowledgments
We acknowledge the providers of the original datasets and thank them for producing and making these data publicly 
available. The providers are not responsible for any use of the extracted or processed data. Projects using this 
repository, the derived data, or information from the publication are kindly requested to cite both
this project and the original source datasets from which the area-level estimates are derived, 
as well as the accompanying publication cited above. The generated dataset is registered on Zenodo and hosted in the 
associated public Box repository. Users are referred to the publication for information and citations 
regarding data sources, methods, software packages and tools, funding, and supporting institutions.
