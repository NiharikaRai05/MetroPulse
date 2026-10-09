{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_transit
    - Grain: 1 row per station complex x transit date x hour
    - Details station-level subway tap activity across NYC boroughs
    - Stores strictly additive counts
*/

WITH subway_staging AS (
    SELECT
        transit_hour,
        transit_date,
        station_complex_id,
        station_complex_name,
        borough,
        latitude,
        longitude,
        ridership
    FROM {{ ref('stg_subway') }}
)

SELECT
    transit_hour,
    transit_date,
    EXTRACT(HOUR FROM transit_hour) AS hour_of_day,
    station_complex_id,
    station_complex_name,
    borough,
    latitude,
    longitude,
    COALESCE(ridership, 0) AS subway_ridership
FROM subway_staging
