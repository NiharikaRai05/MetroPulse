{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Dimension Model: dim_hour
    - Grain: 1 row per hour of day (0..23)
    - Captures time-of-day buckets, peak rush hours, night surcharges, and mobility intervals
*/

WITH hours AS (
    SELECT UNNEST(generate_series(0, 23)) AS hour_of_day
)

SELECT
    hour_of_day,
    printf('%02d:00', hour_of_day) AS hour_label_24h,
    CASE 
        WHEN hour_of_day = 0 THEN '12:00 AM'
        WHEN hour_of_day < 12 THEN printf('%02d:00 AM', hour_of_day)
        WHEN hour_of_day = 12 THEN '12:00 PM'
        ELSE printf('%02d:00 PM', hour_of_day - 12)
    END AS hour_label_12h,

    -- Temporal period classifications
    CASE
        WHEN hour_of_day BETWEEN 0 AND 5 THEN 'Late Night'
        WHEN hour_of_day BETWEEN 6 AND 9 THEN 'Morning Rush'
        WHEN hour_of_day BETWEEN 10 AND 15 THEN 'Midday'
        WHEN hour_of_day BETWEEN 16 AND 19 THEN 'Evening Rush'
        ELSE 'Night'
    END AS time_of_day_bucket,

    -- TLC Rush Hour Surcharge Window (4 PM - 8 PM weekdays)
    CASE WHEN hour_of_day BETWEEN 16 AND 19 THEN TRUE ELSE FALSE END AS is_rush_hour_window,

    -- TLC Overnight Surcharge Window (8 PM - 6 AM)
    CASE WHEN hour_of_day >= 20 OR hour_of_day <= 5 THEN TRUE ELSE FALSE END AS is_overnight_window

FROM hours
