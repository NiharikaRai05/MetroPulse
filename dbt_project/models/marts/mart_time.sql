{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_time
    - Grain: 1 row per date x hour (2,184 hours in Q2 2024)
    - Captures temporal demand patterns, rush hour trends, and day-of-week rhythms
    - Stores strictly additive sums and counts
*/

WITH date_dim AS (
    SELECT * FROM {{ ref('dim_date') }}
),

hour_dim AS (
    SELECT * FROM {{ ref('dim_hour') }}
),

time_spine AS (
    SELECT
        d.date_day,
        d.date_key,
        d.day_of_week,
        d.day_name,
        d.month_actual,
        d.month_name,
        d.is_weekend,
        d.is_weekday,
        d.is_holiday,
        d.holiday_name,
        h.hour_of_day,
        h.hour_label_24h,
        h.hour_label_12h,
        h.time_of_day_bucket,
        h.is_rush_hour_window,
        h.is_overnight_window,
        CAST(d.date_day AS TIMESTAMP) + (h.hour_of_day * INTERVAL 1 HOUR) AS hour_timestamp
    FROM date_dim d
    CROSS JOIN hour_dim h
),

trip_aggregates AS (
    SELECT
        pickup_date,
        pickup_hour_of_day,
        COUNT(*) AS trip_count,
        SUM(passenger_count) AS total_passengers,
        SUM(total_amount) AS total_passenger_spending,
        SUM(fare_amount) AS total_fare_amount,
        SUM(tip_amount) AS total_tip_amount,
        SUM(tolls_amount) AS total_tolls_amount,
        SUM(congestion_surcharge) AS total_congestion_surcharge,
        SUM(airport_fee) AS total_airport_fee,
        SUM(trip_distance_miles) AS total_distance_miles,
        SUM(duration_minutes) AS total_duration_minutes,
        COUNT(CASE WHEN payment_type_id = 1 THEN 1 END) AS credit_card_trip_count,
        COUNT(CASE WHEN payment_type_id = 2 THEN 1 END) AS cash_trip_count
    FROM {{ ref('fct_trips') }}
    GROUP BY pickup_date, pickup_hour_of_day
)

SELECT
    s.hour_timestamp,
    s.date_day,
    s.date_key,
    s.day_of_week,
    s.day_name,
    s.month_actual,
    s.month_name,
    s.is_weekend,
    s.is_weekday,
    s.is_holiday,
    s.holiday_name,
    s.hour_of_day,
    s.hour_label_24h,
    s.hour_label_12h,
    s.time_of_day_bucket,
    s.is_rush_hour_window,
    s.is_overnight_window,

    -- Additive metrics
    COALESCE(t.trip_count, 0) AS trip_count,
    COALESCE(t.total_passengers, 0) AS total_passengers,
    COALESCE(t.total_passenger_spending, 0.0) AS total_passenger_spending,
    COALESCE(t.total_fare_amount, 0.0) AS total_fare_amount,
    COALESCE(t.total_tip_amount, 0.0) AS total_tip_amount,
    COALESCE(t.total_tolls_amount, 0.0) AS total_tolls_amount,
    COALESCE(t.total_congestion_surcharge, 0.0) AS total_congestion_surcharge,
    COALESCE(t.total_airport_fee, 0.0) AS total_airport_fee,
    COALESCE(t.total_distance_miles, 0.0) AS total_distance_miles,
    COALESCE(t.total_duration_minutes, 0.0) AS total_duration_minutes,
    COALESCE(t.credit_card_trip_count, 0) AS credit_card_trip_count,
    COALESCE(t.cash_trip_count, 0) AS cash_trip_count

FROM time_spine s
LEFT JOIN trip_aggregates t
    ON s.date_day = t.pickup_date AND s.hour_of_day = t.pickup_hour_of_day
