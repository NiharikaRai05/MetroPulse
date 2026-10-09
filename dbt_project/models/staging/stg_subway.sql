{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model: stg_subway
    - Standardized snake_case naming
    - Strictly typed casts
    - Preserves hourly ridership per station complex
    - NO rows removed
*/

SELECT
    cast(transit_timestamp as timestamp) AS transit_timestamp,
    cast(date_trunc('hour', transit_timestamp) as timestamp) AS transit_hour,
    cast(date_trunc('day', transit_timestamp) as date) AS transit_date,
    cast(station_complex_id as varchar) AS station_complex_id,
    cast(station_complex as varchar) AS station_complex_name,
    cast(borough as varchar) AS borough,
    cast(ridership as bigint) AS ridership,
    cast(latitude as double) AS latitude,
    cast(longitude as double) AS longitude,
    cast(_source_period as varchar) AS source_period,
    cast(_loaded_at as timestamp) AS loaded_at

FROM {{ source('raw', 'mta_subway_hourly') }}
