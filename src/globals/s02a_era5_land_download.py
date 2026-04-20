# ScriptOverview
# Download file to download hourly ERA5-Land data provided by  European Centre for Medium-Range Weather Forecasts
# (ECMWF) via the Copernicus Climate Data Store (CDS). For further instructions on retrieval please refer to
# https://cds.climate.copernicus.eu/api-how-to .

import os
import cdsapi
from src.config.data_sets import ERA5_LAND_CONFIG
from src.config.data_catalog import get_download_folder
from src.utils.date_helper import reformat_era5_date
from src.utils.path_helper import create_folder
from src.config.param import url_era5land, key_era5land
from src.config.args import DateUpdateArgs

variables_main = ['surface_pressure', '2m_dewpoint_temperature', '2m_temperature']
config = DateUpdateArgs(year_start=1981, year_end=2024, month_start=1, month_end=12)


def main(update_config: DateUpdateArgs, variables):
    if update_config.year_start < 1950:
        raise AttributeError("Minimum year for ERA5-LAND is 1950.")
    for year in list(range(update_config.year_start, update_config.year_end + 1)):
        for month in list(range(update_config.month_start, update_config.month_end + 1)):
            for var_selected in list(variables):
                target_path = get_download_folder(ERA5_LAND_CONFIG, var_selected)
                create_folder(target_path)
                month_selected, year_selected = reformat_era5_date(month, year)
                target_path_results = os.path.join(target_path, "{}_hourly_{}_{}.nc".format(var_selected,
                                                                                            month_selected,
                                                                                            year_selected))
                days = [f"{d:02d}" for d in range(1, 32)]
                if not os.path.exists(target_path_results):
                    try:
                        retrieve_era(var_selected, year_selected, month_selected, days, target_path_results)
                    except Exception as e:
                        print(f"not done: {e}")
                        continue


def retrieve_era(var_sel, year_sel, month_sel, day_list, target_path):
    c = cdsapi.Client(url=url_era5land, key=key_era5land)
    print(str(var_sel))
    dataset = "reanalysis-era5-land"
    request = {
        'variable': [str(var_sel)],
        'year': str(year_sel),
        'month': str(month_sel),
        'day': day_list,
        'time': [
            '00:00', '01:00', '02:00',
            '03:00', '04:00', '05:00',
            '06:00', '07:00', '08:00',
            '09:00', '10:00', '11:00',
            '12:00', '13:00', '14:00',
            '15:00', '16:00', '17:00',
            '18:00', '19:00', '20:00',
            '21:00', '22:00', '23:00',
        ],
        "data_format": "netcdf",
        "download_format": "unarchived"
    }
    target = target_path
    c.retrieve(dataset, request, target)


if __name__ == '__main__':
    main(config, variables_main)
