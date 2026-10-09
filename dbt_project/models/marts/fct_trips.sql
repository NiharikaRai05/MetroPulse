{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Fact Model: fct_trips
    - Grain: 1 row per valid, cleaned yellow taxi trip
    - Excludes corrupted records via int_trips_clean
    - Preserves exact trip_id surrogate key
    - Links to dim_zone (pickup & dropoff), dim_date, dim_hour, dim_payment, dim_rate, and dim_weather
*/

WITH clean_trips AS (
    SELECT * FROM {{ ref('int_trips_clean') }}
)

SELECT
    -- Surrogate Primary Key
    t.trip_id,

    -- Foreign Keys & Degenerate Dimensions
    t.vendor_id,
    t.rate_code_id,
    t.payment_type AS payment_type_id,
    t.store_and_fwd_flag,
    
    -- Spatial Keys
    t.pickup_location_id,
    t.dropoff_location_id,

    -- Temporal Keys
    t.pickup_datetime,
    t.dropoff_datetime,
    CAST(strftime(t.pickup_datetime, '%Y%m%d') AS INTEGER) AS pickup_date_key,
    CAST(date_trunc('day', t.pickup_datetime) AS DATE) AS pickup_date,
    EXTRACT(HOUR FROM t.pickup_datetime) AS pickup_hour_of_day,
    date_trunc('hour', t.pickup_datetime) AS pickup_weather_hour,

    CAST(date_trunc('day', t.dropoff_datetime) AS DATE) AS dropoff_date,
    EXTRACT(HOUR FROM t.dropoff_datetime) AS dropoff_hour_of_day,

    -- Operational & Passenger Metrics
    t.passenger_count,
    t.trip_distance_miles,
    t.duration_seconds,
    t.duration_minutes,
    t.speed_mph,

    -- Market Activity & Financial Metrics (Market activity, NOT company revenue)
    t.fare_amount,
    t.extra_amount,
    t.mta_tax_amount,
    t.tip_amount,
    t.tolls_amount,
    t.improvement_surcharge,
    t.congestion_surcharge,
    t.airport_fee,
    t.total_amount,
    t.fare_per_mile,

    -- Derived Financial Metrics
    CASE 
        WHEN t.fare_amount > 0 AND t.payment_type = 1 
        THEN (t.tip_amount / t.fare_amount) * 100.0 
        ELSE 0.0 
    END AS tip_percentage,

    -- Governance & Audit Flags
    t.is_unknown_zone,
    t.is_passenger_count_imputed,
    t.is_cash_tip_anomaly,
    t.source_period,
    t.loaded_at

FROM clean_trips t
