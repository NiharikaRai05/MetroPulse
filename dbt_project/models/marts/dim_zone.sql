{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Dimension Model: dim_zone
    - Grain: 1 row per unique location_id (1..265)
    - Joins TLC Zone Lookup with Taxi Zone Shapefiles
    - Deduplication: Handles multi-part / duplicate polygon geometries (e.g. zones 56, 57, 103, 104, 105)
      by aggregating geometries via ST_Union_Agg or taking max area polygon with row_number
*/

WITH lookup_zones AS (
    SELECT
        location_id,
        borough,
        zone_name,
        service_zone
    FROM {{ ref('stg_zones') }}
),

geo_zones AS (
    SELECT
        location_id,
        borough,
        zone_name,
        shape_length,
        shape_area,
        geometry,
        -- Window function to pick primary polygon if duplicate location_id occurs in shapefile
        ROW_NUMBER() OVER (
            PARTITION BY location_id 
            ORDER BY shape_area DESC, shape_length DESC
        ) AS geo_rank
    FROM {{ ref('stg_zone_geo') }}
),

deduped_geo AS (
    SELECT
        location_id,
        shape_length,
        shape_area,
        geometry
    FROM geo_zones
    WHERE geo_rank = 1
)

SELECT
    l.location_id,
    coalesce(l.borough, 'Unknown') AS borough,
    coalesce(l.zone_name, 'Unknown') AS zone_name,
    coalesce(l.service_zone, 'Unknown') AS service_zone,
    
    -- Spatial attributes
    g.shape_length,
    g.shape_area,
    g.geometry,
    
    -- Derived zone classifications
    CASE 
        WHEN l.borough = 'Manhattan' AND l.location_id NOT IN (103, 104, 105, 127, 128, 243, 244) THEN TRUE
        ELSE FALSE
    END AS is_congestion_zone,
    
    CASE 
        WHEN l.service_zone IN ('Airports', 'EWR') OR l.location_id IN (1, 132, 138) THEN TRUE
        ELSE FALSE
    END AS is_airport_zone

FROM lookup_zones l
LEFT JOIN deduped_geo g
    ON l.location_id = g.location_id
