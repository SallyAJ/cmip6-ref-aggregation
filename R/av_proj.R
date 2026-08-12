# Copyright © 2026 Wes Hinsley and Neil Ferguson (GitHubIDs: weshinsley and NeilFerguson)

run_proj <- function(region_selected,
                     all_scenarios = list("HISTORICAL","SSP245", "SSP585")) {

  # region_selected <- "Africa"
  # all_scenarios <- list("HISTORICAL","SSP245", "SSP585")
  all_models <- list("MRI-ESM2-0", "CanESM5", "GFDL-ESM4", "MPI-ESM1-2-LR", "TaiESM1", "UKESM1.0-LL")
  all_model_versions <- list("r1i1p1f1","r1i1p1f1","r1i1p1f1","r1i1p1f1","r1i1p1f1","r1i1p1f2")

  # all_models <- list("UKESM1.0-LL")
  # all_model_versions <- list("r1i1p1f2")
  
    
  ## Packages needed
  
  # install.packages(c("terra", "sf", "exactextractr", "data.table", "ggplot2",
  #                    "scales", "ncdf4", "dplyr", "arrow"))
  
  # if (!require("BiocManager", quietly = TRUE))
  #   install.packages("BiocManager")
  # 
  # BiocManager::install(c("rhdf5","rhdf5filters"))
  
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
  
  ## Initial set-up 
  
  {
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
    
    # Replace Placeholders Paths
    ## TODO
    infiniband_share <- "<INFINIBAND_SHARE>"
    non_infiniband_share <- "<NON_INFINIBAND_SHARE>"
    
    base <- get_base()
    
    ## match of countries to regions
    
    country_regions <- read.csv(file.path(base, "DataCentre", "data",
                                          "country_regions_subset.txt"), sep = "\t")
    
    countries <- country_regions$country[country_regions$region==region_selected]
    
    # Output folder
    
    output_path <- file.path(base, "DataCentre", "data", "countries", "projections_areapop")
    
    ## Population 
  
    pop_file <- "Landscan/2024/landscan-global-2024.tif"
    pop_name <- "LS2024"
    
    pop_file2 <- "WorldPop/GlobalV2/global_pop_2024_CN_1km_R2025A_UA_v1.tif"
    pop_name2 <- "WP2024"
    
    pop_file3 <- "GPW/gpw_v4_population_count_adjusted_to_2015_unwpp_country_totals_rev11_2020_30_sec.tif"
    pop_name2 <- "GPW2020"
    
    adm_level <- 2
    gadm_gpkg <- "DataCentre/data/global/observation/external/GADM/gadm_410-levels.gpkg"
    
    ## Load pop rasters
    
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
    admin1_rows <- data.frame(GID_1=admin1_pops$GID_1,gid1_row = (1:nr_adm1))
    
    pop_df$gid1_row <- admin1_rows$gid1_row[match(pop_df$GID_1, admin1_rows$GID_1)]
    pop_df$adm1_pop <- admin1_pops$pop[match(pop_df$GID_1, admin1_pops$GID_1)]
    pop_df$adm1_pop2 <- admin1_pops$pop2[match(pop_df$GID_1, admin1_pops$GID_1)]
    pop_df$adm1_pop3 <- admin1_pops$pop3[match(pop_df$GID_1, admin1_pops$GID_1)]
    pop_df$adm1_area <- admin1_areas$area[match(pop_df$GID_1, admin1_areas$GID_1)]
    pop_df$pop_weight1 <- pop_df$pop / pop_df$adm1_pop
    pop_df$pop2_weight1 <- pop_df$pop2 / pop_df$adm1_pop2
    pop_df$pop3_weight1 <- pop_df$pop3 / pop_df$adm1_pop3
    pop_df$area_weight1 <- pop_df$area / pop_df$adm1_area
  }
  
  first_run <- TRUE
  
  for(scen_num in 1:length(all_scenarios)) {
    gc()
    scenario_selected <- all_scenarios[[scen_num]]
    ## paths for projection rasters 
    
    if(scenario_selected=="HISTORICAL") {
      start_year <- 1985; end_year <- 2014 
    } else if(scenario_selected %in% c("SSP245","SSP585")) {
      start_year <- 2015; end_year <- 2100 
    } else {
      stop("Scenario selected not one of HISTORICAL, SSP245 or SSP585.\n")
    }
    
    proj_path <- file.path(base, "DataCentre", "data", "global", "projections","external", scenario_selected, region_selected)
    scenario_fn <- tolower(scenario_selected)
    
    for(model_num in 1:length(all_models)) {
      model_selected <- all_models[[model_num]]
      version_selected <- all_model_versions[[model_num]]
      cat(paste0(round((proc.time()-ptm)[3],1),"  Model = ",model_selected,"\n"))
      
      input_fn <- paste0(proj_path, "_%s_DBCCA_",model_selected,"_",start_year,"_",
                         end_year,"_",version_selected,"_",tolower(scenario_selected),"_compressed.nc")
  
      ## find NetCDF lat-long extent, number of timesteps, chunk size
  
      if(first_run || ((scen_num < 3) && (model_num == 1))) {
        print(paste0("Trying to open ",sprintf(input_fn,"tas")))
        test <- H5Fopen(sprintf(input_fn,"tas"))
        testd <- H5Dopen(test,"tas")
        time_chunk <- H5Dchunk_dims(testd)[3]
        raster_lat <- test$lat
        raster_lon <- test$lon
        h5closeAll()
        ras_info <- h5ls(sprintf(input_fn,"tas"))
        n_lat <- as.numeric(ras_info[ras_info$name=="lat",5])
        n_lon <- as.numeric(ras_info[ras_info$name=="lon",5])
        n_time <- as.numeric(ras_info[ras_info$name=="time",5])
        grid_lat <- raster_lat[2] - raster_lat[1]  # grid size for lat
        min_lat <- raster_lat[1] - grid_lat/2      # lower edge of raster 
        grid_lon <- raster_lon[2] - raster_lon[1]  # grid size for lon 
        min_lon <- raster_lon[1] - grid_lon/2      # left edge of raster
        scale_lat <- grid_lat*120                  # number of pop raster cells per climate raster cell (lat)
        scale_lon <- grid_lon*120                  # number of pop raster cells per climate raster cell (lon)
 

        ## test plot of temperature layer
        # test <- as.vector(h5read(file = sprintf(input_fn, "tas"), name = "tas", index = list(NULL,NULL,1)))
        #     df <- data.frame(y = rep(raster_lat, each = n_lon),
        #                  x = rep(raster_lon, n_lat),
        #                  temp = test)
        # 
        # ggplot(df, aes(x, y, fill = temp)) +
        #   geom_raster() +
        #   scale_fill_viridis_c() +
        #   coord_equal()
        }
      if(first_run) {
        # load first temp raster to find NA pixels later
        test_rast <- as.vector(h5read(file = sprintf(input_fn, "tas"), name = "tas", index = list(NULL,NULL,1)))
        ## lookup from pop raster cells to climate raster cells using lat/long centres of each
        ## R is column major, so climate raster is [lon, lat, time]
        ## so one column has all lon (x), one row has all lat (y) 
        
        pop_df$era_x <- floor((pop_df$x - 1/240 - min_lon)/grid_lon)
        pop_df$era_y <- floor((pop_df$y - 1/240 - min_lat)/grid_lat)
        if(max(pop_df$era_x) >= n_lon) stop("Population raster has larger max lon than climate raster\n")
        if(max(pop_df$era_y) >= n_lat) stop("Population raster has larger max lat than climate raster\n")
        if(min(pop_df$era_x) < 0) stop("Population raster has smaller min lon than climate raster\n")
        if(min(pop_df$era_y) < 0) stop("Population raster has smaller min lat than climate raster\n")
        pop_df$era_i <- n_lon * pop_df$era_y + pop_df$era_x + 1 # remember to add 1!
        
        
        ## further simplify to speed up later calculations
        area_adm1_era <- pop_df[, .(area_weight=sum(area_weight1),
                                    pop_weight=sum(pop_weight1),
                                    pop2_weight=sum(pop2_weight1),
                                    pop3_weight=sum(pop3_weight1)),
                                    list(gid1_row,era_i)]
        area_adm2_era <- pop_df[, .(area_weight=sum(area_weight2),
                                    pop_weight=sum(pop_weight2),
                                    pop2_weight=sum(pop2_weight2),
                                    pop3_weight=sum(pop3_weight2)),
                                list(gid2_row,era_i)]
        
        ## count era pixels before NA pixel extension to area_adm2_era
        n_adm1_era <- area_adm1_era[,.(n_era=.N),by=gid1_row]
        n_adm2_era <- area_adm2_era[,.(n_era=.N),gid2_row]
        
        ## now get NA pixels included in area_adm2_era
        all_pixels <- unique(area_adm2_era$era_i)
        na_pixels <- all_pixels[is.na(test_rast[all_pixels])]
        
        ## back transform to x and y
        na_pixels_x <- (na_pixels-1) %% n_lon
        na_pixels_y <- (na_pixels-1) %/% n_lon
        ## move +/- on on lat and lon
        na_p_x_p <- ifelse(na_pixels_x < n_lon, na_pixels_x+1, na_pixels_x)
        na_p_x_m <- ifelse(na_pixels_x > 0, na_pixels_x-1, na_pixels_x)
        na_p_y_p <- ifelse(na_pixels_y < n_lat, na_pixels_y+1, na_pixels_y)
        na_p_y_m <- ifelse(na_pixels_y > 0, na_pixels_y-1, na_pixels_y)
        ## indices of 4 adjacent pixels 
        na_p_a1 <- n_lon * na_p_y_p + na_pixels_x + 1
        na_p_a2 <- n_lon * na_p_y_m + na_pixels_x + 1
        na_p_a3 <- n_lon * na_pixels_y + na_p_x_p + 1
        na_p_a4 <- n_lon * na_pixels_y + na_p_x_m + 1
        na_p_a5 <- n_lon * na_p_y_p + na_p_x_m + 1
        na_p_a6 <- n_lon * na_p_y_p + na_p_x_p + 1
        na_p_a7 <- n_lon * na_p_y_m + na_p_x_m + 1
        na_p_a8 <- n_lon * na_p_y_m + na_p_x_p + 1
        ## now organise adjacent pixels in long format data.table
        na_pixel_dt <- as.data.table(rbind(cbind(era_i=na_pixels,ad=na_p_a1),
                                 cbind(era_i=na_pixels,ad=na_p_a2),
                                 cbind(era_i=na_pixels,ad=na_p_a3),
                                 cbind(era_i=na_pixels,ad=na_p_a4),
                                 cbind(era_i=na_pixels,ad=na_p_a5),
                                 cbind(era_i=na_pixels,ad=na_p_a6),
                                 cbind(era_i=na_pixels,ad=na_p_a7),
                                 cbind(era_i=na_pixels,ad=na_p_a8)))
        ## remove adjacent pixels which are also NA
        na_pixel_dt <- na_pixel_dt[!is.na(test_rast[ad])]
        ## count non-NA adjacent pixels
        na_pix_ad_n <- na_pixel_dt[, .(n_ad = .N), by=era_i]
        ## and put counts back in full table
        na_pixel_dt$n_ad <- na_pix_ad_n$n_ad[match(na_pixel_dt$era_i,na_pix_ad_n$era_i)]
        
        ## now extend area_adm2_era with additional non-na pixels
        area_adm2_era_m <- as.data.table(merge(area_adm2_era,na_pixel_dt, by="era_i", all=TRUE, allow.cartesian=TRUE))
        # non NA era_i pixels get weight 1
        area_adm2_era_m[is.na(n_ad), n_ad := 1]
        # replace era_i for NA pixels with index of non-NA adjacent pixel
        area_adm2_era_m[!is.na(ad), era_i := ad]
        ## adjust weights to reflect contributing pixels
        area_adm2_era_m[, `:=`(area_weight = area_weight/n_ad, pop_weight = pop_weight/n_ad,
                            pop2_weight = pop2_weight/n_ad, pop3_weight = pop3_weight/n_ad)]
        ## replace original area_adm2_era
        area_adm2_era <- area_adm2_era_m[,.(gid2_row,era_i,area_weight,pop_weight,pop2_weight,pop3_weight)]
        rm(area_adm2_era_m)
        
        ## now extend area_adm1_era with additional non-na pixels
        area_adm1_era_m <- as.data.table(merge(area_adm1_era,na_pixel_dt, by="era_i", all=TRUE, allow.cartesian=TRUE))
        # non NA era_i pixels get weight 1
        area_adm1_era_m[is.na(n_ad), n_ad := 1]
        # replace era_i for NA pixels with index of non-NA adjacent pixel
        area_adm1_era_m[!is.na(ad), era_i := ad]
        ## adjust weights to reflect contributing pixels
        area_adm1_era_m[, `:=`(area_weight = area_weight/n_ad, pop_weight = pop_weight/n_ad,
                               pop2_weight = pop2_weight/n_ad, pop3_weight = pop3_weight/n_ad)]
        ## replace original area_adm1_era
        area_adm1_era <- area_adm1_era_m[,.(gid1_row,era_i,area_weight,pop_weight,pop2_weight,pop3_weight)]
        rm(area_adm1_era_m)
        
        ## tables summarising adm areas
        sum_adm1 <- cbind(admin1_pops,admin1_areas[,2]/1e6,n_adm1_era[,2],admin1_pixels[,2])
        sum_adm1[,2:4] <- round(sum_adm1[,2:4])
        sum_adm1$area <- round(sum_adm1$area,digits = 1)
        
        sum_adm2 <- cbind(admin2_pops,admin2_areas[,2]/1e6,n_adm2_era[,2],admin2_pixels[,2])
        gadm_rows <- sum_adm2$gid2_row
        sum_adm2[,2:4] <- round(sum_adm2[,2:4])
        sum_adm2$area <- round(sum_adm2$area,digits = 1)
        sum_adm2$gid2_row <- gadm$GID_2[gadm_rows]
        names(sum_adm2)[1] <- "GID_2"
        
        out_col_names_era <- c("pr","tas","tmin","tmax","hurs","huss")
        out_col_names_era_area <- paste0(out_col_names_era,"_area")
        out_col_names_era_popLS <- paste0(out_col_names_era,"_popLS")
        out_col_names_era_popWP <- paste0(out_col_names_era,"_popWP")
        out_col_names_era_popGPW <- paste0(out_col_names_era,"_popGPW")
        
        out_col_names_era_both <- c(out_col_names_era_area,out_col_names_era_popLS,out_col_names_era_popWP,out_col_names_era_popGPW)
        out_col_names_all <- c(out_col_names_era,out_col_names_era_both)
        set(area_adm1_era, j = out_col_names_all, value = NA_real_)
        set(area_adm2_era, j = out_col_names_all, value = NA_real_)
        
        # rm(pop_df)
        
        setkey(area_adm1_era, gid1_row)
        setkey(area_adm2_era, gid2_row)
      }
      if(first_run || ((scen_num < 3) && (model_num == 1))) {
        
        ## Output data.tables
        
        nout_adm1 <- nr_adm1*ceiling((end_year-start_year+1)*365.25+1)
        final_adm1 <- data.table(Date=structure(numeric(),class='Date'),gid1_row=integer(),
                                 pr_area=numeric(), tas_area=numeric(), tmin_area=numeric(),
                                 tmax_area=numeric(), hurs_area=numeric(), huss_area=numeric(), 
                                 pr_popLS = numeric(),  tas_popLS = numeric(), tmin_popLS = numeric(),
                                 tmax_popLS = numeric(), hurs_popLS = numeric(), huss_popLS = numeric(),
                                 pr_popWP = numeric(),  tas_popWP = numeric(), tmin_popWP = numeric(), 
                                 tmax_popWP = numeric(), hurs_popWP = numeric(), huss_popWP = numeric(),
                                 pr_popGPW = numeric(), tas_popGPW = numeric(), tmin_popGPW = numeric(),
                                 tmax_popGPW = numeric(), hurs_popGPW = numeric(), huss_popGPW = numeric() )[1:nout_adm1]
        nout_adm2 <- nr_adm2*ceiling((end_year-start_year+1)*365.25+1)
        final_adm2 <- data.table(Date=structure(numeric(),class='Date'),gid2_row=integer(),
                                 pr_area=numeric(), tas_area=numeric(), tmin_area=numeric(),
                                 tmax_area=numeric(), hurs_area=numeric(), huss_area=numeric(), 
                                 pr_popLS = numeric(),  tas_popLS = numeric(), tmin_popLS = numeric(),
                                 tmax_popLS = numeric(), hurs_popLS = numeric(), huss_popLS = numeric(),
                                 pr_popWP = numeric(),  tas_popWP = numeric(), tmin_popWP = numeric(), 
                                 tmax_popWP = numeric(), hurs_popWP = numeric(), huss_popWP = numeric(),
                                 pr_popGPW = numeric(), tas_popGPW = numeric(), tmin_popGPW = numeric(),
                                 tmax_popGPW = numeric(), hurs_popGPW = numeric(), huss_popGPW = numeric() )[1:nout_adm2]
        
        # Go from t=1 to n_time in steps of time_chunk
        
        n_chunks <- ceiling(n_time/time_chunk)
        time_steps <- (1:n_chunks)*time_chunk
        time_steps[n_chunks] <- n_time # last step to read may be shorter
      }
      
      ## Main loop  
      time_point <- 0
      last_t <- 0
      base_date <- as.Date(sprintf("%d-01-01",start_year))
      cat(proc.time()-ptm)
      for (cn in 1:n_chunks) {
       time_range <- (last_t + 1):(time_steps[cn])
       last_t <- time_steps[cn]
       index_list <- list(NULL,NULL,time_range)
       
       precip_m <- h5read(file = sprintf(input_fn, "pr"), name = "pr", index = index_list)
       temp_m <- h5read(file = sprintf(input_fn, "tas"), name = "tas", index = index_list)
       temp_min_m <- h5read(file = sprintf(input_fn, "tasmin"), name = "tasmin", index = index_list)
       temp_max_m <- h5read(file = sprintf(input_fn, "tasmax"), name = "tasmax", index = index_list)
       rel_hum_m <- h5read(file = sprintf(input_fn, "hurs"), name = "hurs", index = index_list)
       spec_hum_m <- h5read(file = sprintf(input_fn, "huss"), name = "huss", index = index_list)
       dims_era <- dim(temp_m)
       days <- dims_era[3]
       vlen_era <- dims_era[1]*dims_era[2]
       dim(precip_m) <- c(vlen_era,days)
       dim(temp_m) <- c(vlen_era,days)
       dim(temp_min_m) <- c(vlen_era,days)
       dim(temp_max_m) <- c(vlen_era,days)
       dim(rel_hum_m) <- c(vlen_era,days)
       dim(spec_hum_m) <- c(vlen_era,days)
       
        for (day in seq_len(days)) {
          dt <- base_date + time_point
          time_point <- time_point + 1
      
          set(area_adm1_era, j=out_col_names_era, value=with(area_adm1_era, list(precip_m[era_i,day], temp_m[era_i,day],
              temp_min_m[era_i,day], temp_max_m[era_i,day], rel_hum_m[era_i,day], spec_hum_m[era_i,day])))
          set(area_adm2_era, j=out_col_names_era, value=with(area_adm2_era, list(precip_m[era_i,day], temp_m[era_i,day],
              temp_min_m[era_i,day], temp_max_m[era_i,day], rel_hum_m[era_i,day], spec_hum_m[era_i,day])))
          set(area_adm1_era, j = out_col_names_era_both,
              value = with(area_adm1_era, list(
                pr*area_weight, tas*area_weight, tmin*area_weight, tmax*area_weight, hurs*area_weight, huss*area_weight,
                pr*pop_weight, tas*pop_weight, tmin*pop_weight, tmax*pop_weight,  hurs*pop_weight,  huss*pop_weight,
                pr*pop2_weight, tas*pop2_weight,  tmin*pop2_weight,  tmax*pop2_weight,  hurs*pop2_weight,  huss*pop2_weight,
                pr*pop3_weight, tas*pop3_weight,  tmin*pop3_weight,  tmax*pop3_weight,  hurs*pop3_weight,  huss*pop3_weight)))
          set(area_adm2_era, j = out_col_names_era_both,
              value = with(area_adm2_era, list(
                pr*area_weight, tas*area_weight, tmin*area_weight, tmax*area_weight, hurs*area_weight, huss*area_weight,
                pr*pop_weight, tas*pop_weight, tmin*pop_weight, tmax*pop_weight,  hurs*pop_weight,  huss*pop_weight,
                pr*pop2_weight, tas*pop2_weight,  tmin*pop2_weight,  tmax*pop2_weight,  hurs*pop2_weight,  huss*pop2_weight,
                pr*pop3_weight, tas*pop3_weight,  tmin*pop3_weight,  tmax*pop3_weight,  hurs*pop3_weight,  huss*pop3_weight)))
          out1_rows <- (nr_adm1*(time_point-1)+1):(nr_adm1*time_point)
          out2_rows <- (nr_adm2*(time_point-1)+1):(nr_adm2*time_point)
          set(final_adm1,out1_rows,1,value = dt)
          set(final_adm2,out2_rows,1,value = dt)
         
          set(final_adm1,out1_rows,2:26,value = 
                area_adm1_era[, lapply(.SD, sum, na.rm = TRUE), 
                              by = gid1_row, .SDcols = out_col_names_era_both])
          set(final_adm2,out2_rows,2:26,value = 
                area_adm2_era[, lapply(.SD, sum, na.rm = TRUE), 
                              by = gid2_row, .SDcols = out_col_names_era_both])
        } # Day loop
        
       cat(paste0(round((proc.time()-ptm)[3],1),"  ", dt,"\n"))
          
      } # chunk loop
      
      ## Save everything...
      ## Create folders and CSV stubs to append to. Think better to append to
      ## CSVs and then convert to parquet at the end
      
      dir.create(output_path, showWarnings = FALSE)
      
      regions <- gsub(".","_",country_regions$region[match(gadm$GID_0, country_regions$country)],fixed=TRUE)
      admins <- gadm$GID_2
      admins[is.na(admins)] <- gadm$GID_1[is.na(admins)]
      admins[is.na(admins)] <- gadm$GID_0[is.na(admins)]
      gadm$filename <- sprintf(
        "%s/%s/%s_v410_%s_%s_%d_%d_%s_%s_adm2.pq",
        output_path, gadm$GID_0, regions, admins,model_selected,start_year,end_year,version_selected,scenario_fn)
      
      
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
      out_col_reorder <- c(1,3:26)
      gc()
      
      setkey(final_adm1,gid1_row,Date)
      cols4 <- c(3, 9, 15, 21)
      cols2 <- c(4:8, 10:14, 16:20, 22:26)
      
      final_adm1[, (cols4) := round(.SD, 4), .SDcols = cols4]
      final_adm1[, (cols2) := round(.SD, 2), .SDcols = cols2]
      
      # metadata
      authors <- "(c) 2026: Sally Jahn, Wes Hinsley and Neil Ferguson, Imperial College London"
      variable_description <- "pr: total precipitation [mm], tas: 2m surface air temperature [Celsius], tasmax: maximum 2m surface air temperature [Celsius], tasmin: minimum 2m surface air temperature [Celsius], hurs: relative humidity [%], huss: specific humidity [g/kg]"
      variable_suffix_description = "area: area average, LS: Landscan population-weighted average, WP: WorldPop population-weighted average, GPW: GPW population-weighted average"
      time_period_covered <- paste0(start_year,"-",end_year)
      population_data <- "Lansdscan Global 2024, WorldPop GlobalPop V2, Gridded Population of the World (GPW v11) 2020 [all 30 arc-second rasters]"
      administrative_boundary_data <- "GADM v4.10"
      climate_projection_model <- model_selected
      climate_scenario <- scenario_fn
      BCD_method <- "DBCCA"
      downscaled_raster_resolution <- "0.1 dgrees"
      temperature_data_ref <- "ERA5-Land, 0.1 degree raster"
      precipitation_data_ref <- "CHIRPS v3, (upscaled to) 0.1 degree raster"
      meta_names <- c("authors","variable_description","variable_suffix_description",
                      "time_period_covered","population_data","administrative_boundary_data",
                      "climate_projection_model","climate_scenario","BCD_method","downscaled_raster_resolution",
                      "temperature_data_ref","precipitation_data_ref","GADM_GID_1",
                      "population_LS","population_WP","population_GPW",
                      "admin_area_km2","climate_raster_pixels","population_raster_pixels")
      # vector to store checks for blank results
      gid1_check <- rep(NA, nrow(sum_adm1))
      
      for (i in seq_len(nrow(sum_adm1))) {
        adm1 <- sum_adm1$GID_1[i]
        gadm0 <- substring(adm1, 1, 3)
        region <- gsub(".","_",country_regions$region[country_regions$country == gadm0],fixed=TRUE)
        fn <- sprintf(
          "%s/%s/%s_v410_%s_%s_%d_%d_%s_%s_adm1.pq",
          output_path, gadm0, region, adm1,model_selected,start_year,end_year,version_selected,scenario_fn)
        cat(paste0(fn, "          \r"))
        out_dt <- final_adm1[gid1_row==i, ..out_col_reorder]
        chk <- sum(out_dt$tas_area)  # quick check for all zeros in TAS
        gid1_check[i] <- is.na(chk) || (chk == 0)
        out_ar <- arrow_table(out_dt,schema=out_schema)
        meta_data <- c(authors,variable_description,variable_suffix_description,
                       time_period_covered, population_data,administrative_boundary_data,
                       climate_projection_model,climate_scenario,BCD_method,downscaled_raster_resolution,
                       temperature_data_ref,precipitation_data_ref,as.vector(sum_adm1[i,]))
        out_ar$metadata[meta_names] <- meta_data
        if(gid1_check[i]) fn <- paste0(fn, ".bad")
        arrow::write_parquet(out_ar, fn, compression="uncompressed")
      }
      cat("\n")
      cat(proc.time()-ptm)
      
      cat("Saving ADM2 to disk\n")
      gc()
      
      setkey(final_adm2,gid2_row,Date)
      final_adm2[, (cols4) := round(.SD, 4), .SDcols = cols4]
      final_adm2[, (cols2) := round(.SD, 2), .SDcols = cols2]
      meta_names[13] <- "GADM_GID_2"
      
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
                       climate_projection_model,climate_scenario,BCD_method,downscaled_raster_resolution,
                       temperature_data_ref,precipitation_data_ref,as.vector(sum_adm2[i,]))
        out_ar$metadata[meta_names] <- meta_data
        arrow::write_parquet(out_ar, fn, compression="uncompressed")
      }
      
      cat("\n")
      
      ## Areas with no ERA5 Land coverage - results in zeros
      # CHIRPS blanks generally a subset of these
      print(paste0("Number of zero or NA admin1 areas = ",sum(gid1_check, na.rm=TRUE), " out of ",length(gid1_check)))
      missing_adm1 <- sum_adm1[gid1_check]
      print(sum_adm1[gid1_check,1])
      print(paste0("Number of zero or NA admin2 areas = ",sum(gid2_check, na.rm=TRUE), " out of ",length(gid2_check)))
      print(sum_adm2[gid2_check,1])
      
      first_run <- FALSE
      gc()
      print(proc.time()-ptm)
    }
  }
}
    
