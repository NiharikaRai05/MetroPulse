{{
    config(
        materialized='view',
        schema='intermediate'
    )
}}

/*
    Intermediate Model: int_weather_hourly
    - Grain: Exactly 1 row per hour (observation_hour) in America/New_York
    - Standardizes continuous temperature, precipitation, and rain features
    - Aggregates multiple sensor records if present to guarantee primary key uniqueness
*/

WITH weather_raw AS (
    SELECT
        observation_hour,
        observation_date,
        temperature_celsius,
        (temperature_celsius * 9.0 / 5.0) + 32.0 AS temperature_fahrenheit,
        precipitation_mm,
        rain_mm,
        snowfall_cm,
        wind_speed_kmh,
        cloud_cover_pct,
        weather_code
    FROM {{ ref('stg_weather') }}
)

SELECT
    observation_hour,
    CAST(date_trunc('day', observation_hour) AS DATE) AS observation_date,
    EXTRACT(HOUR FROM observation_hour) AS hour_of_day,
    
    -- Aggregated metrics (deterministic 1 row per hour)
    round(avg(temperature_celsius), 2) AS avg_temperature_celsius,
    round(avg(temperature_fahrenheit), 2) AS avg_temperature_fahrenheit,
    round(max(precipitation_mm), 2) AS max_precipitation_mm,
    round(max(rain_mm), 2) AS max_rain_mm,
    round(max(snowfall_cm), 2) AS max_snowfall_cm,
    round(avg(wind_speed_kmh), 2) AS avg_wind_speed_kmh,
    round(avg(cloud_cover_pct), 1) AS avg_cloud_cover_pct,
    max(weather_code) AS prevailing_weather_code,

    -- Precipitation classification
    CASE WHEN max(precipitation_mm) > 0.0 THEN 1 ELSE 0 END AS is_raining,
    CASE WHEN max(precipitation_mm) >= 2.5 THEN 1 ELSE 0 END AS is_heavy_rain

FROM weather_raw
GROUP BY observation_hour
