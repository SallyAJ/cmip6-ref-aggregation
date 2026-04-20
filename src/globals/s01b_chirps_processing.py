# ScriptOverview
# Processing CHIRPS-3.0 data (based on raw files downloaded via s01a_chirps_download.py) to e.g., standardize date and
# file formats, align model grids, and ensure consistent directional orientation (e.g., North-South).

import os
from src.config.param import missing_value
from src.config.args import DateUpdateArgs
from src.config.data_sets import CHIRPS_CONFIG
from src.config.data_catalog import get_download_folder, get_processed_folder
from src.utils.cdo_helper import main_grid_lon_lat, set_miss, get_cdo
from src.utils.date_helper import reformat_chirps_date
from osgeo import gdal

config = DateUpdateArgs(year_start=1981, year_end=2024, month_start=1, month_end=12)


def main(update_config: DateUpdateArgs):
    if update_config.year_start < 1981:
        raise AttributeError("Minimum year for CHIRPS is 1981.")
    chirps_raw = get_download_folder(CHIRPS_CONFIG, "total_precipitation")
    chirps_processed = get_processed_folder(CHIRPS_CONFIG, "total_precipitation")
    for year in list(range(update_config.year_start, update_config.year_end + 1)):
        for month in list(range(update_config.month_start, update_config.month_end + 1)):
            for days in list(range(update_config.day_start, update_config.day_end + 1)):
                try:
                    day_selected, month_selected, year_selected = reformat_chirps_date(days, month, year)
                    chirps_path_storage = define_chirps_filepath_name_nc(year_selected, month_selected, day_selected,
                                                                         chirps_processed)
                    if not os.path.exists(chirps_path_storage):
                        chirps_path_raw = define_chirps_filepath_name(year_selected, month_selected, day_selected,
                                                                      chirps_raw)
                        chirps_path_raw_nc = define_chirps_filepath_name_nc(year_selected, month_selected, day_selected,
                                                                            chirps_raw)
                        from_tiff_to_nc(chirps_path_raw, chirps_path_raw_nc)
                        date_str = f"{year}-{month:02d}-{days:02d}"
                        chirps_nc = get_cdo().setdate(date_str, input=chirps_path_raw_nc)
                        chirps_invert_miss = set_miss(chirps_nc)
                        main_grid_lon_lat(chirps_invert_miss, chirps_path_storage)
                except:
                    continue


def from_tiff_to_nc(tiffile, ncfile, missing_val=missing_value):
    gdal.Translate(ncfile,
                   tiffile,
                   format='NETCDF', noData=missing_val)


def define_chirps_filepath_name(year_sel, month_sel, day_sel, path):
    chirps_daily_path = os.path.join(path,
                                     "chirps-v3.0.{}.{}.{}.tif".format(year_sel, month_sel, day_sel))
    return chirps_daily_path


def define_chirps_filepath_name_nc(year_sel, month_sel, day_sel, path):
    chirps_daily_path = os.path.join(path,
                                     "chirps-v3.0.{}.{}.{}.nc".format(year_sel, month_sel, day_sel))
    return chirps_daily_path


if __name__ == "__main__":
    main(config)
