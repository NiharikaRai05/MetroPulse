{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_quality
    - Complete Data Quality & Hygiene Profiler Mart
    - Computes exact anomaly counts, percentages, treatments, and status badges
    - Sourced directly from int_trips_flagged without hardcoding
*/

WITH flagged AS (
    SELECT * FROM {{ ref('int_trips_flagged') }}
),

totals AS (
    SELECT count(*) AS total_dataset_rows FROM flagged
),

rules AS (
    SELECT
        1 AS rule_order,
        'RULE_01_PERIOD' AS rule_id,
        'Out of Target Period' AS rule_name,
        'Pickups outside 2024-04-01 to 2024-06-30' AS rule_description,
        'EXCLUDE' AS treatment,
        'FAIL' AS status,
        SUM(CASE WHEN flag_outside_period THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        2 AS rule_order,
        'RULE_02_TEMPORAL' AS rule_id,
        'Temporal Inversion' AS rule_name,
        'Dropoff datetime occurs before or equal to pickup' AS rule_description,
        'EXCLUDE' AS treatment,
        'FAIL' AS status,
        SUM(CASE WHEN flag_dropoff_before_pickup THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        3 AS rule_order,
        'RULE_03_DURATION' AS rule_id,
        'Duration Bounds Anomaly' AS rule_name,
        'Trip duration < 60 seconds or > 360 minutes' AS rule_description,
        'EXCLUDE' AS treatment,
        'FAIL' AS status,
        SUM(CASE WHEN flag_duration_anomaly THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        4 AS rule_order,
        'RULE_04_DISTANCE' AS rule_id,
        'Distance Bounds Anomaly' AS rule_name,
        'Distance < 0.1 miles with positive fare, or > 100 miles' AS rule_description,
        'EXCLUDE' AS treatment,
        'FAIL' AS status,
        SUM(CASE WHEN flag_distance_anomaly THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        5 AS rule_order,
        'RULE_05_SPEED' AS rule_id,
        'Implausible Velocity' AS rule_name,
        'Calculated trip speed > 85.0 mph' AS rule_description,
        'EXCLUDE' AS treatment,
        'FAIL' AS status,
        SUM(CASE WHEN flag_impossible_speed THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        6 AS rule_order,
        'RULE_06_FARE' AS rule_id,
        'Fare Bounds Anomaly' AS rule_name,
        'Base fare < $3.00 or > $500.00' AS rule_description,
        'EXCLUDE' AS treatment,
        'FAIL' AS status,
        SUM(CASE WHEN flag_fare_anomaly THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        7 AS rule_order,
        'RULE_07_LOCATION' AS rule_id,
        'Unknown LocationID' AS rule_name,
        'LocationID in (264, 265, NULL) or outside 1..265' AS rule_description,
        'LABEL_AND_RETAIN' AS treatment,
        'WARN' AS status,
        SUM(CASE WHEN flag_unknown_location THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        8 AS rule_order,
        'RULE_08_PASSENGER' AS rule_id,
        'Passenger Count Anomaly' AS rule_name,
        'Passenger count <= 0 or > 6 (imputed to 1)' AS rule_description,
        'IMPUTE_AND_LABEL' AS treatment,
        'PASS' AS status,
        SUM(CASE WHEN flag_passenger_anomaly THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged

    UNION ALL

    SELECT
        9 AS rule_order,
        'RULE_09_CASH_TIP' AS rule_id,
        'Cash Tip Discrepancy' AS rule_name,
        'Cash payment (type=2) with recorded positive tip' AS rule_description,
        'FLAG_AND_RETAIN' AS treatment,
        'PASS' AS status,
        SUM(CASE WHEN flag_cash_tip_anomaly THEN 1 ELSE 0 END) AS affected_rows
    FROM flagged
)

SELECT
    r.rule_order,
    r.rule_id,
    r.rule_name,
    r.rule_description,
    r.treatment,
    r.status,
    r.affected_rows,
    t.total_dataset_rows,
    ROUND((r.affected_rows * 100.0) / NULLIF(t.total_dataset_rows, 0), 4) AS pct_of_dataset
FROM rules r
CROSS JOIN totals t
ORDER BY r.rule_order ASC;

