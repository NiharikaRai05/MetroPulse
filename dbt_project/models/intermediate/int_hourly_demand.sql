{{
    config(
        materialized='table',
        schema='intermediate'
    )
}}

/*
    Intermediate Model: int_hourly_demand
    - Grain: Exactly 1 row per hour (hour_timestamp) across Q2 2024 in America/New_York
    - Joins:
        1. Hourly Taxi aggregates (int_trips_clean rolled up to hour)
        2. Hourly Weather aggregates (int_weather_hourly)
        3. Hourly Subway ridership aggregates (int_subway_hourly)
    - Adds time-series lag features (Lag 0, Lag 1, Lag 2 hours) for:
        * Taxi trips & passenger demand
        * Subway ridership
        * Precipitation & temperature
    
    ARCHITECTURAL DEFENSE NOTE:
    Aggregating trips and station-level subway taps to 1 row per hour BEFORE joining
    guarantees a strict 1-to-1 join on timestamp. This completely eliminates fan-out
    (Cartesian expansion) that would otherwise inflate trip counts, ridership totals,
    and revenue sums if joined at the raw trip / station grain.
*/

WITH hourly_spine AS (
    SELECT 
        CAST(h AS TIMESTAMP) AS hour_timestamp
    FROM generate_series(
        TIMESTAMP '2024-04-01 00:00:00',
        TIMESTAMP '2024-06-30 23:00:00',
        INTERVAL 1 HOUR
    ) AS t(h)
),

taxi_hourly AS (
    SELECT
        date_trunc('hour', pickup_datetime) AS taxi_hour,
        count(*) AS taxi_trip_count,
        sum(passenger_count) AS taxi_total_passengers,
        sum(total_amount) AS taxi_total_passenger_spending,
        sum(fare_amount) AS taxi_total_base_fares,
        sum(tip_amount) AS taxi_total_tips,
        sum(tolls_amount) AS taxi_total_tolls,
        sum(trip_distance_miles) AS taxi_total_distance_miles,
        round(avg(trip_distance_miles), 2) AS taxi_avg_trip_distance,
        round(avg(duration_minutes), 2) AS taxi_avg_duration_minutes,
        round(avg(speed_mph), 2) AS taxi_avg_speed_mph,
        round(avg(fare_per_mile), 2) AS taxi_avg_fare_per_mile,
        -- Key geographic breakdown
        count(CASE WHEN is_unknown_zone THEN 1 END) AS taxi_trips_unknown_zone
    FROM {{ ref('int_trips_clean') }}
    GROUP BY date_trunc('hour', pickup_datetime)
),

weather_hourly AS (
    SELECT * FROM {{ ref('int_weather_hourly') }}
),

subway_hourly AS (
    SELECT * FROM {{ ref('int_subway_hourly') }}
),

joined_demand AS (
    SELECT
        s.hour_timestamp,
        CAST(date_trunc('day', s.hour_timestamp) AS DATE) AS date_day,
        EXTRACT(HOUR FROM s.hour_timestamp) AS hour_of_day,
        EXTRACT(DOW FROM s.hour_timestamp) AS day_of_week,
        CASE WHEN EXTRACT(DOW FROM s.hour_timestamp) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,

        -- Taxi Metrics (Lag 0)
        coalesce(t.taxi_trip_count, 0) AS taxi_trip_count,
        coalesce(t.taxi_total_passengers, 0) AS taxi_total_passengers,
        coalesce(t.taxi_total_passenger_spending, 0.0) AS taxi_total_passenger_spending,
        coalesce(t.taxi_total_base_fares, 0.0) AS taxi_total_base_fares,
        coalesce(t.taxi_total_tips, 0.0) AS taxi_total_tips,
        coalesce(t.taxi_total_tolls, 0.0) AS taxi_total_tolls,
        coalesce(t.taxi_total_distance_miles, 0.0) AS taxi_total_distance_miles,
        coalesce(t.taxi_avg_trip_distance, 0.0) AS taxi_avg_trip_distance,
        coalesce(t.taxi_avg_duration_minutes, 0.0) AS taxi_avg_duration_minutes,
        coalesce(t.taxi_avg_speed_mph, 0.0) AS taxi_avg_speed_mph,
        coalesce(t.taxi_avg_fare_per_mile, 0.0) AS taxi_avg_fare_per_mile,

        -- Weather Metrics (Lag 0)
        w.avg_temperature_celsius,
        w.avg_temperature_fahrenheit,
        coalesce(w.max_precipitation_mm, 0.0) AS precipitation_mm,
        coalesce(w.max_rain_mm, 0.0) AS rain_mm,
        coalesce(w.is_raining, 0) AS is_raining,
        coalesce(w.is_heavy_rain, 0) AS is_heavy_rain,
        w.avg_wind_speed_kmh,
        w.prevailing_weather_code,

        -- Subway Metrics (Lag 0)
        coalesce(sub.total_subway_ridership, 0) AS total_subway_ridership,
        coalesce(sub.subway_ridership_manhattan, 0) AS subway_ridership_manhattan,
        coalesce(sub.subway_ridership_brooklyn, 0) AS subway_ridership_brooklyn,
        coalesce(sub.subway_ridership_queens, 0) AS subway_ridership_queens,
        coalesce(sub.subway_ridership_bronx, 0) AS subway_ridership_bronx

    FROM hourly_spine s
    LEFT JOIN taxi_hourly t
        ON s.hour_timestamp = t.taxi_hour
    LEFT JOIN weather_hourly w
        ON s.hour_timestamp = w.observation_hour
    LEFT JOIN subway_hourly sub
        ON s.hour_timestamp = sub.transit_hour
)

SELECT
    *,

    -- =========================================================================
    -- Time-Series Lag Features (Lag 1 Hour, Lag 2 Hours)
    -- =========================================================================
    
    -- Taxi Demand Lags
    LAG(taxi_trip_count, 1) OVER (ORDER BY hour_timestamp ASC) AS taxi_trip_count_lag1,
    LAG(taxi_trip_count, 2) OVER (ORDER BY hour_timestamp ASC) AS taxi_trip_count_lag2,

    -- Subway Ridership Lags
    LAG(total_subway_ridership, 1) OVER (ORDER BY hour_timestamp ASC) AS total_subway_ridership_lag1,
    LAG(total_subway_ridership, 2) OVER (ORDER BY hour_timestamp ASC) AS total_subway_ridership_lag2,

    -- Weather Lags (Rain & Temp shifts)
    LAG(precipitation_mm, 1) OVER (ORDER BY hour_timestamp ASC) AS precipitation_mm_lag1,
    LAG(precipitation_mm, 2) OVER (ORDER BY hour_timestamp ASC) AS precipitation_mm_lag2,
    LAG(avg_temperature_fahrenheit, 1) OVER (ORDER BY hour_timestamp ASC) AS avg_temperature_fahrenheit_lag1,
    LAG(avg_temperature_fahrenheit, 2) OVER (ORDER BY hour_timestamp ASC) AS avg_temperature_fahrenheit_lag2,

    -- Dynamic Demand Elasticity Diagnostics
    CASE 
        WHEN LAG(taxi_trip_count, 1) OVER (ORDER BY hour_timestamp ASC) > 0
        THEN round(((taxi_trip_count - LAG(taxi_trip_count, 1) OVER (ORDER BY hour_timestamp ASC)) * 100.0) / LAG(taxi_trip_count, 1) OVER (ORDER BY hour_timestamp ASC), 2)
        ELSE NULL
    END AS taxi_demand_pct_change_1h,

    CASE 
        WHEN LAG(total_subway_ridership, 1) OVER (ORDER BY hour_timestamp ASC) > 0
        THEN round(((total_subway_ridership - LAG(total_subway_ridership, 1) OVER (ORDER BY hour_timestamp ASC)) * 100.0) / LAG(total_subway_ridership, 1) OVER (ORDER BY hour_timestamp ASC), 2)
        ELSE NULL
    END AS subway_ridership_pct_change_1h

FROM joined_demand
