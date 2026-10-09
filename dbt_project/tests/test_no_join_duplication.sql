-- Test: No Join Fan-out / Row Duplication in int_hourly_demand
-- Fails if int_hourly_demand has more or fewer rows than the exact 2,184 hours in Q2 2024

WITH hour_spine_count AS (
    SELECT COUNT(*) AS expected_hour_count
    FROM generate_series(
        TIMESTAMP '2024-04-01 00:00:00',
        TIMESTAMP '2024-06-30 23:00:00',
        INTERVAL 1 HOUR
    ) AS t(h)
),

demand_count AS (
    SELECT COUNT(*) AS actual_demand_count
    FROM {{ ref('int_hourly_demand') }}
)

SELECT
    s.expected_hour_count,
    d.actual_demand_count,
    (d.actual_demand_count - s.expected_hour_count) AS row_difference
FROM hour_spine_count s
CROSS JOIN demand_count d
WHERE s.expected_hour_count != d.actual_demand_count
