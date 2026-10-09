{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Mart Model: mart_route_pairs
    - Grain: 1 row per pickup_zone x dropoff_zone (Origin-Destination route pair)
    - Captures corridor density, inter-borough mobility flows, and airport travel channels
    - Preserves additive sums and counts only
*/

WITH trips AS (
    SELECT * FROM {{ ref('fct_trips') }}
),

zones AS (
    SELECT location_id, borough, zone_name, is_congestion_zone, is_airport_zone FROM {{ ref('dim_zone') }}
),

routes_agg AS (
    SELECT
        pickup_location_id,
        dropoff_location_id,
        COUNT(*) AS trip_count,
        SUM(passenger_count) AS total_passengers,
        SUM(total_amount) AS total_passenger_spending,
        SUM(fare_amount) AS total_fare_amount,
        SUM(tip_amount) AS total_tip_amount,
        SUM(tolls_amount) AS total_tolls_amount,
        SUM(trip_distance_miles) AS total_distance_miles,
        SUM(duration_minutes) AS total_duration_minutes
    FROM trips
    GROUP BY pickup_location_id, dropoff_location_id
)

SELECT
    r.pickup_location_id,
    pz.zone_name AS pickup_zone_name,
    pz.borough AS pickup_borough,
    pz.is_congestion_zone AS pickup_is_congestion_zone,
    pz.is_airport_zone AS pickup_is_airport_zone,

    r.dropoff_location_id,
    dz.zone_name AS dropoff_zone_name,
    dz.borough AS dropoff_borough,
    dz.is_congestion_zone AS dropoff_is_congestion_zone,
    dz.is_airport_zone AS dropoff_is_airport_zone,

    -- Route classification
    CASE 
        WHEN pz.borough = dz.borough THEN 'Intra-Borough'
        ELSE 'Inter-Borough'
    END AS route_flow_type,

    CASE 
        WHEN pz.is_airport_zone OR dz.is_airport_zone THEN TRUE
        ELSE FALSE
    END AS is_airport_corridor,

    -- Additive metrics
    r.trip_count,
    r.total_passengers,
    r.total_passenger_spending,
    r.total_fare_amount,
    r.total_tip_amount,
    r.total_tolls_amount,
    r.total_distance_miles,
    r.total_duration_minutes

FROM routes_agg r
LEFT JOIN zones pz ON r.pickup_location_id = pz.location_id
LEFT JOIN zones dz ON r.dropoff_location_id = dz.location_id
