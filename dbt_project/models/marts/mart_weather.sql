{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_weather
    - Grain: 1 row per hour (observation_hour)
    - Joins weather dimensions with hourly taxi mobility demand and subway ridership
    - Stores strictly additive sums and counts (facilitates downstream correlation & elasticity models)
*/

WITH weather_dim AS (
    SELECT * FROM {{ ref('dim_weather') }}
),

demand_hourly AS (
    SELECT * FROM {{ ref('int_hourly_demand') }}
)

SELECT
    w.observation_hour,
    w.observation_date,
    w.temperature_celsius,
    w.temperature_fahrenheit,
    w.precipitation_mm,
    w.rain_mm,
    w.snowfall_cm,
    w.wind_speed_kmh,
    w.cloud_cover_pct,
    w.weather_code,
    w.weather_condition_name,
    w.precipitation_intensity_band,
    w.has_precipitation,
    w.has_heavy_precipitation,
    w.is_extreme_heat,

    -- Additive mobility demand metrics
    COALESCE(d.taxi_trip_count, 0) AS taxi_trip_count,
    COALESCE(d.taxi_total_passengers, 0) AS taxi_total_passengers,
    COALESCE(d.taxi_total_passenger_spending, 0.0) AS taxi_total_passenger_spending,
    COALESCE(d.taxi_total_base_fares, 0.0) AS taxi_total_base_fares,
    COALESCE(d.taxi_total_tips, 0.0) AS taxi_total_tips,
    COALESCE(d.taxi_total_distance_miles, 0.0) AS taxi_total_distance_miles,
    COALESCE(d.total_subway_ridership, 0) AS total_subway_ridership,
    COALESCE(d.subway_ridership_manhattan, 0) AS subway_ridership_manhattan,
    COALESCE(d.subway_ridership_brooklyn, 0) AS subway_ridership_brooklyn,
    COALESCE(d.subway_ridership_queens, 0) AS subway_ridership_queens,
    COALESCE(d.subway_ridership_bronx, 0) AS subway_ridership_bronx,

    -- Lag columns for weather impact analysis
    d.taxi_trip_count_lag1,
    d.taxi_trip_count_lag2,
    d.total_subway_ridership_lag1,
    d.precipitation_mm_lag1

FROM weather_dim w
LEFT JOIN demand_hourly d
    ON w.observation_hour = d.hour_timestamp
