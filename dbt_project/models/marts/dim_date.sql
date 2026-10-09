{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Dimension Model: dim_date
    - Grain: 1 row per calendar day covering Q2 2024 (2024-04-01 to 2024-06-30)
    - Full calendar dimension with day of week, weekend flags, holidays, and quarter
*/

WITH date_spine AS (
    SELECT 
        CAST(d AS DATE) AS date_day
    FROM generate_series(
        DATE '2024-04-01', 
        DATE '2024-06-30', 
        INTERVAL 1 DAY
    ) AS t(d)
)

SELECT
    date_day,
    CAST(strftime(date_day, '%Y%m%d') AS INTEGER) AS date_key,
    EXTRACT(YEAR FROM date_day) AS year_actual,
    EXTRACT(MONTH FROM date_day) AS month_actual,
    strftime(date_day, '%B') AS month_name,
    EXTRACT(DAY FROM date_day) AS day_of_month,
    EXTRACT(DOW FROM date_day) AS day_of_week,  -- 0 = Sunday, 6 = Saturday
    strftime(date_day, '%A') AS day_name,
    EXTRACT(QUARTER FROM date_day) AS quarter_actual,
    EXTRACT(WEEK FROM date_day) AS week_of_year,

    -- Flags
    CASE WHEN EXTRACT(DOW FROM date_day) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
    CASE WHEN EXTRACT(DOW FROM date_day) BETWEEN 1 AND 5 THEN TRUE ELSE FALSE END AS is_weekday,
    
    -- US Federal Holidays in Q2 2024 (Memorial Day: May 27, Juneteenth: June 19)
    CASE 
        WHEN date_day = DATE '2024-05-27' THEN 'Memorial Day'
        WHEN date_day = DATE '2024-06-19' THEN 'Juneteenth'
        ELSE NULL
    END AS holiday_name,
    CASE 
        WHEN date_day IN (DATE '2024-05-27', DATE '2024-06-19') THEN TRUE 
        ELSE FALSE 
    END AS is_holiday

FROM date_spine
