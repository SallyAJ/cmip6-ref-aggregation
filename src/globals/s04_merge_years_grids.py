# ScriptOverview
# Preparation of data (based on the processed outputs of all "_processing.py" scripts) to generate yearly NetCDF files
# on various grids (0.1° for downscaling; 1° for comparisons with global climate model outputs). Based on the spatial
# extent of the data, the final outputs are sliced from 60°S to 60°N (180°W - 180°E).

import os
import xarray as xr
from src.config.args import DateUpdateArgs
from src.config.data_sets import CHIRPS_CONFIG, ERA5_LAND_CONFIG, get_abbreviation_era5, harmonize_abbrevation, \
    get_merged_path_filename
from src.config.data_catalog import get_grid_raw, get_merged_folder, \
    get_processed_folder, get_ref_folder
from src.utils.path_helper import get_files_by_pattern, write_nc_file
from src.utils.cdo_helper import get_cdo, main_grid_lon_lat
from src.utils.grid_helper import regrid_domain_conservative, regrid_domain_bilinear


config = DateUpdateArgs(year_start=1981, year_end=2024, month_start=1, month_end=12)
cdo_domain_1deg_txt = os.path.join(get_grid_raw(), 'grid_1deg_quasiglobal.txt')
cdo_domain_01deg_txt = os.path.join(get_grid_raw(), 'grid_0_1deg_quasiglobal.txt')

def main(update_config: DateUpdateArgs, cdo_domain_01deg, cdo_domain_1deg):
    if update_config.year_start < 1950:  # ERA5-Land is available from 1950.
        raise AttributeError("Minimum year is 1950.")
    for year_sel in list(range(update_config.year_start, update_config.year_end + 1)):
        if year_sel > 1980:
            path_chirps_merged_year, path_chirps_merged_year_box, path_chirps_merged_year_time = get_merged_paths(
                CHIRPS_CONFIG, year_sel,
                variable="total_precipitation")
            path_chirps_ref_year_1deg = get_ref_paths(CHIRPS_CONFIG, year_sel, variable="total_precipitation",
                                                      resolution="1_deg")
            path_chirps_ref_year_01deg = get_ref_paths(CHIRPS_CONFIG, year_sel, variable="total_precipitation",
                                                       resolution="0_1_deg")
            path_var_store_chirps = get_processed_folder(CHIRPS_CONFIG, "total_precipitation")
            merge_files_year(path_var_store_chirps, "Band1", "pr", year_sel, path_chirps_merged_year,
                             path_chirps_merged_year_box, path_chirps_merged_year_time, lon_min=-180, lon_max=180,
                             lat_min=-60,
                             lat_max=60)
            regrid_domain_conservative(cdo_domain_01deg, path_chirps_merged_year, path_chirps_ref_year_01deg)
            regrid_domain_conservative(cdo_domain_1deg, path_chirps_merged_year, path_chirps_ref_year_1deg)
            os.remove(path_chirps_merged_year)
        excluded_variables = ["surface_pressure", "2m_dewpoint_temperature", "2m_dewpoint_temperature_daymin",
                              "2m_dewpoint_temperature_daymax", "population_era5land",
                              "surface_solar_radiation_downwards", "surface_thermal_radiation_downwards",
                              "total_precipitation"]
        variables_era5land = [
            var for var in ERA5_LAND_CONFIG["variables"] if var not in excluded_variables
        ]
        for variable_sel in variables_era5land:
            var_abb = get_abbreviation_era5(variable_sel)
            var_abb_harm = harmonize_abbrevation(var_abb)
            if variable_sel == "2m_temperature_daymax":
                var_abb_harm = "tasmax"
            if variable_sel == "2m_temperature_daymin":
                var_abb_harm = "tasmin"
            path_era5land_merged_year, path_era5land_merged_year_box, path_era5land_merged_year_time = get_merged_paths(
                ERA5_LAND_CONFIG, year_sel,
                variable_sel)
            path_era5land_ref_year_1deg = get_ref_paths(ERA5_LAND_CONFIG, year_sel, variable=variable_sel,
                                                        resolution="1_deg")
            path_era5land_ref_year_01deg = get_ref_paths(ERA5_LAND_CONFIG, year_sel, variable=variable_sel,
                                                         resolution="0_1_deg")
            path_var_store_era5land = get_processed_folder(ERA5_LAND_CONFIG, variable_sel)
            merge_files_year(path_var_store_era5land, var_abb, var_abb_harm, year_sel, path_era5land_merged_year,
                             path_era5land_merged_year_box, path_era5land_merged_year_time,
                             lon_min=-180, lon_max=180, lat_min=-60,
                             lat_max=60)
            regrid_domain_bilinear(cdo_domain_01deg, path_era5land_merged_year, path_era5land_ref_year_01deg)
            regrid_domain_bilinear(cdo_domain_1deg, path_era5land_merged_year, path_era5land_ref_year_1deg)
            os.remove(path_era5land_merged_year)


def merge_files_year(input_path, org_name, new_name, year, path_merged_year, path_merged_year_box, output_file_time,
                     lon_min,
                     lon_max, lat_min,
                     lat_max):
    files_year = get_files_by_pattern(input_path, str(year))
    input_files_with_path = [os.path.join(input_path, file) for file in files_year]
    if not os.path.exists(path_merged_year):
        get_cdo().mergetime(input=" ".join(input_files_with_path), output=output_file_time)
        main_grid_lon_lat(output_file_time, path_merged_year_box, minlat=lat_min, maxlat=lat_max, minlon=lon_min,
                          maxlon=lon_max)
        ds = change_time_name(path_merged_year_box, org_name, new_name)
        write_nc_file(ds, new_name, path_merged_year)
        os.remove(path_merged_year_box)


def change_time_name(path_merged_year_box, org_name, new_name):
    output = xr.open_dataset(path_merged_year_box, engine="netcdf4")
    domain_output = output.rename(
        {org_name: new_name})
    if 'valid_time' in domain_output.dims:
        domain_output = domain_output.rename({'valid_time': 'time'})
    if 'valid_time_bnds' in domain_output.dims:
        domain_output = domain_output.drop_vars('valid_time_bnds')
    return domain_output


# paths and names
def get_ref_path_filename(ref_path, variable, year, resolution):
    output_file_ref = os.path.join(ref_path, "{}_years_{}_{}_grid.nc".format(variable, year, resolution))
    return output_file_ref


def get_merged_paths(data_config, year, variable):
    merged_path = get_merged_folder(data_config, variable)
    path_merged_year, path_merged_year_box, output_file_time = get_merged_path_filename(merged_path, variable, year)
    return path_merged_year, path_merged_year_box, output_file_time


def get_ref_paths(data_config, year, variable, resolution):
    ref_path = get_ref_folder(data_config, variable)
    path_ref_year = get_ref_path_filename(ref_path, variable, year, resolution)
    return path_ref_year


if __name__ == "__main__":
    main(config, cdo_domain_01deg_txt, cdo_domain_1deg_txt)
