{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_zone
    - Grain: 1 row per official TLC Taxi Zone (LocationID 1..265)
    - Computes demand concentration, inbound/outbound trip volumes, and spending
    - EXPLICITLY DEFINED UNDERSERVED INDICATOR:
      A zone is flagged as 'is_underserved' if:
        1. It is a residential/commercial borough zone (Borough != 'EWR' and Borough != 'Unknown')
        2. Its total pickup trip volume falls into the bottom 25th percentile (< 1,000 pickups over Q2 2024)
           OR pickup-to-dropoff ratio < 0.20 (passengers arrive by taxi but cannot hail one to depart).
    - Preserves strictly additive sums and counts.
*/

WITH all_zones AS (
    SELECT * FROM {{ ref('dim_zone') }}
),

pickup_stats AS (
    SELECT
        pickup_location_id AS location_id,
        COUNT(*) AS pickup_trip_count,
        SUM(passenger_count) AS pickup_passenger_count,
        SUM(total_amount) AS pickup_passenger_spending,
        SUM(fare_amount) AS pickup_fare_amount,
        SUM(tip_amount) AS pickup_tip_amount,
        SUM(trip_distance_miles) AS pickup_distance_miles,
        SUM(duration_minutes) AS pickup_duration_minutes
    FROM {{ ref('fct_trips') }}
    GROUP BY pickup_location_id
),

dropoff_stats AS (
    SELECT
        dropoff_location_id AS location_id,
        COUNT(*) AS dropoff_trip_count,
        SUM(passenger_count) AS dropoff_passenger_count,
        SUM(total_amount) AS dropoff_passenger_spending,
        SUM(trip_distance_miles) AS dropoff_distance_miles
    FROM {{ ref('fct_trips') }}
    GROUP BY dropoff_location_id
)

SELECT
    z.location_id,
    z.borough,
    z.zone_name,
    z.service_zone,
    z.is_congestion_zone,
    z.is_airport_zone,
    z.shape_area,
    z.shape_length,

    -- Outbound / Pickup Aggregates
    COALESCE(p.pickup_trip_count, 0) AS pickup_trip_count,
    COALESCE(p.pickup_passenger_count, 0) AS pickup_passenger_count,
    COALESCE(p.pickup_passenger_spending, 0.0) AS pickup_passenger_spending,
    COALESCE(p.pickup_fare_amount, 0.0) AS pickup_fare_amount,
    COALESCE(p.pickup_tip_amount, 0.0) AS pickup_tip_amount,
    COALESCE(p.pickup_distance_miles, 0.0) AS pickup_distance_miles,
    COALESCE(p.pickup_duration_minutes, 0.0) AS pickup_duration_minutes,

    -- Inbound / Dropoff Aggregates
    COALESCE(d.dropoff_trip_count, 0) AS dropoff_trip_count,
    COALESCE(d.dropoff_passenger_count, 0) AS dropoff_passenger_count,
    COALESCE(d.dropoff_passenger_spending, 0.0) AS dropoff_passenger_spending,
    COALESCE(d.dropoff_distance_miles, 0.0) AS dropoff_distance_miles,

    -- Total Zone Mobility Activity
    (COALESCE(p.pickup_trip_count, 0) + COALESCE(d.dropoff_trip_count, 0)) AS total_zone_trip_touchpoints,

    -- Explicitly Defined Underserved Classification
    CASE
        WHEN z.borough IN ('Unknown', 'EWR') THEN FALSE
        WHEN COALESCE(p.pickup_trip_count, 0) < 1000 THEN TRUE
        WHEN COALESCE(d.dropoff_trip_count, 0) > 2000 AND (CAST(COALESCE(p.pickup_trip_count, 0) AS DOUBLE) / NULLIF(d.dropoff_trip_count, 0)) < 0.20 THEN TRUE
        ELSE FALSE
    END AS is_underserved

FROM all_zones z
LEFT JOIN pickup_stats p ON z.location_id = p.location_id
LEFT JOIN dropoff_stats d ON z.location_id = d.location_id
