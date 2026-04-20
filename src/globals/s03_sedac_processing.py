# ScriptOverview
# Processing gridded population data to check and harmonize with environmental datasets, e.g., with respect to model
# grids and directional orientation (e.g., North-South). The population data is considered stationary (external), was
# extracted from the Harvard Dataverse, and represents UN WPP-adjusted, SSP-RCP consistent population projections.
# For further information on underlying data sources and methods, please refer to the Readme.md as well as the
# respective Scientific Data Descriptor publication.

import os
import xarray as xr
import pandas as pd
from src.config.data_catalog import get_sedac_raw, get_grid_raw, get_processed_folder
from src.config.data_sets import SEDAC_CONFIG
from src.utils.cdo_helper import get_cdo, main_grid_lon_lat
from src.utils.path_helper import get_files_by_pattern, write_nc_file, create_folder
from src.utils.grid_helper import attributes
from src.config.param import missing_value


ssp_set_config = ["SSP2", "SSP5"]  # combined with base year
cdo_domain_path = os.path.join(get_grid_raw(), 'grid_0_1deg_sedac.txt')
    
def main(ssp_set, cdo_domain_0_1_deg):
    for ssp in ssp_set:
        for year in list(range(1, 12)):  # base year and projection years
            sedac_year = SEDAC_CONFIG["years"][year - 1]
            sedac_path_proj = os.path.join(get_processed_folder(SEDAC_CONFIG), ssp)
            create_folder(sedac_path_proj)
            file_pop_year = load_years_pop(sedac_path_proj, sedac_year, ssp, cdo_domain_0_1_deg)
            prepare_population_sedac(sedac_path_proj, sedac_year, ssp)
            os.remove(file_pop_year)


def load_years_pop(sedac_path_processed, year_sedac, ssp, cdo_domain_0_1_deg):
    sedac_raw = get_sedac_raw()
    sedac_raw_ssp = os.path.join(sedac_raw, "NetCDF_{}_total_allyears".format(ssp))
    file_pop = get_files_by_pattern(sedac_raw_ssp, "{}.nc4".format(year_sedac))
    file_pop_path = os.path.join(sedac_raw_ssp, file_pop[0])
    file_pop_year = os.path.join(sedac_path_processed, f"pop_{ssp}_{year_sedac}_ya.nc")
    if not os.path.exists(file_pop_year):
        get_cdo().remapcon(
            cdo_domain_0_1_deg,
            input=file_pop_path,
            output=file_pop_year
        )
    return file_pop_year


def prepare_population_sedac(path_invert, year_number, ssp):
    path_regrid = define_pop_out_path("grid_regrid", year_number, ssp)
    path_grid = define_pop_out_path("grid", year_number, ssp)
    output_pop_renamed = prep_files_year_pop(path_invert, pattern=f"{year_number}_ya.nc",
                                             resolution=0.1, year_number=year_number)
    ds = output_pop_renamed.rename({"Band1": "population"})
    time = pd.to_datetime([f"{year_number}-01-01"])
    if 'time' not in ds.dims:
        ds = ds.expand_dims('time')
    ds = ds.assign_coords(time=time)
    write_nc_file(ds, "population", path_regrid)
    main_grid_lon_lat(path_regrid, path_grid, minlat=-56, maxlat=60, minlon=-180, maxlon=180)
    os.remove(path_regrid)


def prep_files_year_pop(input_path, pattern, resolution, year_number):
    files_year = get_files_by_pattern(input_path, str(pattern))
    ds = xr.open_dataset(os.path.join(input_path, files_year[0]))
    domain_output = attributes(resolution, ds)
    domain_output_miss = domain_output.fillna(missing_value)
    return domain_output_miss


def define_pop_out_path(metadata, year_number, ssp):
    store = os.path.join(get_processed_folder(SEDAC_CONFIG), ssp)
    create_folder(store)
    file_year_path = os.path.join(store, "population_{}_{}_total_{}.nc".format(metadata, ssp, year_number))
    return file_year_path


if __name__ == "__main__":
    main(ssp_set_config, cdo_domain_path)
