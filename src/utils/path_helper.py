# Path Helper

import os
import hdf5plugin
import pandas as pd
import numpy as np
from src.config.param import missing_value


def create_folder(path):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def get_files_by_pattern(folder, pattern):
    files = os.listdir(folder)
    filtered_files = [file for file in files if pattern in file]
    return filtered_files


def write_nc_file(ds, variable, storage_path):
    encoding = {variable: {'dtype': 'float32', '_FillValue': -9999}}
    ds.to_netcdf(storage_path, mode="w", format="NETCDF4",
                 engine="netcdf4", encoding=encoding)


def compress(esm_path_file, ds, var, start_year):
    config = dict(
        engine="h5netcdf",
        compr=dict(**hdf5plugin.Blosc(cname='blosclz', shuffle=1))
    )
    enc = {var: config["compr"] for var in ds.data_vars}
    for attr in ["units", "calendar"]:
        if attr in ds["time"].attrs:
            del ds["time"].attrs[attr]
    ds["time"].encoding = {
        "units": f"days since {start_year}-01-01 00:00:00",
        "calendar": "gregorian"
    }
    if 'coordinates' in ds[var].encoding:
        del ds[var].encoding['coordinates']
    # Write NetCDF file with 'blosc' compression
    ds = clean_attrs(ds)
    ds.to_netcdf(
        path=esm_path_file,
        mode="w",
        engine=config["engine"],
        unlimited_dims="time",
        encoding=enc
    )


def clean_attrs(ds):
    for var in ds.variables:
        ds[var].attrs = {k: v for k, v in ds[var].attrs.items() if v is not None}
    ds.attrs = {k: v for k, v in ds.attrs.items() if v is not None}
    return ds


# pq files
def file_storage(start, end, entry, storage_path_pq):
    value_columns = {}
    daily_dates = pd.date_range(start=f"{start}-01-01", end=f"{end}-12-31", freq="D")
    for key, value_raw in entry.items():
        if key == "pixels" or key == "admin_name":
            continue
        if isinstance(value_raw, list) and value_raw and isinstance(value_raw[0], list):
            value = flatten_list_of_lists(value_raw)
        else:
            value = value_raw
        if len(value) == len(daily_dates):
            arr = np.array(value, dtype=np.float64)
            arr[~np.isfinite(arr)] = missing_value
            arr[arr != missing_value] = np.round(arr[arr != missing_value], 2)
            value_columns[key] = arr
    data_df = pd.DataFrame({"Date": daily_dates.date, **value_columns, })
    data_df.attrs = {
        "admin_name": entry["admin_name"],
        "pixels": entry["pixels"],
        "suffix": "simple: standard area-level spatial aggregation, "
                  "static: population-weighted values (population data from 2000), "
                  "dynamic: population-weighted values (updated every ten years)",
        "variables": "pr: total precipitation [mm], "
                     "tas: 2m surface air temperature [°C], "
                     "tasmax: maximum 2m surface air temperature [°C], "
                     "tasmin: minimum 2m surface air temperature [°C], "
                     "hurs: relative humidity [%], "
                     "huss: specific humidity [g/kg]",
    }
    data_df.to_parquet(storage_path_pq, index=False, compression="gzip")


def flatten_list_of_lists(x):
    return [v for sub in x for v in (sub if isinstance(sub, list) else [sub])]
