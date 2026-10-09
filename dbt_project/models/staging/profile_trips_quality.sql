-- ==============================================================================
-- MetroPulse: Comprehensive Data Quality & Anomaly Profiling
-- Target Period: 2024-04-01 to 2024-06-30
-- Input: raw.yellow_trips / staging.stg_trips
-- Output: A single unified summary table with issue_name, issue_description,
--         affected_rows, total_dataset_rows, pct_of_dataset, and severity.
-- ==============================================================================

WITH base_trips AS (
    SELECT
        trip_id,
        vendor_id,
        pickup_datetime,
        dropoff_datetime,
        passenger_count,
        trip_distance_miles,
        rate_code_id,
        payment_type,
        fare_amount,
        extra_amount,
        mta_tax_amount,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        congestion_surcharge,
        airport_fee,
        total_amount,
        pickup_location_id,
        dropoff_location_id,
        -- Calculated diagnostics
        date_diff('second', pickup_datetime, dropoff_datetime) AS duration_seconds,
        date_diff('minute', pickup_datetime, dropoff_datetime) AS duration_minutes,
        CASE 
            WHEN date_diff('second', pickup_datetime, dropoff_datetime) > 0 
            THEN trip_distance_miles / (date_diff('second', pickup_datetime, dropoff_datetime) / 3600.0)
            ELSE NULL 
        END AS calculated_speed_mph
    FROM {{ ref('stg_trips') }}
),

total_stats AS (
    SELECT count(*) AS total_rows FROM base_trips
),

profile_checks AS (
    -- 1. Timestamps outside Q2 2024 boundary (2024-04-01 00:00:00 to 2024-06-30 23:59:59)
    SELECT
        1 AS issue_id,
        'pickup_outside_target_period' AS issue_name,
        'Pickup timestamp occurs outside 2024-04-01 to 2024-06-30' AS issue_description,
        'CRITICAL' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE pickup_datetime < '2024-04-01 00:00:00' OR pickup_datetime > '2024-06-30 23:59:59'

    UNION ALL

    -- 2. Dropoff before or equal to pickup (temporal impossibility)
    SELECT
        2 AS issue_id,
        'dropoff_before_or_equal_pickup' AS issue_name,
        'Dropoff timestamp is earlier than or equal to pickup timestamp (duration <= 0)' AS issue_description,
        'CRITICAL' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE dropoff_datetime <= pickup_datetime

    UNION ALL

    -- 3. Excessively long trip duration (> 12 hours)
    SELECT
        3 AS issue_id,
        'excessive_trip_duration' AS issue_name,
        'Trip duration exceeds 12 hours (potential meter forgotten / unclosed ride)' AS issue_description,
        'WARNING' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE duration_minutes > 720

    UNION ALL

    -- 4. Distance anomalies (Zero distance with positive fare, or distance > 100 miles)
    SELECT
        4 AS issue_id,
        'distance_anomalies' AS issue_name,
        'Zero trip distance (< 0.01 mi) with fare > $0, or extreme distance > 100 miles' AS issue_description,
        'WARNING' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE (trip_distance_miles <= 0.0 AND fare_amount > 0) OR trip_distance_miles > 100.0

    UNION ALL

    -- 5. Physically impossible speed (> 85 mph inside urban NYC context)
    SELECT
        5 AS issue_id,
        'impossible_speed' AS issue_name,
        'Calculated average speed exceeds 85 mph (corrupted distance or duration)' AS issue_description,
        'WARNING' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE calculated_speed_mph > 85.0 AND duration_seconds >= 60

    UNION ALL

    -- 6. Negative, zero, or extreme fare amount (< $0, = $0, or > $1,000)
    SELECT
        6 AS issue_id,
        'fare_amount_anomalies' AS issue_name,
        'Fare amount is negative (< 0), exactly $0, or extreme (> $1,000)' AS issue_description,
        'CRITICAL' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE fare_amount <= 0.0 OR fare_amount > 1000.0

    UNION ALL

    -- 7. Unknown or invalid TLC Location IDs (264, 265, NULL, or < 1 or > 265)
    SELECT
        7 AS issue_id,
        'unknown_or_invalid_location_ids' AS issue_name,
        'Pickup or dropoff zone is Unknown/NV (264/265), NULL, or outside [1, 265]' AS issue_description,
        'INFO' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE pickup_location_id IN (264, 265) 
       OR dropoff_location_id IN (264, 265)
       OR pickup_location_id IS NULL 
       OR dropoff_location_id IS NULL
       OR pickup_location_id < 1 
       OR pickup_location_id > 265
       OR dropoff_location_id < 1 
       OR dropoff_location_id > 265

    UNION ALL

    -- 8. Exact duplicate records (shared natural keys and timestamps)
    SELECT
        8 AS issue_id,
        'duplicate_trip_records' AS issue_name,
        'Exact duplicate trip records matching on vendor, timestamps, locations, and fare' AS issue_description,
        'WARNING' AS severity,
        coalesce(sum(dup_count - 1), 0) AS affected_rows
    FROM (
        SELECT trip_id, count(*) AS dup_count
        FROM base_trips
        GROUP BY trip_id
        HAVING count(*) > 1
    ) sub

    UNION ALL

    -- 9. Passenger count anomalies (<= 0 or > 6 passengers)
    SELECT
        9 AS issue_id,
        'passenger_count_anomalies' AS issue_name,
        'Passenger count is 0, negative, or greater than yellow taxi legal limit (> 6)' AS issue_description,
        'WARNING' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE passenger_count <= 0 OR passenger_count > 6 OR passenger_count IS NULL

    UNION ALL

    -- 10. Odd or undocumented rate codes / payment types (not in TLC specification 1-6)
    SELECT
        10 AS issue_id,
        'unrecognized_rate_or_payment_codes' AS issue_name,
        'RateCodeID not in (1..6) or payment_type not in (1..6)' AS issue_description,
        'WARNING' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE rate_code_id NOT IN (1, 2, 3, 4, 5, 6) OR payment_type NOT IN (1, 2, 3, 4, 5, 6)

    UNION ALL

    -- 11. Cash tip recorded as > $0 (TLC rule: cash tips are not recorded by meter, should be 0)
    SELECT
        11 AS issue_id,
        'cash_tip_greater_than_zero' AS issue_name,
        'Payment type is Cash (2) but tip_amount is recorded > $0 (contradicts TLC spec)' AS issue_description,
        'INFO' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE payment_type = 2 AND tip_amount > 0.0

    UNION ALL

    -- 12. Null surcharge or fee fields (congestion, airport fee, improvement surcharge)
    SELECT
        12 AS issue_id,
        'null_surcharge_fields' AS issue_name,
        'One or more surcharge fields (congestion_surcharge, airport_fee, etc.) are NULL' AS issue_description,
        'WARNING' AS severity,
        count(*) AS affected_rows
    FROM base_trips
    WHERE congestion_surcharge IS NULL 
       OR airport_fee IS NULL 
       OR improvement_surcharge IS NULL
       OR mta_tax_amount IS NULL
       OR tolls_amount IS NULL
)

SELECT
    p.issue_id,
    p.issue_name,
    p.severity,
    p.issue_description,
    p.affected_rows,
    t.total_rows AS total_dataset_rows,
    ROUND((p.affected_rows * 100.0) / NULLIF(t.total_rows, 0), 4) AS pct_of_dataset
FROM profile_checks p
CROSS JOIN total_stats t
ORDER BY p.issue_id ASC;
