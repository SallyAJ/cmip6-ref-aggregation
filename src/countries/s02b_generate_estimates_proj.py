# Copyright © 2026 Sally Jahn (GitHubID: SallyAJ)

# ScriptOverview
# Example script demonstrating how to create daily estimates of climate variables,
# aggregated across different administrative levels for a specific country.
# This example focuses on the analysis for a single selected country.

# Input: DBCCA-adjusted climate model outputs from 6 CMIP models.
# Output: area-specific gridded information based on GADM national borders and admin units [nc],
# area-level estimates (cosine of latitude as proxy).

# We created area-level estimates for over 100 countries (GADM admin unit levels 1 and 2). Final estimates are provided
# in Parquet-format.

import os
import pandas as pd
import geopandas as gpd
import numpy as np
import rioxarray
import hdf5plugin
import xarray as xr
import re

from src.config.data_catalog import (get_country_gadm, get_dbcca, get_countries_base, get_countries_projections,
                                     domains_file_subset, get_countries_observation)
from src.config.data_sets import MODEL_CONFIGS, get_abbreviation
from src.config.param import crs_reference_global, admin_unit_levels, missing_value
from src.utils.path_helper import create_folder, file_storage
from src.utils.data_helper import replace_f_number
from src.utils.avg_helper import (admin_name_func, define_names, clip_pixel_admin_units_levels,
                                  weights_cos_lat, weighted_mean, get_domain_from_country)
from src.utils.grid_helper import get_area

# global parameters
realization = "r1i1p1f1"  # "r2i1p1f1", "r3i1p1f1", etc.
scenarios = ["historical", "ssp245", "ssp585"]
country_code_sel = "VEN"  # select country


def main(domain, country_code, scenarios_list):
    for scenario in scenarios_list:
        shape_country_level = get_country_gadm(country_code, admin_level="ADM_0")
        for model_name, model_config in MODEL_CONFIGS.items():
            datasets_local = load_files(
                domain, model_name=model_name, scenario=scenario, model_config=model_config,
                shapefile_boundaries=shape_country_level
            )
            for admin_unit in admin_unit_levels:
                shape_admin = get_country_gadm(country_code, admin_level=admin_unit)
                if shape_admin is None:
                    continue
                admin_names_list = admin_name_func(shape_admin, admin_level=admin_unit)
                indices_list = shape_admin.index.values
                if shape_admin is not None:
                    # Sequential execution for clarity (replacing the original multiprocessing block)
                    for index in indices_list:
                        run_country_sequential(domain=domain,
                                               index=index,
                                               shape_admin=shape_admin,
                                               country_code=country_code,
                                               admin_unit_level=admin_unit,
                                               datasets=datasets_local,
                                               model_name=model_name,
                                               model_config=model_config,
                                               scenario=scenario,
                                               admin_names=admin_names_list
                                               )


# ============================================================
# Originally implemented using parallel processing, but rewritten here
# for clarity and easier sequential execution.
# ============================================================


def run_country_sequential(domain, index, country_code, admin_unit_level, shape_admin, datasets, model_name, model_config,
                           scenario, admin_names):
    polygon = shape_admin.geometry.iloc[index]
    polygon_gdf = gpd.GeoDataFrame(geometry=[polygon], crs=crs_reference_global)
    cleaned_admin_unit_name = define_names(admin_names[index])
    variables = model_config["variables"]
    esm_country_avg(domain=domain, polygon_gdf=polygon_gdf,
                    cleaned_admin_unit_name=cleaned_admin_unit_name, admin_unit_level=admin_unit_level,
                    country=country_code, scenario=scenario,
                    model_name=model_name, variables=variables, variable_to_country_paths=datasets)


# area-level estimates per country
def esm_country_avg(domain, polygon_gdf, cleaned_admin_unit_name, admin_unit_level, country, scenario, model_name,
                    variables,
                    variable_to_country_paths):
    path_country = os.path.join(get_countries_projections(), country)
    start, end = get_scenario_settings(scenario)
    if model_name == "UKESM1.0-LL":
        realization_sel = replace_f_number(realization, 2)
    else:
        realization_sel = realization
    information_model = "{}_{}".format(realization_sel, scenario)
    storage_path_pq_admin_model = create_storage_path(path_country, domain, cleaned_admin_unit_name, admin_unit_level, model_name,
                                                      start, end, information_model, "pq")
    if not os.path.exists(storage_path_pq_admin_model):
        result_esm = pq_file_esm(
            polygon_gdf=polygon_gdf,
            variable_to_country_paths=variable_to_country_paths,
            cleaned_admin_unit_name=cleaned_admin_unit_name,
            variables=variables
        )
        if not os.path.exists(storage_path_pq_admin_model):
            file_storage(start, end, result_esm, storage_path_pq_admin_model)


def pq_file_esm(polygon_gdf, variable_to_country_paths, cleaned_admin_unit_name, variables):
    admin_area_km2 = get_area(polygon_gdf)
    entry = {"admin_name": cleaned_admin_unit_name}
    entry["admin_area_km2"] = admin_area_km2
    for variable in variables:
        var_name = get_abbreviation(variable)
        ds_var = variable_to_country_paths[variable]
        mean_values_area, num_pixels_nc = (
            combine_years_esm(ds_var, var_name, polygon_gdf)
        )
        entry[f"{var_name}_simple"] = mean_values_area
        entry["pixels"] = num_pixels_nc
    return entry


def combine_years_esm(ds_sel, var_abb, polygon_gdf):
    clipped_nc_admin, num_pixels_nc = clip_pixel_admin_units_levels(ds_sel, polygon_gdf, var_abb)
    clipped_nc_weighted, weights_single = weights_cos_lat(clipped_nc_admin)
    mean_area = weighted_mean(clipped_nc_weighted)
    da_mean_area = mean_area[var_abb]
    mean_values_area = da_mean_area.where(np.isfinite(da_mean_area), missing_value).values.tolist()
    ds_sel.close()
    clipped_nc_admin.close()
    return mean_values_area, num_pixels_nc


# load data
def load_files(reg_sel, model_name, model_config, shapefile_boundaries, scenario, realization_sel=realization):
    start, end = get_scenario_settings(scenario)
    path_source = os.path.join(get_dbcca(), scenario.upper())
    variables = model_config["variables"]
    datasets = {}
    for variable in variables:
        var_abb = get_abbreviation(variable)
        if model_name == "UKESM1.0-LL":
            realization_chosen = replace_f_number(realization_sel, 2)
        else:
            realization_chosen = realization_sel
        ds_file = prepare_continent_file_model(shapefile_boundaries, scenario, start, end, realization_chosen,
                                               path_source, reg_sel, var_abb, model_name)
        datasets[variable] = ds_file
    return datasets


def prepare_continent_file_model(shapefile_boundaries, scenario, start, end, realization, path_source, continent,
                                 var_abb, model, crs_reference=crs_reference_global):
    pattern = "{}_{}_DBCCA_{}_{}_{}_{}_{}_compressed.nc".format(
        continent, var_abb, model, start, end, realization, scenario
    )
    path_file = os.path.join(path_source, pattern)
    ds = xr.open_dataset(path_file, engine="h5netcdf")
    ds.rio.write_crs(crs_reference, inplace=True)
    if "time_bnds" in ds.data_vars:
        ds = ds.drop_vars("time_bnds")
    ds_clip_ad0, num_pix_ad0 = clip_pixel_admin_units_levels(ds, shapefile_boundaries, var_abb)
    return ds_clip_ad0


# helper
def get_scenario_settings(scenario):
    if scenario == "historical":
        start = 1985
        end = 2014
    elif scenario == "ssp245":
        start = 2015
        end = 2100
    else:
        start = 2015
        end = 2100
    return start, end


def get_level_gadm(admin_level):
    level = admin_level.lower().replace("_", "")
    return level


# storage
def create_storage_path(storage_path, continent, gadm_code, admin_unit_level, data_source, start, end, information, end_format):
    create_folder(storage_path)
    admin_level = get_level_gadm(admin_unit_level)
    storage_path_format = os.path.join(storage_path, "{}_{}_{}_reference_{}_{}_{}{}.{}".format(continent, gadm_code,
                                                                                               data_source, str(start),
                                                                                               str(end), information,
                                                                                               admin_level, end_format))
    if "?" in storage_path_format:
        storage_path_format = storage_path_format.replace("Europe_?_v410_", "Europe_UKR_v410_unknown_")

    if "_GHA" in storage_path_format:
        storage_path_format = re.sub(
            r"(Africa_GHA)([^_]+(?:_[^_]+)*)_v410",
            lambda m: f"{m.group(1)}_v410_{m.group(2)}",
            storage_path_format
        )
    return storage_path_format


if __name__ == "__main__":
    create_folder(get_countries_base())
    create_folder(get_countries_projections())
    create_folder(get_countries_observation())
    domain_df = pd.read_csv(domains_file_subset, sep="\t")
    domain_sel = get_domain_from_country(domain_df, country_code_sel)
    main(domain_sel, country_code_sel, scenarios)
