-- Test: Speed Bounds in fct_trips
-- Fails if any valid clean trip exceeds the maximum realistic speed (85 mph) for trips >= 60 seconds

SELECT
    trip_id,
    speed_mph,
    trip_distance_miles,
    duration_seconds
FROM {{ ref('fct_trips') }}
WHERE speed_mph > 85.0
  AND duration_seconds >= 60
