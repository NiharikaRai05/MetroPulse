{{
    config(
        materialized='view',
        schema='intermediate'
    )
}}

/*
    Intermediate Model: int_trips_flagged
    - Calculates diagnostic fields (duration, speed, fare per mile)
    - Evaluates explicit boolean flags for each DQ rule using thresholds from dbt vars
    - Preserves all rows with full auditability
*/

WITH base AS (
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
        passenger_count,
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
        source_period,
        loaded_at,

        -- Computed Diagnostic Metrics
        date_diff('second', pickup_datetime, dropoff_datetime) AS duration_seconds,
        date_diff('minute', pickup_datetime, dropoff_datetime) AS duration_minutes,
        CASE
            WHEN date_diff('second', pickup_datetime, dropoff_datetime) > 0
            THEN trip_distance_miles / (date_diff('second', pickup_datetime, dropoff_datetime) / 3600.0)
            ELSE NULL
        END AS speed_mph,
        CASE
            WHEN trip_distance_miles > 0
            THEN fare_amount / trip_distance_miles
            ELSE NULL
        END AS fare_per_mile

    FROM {{ ref('stg_trips') }}
)

SELECT
    *,

    -- =========================================================================
    -- DQ Boolean Flags (TRUE = Anomaly/Violation Detected)
    -- =========================================================================

    -- Rule 1: Outside Target Period (2024-04-01 to 2024-06-30)
    (
        pickup_datetime < cast('{{ var("min_pickup_timestamp") }}' as timestamp) 
        OR pickup_datetime > cast('{{ var("max_pickup_timestamp") }}' as timestamp)
    ) AS flag_outside_period,

    -- Rule 2: Temporal Inversion (Dropoff before or equal to Pickup)
    (dropoff_datetime <= pickup_datetime) AS flag_dropoff_before_pickup,

    -- Rule 3: Duration Anomaly (< 60s or > 360m)
    (
        duration_seconds < {{ var("min_duration_seconds") }}
        OR duration_minutes > {{ var("max_duration_minutes") }}
    ) AS flag_duration_anomaly,

    -- Rule 4: Distance Anomaly (< 0.1 miles with positive fare, or > 100 miles)
    (
        (trip_distance_miles < {{ var("min_distance_miles") }} AND fare_amount > 0)
        OR trip_distance_miles > {{ var("max_distance_miles") }}
        OR trip_distance_miles IS NULL
    ) AS flag_distance_anomaly,

    -- Rule 5: Impossible Speed (> 85 mph)
    (
        speed_mph > {{ var("max_speed_mph") }}
        AND duration_seconds >= {{ var("min_duration_seconds") }}
    ) AS flag_impossible_speed,

    -- Rule 6: Fare Amount Anomaly (< $3.00 base drop or > $500.00)
    (
        fare_amount < {{ var("min_fare_amount") }}
        OR fare_amount > {{ var("max_fare_amount") }}
        OR total_amount < {{ var("min_total_amount") }}
        OR total_amount > {{ var("max_total_amount") }}
        OR fare_amount IS NULL
    ) AS flag_fare_anomaly,

    -- Rule 7: Unknown Location Zone (264, 265, NULL, or outside [1, 265])
    (
        pickup_location_id IN (264, 265)
        OR dropoff_location_id IN (264, 265)
        OR pickup_location_id IS NULL
        OR dropoff_location_id IS NULL
        OR pickup_location_id < 1
        OR pickup_location_id > 265
        OR dropoff_location_id < 1
        OR dropoff_location_id > 265
    ) AS flag_unknown_location,

    -- Rule 8: Passenger Count Anomaly (<= 0 or > 6)
    (
        passenger_count < {{ var("min_passenger_count") }}
        OR passenger_count > {{ var("max_passenger_count") }}
        OR passenger_count IS NULL
    ) AS flag_passenger_anomaly,

    -- Rule 9: Cash Tip Anomaly (payment_type = 2 with tip > 0)
    (
        payment_type = 2
        AND tip_amount > 0.0
    ) AS flag_cash_tip_anomaly

FROM base
