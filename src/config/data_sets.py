import os

# value ranges
CHIRPS_RANGES = {
    "total_precipitation": {"min": 0, "max": 1040, "units": "mm/day"},
}

ERA5_LAND_VALUE_RANGES = {
    "relative_humidity": {"min": 0, "max": 100, "units": "%"},
    "specific_humidity": {"min": 0.0, "max": 40.0, "units": "g/kg"},
    "total_precipitation": {"min": 0, "max": 1040, "units": "mm/day"},
    "2m_temperature": {"min": -73, "max": 67, "units": "°C"},
    "2m_temperature_daymin": {"min": -73, "max": 67, "units": "°C"},
    "2m_temperature_daymax": {"min": -73, "max": 67, "units": "°C"},
    "surface_solar_radiation_downwards": {"min": 0, "max": 500, "units": "W/m²"},
    "surface_thermal_radiation_downwards": {"min": 0, "max": 500, "units": "W/m²"},
}

RANGES_ESM = {
    "total_precipitation": {"min": 0, "max": 1040, "units": "mm/day"},
    "2m_temperature": {"min": -73, "max": 67, "units": "°C"},
    "2m_temperature_daymax": {"min": -73, "max": 67, "units": "°C"},
    "2m_temperature_daymin": {"min": -73, "max": 67, "units": "°C"},
    "relative_humidity": {"min": 0, "max": 100, "units": "%"},
    "specific_humidity": {"min": 0.0, "max": 40.0, "units": "g/kg"}
}

# configs
ERA5_LAND_CONFIG = {
    "id": "ERA5_Land",
    "variables": [
        "2m_temperature",
        "2m_temperature_daymin",
        "2m_temperature_daymax",
        "surface_pressure",
        "2m_dewpoint_temperature",
        "2m_dewpoint_temperature_daymin",
        "2m_dewpoint_temperature_daymax",
        "relative_humidity",
        "specific_humidity",
        "surface_solar_radiation_downwards",
        "surface_thermal_radiation_downwards",
        "total_precipitation",
        "population_era5land"
    ],
    "value_ranges": ERA5_LAND_VALUE_RANGES,

}

CHIRPS_CONFIG = {
    "id": "CHIRPS",
    "variables": ["total_precipitation", "population_chirps"],
    "value_ranges": CHIRPS_RANGES,
}


MODEL_CONFIGS = {
    "CanESM5": {
        "id": "CanESM5",
        "scenarios": ["historical", "ssp245", "ssp585"],
        "variables": list(RANGES_ESM.keys()),
        "value_ranges": RANGES_ESM
    },
    "GFDL-ESM4": {
        "id": "GFDL_ESM4",
        "scenarios": ["historical", "ssp245", "ssp585"],
        "variables": list(RANGES_ESM.keys()),
        "value_ranges": RANGES_ESM
    },
    "MPI-ESM1-2-LR": {
        "id": "MPI_ESM1_2_LR",
        "scenarios": ["historical", "ssp245", "ssp585"],
        "variables": list(RANGES_ESM.keys()),
        "value_ranges": RANGES_ESM
    },
    "MRI-ESM2-0": {
        "id": "MRI_ESM2_0",
        "scenarios": ["historical", "ssp245", "ssp585"],
        "variables": list(RANGES_ESM.keys()),
        "value_ranges": RANGES_ESM
    },
    "TaiESM1": {
        "id": "TaiESM1",
        "scenarios": ["historical", "ssp245", "ssp585"],
        "variables": list(RANGES_ESM.keys()),
        "value_ranges": RANGES_ESM
    },
    "UKESM1.0-LL": {
        "id": "UKESM1_0_LL",
        "scenarios": ["historical", "ssp245", "ssp585"],
        "variables": list(RANGES_ESM.keys()),
        "value_ranges": RANGES_ESM
    }
}


def get_abbreviation(variable):
    abbreviation_dict = {
        "relative_humidity": "hurs",
        "specific_humidity": "huss",
        "2m_temperature": "tas",
        "2m_temperature_daymin": "tasmin",
        "2m_temperature_daymax": "tasmax",
        "total_precipitation": "pr"
    }
    return abbreviation_dict.get(variable, None)


def get_unit(variable):
    abbreviation_dict = {
        "relative_humidity": "%",
        "specific_humidity": "g/kg",
        "2m_temperature": "°C",
        "2m_temperature_daymin": "°C",
        "2m_temperature_daymax": "°C",
        "total_precipitation": "mm"
    }
    return abbreviation_dict.get(variable, None)


def get_long_variable(variable):
    abbreviation_dict = {
        "relative_humidity": "relative humidity (single levels)",
        "specific_humidity": "specific humidity (single levels)",
        "2m_temperature": "2m surface air temperature (single levels)",
        "2m_temperature_daymin": "2m surface minimum air temperature (single levels)",
        "2m_temperature_daymax": "2m surface maximum air temperature (single levels)",
        "total precipitation": "Total precipitation",
    }
    return abbreviation_dict.get(variable, None)


abbreviation_dict = {
    "rh": "hurs",
    "sh": "huss",
    "2t": "tas",
    "precip": "pr",
    "strd": "rlds",
    "ssrd": "rsds",
}


def harmonize_abbrevation_rev(var_abb):
    reverse_abbreviation_dict = {v: k for k, v in abbreviation_dict.items()}
    return reverse_abbreviation_dict.get(var_abb, None)


def get_merged_path_filename(merged_path, variable, year):
    output_file = os.path.join(merged_path, "{}_years_{}_base.nc".format(variable, year))
    output_file_box = os.path.join(merged_path, "{}_years_{}_box.nc".format(variable, year))
    output_file_time = os.path.join(merged_path, "{}_years_{}.nc".format(variable, year))
    return output_file, output_file_box, output_file_time
