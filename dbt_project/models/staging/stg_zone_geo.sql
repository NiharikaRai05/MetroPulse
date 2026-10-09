{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model: stg_zone_geo
    - Direct view over TLC Taxi Zone Shapefile
    - Standardized snake_case naming
    - Strictly typed casts
    - Preserves spatial geometry & bounding boxes
    - NO rows removed
*/

SELECT
    cast(location_id as integer) AS location_id,
    cast(borough as varchar) AS borough,
    cast(zone as varchar) AS zone_name,
    cast(shape_leng as double) AS shape_length,
    cast(shape_area as double) AS shape_area,
    geom AS geometry

FROM ST_Read('../data/raw/zones/shapefile/taxi_zones.shp')
