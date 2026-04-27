########################################################################
# ScriptOverview
# Example script demonstrating how to create daily, population-weighted estimates of climate variables,
# aggregated across different administrative levels for a specific country.
# This example focuses on the analysis for a single selected country.

# Input: observational reference climatology (ERA5-Land, CHIRPS).
# Output: area-specific gridded information based on GADM national borders and admin units [nc], (population-weighted)
# area-level estimates (cosine of latitude as proxy / weighted by SEDAC population).

# We created area-level estimates for over 100 countries (GADM admin unit levels 1 and 2). Final estimates are provided
# in parquet-format.

# For further information on underlying data sources and methods (including GADM, which is considered an external
# dataset), please refer to this README and the associated Scientific Data Descriptor publication.

import os
import pandas as pd
import geopandas as gpd
import xarray as xr
import numpy as np
import rioxarray
from src.config.args import DateUpdateArgs
from src.config.data_catalog import (domains_file_subset, get_countries_base, get_compressed_folder,
                                     get_country_gadm, get_countries_observation)
from src.config.data_sets import CHIRPS_CONFIG, ERA5_LAND_CONFIG, SEDAC_CONFIG, get_abbreviation
from src.utils.path_helper import create_folder, file_storage
from src.config.param import crs_reference_global, variables_era5land_list, admin_unit_levels, missing_value
from src.utils.avg_helper import (admin_name_func, define_names, clip_pixel_admin_units_levels,
                                  weights_cos_lat, weighted_mean, get_domain_from_country)
from src.utils.pop_helper import prepare_pop, _clip_pop_to_country, get_pop_for_year, get_decade, weights_pop, \
    load_decadal_populations
from src.utils.data_helper import read_in_time

# global parameters
config = DateUpdateArgs(1981, 2024, 1, 12)
path_chirps_load = get_compressed_folder(CHIRPS_CONFIG, variable="total_precipitation")
country_code_sel = "VEN"  # select country


def main(domain, country_code, period_config, path_chirps, variables_era5land=variables_era5land_list):
    shape_country_ad0 = get_country_gadm(country_code, admin_level="ADM_0")
    ds_variables = {}
    var_abb = get_abbreviation("total_precipitation")
    ds_variables["total_precipitation"] = prepare_continent_file(path_chirps, domain, "total_precipitation",
                                                                 period_config,
                                                                 shape_country_ad0, var_abb)
    for variable in variables_era5land:
        path_era5land_compressed = get_compressed_folder(ERA5_LAND_CONFIG, variable=variable)
        var_abb = get_abbreviation(variable)
        ds_variables[variable] = prepare_continent_file(path_era5land_compressed, domain, variable, period_config,
                                                        shape_country_ad0, var_abb)
    avg_admin(country_code, shape_country_ad0, ds_variables, variables_era5land, domain, period_config)


def prepare_continent_file(path_source, continent, variable, period, shape_ad0, var_abb,
                           crs_reference=crs_reference_global):
    datasets = []
    for year in period:
        pattern = "{}_{}_{}_compressed.nc".format(continent, variable, year)
        path_file = os.path.join(path_source, pattern)
        ds = read_in_time(path_file, year)
        datasets.append(ds)
        ds.close()
    ds_merged = xr.concat(datasets, dim="time")
    ds_merged.rio.write_crs(crs_reference, inplace=True)
    clipped_nc_shape_ad0, num_pixels_nc_ad0 = clip_pixel_admin_units_levels(
        ds_merged, shape_ad0, var_abb
    )
    return clipped_nc_shape_ad0


def avg_admin(country_code, shape_country_ad0, ds_variables, variables_era5land, domain, period_config):
    for admin_unit in admin_unit_levels:
        shape_country = get_country_gadm(country_code, admin_level=admin_unit)
        if shape_country is not None:
            admin_names = admin_name_func(shape_country, admin_level=admin_unit)
            indices_list = shape_country.index.values
            for index in indices_list:
                run_country_obs(country_code, SEDAC_CONFIG, index, shape_country_ad0, shape_country, admin_names,
                                ds_variables,
                                variables_era5land,
                                domain,
                                period_config)


def run_country_obs(country_code, sedac_config, index, shape_country_ad0, shape_country, admin_names, ds_variables,
                    variables_era5land_list,
                    domain,
                    period_config):
    pop_ssp2_raw = load_decadal_populations(
        sedac_config, scenario="SSP2", start_year=2000, end_year=2100, step=10
    )
    POP_SSP2 = {
        decade: _clip_pop_to_country(da, shape_country_ad0)
        for decade, da in pop_ssp2_raw.items()
    }
    polygon = shape_country.geometry.iloc[index]
    polygon_gdf = gpd.GeoDataFrame(geometry=[polygon], crs=crs_reference_global)
    cleaned_admin_unit_name = define_names(admin_names[index])
    pq_file(polygon_gdf=polygon_gdf, cleaned_admin_unit_name=cleaned_admin_unit_name,
            country=country_code,
            period=period_config,
            ds_variables=ds_variables,
            pop_grids_ssp=POP_SSP2,
            variables_era5land=variables_era5land_list,
            reg_sel=domain
            )


def pq_file(polygon_gdf, cleaned_admin_unit_name, country, period, ds_variables, pop_grids_ssp, variables_era5land,
            reg_sel):
    path_country = os.path.join(get_countries_observation(), country)
    storage_path_pq_admin = create_storage_path(
        path_country, reg_sel, cleaned_admin_unit_name,
        "CHIRPSv3_ERA5Land", period[0], period[-1],
        "observation", "parquet.gzip"
    )
    # 1) CHIRPS
    results_chirps = obs_avg(ds_variables, polygon_gdf, cleaned_admin_unit_name,
                             pop_grids_ssp,
                             "total_precipitation")
    merged_records = {rec["admin_name"]: rec for rec in results_chirps}
    # 2) ERA5_Land variables: add to merged_record
    for variable in variables_era5land:
        results_era5_land = obs_avg(ds_variables, polygon_gdf, cleaned_admin_unit_name,
                                    pop_grids_ssp, variable)
        for rec in results_era5_land:
            admin_name = rec["admin_name"]
            if admin_name in merged_records:
                merged_records[admin_name].update(rec)
            else:
                merged_records[admin_name] = rec
    merged_records_list = list(merged_records.values())
    merged_record_sel = merged_records_list[0]
    if not os.path.exists(storage_path_pq_admin):
        file_storage(
            period[0], period[-1],
            merged_record_sel,
            storage_path_pq_admin
        )


def obs_avg(ds_variables, polygon_gdf, cleaned_admin_unit_name, pop_grids, var_long):
    var_name = get_abbreviation(var_long)
    results = []
    mean_values_pop, mean_values_area, mean_values_pop_dynamic, num_pixels_nc = combine_years_obs(var_long,
                                                                                                  ds_variables,
                                                                                                  pop_grids,
                                                                                                  polygon_gdf)
    results.append({
        "admin_name": cleaned_admin_unit_name,
        "pixels": num_pixels_nc,
        f"{var_name}_simple": mean_values_area,
        f"{var_name}_static": mean_values_pop,
        f"{var_name}_dynamic": mean_values_pop_dynamic
    })
    return results


def combine_years_obs(variable, ds_variables, pop_grids, polygon_gdf, crs_reference=crs_reference_global):
    var_abb = get_abbreviation(variable)
    ds_var = ds_variables[variable]
    data = ds_var.rio.write_crs(crs_reference, inplace=True)
    clipped_nc_admin, num_pixels_nc = clip_pixel_admin_units_levels(
        data, polygon_gdf, var_abb
    )
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
            decade_pop_cache[_decade] = (
                _pop_prep,
                np.isfinite(_pop_da) & _pop_da.notnull(),
            )
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
    data.close()
    clipped_nc_admin.close()
    return mean_values_pop, mean_values_area, mean_values_pop_dynamic, num_pixels_nc


# storage
def create_storage_path(storage_path, continent, gadm_code, data_source, start, end, information, end_format):
    create_folder(storage_path)
    storage_path_format = os.path.join(storage_path, "{}_{}_{}_{}_{}_{}.{}".format(continent, gadm_code,
                                                                                   data_source, str(start), str(end),
                                                                                   information,
                                                                                   end_format))
    return storage_path_format


if __name__ == "__main__":
    create_folder(get_countries_base())
    create_folder(get_countries_observation())
    period_config_sel = list(range(config.year_start, config.year_end + 1))
    domain_df = pd.read_csv(domains_file_subset, sep="\t")
    domain_sel = get_domain_from_country(domain_df, country_code_sel)
    main(domain_sel, country_code_sel, period_config_sel, path_chirps=path_chirps_load,
         variables_era5land=variables_era5land_list)
