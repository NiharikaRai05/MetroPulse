-- Test: Mart Totals must match Fact Totals (Conservation of Measure)
-- Fails if the sum of trips or revenue across mart_zone or mart_time differs from fct_trips

WITH fct_totals AS (
    SELECT
        COUNT(*) AS fct_total_trips,
        ROUND(SUM(total_amount), 2) AS fct_total_spending,
        ROUND(SUM(fare_amount), 2) AS fct_total_fare
    FROM {{ ref('fct_trips') }}
),

mart_zone_totals AS (
    SELECT
        SUM(pickup_trip_count) AS zone_total_pickups,
        ROUND(SUM(pickup_passenger_spending), 2) AS zone_total_spending,
        ROUND(SUM(pickup_fare_amount), 2) AS zone_total_fare
    FROM {{ ref('mart_zone') }}
),

mart_time_totals AS (
    SELECT
        SUM(trip_count) AS time_total_trips,
        ROUND(SUM(total_passenger_spending), 2) AS time_total_spending,
        ROUND(SUM(total_fare_amount), 2) AS time_total_fare
    FROM {{ ref('mart_time') }}
)

SELECT
    f.fct_total_trips,
    z.zone_total_pickups,
    t.time_total_trips,
    f.fct_total_spending,
    z.zone_total_spending,
    t.time_total_spending
FROM fct_totals f
CROSS JOIN mart_zone_totals z
CROSS JOIN mart_time_totals t
WHERE f.fct_total_trips != z.zone_total_pickups
   OR f.fct_total_trips != t.time_total_trips
   OR ABS(f.fct_total_spending - z.zone_total_spending) > 0.05
   OR ABS(f.fct_total_spending - t.time_total_spending) > 0.05
