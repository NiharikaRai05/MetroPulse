{{
    config(
        materialized='view',
        schema='intermediate'
    )
}}

/*
    Intermediate Model: int_trips_clean
    - Implements an explicit Exclude / Retain / Label policy:
      * EXCLUDE: Critical physical/temporal impossibilities that distort metrics:
          - Outside target period (1 Apr - 30 Jun 2024)
          - Dropoff <= Pickup
          - Extreme duration (< 60s or > 360m)
          - Distance anomalies (< 0.1 mi with fare, or > 100 mi)
          - Impossible speed (> 85 mph)
          - Negative, zero, or extreme fares (< $3.00 or > $500.00)
      * RETAIN & LABEL:
          - Unknown zones (retained, labeled as has_unknown_zone = TRUE)
          - Missing/odd passenger counts (retained, imputed/flagged)
          - Cash tips anomalies (retained, tip_amount treated with caution)
*/

WITH flagged_trips AS (
    SELECT * FROM {{ ref('int_trips_flagged') }}
)

SELECT
    trip_id,
    vendor_id,
    rate_code_id,
    store_and_fwd_flag,
    payment_type,
    pickup_datetime,
    dropoff_datetime,
    pickup_location_id,
    dropoff_location_id,
    
    -- Cleaned passenger count (impute null/anomalies with 1 for capacity estimations while labeling)
    coalesce(
        CASE WHEN passenger_count BETWEEN 1 AND 6 THEN passenger_count ELSE NULL END,
        1
    ) AS passenger_count,
    
    trip_distance_miles,
    fare_amount,
    extra_amount,
    mta_tax_amount,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    congestion_surcharge,
    airport_fee,
    total_amount,

    -- Calculated metrics
    duration_seconds,
    duration_minutes,
    speed_mph,
    fare_per_mile,

    -- Labeled dimensions (retained anomalies)
    flag_unknown_location AS is_unknown_zone,
    flag_passenger_anomaly AS is_passenger_count_imputed,
    flag_cash_tip_anomaly AS is_cash_tip_anomaly,

    -- Lineage
    source_period,
    loaded_at

FROM flagged_trips
WHERE
    -- Critical exclusion gates
    NOT flag_outside_period
    AND NOT flag_dropoff_before_pickup
    AND NOT flag_duration_anomaly
    AND NOT flag_distance_anomaly
    AND NOT flag_impossible_speed
    AND NOT flag_fare_anomaly
