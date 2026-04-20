# Date Helper

def reformat_chirps_date(day_sel, month_sel, year_sel):
    month_selected = str(month_sel).zfill(2)
    year_selected = str(year_sel)
    day_selected = str(day_sel).zfill(2)
    return day_selected, month_selected, year_selected


def reformat_era5_date(month_sel,  year_sel):
    month_selected = str(month_sel).zfill(2)
    year_selected = str(year_sel)
    return month_selected, year_selected


def check_leapyear(ds):
    ds["time"] = ds["time"].astype("datetime64[ns]")
    years = ds["time"].dt.year
    leap_years = years[(years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0))]
    if len(leap_years) > 0:
        print("Leap year(s) found:", leap_years.values)
    else:
        print(" No leap years found in the time coordinate.")
