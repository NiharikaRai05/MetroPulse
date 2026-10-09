{{
    config(
        materialized='view',
        schema='intermediate'
    )
}}

/*
    Intermediate Model: int_subway_hourly
    - Grain: Exactly 1 row per hour (transit_hour) in America/New_York
    - Aggregates station-level turnstile entries across all 420+ complexes
    - Includes borough-level ridership breakdowns as structured metric columns
      to enable seamless joins without multiplying rows.
*/

WITH subway_base AS (
    SELECT
        transit_hour,
        transit_date,
        coalesce(borough, 'Unknown') AS borough,
        station_complex_id,
        ridership
    FROM {{ ref('stg_subway') }}
)

SELECT
    transit_hour,
    CAST(date_trunc('day', transit_hour) AS DATE) AS transit_date,
    EXTRACT(HOUR FROM transit_hour) AS hour_of_day,

    -- Citywide aggregate ridership
    coalesce(sum(ridership), 0) AS total_subway_ridership,
    count(DISTINCT station_complex_id) AS reporting_station_complex_count,

    -- Borough-level ridership breakdown (pivoted cleanly)
    coalesce(sum(CASE WHEN upper(borough) = 'MANHATTAN' OR upper(borough) = 'M' THEN ridership ELSE 0 END), 0) AS subway_ridership_manhattan,
    coalesce(sum(CASE WHEN upper(borough) = 'BROOKLYN' OR upper(borough) = 'BK' THEN ridership ELSE 0 END), 0) AS subway_ridership_brooklyn,
    coalesce(sum(CASE WHEN upper(borough) = 'QUEENS' OR upper(borough) = 'Q' THEN ridership ELSE 0 END), 0) AS subway_ridership_queens,
    coalesce(sum(CASE WHEN upper(borough) = 'BRONX' OR upper(borough) = 'BX' THEN ridership ELSE 0 END), 0) AS subway_ridership_bronx,
    coalesce(sum(CASE WHEN upper(borough) = 'STATEN ISLAND' OR upper(borough) = 'SI' THEN ridership ELSE 0 END), 0) AS subway_ridership_staten_island

FROM subway_base
GROUP BY transit_hour
