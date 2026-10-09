{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Dimension Model: dim_weather
    - Grain: 1 row per hour in Q2 2024 (observation_hour)
    - Enriches raw Open-Meteo observations with descriptive weather condition tiers,
      precipitation intensity bands, and weather impact categories.
*/

WITH weather_base AS (
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
        weather_code,
        ROW_NUMBER() OVER (PARTITION BY observation_hour ORDER BY loaded_at DESC) AS rn
    FROM {{ ref('stg_weather') }}
)

SELECT
    observation_hour,
    observation_date,
    round(temperature_celsius, 2) AS temperature_celsius,
    round(temperature_fahrenheit, 2) AS temperature_fahrenheit,
    round(precipitation_mm, 2) AS precipitation_mm,
    round(rain_mm, 2) AS rain_mm,
    round(snowfall_cm, 2) AS snowfall_cm,
    round(wind_speed_kmh, 2) AS wind_speed_kmh,
    round(cloud_cover_pct, 1) AS cloud_cover_pct,
    weather_code,

    -- WMO Weather Code Interpretation
    CASE
        WHEN weather_code = 0 THEN 'Clear sky'
        WHEN weather_code IN (1, 2, 3) THEN 'Mainly clear / Partly cloudy'
        WHEN weather_code IN (45, 48) THEN 'Fog'
        WHEN weather_code IN (51, 53, 55) THEN 'Drizzle'
        WHEN weather_code IN (61, 63, 65) THEN 'Rain'
        WHEN weather_code IN (71, 73, 75) THEN 'Snow'
        WHEN weather_code IN (80, 81, 82) THEN 'Rain showers'
        WHEN weather_code IN (95, 96, 99) THEN 'Thunderstorm'
        ELSE 'Other / Unclassified'
    END AS weather_condition_name,

    -- Precipitation Intensity Classification
    CASE
        WHEN precipitation_mm = 0.0 THEN 'No Precipitation'
        WHEN precipitation_mm < 2.5 THEN 'Light Rain'
        WHEN precipitation_mm < 7.6 THEN 'Moderate Rain'
        ELSE 'Heavy Rain'
    END AS precipitation_intensity_band,

    -- Binary flags for mobility impact correlation
    CASE WHEN precipitation_mm > 0.0 THEN TRUE ELSE FALSE END AS has_precipitation,
    CASE WHEN precipitation_mm >= 2.5 THEN TRUE ELSE FALSE END AS has_heavy_precipitation,
    CASE WHEN temperature_fahrenheit >= 85.0 THEN TRUE ELSE FALSE END AS is_extreme_heat

FROM weather_base
WHERE rn = 1
