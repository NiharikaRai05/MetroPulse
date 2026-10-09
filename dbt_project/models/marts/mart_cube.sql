{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_cube
    - Grain: date_day x hour_of_day x pickup_borough x dropoff_borough x payment_type x rate_code x airport_flag
    - Multimodal multidimensional aggregation cube
    - Joined with hourly weather metrics (temperature, precipitation, rain) by hour_timestamp
    - STORES SUMS AND COUNTS ONLY:
      No pre-baked division ratios (e.g. avg_fare, tip_pct, avg_distance) are stored,
      guaranteeing that any downstream slice-and-dice in Streamlit or DuckDB
      recomputes weighted averages and proportions mathematically without Simpson's Paradox.
*/

WITH trips AS (
    SELECT * FROM {{ ref('fct_trips') }}
),

zones AS (
    SELECT location_id, borough, is_airport_zone FROM {{ ref('dim_zone') }}
),

weather AS (
    SELECT * FROM {{ ref('int_weather_hourly') }}
),

cube_base AS (
    SELECT
        t.pickup_date AS date_day,
        t.pickup_hour_of_day AS hour_of_day,
        COALESCE(pz.borough, 'Unknown') AS pickup_borough,
        COALESCE(dz.borough, 'Unknown') AS dropoff_borough,
        t.payment_type_id,
        t.rate_code_id,
        CASE WHEN pz.is_airport_zone OR dz.is_airport_zone THEN TRUE ELSE FALSE END AS is_airport_trip,

        -- Additive aggregations
        COUNT(*) AS trip_count,
        SUM(t.passenger_count) AS total_passenger_count,
        SUM(t.total_amount) AS total_passenger_spending,
        SUM(t.fare_amount) AS total_fare_amount,
        SUM(t.tip_amount) AS total_tip_amount,
        SUM(t.tolls_amount) AS total_tolls_amount,
        SUM(t.congestion_surcharge) AS total_congestion_surcharge,
        SUM(t.airport_fee) AS total_airport_fee,
        SUM(t.trip_distance_miles) AS total_distance_miles,
        SUM(t.duration_minutes) AS total_duration_minutes,
        SUM(t.duration_seconds) AS total_duration_seconds
    FROM trips t
    LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
    LEFT JOIN zones dz ON t.dropoff_location_id = dz.location_id
    GROUP BY
        t.pickup_date,
        t.pickup_hour_of_day,
        pz.borough,
        dz.borough,
        t.payment_type_id,
        t.rate_code_id,
        CASE WHEN pz.is_airport_zone OR dz.is_airport_zone THEN TRUE ELSE FALSE END
)

SELECT
    c.date_day,
    c.hour_of_day,
    CAST(c.date_day AS TIMESTAMP) + (c.hour_of_day * INTERVAL 1 HOUR) AS hour_timestamp,
    c.pickup_borough,
    c.dropoff_borough,
    c.payment_type_id,
    c.rate_code_id,
    c.is_airport_trip,

    -- Pure additive metrics
    c.trip_count,
    c.total_passenger_count,
    c.total_passenger_spending,
    c.total_fare_amount,
    c.total_tip_amount,
    c.total_tolls_amount,
    c.total_congestion_surcharge,
    c.total_airport_fee,
    c.total_distance_miles,
    c.total_duration_minutes,
    c.total_duration_seconds,

    -- Hourly weather context joined cleanly
    w.avg_temperature_fahrenheit AS weather_temperature_f,
    COALESCE(w.max_precipitation_mm, 0.0) AS weather_precipitation_mm,
    COALESCE(w.max_rain_mm, 0.0) AS weather_rain_mm,
    COALESCE(w.is_raining, 0) AS weather_is_raining,
    COALESCE(w.is_heavy_rain, 0) AS weather_is_heavy_rain

FROM cube_base c
LEFT JOIN weather w
    ON (CAST(c.date_day AS TIMESTAMP) + (c.hour_of_day * INTERVAL 1 HOUR)) = w.observation_hour
