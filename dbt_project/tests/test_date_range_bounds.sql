-- Test: Strict Date Boundary Range (1 Apr 2024 to 30 Jun 2024)
-- Fails if any trip pickup_datetime is outside 2024-04-01 00:00:00 and 2024-06-30 23:59:59

SELECT
    trip_id,
    pickup_datetime
FROM {{ ref('fct_trips') }}
WHERE pickup_datetime < '2024-04-01 00:00:00'
   OR pickup_datetime > '2024-06-30 23:59:59'
