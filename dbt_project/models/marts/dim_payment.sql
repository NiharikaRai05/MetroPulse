{{
    config(
        materialized='table',
        schema='marts'
    )
}}

/*
    Dimension Model: dim_payment
    - Grain: 1 row per payment type code
    - Standard TLC payment type mappings
*/

SELECT * FROM (
    VALUES
        (1, 'Credit card', 'Electronic card payment; tip recorded on meter', TRUE),
        (2, 'Cash', 'Cash transaction; tips are not recorded on meter', FALSE),
        (3, 'No charge', 'No charge trip', FALSE),
        (4, 'Dispute', 'Disputed fare transaction', FALSE),
        (5, 'Unknown', 'Unknown payment method', FALSE),
        (6, 'Voided trip', 'Voided trip transaction', FALSE)
) AS t(payment_type_id, payment_type_name, payment_description, is_electronic_tip_recorded)
