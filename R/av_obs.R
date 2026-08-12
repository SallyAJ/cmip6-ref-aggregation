## Packages needed

# install.packages(c("terra", "sf", "exactextractr", "data.table", "ggplot2",
#                    "scales", "ncdf4", "dplyr", "arrow"))

# if (!require("BiocManager", quietly = TRUE))
#   install.packages("BiocManager")
# 
# BiocManager::install("rhdf5","rhdf5filters")

require(terra)
require(sf)
require(exactextractr)
require(data.table)
require(ggplot2)
require(scales)
require(ncdf4)
require(dplyr)
require(arrow)
require(rhdf5)
require(rhdf5filters)

library(dplyr)

ptm <- proc.time()

# Replace Placeholders Paths
## TODO
infiniband_share <- "<INFINIBAND_SHARE>"
non_infiniband_share <- "<NON_INFINIBAND_SHARE>"


## Get the path to the data, detecting infiniband

get_base <- function() {
  if (.Platform$OS.type == "windows") {
    status <- suppressWarnings(shell(
      "ping -n 1 -w 1000 10.0.2.253",
      wait = TRUE, ignore.stdout = TRUE))
    if (status == 0) {
      message("Infiniband detected")
      return(infiniband_share)
    } else {
      message("Couldn't ping 10.0.2.253 - using normal ethernet")
      return(non_infiniband_share)
    }
  }
  
  message("Linux/Mac - using infiniband_share param as the path")
  infiniband_share
}

# share
base <- get_base()

# Output folder

output_path <- file.path(base, "DataCentre", "data", "countries",
                         "observations_areapop")

# These are the paths to the various nc folders we need. Using data at their
# original resolutions, and (quasi-)global.

obs_path <- file.path(base, "DataCentre", "data", "global", "observation")
chirps_path <- file.path(obs_path, "CHIRPS", "compressed", "total_precipitation", "total_precipitation_%s_compressed_native.nc")

era_path <- file.path(obs_path, "ERA5_Land", "compressed")
temp_path <- file.path(era_path, "2m_temperature", "2m_temperature_%d_compressed_native.nc")
tempmin_path <- file.path(era_path, "2m_temperature_daymin", "2m_temperature_daymin_%d_compressed_native.nc")
tempmax_path <- file.path(era_path, "2m_temperature_daymax", "2m_temperature_daymax_%d_compressed_native.nc")
rh_path <- file.path(era_path, "relative_humidity", "relative_humidity_%d_compressed_native.nc")
sh_path <- file.path(era_path, "specific_humidity", "specific_humidity_%d_compressed_native.nc")

## Population
pop_file <- "Landscan/2024/landscan-global-2024.tif"
pop_name <- "LS2024"
pop_file2 <- "WorldPop/GlobalV2/global_pop_2024_CN_1km_R2025A_UA_v1.tif"
pop_name2 <- "WP2024"
pop_file3 <- "GPW/gpw_v4_population_count_adjusted_to_2015_unwpp_country_totals_rev11_2020_30_sec.tif"
pop_name3 <- "GPW2020"
gadm_gpkg <- "DataCentre/data/global/observation/external/GADM/gadm_410-levels.gpkg"


# Parameters
adm_level <- 2
start_year <- 1981
end_year <- 2025
countries <- c(
  "AFG", "AGO", "ALB", "ARM", "AZE", "BDI", "BEN", "BFA", "BGD", "BIH", "BLR",
  "BLZ", "BOL", "BRA", "BTN", "CAF", "CIV", "CMR", "COD", "COG", "COL", "COM",
  "CPV", "CUB", "DJI", "DZA", "ECU", "EGY", "ERI", "ETH", "GAB", "GEO", "GHA",
  "GIN", "GMB", "GNB", "GTM", "GUF", "GUY", "HND", "HRV", "HTI", "IDN", "IND",
  "IRN", "IRQ", "JAM", "JOR", "KEN", "KGZ", "KHM", "KOR", "LAO", "LBR", "LKA",
  "LSO", "MAR", "MDA", "MDG", "MKD", "MLI", "MMR", "MNG", "MOZ", "MRT", "MWI",
  "NAM", "NER", "NGA", "NIC", "NPL", "PAK", "PAN", "PER", "PHL", "PNG", "PRK",
  "PRY", "PSE", "RWA", "SDN", "SEN", "SLB", "SLE", "SLV", "SOM", "SRB", "SSD",
  "STP", "SUR", "SWZ", "SYR", "TCD", "TGO", "THA", "TJK", "TKM", "TLS", "TUN",
  "TZA", "UGA", "UKR", "UZB", "VEN", "VNM", "VUT", "YEM", "ZAF", "ZMB", "ZWE")

# Landscan
pop_raster <- terra::rast(file.path(base, pop_file))
# Worldpop
pop_raster2 <- terra::rast(file.path(base, pop_file2))
# GPW
pop_raster3 <- terra::rast(file.path(base, pop_file3))

## Worldpop has smaller spatial extent than Landscan, so crop LS and GPW
pop_raster <- crop(pop_raster,pop_raster2)
pop_raster3 <- crop(pop_raster3,pop_raster2)

## extract population rasters as vectors
pop2v <- as.vector(pop_raster2)
pop3v <- as.vector(pop_raster3)
rm(pop_raster2,pop_raster3)

## Load the GADM data. If countries that we need are missing in an admin
## level, back-fill using the parent admin level.
## This means countries with no admin2 levels have admin 1 levels appearing in admin2 output

gadm <- sf::st_read(file.path(base, gadm_gpkg), layer = sprintf("ADM_%s", adm_level))
gadm <- gadm[gadm$GID_0 %in% countries, c("GID_0","GID_1","GID_2","NAME_1","NAME_2","HASC_2","geom")]
missing_countries <- setdiff(countries, unique(gadm$GID_0))
if(length(missing_countries)>0) {
  gadm_1 <- sf::st_read(file.path(base, gadm_gpkg), layer = "ADM_1")
  gadm_1 <- gadm_1[gadm_1$GID_0 %in% missing_countries, ]
  missing_countries_1 <- setdiff(missing_countries, unique(gadm_1$GID_0))
  if(length(missing_countries_1)>0) stop("Still countries missing\n")
  gadm_1$GID_2 <- gadm_1$GID_1
  gadm_1$NAME_2 <- gadm_1$NAME_1
  gadm_1$HASC_2 <- gadm_1$HASC_1
  gadm_1 <- gadm_1[,c("GID_0","GID_1","GID_2","NAME_1","NAME_2","HASC_2","geom")]
  gadm <- rbind(gadm,gadm_1)
  rm(gadm_1)
}
gadm <- sf::st_transform(gadm, crs(pop_raster))


# Fix a GADM bug in Ghana
gha <- which(gadm$GID_0 == "GHA")
gadm$GID_1[gha] <- paste0("GHA.", substring(gadm$GID_1[gha], 4))
gadm$GID_2[gha] <- paste0("GHA.", substring(gadm$GID_2[gha], 4))

# Fig UKraine bug
ukr <- which(gadm$GID_1 == "?")
gadm$GID_1[ukr] <- paste0(gadm$GID_0[ukr],".unknown")
gadm$GID_2[ukr] <- paste0(gadm$GID_0[ukr],".unknown")

# Rasterise GADM into a list of data frames, one for each
# admim unit, with population. (So length(result) == nrow(gadm))

# Each data frame has cols:
#                  x : the longitude of the midpoint of the cell
#                  y : the latitude of the midpoint of the cell
#              value : population of (x, y) *for this admin unit*
#               cell : a large integer cell index.
#  coverage_fraction : the proportion of the cell this admin unit covers.

# (x,y) is unique within a specific data frame result[[n]] - but may
# be duplicated in different frames result[[(n1 != n2)]] - because multiple admin
# units may occupy part of the same cell in the pop_raster. In that case,
# coverage_fraction will sum to 1 across the different (x,y,unit), but will be
# less than 1 in each. Also, the value will be a floating point number of
# people in a specific table, but the sum of coverage_fraction * value across
# the admin units will equal the pop_raster total for that cell.

pop_ext <- as.vector(ext(pop_raster))

pop_df <- exactextractr::exact_extract(
  pop_raster,
  gadm,
  include_cell = TRUE,
  include_xy = TRUE,
  max_cells_in_memory = 1e9,
  default_value = 0
)

gadm <- as.data.table(gadm[,1:(ncol(gadm)-1)])
# Store gid2_row in pop_df, then combine to one data.table

for (i in seq_along(pop_df)) {
  pop_df[[i]]$gid2_row <- i
}

pop_df <- data.table::rbindlist(pop_df)
names(pop_df)[names(pop_df) == "value"] <- "pop"

# add worldpop and gpw
pop_df$pop2 <- pop2v[pop_df$cell]
pop_df$pop3 <- pop3v[pop_df$cell]

# correct pops for coverage fractions
pop_df[,pop:=pop*coverage_fraction]
pop_df[,pop2:=pop2*coverage_fraction]
pop_df[,pop3:=pop3*coverage_fraction]

# remove any NAs
pop_df$pop[is.na(pop_df$pop)] <- 0
pop_df$pop2[is.na(pop_df$pop2)] <- 0
pop_df$pop3[is.na(pop_df$pop3)] <- 0

rm(pop_raster,pop2v,pop3v)
gc()

## Cell areas (where lat below is centre)

cell_area <- function(lat, ddeg = 1/120, R = 6371000) {
  dphi <- ddeg * pi / 180
  dlambda <- ddeg * pi / 180
  phi <- lat * pi / 180
  R^2 * dlambda * (sin(phi + dphi/2) - sin(phi - dphi/2))
}

pop_df$area <- cell_area(pop_df$y + (1/240)) * pop_df$coverage_fraction

pop_df$GID_0 <- gadm$GID_0[pop_df$gid2_row]
pop_df$GID_1 <- gadm$GID_1[pop_df$gid2_row]
pop_df$GID_2 <- gadm$GID_2[pop_df$gid2_row]

# Pre-Calculate ADM2 weightings.
admin2_pops <- pop_df[, .(pop=sum(pop),pop2=sum(pop2),pop3=sum(pop3)),gid2_row]
admin2_areas <- pop_df[, .(area=sum(area)),gid2_row]
admin2_pixels <- pop_df[, .(pixels = .N),gid2_row]
nr_adm2 <- nrow(admin2_pops)

adm2_row_match <- match(pop_df$gid2_row, admin2_pops$gid2_row)
pop_df$adm2_pop <- admin2_pops$pop[adm2_row_match]
pop_df$adm2_pop2 <- admin2_pops$pop2[adm2_row_match]
pop_df$adm2_pop3 <- admin2_pops$pop3[adm2_row_match]
pop_df$adm2_area <- admin2_areas$area[adm2_row_match]
pop_df$pop_weight2 <- pop_df$pop / pop_df$adm2_pop
pop_df$pop2_weight2 <- pop_df$pop2 / pop_df$adm2_pop2
pop_df$pop3_weight2 <- pop_df$pop3 / pop_df$adm2_pop3
pop_df$area_weight2 <- pop_df$area / pop_df$adm2_area
rm(adm2_row_match)

## correction for small number of admin2s with zero pop - replace with area weighting
pop_df$pop_weight2[pop_df$adm2_pop == 0] <- pop_df$area_weight2[pop_df$adm2_pop == 0] 
pop_df$pop2_weight2[pop_df$adm2_pop2 == 0] <- pop_df$area_weight2[pop_df$adm2_pop2 == 0] 
pop_df$pop3_weight2[pop_df$adm2_pop3 == 0] <- pop_df$area_weight2[pop_df$adm2_pop3 == 0] 

# And ADM1 weightings
admin1_pops <- pop_df[, .(pop=sum(pop),pop2=sum(pop2),pop3=sum(pop3)),GID_1]
admin1_areas <- pop_df[, .(area=sum(area)),GID_1]
admin1_pixels <- pop_df[, .(pixels = .N),GID_1]
nr_adm1 <- nrow(admin1_pops)
admin1_rows <- data.frame(GID_1=admin1_pops$GID_1,gid1_row = 1:nr_adm1)

pop_df$gid1_row <- admin1_rows$gid1_row[match(pop_df$GID_1, admin1_rows$GID_1)]
pop_df$adm1_pop <- admin1_pops$pop[match(pop_df$GID_1, admin1_pops$GID_1)]
pop_df$adm1_pop2 <- admin1_pops$pop2[match(pop_df$GID_1, admin1_pops$GID_1)]
pop_df$adm1_pop3 <- admin1_pops$pop3[match(pop_df$GID_1, admin1_pops$GID_1)]
pop_df$adm1_area <- admin1_areas$area[match(pop_df$GID_1, admin1_areas$GID_1)]
pop_df$pop_weight1 <- pop_df$pop / pop_df$adm1_pop
pop_df$pop2_weight1 <- pop_df$pop2 / pop_df$adm1_pop2
pop_df$pop3_weight1 <- pop_df$pop3 / pop_df$adm1_pop3
pop_df$area_weight1 <- pop_df$area / pop_df$adm1_area

## Calculate the x and y co-ordinates for the full -180-180, -90-90 
## 30 arc second grid from the x, y coords of cell centres
## These will be zero-indexed, so (pop_y * 43200) + pop_x + 1 would get
## back to the original 1-indexed cell value (if the raster was global)
## Note that y=0 is the N pole

pop_df$pop_x <- round((pop_df$x + 180)*120-0.5)
pop_df$pop_y <- round((90-pop_df$y)*120-0.5)

## And a test plot may be useful.
## Plotting using landscan co-ords here - but
## negating the y-axis so that 0 is at the top.

test_plot <- function(country) {
  gadm_rows <- which(gadm$GID_0 == country)
  subset <- pop_df[pop_df$gid2_row %in% gadm_rows, ]
  ggplot2::ggplot(subset, aes(x = pop_x, y = -pop_y, fill = pop)) +
    geom_tile() +
    coord_fixed() +
    scale_fill_gradient(
      low = "black",
      high = "white",
      trans = scales::pseudo_log_trans(base = 10),
      name = sprintf("%s Population", country)
    )
}

# pop_df_bord <- pop_df[coverage_fraction < 1]

# test_plot("GMB")


## Calculate index into CHIRPS v3, which is 7200 x 2400
## CHIRPS extent is lon -180..180, lat -60..60
## Trusting at the moment we are not modelling any countries north of 60.

## Test plot of CHIRPS, expanding as a vector

test_chirps <- function() {
  precip <- ncdf4::nc_open(sprintf(chirps_path, 2024, 1))
  d <- ncdf4::ncvar_get(precip, "precip")[, , 1]
  d <- as.vector(d)
  
  # Going to assume we are starting in row 1, and going left-to right.
  
  df <- data.frame(y = rep(0:2399, each = 7200),
                   x = rep(0:7199, 2400),
                   rain = d)
  
  ggplot(df, aes(x, y, fill = rain)) +
    geom_raster() +
    scale_fill_viridis_c() +
    coord_equal()
  
# test_chirps()
  
  # While the plot looks correct, the y-axis is increasing going upwards,
  # so in fact, (0, 0) is the South-West corner (-180, -90)
  
  # We can confirm this with
  
  # lat <- ncdf4::ncvar_get(precip, "latitude")
  # head(lat) # returns negatives, -59.975, -59.925 etc
  # tail(lat) # returns positives ending 52.925, 59.975
  
  # lon <- ncdf4::ncvar_get(precip, "longitude")
  # head(lon) # returns negatives, -179.975 -179.925
  # tail(lon) # returns positives ending 179.925 179.975
  
}

## So, to line this up. Using zero-indexing to stay sane,
## and thinking about lower-left corners of cells

## 0..7199 as Lower-left is -60   latitude, -180 .. +179.95
## 7200..14399 is          -59.95 latitude, -180 .. +179.95

## Landscan: y = 0 is latitude LL +89.99167
##           y = 1                +89.98333
##           y = 3599             +60.00        above chirps range
##           y = 3600             +59.99167     top of chirps_y = 6399
##           y = 17993            -59.95        chirps_y = 1
##           y = 17999            -60.00000     chirps_y = 0

conv_chirps_y <- data.frame(
  ls_y = 17999:3600,
  chirps_y = rep(0:2399, each = 6))

conv_chirps_x <- data.frame(
  ls_x = 0:43199,
  chirps_x = rep(0:7199, each = 6))

pop_df$chirps_x <- conv_chirps_x$chirps_x[match(pop_df$pop_x, conv_chirps_x$ls_x)]
pop_df$chirps_y <- conv_chirps_y$chirps_y[match(pop_df$pop_y, conv_chirps_y$ls_y)]
pop_df$chirps_i <- 1 + (pop_df$chirps_y * 7200) + pop_df$chirps_x

########################################
## All the same for ERA5. 3600 x 1801

test_era <- function() {
  era_t <- ncdf4::nc_open(sprintf(temp_path, 1, 2024))
  d <- ncdf4::ncvar_get(era_t, "2t") # [, , 1]
  d <- as.vector(d)
  # Going to assume we are starting in row 1, and going left-to right.
  
  df <- data.frame(y = rep(0:1800, each = 3600),
                   x = rep(0:3599, 1801),
                   temp = d)
  
  ggplot(df, aes(x, y, fill = temp)) +
    geom_raster() +
    scale_fill_viridis_c() +
    coord_equal()
  
  # Looks good - again, y-axis increases as you go up,
  # and (0,0) is the South-West corner (-180,-90)
  
  # lat <- ncdf4::ncvar_get(era, "latitude")
  # head(lat) # returns negatives, -90.0 -89.9 -89.8
  # tail(lat) # returns positives ending 89.9 90.0
  
  # lon <- ncdf4::ncvar_get(era, "longitude")
  # head(lon) # returns negatives, -179.9 -179.8 -179.7 etc
  # tail(lon) # returns positives ending 179.9 180.0
}

# test_era()

# Fiddly maths again:

# ERA latitude -89.9 covers from -89.85 to -89.95

## Lower-lefts:
## Landscan 0 is latitude +89.99167
## Landscan 6 is latitude +89.95 (so 0..5 = ERA_Y last row)

## So, with zero-indexing again.

conv_era_y <- data.frame(
  ls_y = 0:21599,
  era_y = c(rep(1800, 6),
            rep(1799:1, each = 12),
            rep(0, 6))
)

## Longitude:

## ERA5 -179.9 covers from -179.95 .. -179.85
## Landscan 0 is -180.0
## Landscan 6 is -179.95 - so (0,1,2,3,4,5)  is actually ERA5 3599.
## Last ERA5 is 180.0, which then covers 179.95 until -179.95
##    Landscan 179.95 to -179.95

conv_era_x <- data.frame(
  ls_x = 0:43199,
  era_x = c(rep(3599, 6),
            rep(0:3598, each = 12),
            rep(3599, 6))
)

pop_df$era_x <- conv_era_x$era_x[match(pop_df$pop_x, conv_era_x$ls_x)]
pop_df$era_y <- conv_era_y$era_y[match(pop_df$pop_y, conv_era_y$ls_y)]

## And then final vector index (which starts at 1 in R)

pop_df$era_i <- 1 + (pop_df$era_y * 3600) + pop_df$era_x

## Drop columns we don't need any more

# pop_df <- pop_df[, c("GID_0", "GID_1", "GID_2",
#                      "pop_weight1", "pop_weight2",
#                      "area_weight1", "area_weight2",
#                      "chirps_i", "era_i", "gid1_row", "gid2_row")]

## further simplify to speed up later calculations
area_adm1_era <- pop_df[, .(area_weight=sum(area_weight1),
                            pop_weight=sum(pop_weight1),
                            pop2_weight=sum(pop2_weight1),
                            pop3_weight=sum(pop3_weight1)),
                            list(gid1_row,era_i)]
area_adm1_chirps <- pop_df[, .(area_weight=sum(area_weight1),
                               pop_weight=sum(pop_weight1),
                               pop2_weight=sum(pop2_weight1),
                               pop3_weight=sum(pop3_weight1)),
                               list(gid1_row,chirps_i)]
area_adm2_era <- pop_df[, .(area_weight=sum(area_weight2),
                            pop_weight=sum(pop_weight2),
                            pop2_weight=sum(pop2_weight2),
                            pop3_weight=sum(pop3_weight2)),
                        list(gid2_row,era_i)]
area_adm2_chirps <- pop_df[, .(area_weight=sum(area_weight2),
                               pop_weight=sum(pop_weight2),
                               pop2_weight=sum(pop2_weight2),
                               pop3_weight=sum(pop3_weight2)),
                           list(gid2_row,chirps_i)]

n_adm1_era <- area_adm1_era[,.(n_era=.N),by=gid1_row]
n_adm2_era <- area_adm2_era[,.(n_era=.N),gid2_row]
n_adm1_chirps <- area_adm1_chirps[,.(n_chirps=.N),gid1_row]
n_adm2_chirps <- area_adm2_chirps[,.(n_chirps=.N),gid2_row]

sum_adm1 <- cbind(admin1_pops,admin1_areas[,2]/1e6,n_adm1_era[,2],n_adm1_chirps[,2],admin1_pixels[,2])
sum_adm1[,2:4] <- round(sum_adm1[,2:4])
sum_adm1$area <- round(sum_adm1$area,digits = 1)

sum_adm2 <- cbind(admin2_pops,admin2_areas[,2]/1e6,n_adm2_era[,2],n_adm2_chirps[,2],admin2_pixels[,2])
gadm_rows <- sum_adm2$gid2_row
sum_adm2[,2:4] <- round(sum_adm2[,2:4])
sum_adm2$area <- round(sum_adm2$area,digits = 1)
sum_adm2$gid2_row <- gadm$GID_2[gadm_rows]
names(sum_adm2)[1] <- "GID_2"

out_col_names_era <- c("tas","tmin","tmax","hurs","huss")
out_col_names_era_area <- paste0(out_col_names_era,"_area")
out_col_names_era_popLS <- paste0(out_col_names_era,"_popLS")
out_col_names_era_popWP <- paste0(out_col_names_era,"_popWP")
out_col_names_era_popGPW <- paste0(out_col_names_era,"_popGPW")

out_col_names_era_both <- c(out_col_names_era_area,out_col_names_era_popLS,out_col_names_era_popWP,out_col_names_era_popGPW)
out_col_names_all <- c(out_col_names_era,out_col_names_era_both)
set(area_adm1_era, j = out_col_names_all, value = NA_real_)
set(area_adm2_era, j = out_col_names_all, value = NA_real_)
out_names_pr <- c("pr_area","pr_popLS","pr_popWP","pr_popGPW")
set(area_adm1_chirps, j = c("pr",out_names_pr), value = NA_real_)
set(area_adm2_chirps, j = c("pr",out_names_pr), value = NA_real_)

# rm(pop_df)

setkey(area_adm1_era, gid1_row)
setkey(area_adm1_chirps, gid1_row)
setkey(area_adm2_era, gid2_row)
setkey(area_adm2_chirps, gid2_row)

## Main compute loop


nout_adm1 <- nr_adm1*ceiling((end_year-start_year+1)*365.25+1)
final_adm1 <- data.table(Date=structure(numeric(),class='Date'),gid1_row=integer(),
                         pr_area=numeric(), pr_popLS = numeric(),  pr_popWP = numeric(),  pr_popGPW = numeric(), 
                         tas_area=numeric(), tmin_area=numeric(), tmax_area=numeric(),
                         hurs_area=numeric(), huss_area=numeric(), 
                         tas_popLS = numeric(), tmin_popLS = numeric(), tmax_popLS = numeric(),
                         hurs_popLS = numeric(), huss_popLS = numeric(),
                         tas_popWP = numeric(), tmin_popWP = numeric(), tmax_popWP = numeric(),
                         hurs_popWP = numeric(), huss_popWP = numeric(),
                         tas_popGPW = numeric(), tmin_popGPW = numeric(), tmax_popGPW = numeric(), 
                         hurs_popGPW = numeric(), huss_popGPW = numeric() )[1:nout_adm1]
nout_adm2 <- nr_adm2*ceiling((end_year-start_year+1)*365.25+1)
final_adm2 <- data.table(Date=structure(numeric(),class='Date'),gid2_row=integer(),
                         pr_area=numeric(), pr_popLS = numeric(),  pr_popWP = numeric(),  pr_popGPW = numeric(),  
                         tas_area=numeric(), tmin_area=numeric(), tmax_area=numeric(),
                         hurs_area=numeric(), huss_area=numeric(), 
                         tas_popLS = numeric(), tmin_popLS = numeric(), tmax_popLS = numeric(),
                         hurs_popLS = numeric(), huss_popLS = numeric(),
                         tas_popWP = numeric(), tmin_popWP = numeric(), tmax_popWP = numeric(),
                         hurs_popWP = numeric(), huss_popWP = numeric(),
                         tas_popGPW = numeric(), tmin_popGPW = numeric(), tmax_popGPW = numeric(), 
                         hurs_popGPW = numeric(), huss_popGPW = numeric() )[1:nout_adm2]
time_point <- 0
base_date <- as.Date(sprintf("%d-01-01",start_year))
cat(proc.time()-ptm)
for (year in start_year:end_year) {

 precip_m <- h5read(file = sprintf(chirps_path, year), name = "pr")
 temp_m <- h5read(file = sprintf(temp_path, year), name = "tas")
 temp_min_m <- h5read(file = sprintf(tempmin_path, year), name = "tasmin")
 temp_max_m <- h5read(file = sprintf(tempmax_path, year), name = "tasmax")
 rel_hum_m <- h5read(file = sprintf(rh_path, year), name = "hurs")
 spec_hum_m <- h5read(file = sprintf(sh_path, year), name = "huss")
 dims_era <- dim(temp_m)
 dims_chirps <- dim(precip_m)
 days <- dims_era[3]
 vlen_era <- dims_era[1]*dims_era[2]
 vlen_chirps <- dims_chirps[1]*dims_chirps[2]
 dim(temp_m) <- c(vlen_era,days)
 dim(temp_min_m) <- c(vlen_era,days)
 dim(temp_max_m) <- c(vlen_era,days)
 dim(rel_hum_m) <- c(vlen_era,days)
 dim(spec_hum_m) <- c(vlen_era,days)
 dim(precip_m) <- c(vlen_chirps,days)
  
  for (day in seq_len(days)) {
    dt <- base_date+time_point
    time_point <- time_point + 1

    set(area_adm1_chirps, j="pr", value=precip_m[chirps_i,day])
    set(area_adm2_chirps, j="pr", value=precip_m[chirps_i,day])
    set(area_adm1_era, j=out_col_names_era, value=with(area_adm1_era, list(temp_m[era_i,day],
        temp_min_m[era_i,day], temp_max_m[era_i,day], rel_hum_m[era_i,day], spec_hum_m[era_i,day])))
    set(area_adm2_era, j=out_col_names_era, value=with(area_adm2_era, list(temp_m[era_i,day],
        temp_min_m[era_i,day], temp_max_m[era_i,day], rel_hum_m[era_i,day], spec_hum_m[era_i,day])))
    set(area_adm1_chirps, j = out_names_pr,
        value = with(area_adm1_chirps, list(pr * area_weight, pr * pop_weight,
                                            pr * pop2_weight, pr * pop3_weight)))
    set(area_adm2_chirps, j = out_names_pr,
        value = with(area_adm2_chirps, list(pr * area_weight, pr * pop_weight,
                                            pr * pop2_weight, pr * pop3_weight)))
    set(area_adm1_era, j = out_col_names_era_both,
        value = with(area_adm1_era, list(
          tas*area_weight, tmin*area_weight, tmax*area_weight, hurs*area_weight, huss*area_weight,
          tas*pop_weight,  tmin*pop_weight,  tmax*pop_weight,  hurs*pop_weight,  huss*pop_weight,
          tas*pop2_weight,  tmin*pop2_weight,  tmax*pop2_weight,  hurs*pop2_weight,  huss*pop2_weight,
          tas*pop3_weight,  tmin*pop3_weight,  tmax*pop3_weight,  hurs*pop3_weight,  huss*pop3_weight)))
    set(area_adm2_era, j = out_col_names_era_both,
        value = with(area_adm2_era, list(
          tas*area_weight, tmin*area_weight, tmax*area_weight, hurs*area_weight, huss*area_weight,
          tas*pop_weight,  tmin*pop_weight,  tmax*pop_weight,  hurs*pop_weight,  huss*pop_weight,
          tas*pop2_weight,  tmin*pop2_weight,  tmax*pop2_weight,  hurs*pop2_weight,  huss*pop2_weight,
          tas*pop3_weight,  tmin*pop3_weight,  tmax*pop3_weight,  hurs*pop3_weight,  huss*pop3_weight)))
    out1_rows <- (nr_adm1*(time_point-1)+1):(nr_adm1*time_point)
    out2_rows <- (nr_adm2*(time_point-1)+1):(nr_adm2*time_point)
    set(final_adm1,out1_rows,1,value = dt)
    set(final_adm2,out2_rows,1,value = dt)
    set(final_adm1,out1_rows,2:6,value = 
          area_adm1_chirps[, lapply(.SD, sum, na.rm = TRUE),
                           by = gid1_row, .SDcols = out_names_pr])
    set(final_adm2,out2_rows,2:6,value = 
          area_adm2_chirps[, lapply(.SD, sum, na.rm = TRUE),
                           by = gid2_row, .SDcols = out_names_pr])
    
    set(final_adm1,out1_rows,7:26,value = 
          area_adm1_era[, lapply(.SD, sum, na.rm = TRUE), 
                        by = gid1_row, .SDcols = out_col_names_era_both][,-1])
    set(final_adm2,out2_rows,7:26,value = 
          area_adm2_era[, lapply(.SD, sum, na.rm = TRUE), 
                        by = gid2_row, .SDcols = out_col_names_era_both][,-1])
  } # Day loop
  
 cat(paste0(round((proc.time()-ptm)[3],1),"  ", year,"\n"))
    
} # Year loop

## Save everything...
## Create folders and CSV stubs to append to. Think better to append to
## CSVs and then convert to parquet at the end

dir.create(output_path, showWarnings = FALSE)

country_regions <- read.csv(file.path(base, "DataCentre", "data",
                                      "country_regions_subset.txt"), sep = "\t")


regions <- gsub(".","_",country_regions$region[match(gadm$GID_0, country_regions$country)],fixed=TRUE)
admins <- gadm$GID_2
admins[is.na(admins)] <- gadm$GID_1[is.na(admins)]
admins[is.na(admins)] <- gadm$GID_0[is.na(admins)]
gadm$filename <- sprintf(
  "%s/%s/%s_v410_%s_CHIRPSv3_ERA5Land_1981_2025_observation_adm2.pq",
  output_path, gadm$GID_0, regions, admins)

# Create empty country folder

for (country in countries) {
  cpath <- file.path(output_path, country)
  dir.create(cpath, showWarnings = FALSE, recursive = TRUE)
}


cat("Saving ADM1 to disk\n")
out_schema <- schema(Date = date32(), pr_area = float32(), tas_area = float32(),
                     tmin_area = float32(), tmax_area = float32(), hurs_area = float32(),
                     huss_area = float32(), 
                     pr_popLS = float32(), tas_popLS = float32(),
                     tmin_popLS = float32(), tmax_popLS = float32(),
                     hurs_popLS = float32(), huss_popLS = float32(),
                     pr_popWP = float32(), tas_popWP = float32(),
                     tmin_popWP = float32(), tmax_popWP = float32(),
                     hurs_popWP = float32(), huss_popWP = float32(),
                     pr_popGPW = float32(), tas_popGPW = float32(),
                     tmin_popGPW = float32(), tmax_popGPW = float32(),
                     hurs_popGPW = float32(), huss_popGPW = float32()
                     )
out_col_reorder <- c(1,3,7:11,4,12:16,5,17:21,6,22:26)
gc()

setkey(final_adm1,gid1_row,Date)
final_adm1[,c(3:6)] <- round(final_adm1[,c(3:6)],digits = 4)
final_adm1[,c(7:26)] <- round(final_adm1[,c(7:26)],digits = 2)

# metadata
authors <- "(c) 2026: Sally Jahn, Wes Hinsley and Neil Ferguson, Imperial College London"
variable_description <- "pr: total precipitation [mm], tas: 2m surface air temperature [Celsius], tasmax: maximum 2m surface air temperature [Celsius], tasmin: minimum 2m surface air temperature [Celsius], hurs: relative humidity [%], huss: specific humidity [g/kg]"
variable_suffix_description = "area: area average, LS: Landscan population-weighted average, WP: WorldPop population-weighted average, GPW: GPW population-weighted average"
time_period_covered <- paste0(start_year,"-",end_year)
population_data <- "Lansdscan Global 2024, WorldPop GlobalPop V2, Gridded Population of the World (GPW v11) 2020 [all 30 arc-second rasters]"
administrative_boundary_data <- "GADM v4.10"
temperature_data <- "ERA5-Land, 0.1 degree raster"
precipitation_data <- "CHIRPS v3, 0.05 degree raster"
meta_names <- c("authors","variable_description","variable_suffix_description",
                "time_period_covered","population_data","administrative_boundary_data",
                "temperature_data","precipitation_data","GADM_GID_1",
                "population_LS","population_WP","population_GPW",
                "admin_area_km2","temp_raster_pixels","precip_raster_pixels",
                "population_raster_pixels")
# vector to store checks for blank results
gid1_check <- rep(NA, nrow(sum_adm1))

for (i in seq_len(nrow(sum_adm1))) {
  adm1 <- sum_adm1$GID_1[i]
  gadm0 <- substring(adm1, 1, 3)
  region <- gsub(".","_",country_regions$region[country_regions$country == gadm0],fixed=TRUE)
  fn <- sprintf(
    "%s/%s/%s_v410_%s_CHIRPSv3_ERA5Land_1981_2025_observation_adm1.pq",
    output_path, gadm0, region, adm1)
  cat(paste0(fn, "          \r"))
  out_dt <- final_adm1[gid1_row==i, ..out_col_reorder]
  chk <- sum(out_dt$tas_area)  # quick check for all zeros in TAS
  gid1_check[i] <- is.na(chk) || (chk == 0)
  out_ar <- arrow_table(out_dt,schema=out_schema)
  meta_data <- c(authors,variable_description,variable_suffix_description,
                 time_period_covered, population_data,administrative_boundary_data,
                 temperature_data,precipitation_data,as.vector(sum_adm1[i,]))
  out_ar$metadata[meta_names] <- meta_data
  if(gid1_check[i]) fn <- paste0(fn, ".bad")
  arrow::write_parquet(out_ar, fn, compression="uncompressed")
}
cat("\n")
cat(proc.time()-ptm)

cat("Saving ADM2 to disk\n")
gc()

setkey(final_adm2,gid2_row,Date)
final_adm2[,c(3:6)] <- round(final_adm2[,c(3:6)],digits = 4)
final_adm2[,c(7:26)] <- round(final_adm2[,c(7:26)],digits = 2)

meta_names[9] <- "GADM_GID_2"

gid2_check <- rep(NA,nrow(gadm))
for (i in gadm_rows) {
  cat(paste0( gadm$filename[i],"          \r"))
  out_dt <- final_adm2[gid2_row==i, ..out_col_reorder]
  chk <- sum(out_dt$tas_area)  # quick check for all zeros in TAS
  gid2_check[i] <- is.na(chk) || (chk == 0)
  fn <- gadm$filename[i]
  if(gid2_check[i]) fn <- paste0(fn, ".bad")
  out_ar <- arrow_table(out_dt,schema=out_schema)
  meta_data <- c(authors,variable_description,variable_suffix_description,
                 time_period_covered, population_data,administrative_boundary_data,
                 temperature_data,precipitation_data,as.vector(sum_adm2[i,]))
  out_ar$metadata[meta_names] <- meta_data
  arrow::write_parquet(out_ar, fn, compression="uncompressed")

}

cat("\n")

## Areas with no ERA5 Land coverage - results in zeros
# CHIRPS blanks generally a subset of these
print(paste0("Number of zero or NA admin1 areas = ",sum(gid1_check, na.rm=TRUE)))
sum_adm1$index <- 1:nrow(sum_adm1)
missing_adm1 <- sum_adm1[gid1_check]
print(sum_adm1[gid1_check,1])
print(paste0("Number of zero or NA admin2 areas = ",sum(gid2_check, na.rm=TRUE)))
print(sum_adm2[gid2_check,1])

print(proc.time()-ptm)

## csv files for a few countries
out_countries <- c("LKA","THA","COL")
adm0_adm1 <- substring(sum_adm1$GID_1[final_adm1$gid1_row],1,3)
adm0_adm2 <- gadm$GID_0[final_adm2$gid2_row]
for (c in out_countries) {
  out_dt <- final_adm1[adm0_adm1 == c,]
  out_dt$gid1_row <- sum_adm1$GID_1[out_dt$gid1_row ]
  fn <- sprintf("%s/obs_clim_%s_adm1.csv",output_path, c)
  fwrite(out_dt,fn)
  out_dt <- final_adm2[adm0_adm2 == c,]
  out_dt$gid2_row <- sum_adm2$GID_2[out_dt$gid2_row ]
  fn <- sprintf("%s/obs_clim_%s_adm2.csv",output_path, c)
  fwrite(out_dt,fn)
  }
for (c in out_countries) {
  out_dt <- sum_adm1[substring(sum_adm1$GID_1,1,3) == c,-"index"]
  fn <- sprintf("%s/summary_%s_adm1.csv",output_path, c)
  fwrite(out_dt,fn)
  out_dt <- sum_adm2[substring(sum_adm2$GID_2,1,3) == c,]
  fn <- sprintf("%s/summary_%s_adm2.csv",output_path, c)
  fwrite(out_dt,fn)
}
