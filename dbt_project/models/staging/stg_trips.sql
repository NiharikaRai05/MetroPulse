{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model: stg_trips
    - Standardized snake_case naming
    - Strictly typed casts
    - NO rows removed (raw preservation at staging level)
    - Generates surrogate trip_id via MD5 hash of natural keys + timestamps
*/

SELECT
    -- Deterministic surrogate trip_id
    md5(
        concat_ws(
            '||',
            coalesce(cast(VendorID as varchar), ''),
            coalesce(cast(tpep_pickup_datetime as varchar), ''),
            coalesce(cast(tpep_dropoff_datetime as varchar), ''),
            coalesce(cast(PULocationID as varchar), ''),
            coalesce(cast(DOLocationID as varchar), ''),
            coalesce(cast(fare_amount as varchar), ''),
            coalesce(cast(trip_distance as varchar), '')
        )
    ) AS trip_id,

    -- Attributes
    cast(VendorID as integer) AS vendor_id,
    cast(RatecodeID as integer) AS rate_code_id,
    cast(store_and_fwd_flag as varchar) AS store_and_fwd_flag,
    cast(payment_type as integer) AS payment_type,

    -- Timestamps
    cast(tpep_pickup_datetime as timestamp) AS pickup_datetime,
    cast(tpep_dropoff_datetime as timestamp) AS dropoff_datetime,

    -- Spatial Zone IDs
    cast(PULocationID as integer) AS pickup_location_id,
    cast(DOLocationID as integer) AS dropoff_location_id,

    -- Metrics
    cast(passenger_count as integer) AS passenger_count,
    cast(trip_distance as double) AS trip_distance_miles,

    -- Financial Breakdown
    cast(fare_amount as double) AS fare_amount,
    cast(extra as double) AS extra_amount,
    cast(mta_tax as double) AS mta_tax_amount,
    cast(tip_amount as double) AS tip_amount,
    cast(tolls_amount as double) AS tolls_amount,
    cast(improvement_surcharge as double) AS improvement_surcharge,
    cast(congestion_surcharge as double) AS congestion_surcharge,
    cast(Airport_fee as double) AS airport_fee,
    cast(total_amount as double) AS total_amount,

    -- Audit Lineage
    cast(_source_period as varchar) AS source_period,
    cast(_loaded_at as timestamp) AS loaded_at

FROM {{ source('raw', 'yellow_trips') }}
