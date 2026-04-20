# Data Operations

import os
import xarray as xr
import datetime
from datetime import datetime
import pandas as pd
import rioxarray
from src.config.data_catalog import get_dbcca
from src.config.param import crs_reference_global

# Please replace the placeholders in the attributes of the functions `conventions_obs` and `conventions_esm`.
AUTHOR_NAME = "<Name>"
AUTHOR_ORCID = "<ORCID>"
INSTITUTION_NAME = "<Institution>"


def read_in_xarray_var_crs(nc_path, crs_reference=crs_reference_global):
    with xr.open_dataset(nc_path, engine="netcdf4") as data:
        if 'lon' not in data.dims or 'lat' not in data.dims:
            data = data.rename_dims({'longitude': 'lon', 'latitude': 'lat'})
        if 'lon' not in data.coords or 'lat' not in data.coords:
            data = data.rename_vars({'longitude': 'lon', 'latitude': 'lat'})
        data.rio.write_crs(crs_reference, inplace=True)  # set crs reference if not to convert
    return data


def read_in_time(path_file, year):
    ds = xr.open_dataset(path_file, engine="h5netcdf")
    if "time_bnds" in ds.data_vars:
        ds = ds.drop_vars("time_bnds")
    time_len = ds.dims["time"]
    new_time = pd.date_range(
        start=f"{year}-01-01",
        periods=time_len,
        freq="D"
    )
    ds = ds.assign_coords(time=new_time)
    return ds


def replace_f_number(realization, new_f):
    parts = realization.split('f')
    return f"{parts[0]}f{new_f}"


def load_model_output_dbcca(continent, variable, model, path_esm, scen, scen_sel, real):
    hist_path = os.path.join(path_esm, "HISTORICAL",
                             f"{continent}_{variable}_DBCCA_{model}_1985_2014_{real}_historical_compressed.nc")
    scen_path = os.path.join(path_esm, scen_sel,
                             f"{continent}_{variable}_DBCCA_{model}_2015_2100_{real}_{scen}_compressed.nc")
    tas_pr_esm_scen_dbcca = xr.open_dataset(scen_path, engine="h5netcdf")
    tas_pr_esm_hist_dbcca = xr.open_dataset(hist_path, engine="h5netcdf")
    return tas_pr_esm_hist_dbcca, tas_pr_esm_scen_dbcca, hist_path, scen_path


def load_model_data(continent, var, model, scen, real, path_esm=get_dbcca()):
    scen_sel = scen.upper()
    tas_pr_hist_raw_dbcca, tas_pr_esm_scen_dbcca, esm_path_historical_dbcca, esm_path_scenario_dbcca = load_model_output_dbcca(
        continent, var, model, path_esm, scen, scen_sel, real)
    return tas_pr_hist_raw_dbcca, tas_pr_esm_scen_dbcca, esm_path_historical_dbcca, esm_path_scenario_dbcca


def conventions_obs(ds, variable, variable_long, variable_long_extended, unit, start_year, source, version, link):
    today = datetime.today().strftime("%Y-%m-%d")
    ds[variable].attrs = {
        "standard_name": variable_long,
        "long_name": variable_long_extended,
        "units": unit,
        "coordinates": "lat lon"
    }

    ds['lat'].attrs = {
        "standard_name": "latitude",
        "long_name": "Latitude",
        "units": "degrees_north"
    }

    ds['lon'].attrs = {
        "standard_name": "longitude",
        "long_name": "Longitude",
        "units": "degrees_east"
    }

    ds['time'].attrs = {
        "standard_name": "time",
        "long_name": "Time"
    }

    ds['time'].encoding.update({
        "units": f"days since {start_year}-01-01 00:00:00",
        "calendar": "gregorian"
    })

    if 'spatial_ref' in ds.coords:
        ds['spatial_ref'].attrs = {"grid_mapping_name": "latitude_longitude", "epsg_code": "EPSG:4326",
                                   "grid_mapping": "spatial_ref"}

    ds.attrs = {
        "Conventions": "CF-1.8",
        "title": f"{source} {version} {variable_long_extended}",
        "source": f"Processed and clipped {source} {version} data.",
        "institution": f"{INSTITUTION_NAME}",
        "history": f"{today} - File created by {AUTHOR_NAME} (ORCID: {AUTHOR_ORCID})",
        "references": (
            f"{source} data: {link}"
        ),
        "comment": (
            f"Harmonized and clipped observational {source} {version} data for climate impact studies.\n"
            "Data restrictions: for academic research use only."
        )
    }


def conventions_esm(ds, variable, variable_long, variable_long_extended, unit, start_year, model, scen):
    today = datetime.today().strftime("%Y-%m-%d")
    ds[variable].attrs = {
        "standard_name": variable_long,
        "long_name": variable_long_extended,
        "units": unit,
        "coordinates": "lat lon"
    }

    ds['lat'].attrs = {
        "standard_name": "latitude",
        "long_name": "Latitude",
        "units": "degrees_north"
    }

    ds['lon'].attrs = {
        "standard_name": "longitude",
        "long_name": "Longitude",
        "units": "degrees_east"
    }

    ds['time'].attrs = {
        "standard_name": "time",
        "long_name": "Time"
    }

    ds['time'].encoding.update({
        "units": f"days since {start_year}-01-01 00:00:00",
        "calendar": "gregorian"
    })

    if 'spatial_ref' in ds.coords:
        ds['spatial_ref'].attrs = {"grid_mapping_name": "latitude_longitude", "epsg_code": "EPSG:4326",
                                   "grid_mapping": "spatial_ref"}

    # Global attributes — adjusted for archive requirements
    ds.attrs = {
        "Conventions": "CF-1.8",
        "title": f"{model} {scen} {variable_long_extended}",
        "source": f"Bias-corrected and downscaled CMIP model ({model}), scenario {scen}.",
        "institution": f"{INSTITUTION_NAME}",
        "history": f"{today} - File created by {AUTHOR_NAME} (ORCID: {AUTHOR_ORCID}), "
                   f"using the Double Bias-Corrected Constructed Analogues (DBCCA) method.",
        "references": (
            "Methodology: https://hess.copernicus.org/articles/20/1483/2016/hess-20-1483-2016.html\n"
            "CMIP6 data: https://esgf.github.io/nodes.html"
        ),
        "comment": (
            "Bias-corrected and downscaled climate projections for climate impact studies.\n"
            "Data restrictions: for academic research use only."
        )
    }

