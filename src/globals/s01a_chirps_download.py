# ScriptOverview
# Download file to download CHIRPS-3.0 data (CHIRPS: Rainfall Estimates from Rain Gauge and Satellite Observations)
# provided by the Climate Hazard Centre.

import os
import requests
from src.config.data_sets import CHIRPS_CONFIG
from src.config.param import url_chirps
from src.config.data_catalog import get_download_folder
from src.config.args import DateUpdateArgs
from src.utils.date_helper import reformat_chirps_date

config = DateUpdateArgs(year_start=1981, year_end=2024, month_start=1, month_end=12)


def main(update_config: DateUpdateArgs):
    if update_config.year_start < 1981:
        raise AttributeError("Minimum year for CHIRPS is 1981.")
    target_path = get_download_folder(CHIRPS_CONFIG, "total_precipitation")
    for year in list(range(update_config.year_start, update_config.year_end + 1)):
        for month in list(range(update_config.month_start, update_config.month_end + 1)):
            for days in list(range(update_config.day_start, update_config.day_end + 1)):
                day_selected, month_selected, year_selected = reformat_chirps_date(days, month, year)
                file_format = "chirps-v3.0.{}.{}.{}.tif".format(year_selected, month_selected, day_selected)
                file_path = "{}{}/{}".format(url_chirps, year_selected, file_format)
                storage_file_path = os.path.join(target_path, file_format)
                download_data(file_path, storage_file_path)


def download_data(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print("Download successful. Data saved to:", save_path)
    else:
        print("Failed to download data from the URL:", url)


if __name__ == "__main__":
    main(config)
