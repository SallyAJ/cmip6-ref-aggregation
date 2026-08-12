# Grid Operations
from time import gmtime, strftime
from src.utils.cdo_helper import get_cdo


def regrid_domain_conservative(cdo_domain, path_merged_year, file_path_regrid):
    get_cdo().remapcon(
        cdo_domain,
        input=path_merged_year,
        output=file_path_regrid
    )


def regrid_domain_bilinear(cdo_domain, path_merged_year, file_path_regrid):
    get_cdo().remapbil(
        cdo_domain,
        input=path_merged_year,
        output=file_path_regrid
    )


def get_area(polygon_gdf):
    polygon_gdf_equal = polygon_gdf.to_crs("ESRI:54009")
    area_km2 = polygon_gdf_equal.geometry.area.iloc[0] / 1_000_000
    return area_km2