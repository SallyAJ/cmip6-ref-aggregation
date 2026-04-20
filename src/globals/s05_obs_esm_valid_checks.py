# ScriptOverview
# Final check of observational data and bias-corrected, downscaled climate projections before further processing.
# A quality control check ensures that all values fall within realistic ranges (as described in the corresponding
# Scientific Data Descriptor paper). All outputs are clipped to their respective domains and provided on a standard
# leap-year calendar.
# Observational data were retrieved from scripts s01a–s02b, while bias-corrected and downscaled climate
# projections result from the DBBCA downscaling process (external). Outputs from six CMIP6 models were used: CanESM5,
# GFDL-ESM4, MPI-ESM1-2-LR, MRI-ESM2-0, TaiESM1, and UKESM1-0-LL.
# For further information on underlying data sources and methods, please refer to the Readme.md as well as the
# respective Scientific Data Descriptor publication.

import os
import xarray as xr
import rioxarray
from src.config.args import DateUpdateArgs
from src.config.data_sets import CHIRPS_CONFIG, ERA5_LAND_CONFIG, MODEL_CONFIGS, get_abbreviation, get_long_variable, get_unit
from src.utils.path_helper import create_folder, get_files_by_pattern, compress
from src.config.data_catalog import get_global_projections, domains_extent_file, get_compressed_folder, get_ref_paths
from src.utils.date_helper import check_leapyear
from src.config.param import crs_reference_global, cpd_region_list
from src.utils.data_helper import conventions_obs, conventions_esm, replace_f_number, load_model_data


config = DateUpdateArgs(year_start=1981, year_end=2024, month_start=1, month_end=12)
realization_sel = "r1i1p1f1"
scenarios = ["ssp245", "ssp585"]  # in addition to historical


def main(update_config: DateUpdateArgs, realization_gcm, scenarios_gcm, output_dir=domains_extent_file):
    lines = []
    for reg_sel in cpd_region_list.keys():
        lines.append(f"=== REGION: {reg_sel} ===\n")
        for scenario in scenarios_gcm:
            lon_min, lon_max, lat_min, lat_max = main_esm(
                domain=reg_sel,
                scenario=scenario,
                realization=realization_gcm
            )
            TLC = (lon_min, lat_max)
            TRC = (lon_max, lat_max)
            BLC = (lon_min, lat_min)
            BRC = (lon_max, lat_min)
            block = (
                f"Scenario: {scenario}\n"
                f"Realization: {realization_gcm}\n"
                f"TLC: {TLC}\n"
                f"TRC: {TRC}\n"
                f"BLC: {BLC}\n"
                f"BRC: {BRC}\n"
                f"------------------------------\n"
            )
            lines.append(block)
        main_obs(update_config, reg_sel, lon_min, lon_max, lat_min, lat_max)
        lines.append("\n")
    filename = os.path.join(output_dir)
    with open(filename, "w") as f:
        f.writelines(lines)


# main observations and climate model outputs
def main_obs(update_config: DateUpdateArgs, domain, lon_min, lon_max, lat_min, lat_max):
    path_chirps_compressed = get_compressed_folder(CHIRPS_CONFIG, variable="total_precipitation")
    create_folder(path_chirps_compressed)
    if update_config.year_start < 1950:
        raise AttributeError("Minimum year is 1950.")
    for year_sel in list(range(update_config.year_start, update_config.year_end + 1)):
        if year_sel > 1980:
            path_chirps_ref, path_chirps_ref_year = get_ref_paths(CHIRPS_CONFIG, year_sel,
                                                                  variable="total_precipitation")
            min_val_chirps = CHIRPS_CONFIG["value_ranges"]["total_precipitation"]["min"]
            max_val_chirps = CHIRPS_CONFIG["value_ranges"]["total_precipitation"]["max"]
            check_files_year_obs(continent=domain, lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max,
                                 input_path=path_chirps_ref, year=year_sel,
                                 variable="total_precipitation",
                                 source="CHIRPS", path_base=path_chirps_compressed, version="version 3",
                                 min_val=min_val_chirps, max_val=max_val_chirps,
                                 link="https://www.chc.ucsb.edu/data/chirps3", start_year="1981")

        excluded_variables = ["surface_pressure", "2m_dewpoint_temperature", "2m_dewpoint_temperature_daymin",
                              "2m_dewpoint_temperature_daymax", "population_era5land", "total_precipitation",
                              "surface_solar_radiation_downwards", "surface_thermal_radiation_downwards", ]
        variables_era5land = [
            var for var in ERA5_LAND_CONFIG["variables"] if var not in excluded_variables
        ]
        for variable_sel in variables_era5land:
            path_era5land_compressed = get_compressed_folder(ERA5_LAND_CONFIG, variable=variable_sel)
            create_folder(path_era5land_compressed)
            min_val_era5land = ERA5_LAND_CONFIG["value_ranges"][variable_sel]["min"]
            max_val_era5land = ERA5_LAND_CONFIG["value_ranges"][variable_sel]["max"]
            path_era5land_ref, path_era5land_ref_year = get_ref_paths(ERA5_LAND_CONFIG, year_sel, variable_sel)
            check_files_year_obs(continent=domain, lon_min=lon_min, lon_max=lon_max, lat_min=lat_min, lat_max=lat_max,
                                 input_path=path_era5land_ref, year=year_sel,
                                 variable=variable_sel,
                                 source="ERA5-Land", path_base=path_era5land_compressed, version="extracted 2025",
                                 min_val=min_val_era5land, max_val=max_val_era5land,
                                 link="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview",
                                 start_year="1950")


def main_esm(domain, scenario, realization):
    for model_sel in MODEL_CONFIGS:
        if model_sel == "UKESM1.0-LL":
            realization_gcm = replace_f_number(realization, 2)
        else:
            realization_gcm = realization
        for variable_sel in MODEL_CONFIGS[model_sel]["variables"]:
            var = get_abbreviation(variable_sel)
            (var_hist_dbccamodel, var_scen_dbccamodel,
             esm_path_historical_dbcca, esm_path_scenario_dbcca) = load_model_data(continent=domain,
                                                                                   var=var,
                                                                                   model=model_sel,
                                                                                   scen=scenario,
                                                                                   real=realization_gcm)
            min_val_model = MODEL_CONFIGS[model_sel]["value_ranges"][variable_sel]["min"]
            max_val_model = MODEL_CONFIGS[model_sel]["value_ranges"][variable_sel]["max"]
            check_files_years_esm(ds=var_scen_dbccamodel, variable=variable_sel, min_val=min_val_model,
                                  max_val=max_val_model, model=model_sel, path_external=esm_path_scenario_dbcca,
                                  start_year="2015",
                                  scen=scenario)
            check_files_years_esm(ds=var_hist_dbccamodel, variable=variable_sel, min_val=min_val_model,
                                  max_val=max_val_model, model=model_sel, path_external=esm_path_historical_dbcca,
                                  start_year="1985",
                                  scen="historical")
            lon_min, lon_max, lat_min, lat_max = get_corners(var_hist_dbccamodel)
    return lon_min, lon_max, lat_min, lat_max


# checks
def check_files_year_obs(continent, lon_min, lon_max, lat_min, lat_max, input_path, year,
                         variable, path_base, source, version, link, min_val, max_val, start_year="1950"):
    files_merged_ref_veg = get_files_by_pattern(input_path, str(year))  #
    pattern = "_0_1_deg"
    filtered_files = [file for file in files_merged_ref_veg if pattern in file]
    ds = xr.open_dataset(os.path.join(input_path, filtered_files[0]), engine="netcdf4")
    check_leapyear(ds)
    var = get_abbreviation(variable)
    unit = get_unit(variable)
    data_clipped = process_and_clip_continent(ds, lon_min, lon_max, lat_min, lat_max)
    data_clipped, correction = clip_outliers_check(data_clipped, var, min_val, max_val)

    pattern = "{}_{}_{}_compressed.nc".format(continent, variable, year)
    path_file = os.path.join(path_base, pattern)
    variable_long_extended = get_long_variable(variable)
    conventions_obs(ds, var, variable, variable_long_extended, unit, start_year, source, version, link)
    if not os.path.exists(path_file):
        compress(path_file, data_clipped, var, start_year)
    ds.close()
    data_clipped.close()


def check_files_years_esm(ds, variable, min_val, max_val, model, path_external,
                          start_year, scen, path_storage=get_global_projections):
    check_leapyear(ds)
    var = get_abbreviation(variable)
    unit = get_unit(variable)
    variable_long_extended = get_long_variable(variable)
    ds, correction = clip_outliers_check(ds, var, min_val, max_val)
    if correction:
        esm_path = os.path.join(path_storage, "corrected", scen)
        create_folder(esm_path)
        basename = os.path.basename(path_external)
        path_storage_corrected = os.path.join(esm_path, basename)
        conventions_esm(ds, var, variable, variable_long_extended, unit, start_year, model, scen)
        compress(path_storage_corrected, ds, var, start_year)
    ds.close()


def clip_outliers_check(ds, var, min_val, max_val):
    corr = False
    data = ds[var]
    below_min = (data < min_val).sum().item()
    above_max = (data > max_val).sum().item()
    if below_min > 0 or above_max > 0:
        ds[var] = data.clip(min=min_val, max=max_val)
        print(
            f"File {ds}: Clipped '{var}' values. Below min: {below_min}, Above max: {above_max}")
        corr = True
    return ds, corr


# helper
def process_and_clip_continent(data, lon_min, lon_max, lat_min, lat_max, crs_reference=crs_reference_global):
    data.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
    dataarray = data.rio.write_crs(crs_reference)
    clipped_nc = clip_xarray_to_region(dataarray, lon_min, lon_max, lat_min, lat_max)
    return clipped_nc


def clip_xarray_to_region(dataarray, lon_min, lon_max, lat_min, lat_max):
    clipped = dataarray.sel(
        lon=slice(lon_min, lon_max),
        lat=slice(lat_min, lat_max)
    )
    return clipped


def get_corners(ds):
    lon_min = ds.lon.min().item()
    lon_max = ds.lon.max().item()
    lat_min = ds.lat.min().item()
    lat_max = ds.lat.max().item()
    return lon_min, lon_max, lat_min, lat_max


if __name__ == "__main__":
    main(config, realization_sel, scenarios)
