{{
    config(
        materialized='table',
        schema='intermediate'
    )
}}

/*
    Intermediate Model: int_trips_rule_impact
    - Measures the baseline population vs the marginal and isolated effect of each filtering rule
    - Evaluates impact on:
        1. Remaining trip count & percentage
        2. Average trip fare ($)
        3. Average fare per mile ($/mi)
        4. Average trip distance (mi)
*/

WITH flagged AS (
    SELECT * FROM {{ ref('int_trips_flagged') }}
),

baseline AS (
    SELECT
        0 AS step_order,
        '0_raw_baseline' AS rule_evaluated,
        'All raw ingested trips prior to filtering' AS rule_description,
        'BASELINE' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM flagged
),

rule_1_period AS (
    SELECT
        1 AS step_order,
        '1_outside_target_period' AS rule_evaluated,
        'Trips outside 2024-04-01 to 2024-06-30' AS rule_description,
        'EXCLUDE' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM flagged
    WHERE NOT flag_outside_period
),

rule_2_dropoff AS (
    SELECT
        2 AS step_order,
        '2_dropoff_before_pickup' AS rule_evaluated,
        'Trips with dropoff <= pickup timestamp' AS rule_description,
        'EXCLUDE' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM flagged
    WHERE NOT flag_dropoff_before_pickup
),

rule_3_duration AS (
    SELECT
        3 AS step_order,
        '3_duration_bounds' AS rule_evaluated,
        'Trips with duration < 60s or > 360m' AS rule_description,
        'EXCLUDE' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM flagged
    WHERE NOT flag_duration_anomaly
),

rule_4_distance AS (
    SELECT
        4 AS step_order,
        '4_distance_bounds' AS rule_evaluated,
        'Trips with distance < 0.1 mi or > 100 mi' AS rule_description,
        'EXCLUDE' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM flagged
    WHERE NOT flag_distance_anomaly
),

rule_5_speed AS (
    SELECT
        5 AS step_order,
        '5_impossible_speed' AS rule_evaluated,
        'Trips with calculated speed > 85 mph' AS rule_description,
        'EXCLUDE' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM flagged
    WHERE NOT flag_impossible_speed
),

rule_6_fare AS (
    SELECT
        6 AS step_order,
        '6_fare_bounds' AS rule_evaluated,
        'Trips with fare < $3.00 or > $500.00' AS rule_description,
        'EXCLUDE' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM flagged
    WHERE NOT flag_fare_anomaly
),

clean_final AS (
    SELECT
        7 AS step_order,
        '7_clean_dataset_final' AS rule_evaluated,
        'Clean dataset after applying all exclusion rules simultaneously' AS rule_description,
        'FINAL_CLEAN' AS policy_action,
        count(*) AS trip_count,
        round(avg(fare_amount), 2) AS avg_fare_amount,
        round(avg(fare_per_mile), 2) AS avg_fare_per_mile,
        round(avg(trip_distance_miles), 2) AS avg_trip_distance_miles
    FROM {{ ref('int_trips_clean') }}
),

unioned AS (
    SELECT * FROM baseline
    UNION ALL SELECT * FROM rule_1_period
    UNION ALL SELECT * FROM rule_2_dropoff
    UNION ALL SELECT * FROM rule_3_duration
    UNION ALL SELECT * FROM rule_4_distance
    UNION ALL SELECT * FROM rule_5_speed
    UNION ALL SELECT * FROM rule_6_fare
    UNION ALL SELECT * FROM clean_final
)

SELECT
    u.step_order,
    u.rule_evaluated,
    u.policy_action,
    u.rule_description,
    u.trip_count,
    (b.trip_count - u.trip_count) AS rows_removed,
    round(((b.trip_count - u.trip_count) * 100.0) / nullif(b.trip_count, 0), 4) AS pct_rows_removed,
    u.avg_fare_amount,
    round(u.avg_fare_amount - b.avg_fare_amount, 2) AS delta_avg_fare,
    u.avg_fare_per_mile,
    round(u.avg_fare_per_mile - b.avg_fare_per_mile, 2) AS delta_fare_per_mile,
    u.avg_trip_distance_miles
FROM unioned u
CROSS JOIN baseline b
ORDER BY u.step_order ASC;
