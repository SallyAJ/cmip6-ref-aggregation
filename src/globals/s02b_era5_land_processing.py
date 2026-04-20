# ScriptOverview
# Processing of ERA5_Land (based on raw files downloaded via s02a_era5_land_download.py) to e.g., calculate further
# variables, generate daily information, standardize model grids and directional orientation (e.g., North-South).

import os
from src.config.args import DateUpdateArgs
from src.config.data_sets import ERA5_LAND_CONFIG
from src.config.data_catalog import get_download_folder, get_processed_folder
from src.utils.cdo_helper import get_cdo, main_grid_lon_lat, get_celsius, set_miss, north_south
from src.utils.date_helper import reformat_era5_date
from src.utils.path_helper import create_folder

# global parameters
config = DateUpdateArgs(year_start=1981, year_end=2024, month_start=1, month_end=12)


def main(update_config: DateUpdateArgs):
    dew_var = "2m_dewpoint_temperature"
    air_var = "2m_temperature"
    surface_pressure_var = "surface_pressure"
    if update_config.year_start < 1950:
        raise AttributeError("Minimum year for ERA5-LAND is 1950.")
    for year in list(range(update_config.year_start, update_config.year_end + 1)):
        for month in list(range(update_config.month_start, update_config.month_end + 1)):
            out_dew_var, filename_dew_var = filename_definition(dew_var, month, year)
            dew_temperature = calculate_daily(dew_var, out_dew_var, filename_dew_var)
            out_air_var, filename_air_var = filename_definition(air_var, month, year)
            air_temperature = calculate_daily(air_var, out_air_var, filename_air_var)
            surface_pressure_output_path, pressure_file = filename_definition(surface_pressure_var, month, year)
            sp_directory_path = os.path.dirname(surface_pressure_output_path)
            pressure_path = get_download_folder(ERA5_LAND_CONFIG, surface_pressure_var)
            file_pressure = os.path.join(pressure_path, pressure_file + ".nc")
            calculate_daily_surface_pressure(surface_pressure_output_path, file_pressure)
            combined_path_2t_2d_sp = os.path.join(sp_directory_path, "combined_out_{}_{}.nc".format(month, year))
            hum_path = os.path.join(sp_directory_path, "humy_{}_{}.nc".format(month, year))
            get_cdo().merge(input=[surface_pressure_output_path, air_temperature, dew_temperature],
                            output=combined_path_2t_2d_sp)
            calculate_relhum_and_store(combined_path_2t_2d_sp, hum_path, month,
                                       year)
            calculate_spechum_and_store(combined_path_2t_2d_sp, hum_path, month,
                                        year)


# general
def showvar(arg):
    var_attr = get_cdo().showvar(input=arg)
    var_attr_unlisted = var_attr.pop()
    return var_attr_unlisted


def calculate_daily(variable, output_path, filename):
    download_path = get_download_folder(ERA5_LAND_CONFIG, variable)
    file_temp = os.path.join(download_path, filename + ".nc")
    if os.path.isfile(file_temp):
        output_path_celsiusdeg = getdeg(file_temp, output_path)
        daily_var("daymean", output_path, output_path_celsiusdeg)
        daily_var("daymin", output_path, output_path_celsiusdeg)
        daily_var("daymax", output_path, output_path_celsiusdeg)
    return file_temp


def daily_var(calc, output_path, output_path_celsiusdeg):
    # daymean: When you use the daymean operation to calculate daily means, the missing values for each day will not
    # be factored into the mean calculation for that day. The daily mean will be computed only from the valid hourly
    # values present for that day An artificial distinction is made between the notions mean and average. The mean is
    # regarded as a statistical function, whereas the average is found simply by adding the sample members and
    # dividing the result by the sample size. For example, the mean of 1, 2, miss and 3 is (1 + 2 + 3)/3 = 2,
    # whereas the average is (1 + 2 + miss + 3)/4 = miss/4 = miss. If there are no missing values in the sample,
    # the average and mean are identical.
    output_dir, output_filename = os.path.split(output_path)
    if calc == "daymean":
        file_temp_path = output_path
        file_temp_day = get_cdo().daymean(input=output_path_celsiusdeg, option='-b F32')
        var_deglonlat_invert = north_south(file_temp_day)
        var_deglonlat_miss = set_miss(var_deglonlat_invert)
    elif calc == "daymin":
        minmax_path = os.path.join(os.path.dirname(output_dir), os.path.basename(output_dir) + '_' + calc)
        file_temp_path = os.path.join(minmax_path, output_filename.replace(".nc", f"_{calc}.nc"))
        create_folder(minmax_path)
        file_temp_day = get_cdo().daymin(input=output_path_celsiusdeg, option='-b F32')
        var_deglonlat_invert = north_south(file_temp_day)
        var_deglonlat_miss = set_miss(var_deglonlat_invert)
    elif calc == "daymax":
        minmax_path = os.path.join(os.path.dirname(output_dir), os.path.basename(output_dir) + '_' + calc)
        file_temp_path = os.path.join(minmax_path, output_filename.replace(".nc", f"_{calc}.nc"))
        create_folder(minmax_path)
        file_temp_day = get_cdo().daymax(input=output_path_celsiusdeg, option='-b F32')
        var_deglonlat_invert = north_south(file_temp_day)
        var_deglonlat_miss = set_miss(var_deglonlat_invert)
    main_grid_lon_lat(var_deglonlat_miss, file_temp_path)
    os.remove(var_deglonlat_invert)
    os.remove(var_deglonlat_miss)


def getdeg(var_kelvin, output_path):
    output_dir, output_filename = os.path.split(output_path)
    output_path_celsius = os.path.join(os.path.dirname(output_dir), os.path.basename(output_dir) + '_celsius')
    output_path_celsiusdeg = os.path.join(output_path_celsius, output_filename.replace(".nc", "_celsius.nc"))
    create_folder(output_path_celsius)
    attribute, output_path_celsiusdegnoatt_st = get_celsius((var_kelvin))
    get_cdo().setattribute(attribute, input=output_path_celsiusdegnoatt_st, output=output_path_celsiusdeg)
    return output_path_celsiusdeg


def calculate_daily_surface_pressure(surface_pressure_output_path, file_pressure):
    if not os.path.exists(surface_pressure_output_path):
        var_pressurelonlat = get_cdo().daymean(input=file_pressure)
        var_pressurelonlat_invert = north_south(var_pressurelonlat)
        var_pressurelonlat_invert_miss = set_miss(var_pressurelonlat_invert)
        main_grid_lon_lat(var_pressurelonlat_invert_miss, surface_pressure_output_path)
        os.remove(var_pressurelonlat)
        os.remove(var_pressurelonlat_invert)


# humidity
def humidity_calculation(var_hum, expression, combined_2t_2d_sp, hum_path):
    expression_format = "'{}={}'".format(var_hum, expression)
    hum = set_miss(combined_2t_2d_sp)
    cmd = f"-b F64 -O -s expr,{expression_format} {hum} {hum_path}"
    get_cdo().run(cmd)
    os.remove(hum)
    hum_daily_miss = set_miss(hum_path)
    return hum_daily_miss


def expression_sh(dew_att, sp_att):
    expr_sh = (
        f'(287.0597/461.5250)*(611.21*exp(17.502*(({dew_att} + 273.15)-273.16)/(({dew_att} + 273.15)-32.19)))/({sp_att}-((1-('
        f'287.0597/461.5250))*(611.21*exp(17.502*(({dew_att} + 273.15)-273.16)/(({dew_att} + 273.15)-32.19)))))')
    return expr_sh


def expression_rh(dew_att, air_att):
    expr_rh = (
        f'100*((611.21*exp(17.502*(({dew_att} + 273.15)-273.16)/(({dew_att} + 273.15)-32.19)))/(611.21*exp(17.502*(({air_att} + 273.15)-273'
        f'.16)/(({air_att} + 273.15)-32.19))))')
    return expr_rh


def calculate_spechum_and_store(combined_2t_2d_sp, hum_path, month, year):
    vars_str = showvar(combined_2t_2d_sp)
    vars = vars_str.split()
    sp_att = vars[0]
    dew_att = vars[2]
    month_selected, year_selected = reformat_era5_date(month, year)
    output_path = format_output_file("specific_humidity", month_selected, year_selected)
    expression_spechum = expression_sh(dew_att, sp_att)
    specific_hum_daily = humidity_calculation("sh", expression_spechum, combined_2t_2d_sp, hum_path)
    get_cdo().mulc(1000, input=specific_hum_daily, output=hum_path)
    attribute_sh = showvar(hum_path) + '@units=g/kg'
    hum_path_neg = get_cdo().setrtoc('-1e+30,0,0', input=hum_path)
    hum_harmonize(hum_daily=hum_path_neg, attribute_h=attribute_sh, output_path=output_path)
    os.remove(combined_2t_2d_sp)
    os.remove(hum_path)


def calculate_relhum_and_store(combined_2t_2d_sp, hum_path, month, year):
    vars_str = showvar(combined_2t_2d_sp)
    vars = vars_str.split()
    air_att = vars[1]
    dew_att = vars[2]
    month_selected, year_selected = reformat_era5_date(month, year)
    output_path = format_output_file("relative_humidity", month_selected, year_selected)
    expression_relhum = expression_rh(dew_att, air_att)
    relative_hum_daily = humidity_calculation("rh", expression_relhum, combined_2t_2d_sp, hum_path)
    attribute_rh = showvar(relative_hum_daily) + '@units=%'
    relative_hum_daily_0 = get_cdo().setrtoc('-1e+30,0,0', input=relative_hum_daily)
    relative_hum_daily_100 = get_cdo().setrtoc('100,1e+30,100', input=relative_hum_daily_0)
    hum_harmonize(hum_daily=relative_hum_daily_100, attribute_h=attribute_rh, output_path=output_path)


def hum_harmonize(hum_daily, attribute_h, output_path):
    hum_daily_miss = set_miss(hum_daily)
    hum_daily_attr = get_cdo().setattribute(attribute_h, input=hum_daily_miss)
    hum_daily_attr_name = get_cdo().chname("latitude_2,latitude,longitude_2,longitude",
                                           input=hum_daily_attr)
    y_first = get_lat_grid_info(hum_daily_attr_name)
    if y_first > 0:
        hum_daily_attr_name = north_south(hum_daily_attr_name)
    main_grid_lon_lat(hum_daily_attr_name, output_path)


def get_lat_grid_info(file):
    text = get_cdo().griddes(input=file)
    if isinstance(text, list):
        text = "\n".join(text)
    yfirst = None
    for line in text.splitlines():
        if line.strip().startswith("yfirst"):
            yfirst = float(line.split("=")[1].strip())
    return yfirst


# paths and names
def format_output_file(var, month_sel, year_sel):
    output_path = get_processed_folder(ERA5_LAND_CONFIG, var)
    file_name = "{}_{}_{}.nc".format(var, month_sel, year_sel)
    file_var_path = os.path.join(output_path, file_name)
    return file_var_path


def filename_definition(var_name, month, year):
    month_selected, year_selected = reformat_era5_date(month, year)
    filename = "{}_hourly_{}_{}".format(var_name, month_selected, year_selected)
    output_path = format_output_file(var_name, month_selected, year_selected)
    return output_path, filename


if __name__ == '__main__':
    main(config)
