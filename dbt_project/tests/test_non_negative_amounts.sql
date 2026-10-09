-- Test: Financial Amounts and Distances must be Non-Negative in fct_trips
-- Fails if any valid clean trip has negative fare, tip, tolls, total amount, or distance

SELECT
    trip_id,
    fare_amount,
    tip_amount,
    tolls_amount,
    total_amount,
    trip_distance_miles
FROM {{ ref('fct_trips') }}
WHERE fare_amount < 0
   OR tip_amount < 0
   OR tolls_amount < 0
   OR total_amount < 0
   OR trip_distance_miles < 0
