{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Dimension Model: dim_rate
    - Grain: 1 row per RateCodeID
    - Standard TLC rate code classifications
*/

SELECT * FROM (
    VALUES
        (1, 'Standard rate', 'Standard metered rate within NYC', FALSE),
        (2, 'JFK', 'Flat rate between Manhattan and JFK International Airport', TRUE),
        (3, 'Newark', 'Trips to/from Newark Airport (includes surcharge)', TRUE),
        (4, 'Nassau or Westchester', 'Suburban county metered rate', FALSE),
        (5, 'Negotiated fare', 'Agreed flat rate / charter fare', FALSE),
        (6, 'Group ride', 'Group ride flat fare', FALSE),
        (99, 'Special / Unspecified', 'Out of specification rate', FALSE)
) AS t(rate_code_id, rate_code_name, rate_description, is_flat_airport_rate)
