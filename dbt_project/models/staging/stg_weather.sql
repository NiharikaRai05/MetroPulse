{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model: stg_weather
    - Standardized snake_case naming
    - Strictly typed casts
    - Preserves all hourly weather variables for Q2 2024
    - NO rows removed
*/

SELECT
    cast("time" as timestamp) AS observation_timestamp,
    cast(date_trunc('hour', "time") as timestamp) AS observation_hour,
    cast(date_trunc('day', "time") as date) AS observation_date,
    cast(temperature_2m as double) AS temperature_celsius,
    cast(precipitation as double) AS precipitation_mm,
    cast(rain as double) AS rain_mm,
    cast(snowfall as double) AS snowfall_cm,
    cast(wind_speed_10m as double) AS wind_speed_kmh,
    cast(cloud_cover as double) AS cloud_cover_pct,
    cast(weather_code as integer) AS weather_code,
    cast(_source_period as varchar) AS source_period,
    cast(_loaded_at as timestamp) AS loaded_at

FROM {{ source('raw', 'weather_hourly') }}
