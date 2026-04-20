# Population Operations

import os
import xarray as xr
import numpy as np
from src.utils.avg_helper import clip_shape_files
from src.config.param import crs_reference_global
from src.config.data_catalog import get_processed_folder
from src.utils.data_helper import read_in_xarray_var_crs


# weighting
def weights_pop(nc_da, pop, var_short, pop_mask=None):
    if isinstance(nc_da, xr.Dataset):
        nc_da = nc_da[var_short]
    if isinstance(pop, xr.Dataset):
        pop = pop["population"]
    if pop_mask is None:
        pop_mask = np.isfinite(pop) & pop.notnull()
    mask = np.isfinite(nc_da) & nc_da.notnull() & pop_mask
    nc_clean = nc_da.where(mask)
    pop_masked = pop.where(mask)
    weighted = (nc_clean * pop_masked).sum(["lat", "lon"])
    total_pop = pop_masked.sum(["lat", "lon"])
    result = xr.where(total_pop > 0, weighted / total_pop, -9999).values.tolist()
    return result


def get_decade(year):
    return 2000 if int(year) < 2000 else (int(year) // 10) * 10


def clip_pixel_admin_units_levels(data_var, shapefile_boundaries, var_abb):
    clipped_nc, num_pixels = clip_shape_files(data_var, shapefile_boundaries, var_abb)
    print("clipped")
    return clipped_nc, num_pixels


def _clip_pop_to_country(da, shapefile_ad0):
    ds = da.to_dataset()
    clipped, _ = clip_shape_files(ds, shapefile_ad0, "population")
    return clipped["population"]


def get_pop_for_year(year, pop_grids):
    decade = get_decade(year)
    if decade in pop_grids:
        return pop_grids[decade]
    else:
        raise ValueError(f"No population data available for decade {decade}")


def prepare_pop(pop_year, polygon_gdf, ds_2000):
    pop_year_dat = pop_year.to_dataset()
    clipped_pop_nc_raw, num_pix_pop = clip_shape_files(
        pop_year_dat, polygon_gdf, "population"
    )
    population_values = create_pop(clipped_pop_nc_raw)
    population_values = population_values.rio.reproject_match(ds_2000)
    population_values = population_values.rename({"y": "lat", "x": "lon"})
    return population_values


def create_pop(pop_nc, crs=crs_reference_global):
    pop_nc_time = pop_nc.isel(time=0)
    pop_nc_crs = pop_nc_time.rio.write_crs(crs, inplace=True)
    population_values = pop_nc_crs.fillna(0)
    return population_values


def load_decadal_populations(
    config, scenario="SSP2", start_year=2000, end_year=2100, step=10
):
    pop_grids = {}
    for year in range(start_year, end_year + 1, step):
        pop_path = os.path.join(
            get_processed_folder(config),
            scenario,
            f"population_grid_{scenario}_total_{year}.nc",
        )
        if os.path.exists(pop_path):
            da = read_in_xarray_var_crs(pop_path)
            da_pop = da["population"]
            pop_grids[int(year)] = da_pop
        else:
            raise FileNotFoundError(f"Population file not found: {pop_path}")
    return pop_grids
