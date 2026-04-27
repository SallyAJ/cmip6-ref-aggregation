#######################################################################
# ScriptOverview
# Example script demonstrating how to create daily, population-weighted estimates of climate variables,
# aggregated across different administrative levels for a specific country.
# This example focuses on the analysis for a single selected country.

# Input: DBCCA-adjusted climate model outputs from 6 CMIP models.
# Output: area-specific gridded information based on GADM national borders and admin units [nc], (population-weighted)
# area-level estimates (cosine of latitude as proxy / weighted by SEDAC population).

# We created area-level estimates for over 100 countries (GADM admin unit levels 1 and 2). Final estimates are provided
# in parquet-format.

# For further information on underlying data sources and methods (including GADM, which is considered an external
# dataset), please refer to this README and the associated Scientific Data Descriptor publication.

import os
import pandas as pd
import geopandas as gpd
import numpy as np
import rioxarray
import hdf5plugin
import xarray as xr

from src.config.data_catalog import (get_country_gadm, get_dbcca, get_countries_base, get_countries_projections,
                                     domains_file_subset, get_countries_observation)
from src.config.data_sets import SEDAC_CONFIG, MODEL_CONFIGS, get_abbreviation
from src.config.param import crs_reference_global, admin_unit_levels, missing_value
from src.utils.path_helper import create_folder,  file_storage
from src.utils.data_helper import replace_f_number
from src.utils.avg_helper import (admin_name_func, define_names,  clip_pixel_admin_units_levels,
                                  weights_cos_lat, weighted_mean, get_domain_from_country)
from src.utils.pop_helper import (prepare_pop, get_pop_for_year, weights_pop, _clip_pop_to_country,
                                  load_decadal_populations, get_decade)


# global parameters
realization = "r1i1p1f1"  # "r2i1p1f1", "r3i1p1f1", etc.
scenarios = ["historical", "ssp245", "ssp585"]
country_code_sel = "VEN" # select country


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
                            shapefile_ad0=shape_country_level,
                            country_code=country_code,
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


def run_country_sequential(domain,  index, country_code, shapefile_ad0, shape_admin, datasets, model_name, model_config,
        scenario, admin_names):
    pop_ssp2 = load_population_for_country(SEDAC_CONFIG, shapefile_ad0, scenario) if scenario in ["historical", "ssp245"] else None
    pop_ssp5 = load_population_for_country(SEDAC_CONFIG, shapefile_ad0, scenario) if scenario == "ssp585" else None
    polygon = shape_admin.geometry.iloc[index]
    polygon_gdf = gpd.GeoDataFrame(geometry=[polygon], crs=crs_reference_global)
    cleaned_admin_unit_name = define_names(admin_names[index])
    variables = model_config["variables"]
    esm_country_avg(domain=domain, pop_ssp2=pop_ssp2, pop_ssp5=pop_ssp5, polygon_gdf=polygon_gdf,
        cleaned_admin_unit_name=cleaned_admin_unit_name, country=country_code, scenario=scenario,
        model_name=model_name, variables=variables, variable_to_country_paths=datasets)


# area-level estimates per country
def esm_country_avg(domain, pop_ssp2, pop_ssp5, polygon_gdf, cleaned_admin_unit_name, country, scenario, model_name, variables, variable_to_country_paths):
    path_country = os.path.join(get_countries_projections(), country)
    start, end, pop_grids = get_scenario_settings(scenario, pop_ssp2, pop_ssp5)
    if model_name == "UKESM1.0-LL":
        realization_sel = replace_f_number(realization, 2)
    else:
        realization_sel = realization
    information_model = "{}_{}".format(realization_sel, scenario)
    storage_path_pq_admin_model = create_storage_path(path_country, domain, cleaned_admin_unit_name, model_name,
        start, end, information_model,"parquet.gzip")
    if not os.path.exists(storage_path_pq_admin_model):
        result_esm = pq_file_esm(
            polygon_gdf=polygon_gdf,
            variable_to_country_paths=variable_to_country_paths,
            cleaned_admin_unit_name=cleaned_admin_unit_name,
            variables=variables,
            population=pop_grids,
        )
        if not os.path.exists(storage_path_pq_admin_model):
            file_storage(start, end, result_esm, storage_path_pq_admin_model)


def pq_file_esm(polygon_gdf, variable_to_country_paths, cleaned_admin_unit_name, variables, population):
    entry = {"admin_name": cleaned_admin_unit_name}
    for variable in variables:
        var_name = get_abbreviation(variable)
        ds_var = variable_to_country_paths[variable]
        mean_values_pop, mean_values_area, mean_values_pop_dynamic, num_pixels_nc = (
            combine_years_esm(ds_var, var_name, polygon_gdf, population)
        )
        entry[f"{var_name}_simple"] = mean_values_area
        entry[f"{var_name}_static"] = mean_values_pop
        entry[f"{var_name}_dynamic"] = mean_values_pop_dynamic
        entry["pixels"] = num_pixels_nc
    return entry


def combine_years_esm(ds_sel, var_abb, polygon_gdf, pop_grids):
    clipped_nc_admin, num_pixels_nc = clip_pixel_admin_units_levels(ds_sel, polygon_gdf, var_abb)
    decade_pop_cache = {}
    _pop_raw = get_pop_for_year(2000, pop_grids)
    _pop_prep = prepare_pop(_pop_raw, polygon_gdf, clipped_nc_admin)
    _pop_da = _pop_prep["population"]
    decade_pop_cache[2000] = (_pop_prep, np.isfinite(_pop_da) & _pop_da.notnull())
    for _y in np.unique(clipped_nc_admin.time.dt.year.values):
        _decade = get_decade(_y)
        if _decade not in decade_pop_cache:
            _pop_raw = get_pop_for_year(int(_y), pop_grids)
            _pop_prep = prepare_pop(_pop_raw, polygon_gdf, clipped_nc_admin)
            _pop_da = _pop_prep["population"]
            decade_pop_cache[_decade] = (_pop_prep, np.isfinite(_pop_da) & _pop_da.notnull())
    population_values, pop_mask_2000 = decade_pop_cache[2000]
    clipped_nc_weighted, weights_single = weights_cos_lat(clipped_nc_admin)
    mean_area = weighted_mean(clipped_nc_weighted)
    da_mean_area = mean_area[var_abb]
    mean_values_area = da_mean_area.where(np.isfinite(da_mean_area), missing_value).values.tolist()
    mean_values_pop = weights_pop(clipped_nc_admin, population_values, var_abb, pop_mask=pop_mask_2000)
    mean_values_pop_dynamic = []
    for year, ds in clipped_nc_admin.groupby("time.year"):
        _decade = get_decade(year)
        population_values_year, pop_mask_year = decade_pop_cache[_decade]
        daily_means_year = weights_pop(ds, population_values_year, var_abb, pop_mask=pop_mask_year)
        mean_values_pop_dynamic.append(daily_means_year)
    ds_sel.close()
    clipped_nc_admin.close()
    return mean_values_pop, mean_values_area, mean_values_pop_dynamic, num_pixels_nc


# load data
def load_files(reg_sel, model_name, model_config, shapefile_boundaries, scenario, realization_sel=realization,
):
    start, end, pop_grids = get_scenario_settings(scenario, None, None)
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


# load population data
def load_population_for_country(sedac_config, country_shapefile_ad0, scenario):
    if scenario in ["historical", "ssp245"]:
        pop_ssp2_raw = load_decadal_populations(
            sedac_config, scenario="SSP2", start_year=2000, end_year=2100, step=10
        )
        return {
            decade: _clip_pop_to_country(da, country_shapefile_ad0)
            for decade, da in pop_ssp2_raw.items()
        }
    elif scenario == "ssp585":
        pop_ssp5_raw = load_decadal_populations(
            sedac_config, scenario="SSP5", start_year=2000, end_year=2100, step=10
        )
        return {
            decade: _clip_pop_to_country(da, country_shapefile_ad0)
            for decade, da in pop_ssp5_raw.items()
        }
    return None


# helper
def get_scenario_settings(scenario, pop_ssp2, pop_ssp5):
    if scenario == "historical":
        start = 1985
        end = 2014
        pop_grids = pop_ssp2
    elif scenario == "ssp245":
        start = 2015
        end = 2100
        pop_grids = pop_ssp2
    else:
        start = 2015
        end = 2100
        pop_grids = pop_ssp5
    return start, end, pop_grids


# storage
def create_storage_path(storage_path, continent, gadm_code, data_source, start, end, information, end_format):
    create_folder(storage_path)
    storage_path_format = os.path.join(storage_path, "{}_{}_{}_{}_{}_{}.{}".format(
            continent, gadm_code, data_source, str(start), str(end), information, end_format))
    return storage_path_format


if __name__ == "__main__":
    create_folder(get_countries_base())
    create_folder(get_countries_projections())
    create_folder(get_countries_observation())
    domain_df = pd.read_csv(domains_file_subset, sep="\t")
    domain_sel = get_domain_from_country(domain_df, country_code_sel)
    main(domain_sel, country_code_sel, scenarios)