# Grid Operations
from time import gmtime, strftime
from src.utils.cdo_helper import get_cdo


def convert_longitudes(ds, lon_name):
    ds['_longitude_adjusted'] = (ds[lon_name] + 180) % 360 - 180
    ds = (
        ds
        .swap_dims({lon_name: '_longitude_adjusted'})
        .sel(**{'_longitude_adjusted': sorted(ds._longitude_adjusted)})
        .drop(lon_name))
    ds = ds.rename({'_longitude_adjusted': lon_name})
    return ds


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


def attributes(resolution, da):
    attrs = {
        'title': f'Standardized regular lat and lon {resolution}-deg grid',
        'history': f'Created by Sally Jahn, {strftime("%Y-%m-%d %H:%M:%S", gmtime())}',
        'source': f'Grid ({resolution}, {resolution})',
        'institution': 'Imperial College London',
    }
    da.attrs.update(attrs)
    return da