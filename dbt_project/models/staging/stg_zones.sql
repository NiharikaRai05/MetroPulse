{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model: stg_zones
    - Standardized snake_case naming
    - Strictly typed casts
    - NO rows removed
*/

SELECT
    cast(LocationID as integer) AS location_id,
    cast(Borough as varchar) AS borough,
    cast(Zone as varchar) AS zone_name,
    cast(service_zone as varchar) AS service_zone,
    cast(_loaded_at as timestamp) AS loaded_at

FROM {{ source('raw', 'tlc_zones') }}
