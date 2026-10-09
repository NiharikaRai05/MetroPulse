{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Reconciliation Mart Model: reconcile_trip_lineage
    - Mathematical Proof & Integrity Audit:
        raw_row_count - total_excluded_rows = fct_trips_row_count
    - Verifies that zero records are unaccounted for across the transformation pipeline.
*/

WITH flagged AS (
    SELECT
        trip_id,
        flag_outside_period,
        flag_dropoff_before_pickup,
        flag_duration_anomaly,
        flag_distance_anomaly,
        flag_impossible_speed,
        flag_fare_anomaly,
        (
            flag_outside_period 
            OR flag_dropoff_before_pickup 
            OR flag_duration_anomaly 
            OR flag_distance_anomaly 
            OR flag_impossible_speed 
            OR flag_fare_anomaly
        ) AS is_excluded
    FROM {{ ref('int_trips_flagged') }}
),

fct_count AS (
    SELECT COUNT(*) AS fct_trips_count FROM {{ ref('fct_trips') }}
),

reconciliation_calc AS (
    SELECT
        COUNT(*) AS raw_trips_count,
        SUM(CASE WHEN flag_outside_period THEN 1 ELSE 0 END) AS excluded_outside_period,
        SUM(CASE WHEN NOT flag_outside_period AND flag_dropoff_before_pickup THEN 1 ELSE 0 END) AS excluded_dropoff_before_pickup,
        SUM(CASE WHEN NOT flag_outside_period AND NOT flag_dropoff_before_pickup AND flag_duration_anomaly THEN 1 ELSE 0 END) AS excluded_duration_anomaly,
        SUM(CASE WHEN NOT flag_outside_period AND NOT flag_dropoff_before_pickup AND NOT flag_duration_anomaly AND flag_distance_anomaly THEN 1 ELSE 0 END) AS excluded_distance_anomaly,
        SUM(CASE WHEN NOT flag_outside_period AND NOT flag_dropoff_before_pickup AND NOT flag_duration_anomaly AND NOT flag_distance_anomaly AND flag_impossible_speed THEN 1 ELSE 0 END) AS excluded_impossible_speed,
        SUM(CASE WHEN NOT flag_outside_period AND NOT flag_dropoff_before_pickup AND NOT flag_duration_anomaly AND NOT flag_distance_anomaly AND NOT flag_impossible_speed AND flag_fare_anomaly THEN 1 ELSE 0 END) AS excluded_fare_anomaly,
        SUM(CASE WHEN is_excluded THEN 1 ELSE 0 END) AS total_excluded_rows,
        SUM(CASE WHEN NOT is_excluded THEN 1 ELSE 0 END) AS calculated_clean_trips
    FROM flagged
)

SELECT
    r.raw_trips_count,
    r.excluded_outside_period,
    r.excluded_dropoff_before_pickup,
    r.excluded_duration_anomaly,
    r.excluded_distance_anomaly,
    r.excluded_impossible_speed,
    r.excluded_fare_anomaly,
    r.total_excluded_rows,
    r.calculated_clean_trips,
    f.fct_trips_count,
    (r.raw_trips_count - r.total_excluded_rows) AS mathematical_expected_fct_count,
    (f.fct_trips_count - (r.raw_trips_count - r.total_excluded_rows)) AS reconciliation_delta,
    CASE 
        WHEN f.fct_trips_count = (r.raw_trips_count - r.total_excluded_rows) THEN 'BALANCED_PERFECT'
        ELSE 'RECONCILIATION_FAILED'
    END AS reconciliation_status
FROM reconciliation_calc r
CROSS JOIN fct_count f
