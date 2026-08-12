## region to run

source("av_proj.R")
all_regions <- c("Africa", "Australasia", "Central_America", "Central_Asia", "East_Asia", 
                 "Europe", "MED", "MENA", "SEA", "South_America", "South_Asia")

## in reality, would want to run regions in parallel
for(region in all_regions) run_proj(region)

