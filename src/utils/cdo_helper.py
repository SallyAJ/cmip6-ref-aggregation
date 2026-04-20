# CDO Information
# cdo is used for data processing, e.g., for adjusting and harmonizing model grid types.
# For further information on running CDO in Python, please refer to
# https://code.mpimet.mpg.de/projects/cdo/wiki/Cdo%7Brbpy%7D.

from cdo import *
import os

cdo = Cdo()


def get_cdo():
    return cdo


def main_grid_lon_lat(nc_file, output_path, minlat=-90, maxlat=90, minlon=-180, maxlon=180):
    cdo.sellonlatbox(minlon, maxlon, minlat, maxlat, input=nc_file, output=output_path)


def get_celsius(nc_file):
    nc_file_na = get_cdo().setmissval("nan", input=nc_file)
    nc_file_celsius = get_cdo().subc(273.15, input=nc_file_na)
    filename = os.path.basename(nc_file_celsius)
    if "dew_" in filename.lower():
        update_attribute = "2d"
    else:
        update_attribute = "2t"
    ref_attribute = update_attribute + '@units=degC'
    nc_file_celsius_name = get_cdo().setname(update_attribute, input=nc_file_celsius)
    os.remove(nc_file_celsius)
    return ref_attribute, nc_file_celsius_name


def north_south(nc_file):
    out_file = get_cdo().invertlat(input=nc_file)
    return out_file


def set_miss(nc_file):
    nc_file = get_cdo().setrtomiss('-9999,-9999', input=nc_file, option='-b F32')
    out_file = get_cdo().setmissval(-9999.0, input=nc_file, option='-b F32')
    return out_file





