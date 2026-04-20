# Area-level Estimates

import sys
from shapely.geometry import mapping
import numpy as np
from src.config.param import gadm_version

# check crs
def check_crs_reference(data_var, shapefile):
    if data_var.rio.crs != shapefile.crs:
        sys.exit()

# weighting schemes
def weights_cos_lat(nc_data):
    weights = np.cos(np.deg2rad(nc_data.lat))
    weights.name = "weights"
    weights = weights.fillna(0).copy()
    dataset_weighted = nc_data.weighted(weights)
    return dataset_weighted, weights


def weighted_mean(ds_weight):
    ds_weight_area = ds_weight.mean(("lat", "lon"), skipna=True)
    return ds_weight_area


# clip
def clip_nc(data_var, shapefile):
    data_var.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
    check_crs_reference(data_var, shapefile)
    clipped_nc = data_var.rio.clip(shapefile.geometry.apply(mapping),
                                   drop=True,
                                   all_touched=True)
    return clipped_nc


def clip_pixel_admin_units_levels(data_var, shapefile_boundaries, var_abb):
    clipped_nc, num_pixels = clip_shape_files(data_var, shapefile_boundaries, var_abb)
    return clipped_nc, num_pixels


def clip_shape_files(data_var, shapefile, var_abb):
    check_crs_reference(data_var, shapefile)
    clipped_nc = clip_nc(data_var, shapefile)
    num_pixels = clipped_nc[var_abb].notnull().sum().item()
    return clipped_nc, num_pixels


# admin names
def admin_name_func(shape_admin, admin_level):
    admin_number = "GID_{}".format(admin_level[-1])
    gadm_code = shape_admin[admin_number]
    return gadm_code


def define_names(raw_names):
    if "." not in raw_names:
        clean_name = raw_names + "_" + gadm_version
    else:
        parts = raw_names.split('.', 1)
        clean_name = parts[0] + "_" + gadm_version + "_" + parts[1]
        clean_name = clean_name.replace(".", "_")
    return clean_name


# country selection
def get_domain_from_country(domain_df, country):
    result = domain_df.loc[domain_df["country"] == country, "region"]
    if not result.empty:
        return result.iloc[0]
    return None
