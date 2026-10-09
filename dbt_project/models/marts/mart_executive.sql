{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_executive
    - High-level executive KPI summary and market mobility pulse
    - Strictly additive metrics (sums and counts)
    - Distinguishes passenger expenditure (market activity) from company revenue
*/

WITH trips AS (
    SELECT * FROM {{ ref('fct_trips') }}
),

subway AS (
    SELECT * FROM {{ ref('int_subway_hourly') }}
),

weather AS (
    SELECT * FROM {{ ref('int_weather_hourly') }}
),

trips_summary AS (
    SELECT
        COUNT(*) AS total_clean_trips,
        SUM(passenger_count) AS total_taxi_passengers,
        SUM(total_amount) AS total_passenger_spending,
        SUM(fare_amount) AS total_base_fare_amount,
        SUM(tip_amount) AS total_tip_amount,
        SUM(tolls_amount) AS total_tolls_amount,
        SUM(congestion_surcharge) AS total_congestion_surcharge,
        SUM(airport_fee) AS total_airport_fee,
        SUM(trip_distance_miles) AS total_distance_miles,
        SUM(duration_minutes) AS total_duration_minutes,
        COUNT(DISTINCT pickup_date) AS active_service_days
    FROM trips
),

subway_summary AS (
    SELECT
        SUM(total_subway_ridership) AS total_subway_entries,
        SUM(subway_ridership_manhattan) AS subway_entries_manhattan,
        SUM(subway_ridership_brooklyn) AS subway_entries_brooklyn,
        SUM(subway_ridership_queens) AS subway_entries_queens,
        SUM(subway_ridership_bronx) AS subway_entries_bronx
    FROM subway
),

weather_summary AS (
    SELECT
        COUNT(*) AS total_hours_observed,
        SUM(CASE WHEN is_raining = 1 THEN 1 ELSE 0 END) AS total_rain_hours,
        SUM(max_precipitation_mm) AS total_precipitation_mm,
        ROUND(AVG(avg_temperature_fahrenheit), 1) AS period_mean_temperature_f
    FROM weather
)

SELECT
    '2024-04-01 to 2024-06-30' AS analysis_period,
    t.active_service_days,
    t.total_clean_trips,
    t.total_taxi_passengers,
    t.total_passenger_spending,
    t.total_base_fare_amount,
    t.total_tip_amount,
    t.total_tolls_amount,
    t.total_congestion_surcharge,
    t.total_airport_fee,
    t.total_distance_miles,
    t.total_duration_minutes,
    s.total_subway_entries,
    s.subway_entries_manhattan,
    s.subway_entries_brooklyn,
    s.subway_entries_queens,
    s.subway_entries_bronx,
    w.total_hours_observed,
    w.total_rain_hours,
    w.total_precipitation_mm,
    w.period_mean_temperature_f
FROM trips_summary t
CROSS JOIN subway_summary s
CROSS JOIN weather_summary w
