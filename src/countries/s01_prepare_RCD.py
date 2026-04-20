# ScriptOverview
# Countries were assigned to domains based on the overlap with, and the distance between, each country's geographic
# center and predefined reference of the domain.
# This assignment method can be modified depending on the specific criteria used for domain allocation.

# The scripts build on the processing and validated results defined under "global".

# For further information on underlying data sources and methods (including GADM, which is considered an external
# dataset), please refer to this README and the associated Scientific Data Descriptor publication.

import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, Point
from haversine import haversine

from src.config.data_catalog import domains_extent_file, domains_file, domains_file_subset, get_country_gadm
from src.config.param import crs_reference_global, cpd_region_list, countries_codes


def main(input_file = domains_extent_file, cpd_region = cpd_region_list, named_region=cpd_region_list,
         country_codes=countries_codes, outputfile=domains_file):
    if os.path.exists(outputfile):
        print("Domain assignment already complete")
        return
    country_region_map = match_domain_country(input_file, country_codes, named_region, cpd_region)
    country_region_map.to_csv(outputfile, sep="\t", index=False, header=True)
    domains_selection(data_file=domains_file, domains_subset=domains_file_subset)


# assignment
def match_domain_country(input_file, country_list, region_list,cpd_list, crs=crs_reference_global):
    region_polygons = get_polygon(input_file)
    region_names, region_centroids = create_region_centroids(region_list, cpd_list)
    regions_gdf_list = [
        gpd.GeoDataFrame({"region": [region_name]}, geometry=[poly], crs=crs)
        for region_name, poly in region_polygons.items()
    ]
    data = []
    for country_sel in country_list:
        shape_country = get_country_gadm(country_sel, admin_level="ADM_0")
        country_geom = shape_country.geometry.union_all()
        centroid = country_geom.centroid
        country_assigned = False
        for index, polygon in enumerate(shape_country.geometry):
            polygon_gdf = gpd.GeoDataFrame(geometry=[polygon], crs=crs)
            for reg_idx, region_gdf in enumerate(regions_gdf_list):
                assigned_region = region_names[reg_idx]
                region_coords = region_centroids[reg_idx]
                contains = polygon_gdf.geometry.iloc[0].within(region_gdf.geometry.iloc[0])
                if contains:
                    min_distance = dist(centroid.y, centroid.x, region_coords[1],  region_coords[0])
                    data.append({"country": country_sel, "region": assigned_region, "distance": min_distance,  "overlap": "true"})
                    country_assigned = True
                else:
                    intersects = region_gdf.geometry.intersects(polygon_gdf.geometry.iloc[0]).iloc[0]
                    if intersects:
                         min_distance = dist(centroid.y,centroid.x,  region_coords[1],  region_coords[0])
                         data.append({"country": country_sel, "region": assigned_region, "distance":min_distance,  "overlap": "false"})
                         country_assigned = True
        if not country_assigned:
            data.append(
                {"country": country_sel, "region": None, "distance": None, "overlap": "false"})
    df = pd.DataFrame(data)
    return df


# create region polygons & centroids
def extract_centroid(centre):
    centroid = centre["CPD"]
    lon = centroid[0]
    lat = centroid[1]
    if lon > 180:
        lon -= 360
    elif lon < -180:
        lon += 360
    return lon, lat


def create_region_centroids(region_list, cpd_list):
    region_names = []
    region_centroids=[]
    for region, corners in region_list.items():
        centroid_lon, centroid_lat = extract_centroid(cpd_list[region])
        region_names.append(region)
        region_centroids.append([centroid_lon, centroid_lat])
    return region_names, region_centroids


def get_polygon(input_file):
    corner_keys = ["TLC", "TRC", "BRC", "BLC"]
    polygons = {}
    current_region = None
    corners = {}
    with open(input_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("===") and "REGION" in line:
                current_region = line.split(":")[1].strip()
                polygons[current_region] = None
                corners = {}
                continue
            for key in corner_keys:
                if line.startswith(f"{key}:"):
                    corners[key] = tuple(map(float, line.split(":")[1].strip("() ").split(",")))
            if all(k in corners for k in corner_keys):
                poly_coords = [corners[k] for k in ["TLC", "TRC", "BRC", "BLC"]] + [corners["TLC"]]
                polygons[current_region] = Polygon(poly_coords)
                corners = {}
    return polygons


# domains
def domains_selection(data_file = domains_file, domains_subset=domains_file_subset):
    domain_df_raw = pd.read_csv(data_file, sep="\t")
    domain_df = select_best_region(domain_df_raw)
    if not os.path.exists(domains_subset):
        domain_df.to_csv(domains_subset, sep="\t", index=False, header=True)


def select_best_region(df):
    results = []
    for country, group in df.groupby("country"):
        if country == "SOM":
            mena = group[group["region"] == "MENA"]
            if not mena.empty:
                results.append(mena.iloc[0])
            continue
        group_valid = group.dropna(subset=["distance"])
        if group_valid.empty:
            continue  # nothing usable for this country

        overlapping = group_valid[group_valid["overlap"] == True]
        if len(overlapping) == 1:
            best = overlapping.iloc[0]
        elif len(overlapping) > 1:
            best = overlapping.loc[overlapping["distance"].idxmin()]
        else:
            best = group_valid.loc[group["distance"].idxmin()]
        results.append(best)
    return pd.DataFrame(results)


# helper
def dist(lat1, lon1, lat2, lon2):
    p1 = (lat1, lon1)
    p2 = (lat2, lon2)
    dist =  haversine(p1, p2)
    return dist


if __name__ == "__main__":
    main()

