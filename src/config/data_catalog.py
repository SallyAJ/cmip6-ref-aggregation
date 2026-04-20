import os
from src.utils.path_helper import create_folder
import geopandas as gpd
from src.config.param import crs_reference_number

# get_grid_raw returns the path to the grid directory containing spatial grid definitions.
# An example "grids" folder is provided in the repository and can be copied into the corresponding local workflow
# structure.


# cluster / server storage
data_dir_centre = os.getenv("DATA_DIR_CENTRE", None)
if data_dir_centre is None:
    raise ValueError("DATA_DIR_CENTRE environment variable is not set. Please set it to the base data directory.")


def get_base_data_dir():
    return data_dir_centre


# Global 
def get_global_base():
    return os.path.join(get_base_data_dir(), "global")


def get_global_observation():
    return os.path.join(get_global_base(), "observation")


def get_global_projections():
    return os.path.join(get_global_base(), "projections")


# Grids
# Returns the path to the grid directory containing spatial grid definitions.
# An example "grids" folder is provided in the repository and can be copied into the corresponding local workflow
# structure.
def get_grid_raw():
    path = os.path.abspath(os.path.join(get_global_base(), "grids"))
    create_folder(path)
    return path


# GADM
def get_gadm_raw():
    return os.path.join(os.path.join(get_global_observation(), "external", "GADM", "gadm_410-levels.gpkg"))


def get_country_gadm(country_sel, admin_level, crs_reference=crs_reference_number):
    gadm_raw_path = get_gadm_raw()
    df_gadm = gpd.read_file(gadm_raw_path, driver="GPKG", layer=admin_level)
    df_gadm_crs = df_gadm.to_crs(epsg=crs_reference).copy()
    df_gadm_crs_country = df_gadm_crs[df_gadm_crs["GID_0"] == country_sel].reset_index(drop=True).copy()
    if df_gadm_crs_country.empty:
        return None
    return df_gadm_crs_country


# SEDAC
def get_sedac_raw():
    return os.path.join(os.path.join(get_global_observation(), "external", "SEDAC"))


# Projections
def get_dbcca():
    return os.path.join(os.path.join(get_global_projections(), "external"))


# Countries 
def get_countries_base():
    return os.path.join(get_base_data_dir(), "countries")


def get_countries_observation():
    return os.path.join(get_countries_base(), "observation")


def get_countries_projections():
    return os.path.join(get_countries_base(), "projections")


# get download and processing folders

def get_path(config, folder, variable=None):
    assert config["id"]
    if variable is None:
        path = os.path.abspath(os.path.join(get_global_observation(), config["id"], folder))
    else:
        assert config["variables"] and variable in config["variables"]
        path = os.path.abspath(os.path.join(get_global_observation(), config["id"], folder, variable))
    create_folder(path)
    return path


def get_download_folder(config, variable=None):
    return get_path(config, "download", variable)


def get_processed_folder(config, variable=None):
    return get_path(config, "processed", variable)


def get_merged_folder(config, variable=None):
    return get_path(config, "merged", variable)


def get_ref_folder(config, variable=None):
    return get_path(config, "reference", variable)


def get_ref_paths(data_config, year, variable):
    ref_path = get_ref_folder(data_config, variable)
    path_ref_year = get_ref_path_filename(ref_path, variable, year)
    return ref_path, path_ref_year


def get_compressed_folder(config, variable=None):
    return get_path(config, "compressed", variable)


def get_ref_path_filename(ref_path, variable, year):
    output_file_ref = os.path.join(ref_path, "{}_{}.nc".format(variable, year))
    return output_file_ref


# Domains
domains_file = os.path.join(data_dir_centre, "country_regions.txt")
domains_extent_file = os.path.join(data_dir_centre, "domains_extents.txt")
domains_file_subset = os.path.join(data_dir_centre, "country_regions_subset.txt")
