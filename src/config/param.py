import os

# crs
crs_reference_global = 'EPSG:4326'
crs_reference_number = 4326

# missing values
missing_value = -9999.0

# gadm
gadm_version = "v410"

# global parameters
url_chirps = os.getenv("CHIRPS_URL", "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/ERA5/")


# cds download
url_era5land = os.getenv("CDS_API_URL", "https://cds.climate.copernicus.eu/api")
key_era5land = os.getenv("CDS_API_KEY")
if key_era5land is None:
    raise ValueError("CDS_API_KEY environment variable is not set. Please set it to your CDS API key.")

# era5-land
variables_era5land_list = ["2m_temperature", "2m_temperature_daymax",
            "2m_temperature_daymin", "relative_humidity", "specific_humidity"]

# domains and countries
cpd_region_list = {
    "SEA": {
        "CPD": (118.04, 6.5),
    } ,
    "South_America": {
        "CPD": (299.70, -21.11),
    },
    "Central_America": {
        "CPD": (287.29, 10.20),
    },
    "North_America": {
        "CPD": (263.0, 47.28),
    },
    "Europe": {
        "CPD": (9.75, 49.68),
    },
    "Africa": {
        "CPD": (17.60, -1.32),
    },
    "South_Asia": {
        "CPD": (67.18, 16.93),
    },
    "East_Asia": {
        "CPD": (116.57, 34.40),
    },
    "Central_Asia": {
        "CPD": (74.64, 47.82),
    },
    "MED": {
        "CPD": (15.75, 43.02),
    },
    "MENA": {
        "CPD": (24.5, 19.0),
    },
    "Australasia": {
        "CPD": (147.63, -24.26),
    }
}

domains = list(cpd_region_list.keys())

countries_codes = [
    "AFG", "AGO", "ALB", "ARM", "AZE", "BDI", "BEN", "BFA", "BGD", "BIH", "BLR", "BLZ", "BOL", "BRA", "BTN", "CAF",
    "CIV", "CMR", "COD", "COG", "COL", "COM", "CPV", "CUB", "DJI", "DZA", "ECU", "EGY", "ERI", "ETH", "GEO", "GHA",
    "GIN", "GMB", "GNB", "GTM", "GUY", "HND", "HTI", "IDN", "IND", "IRN", "IRQ", "JAM", "JOR", "KEN", "KGZ", "KHM",
    "LAO", "LBR", "LKA", "LSO", "MAR", "MDA", "MDG", "MKD", "MLI", "MMR", "MNG", "MOZ", "MRT", "MWI", "NAM", "NER",
    "NGA", "NIC", "NPL", "PAK", "PER", "PHL", "PNG", "PRK", "PRY", "PSE", "RWA", "SDN", "SEN", "SLB", "SLE", "SLV",
    "SOM", "SRB", "SSD", "STP", "SWZ", "SYR", "TCD", "TGO", "THA", "TJK", "TKM", "TLS", "TUN", "TZA", "UGA", "UKR",
    "UZB", "VEN", "VNM", "VUT", "YEM", "ZAF", "ZMB", "ZWE"]

admin_unit_levels = ["ADM_0", "ADM_1", "ADM_2"]

