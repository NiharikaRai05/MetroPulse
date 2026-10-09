-- Test: Reconciliation must be perfectly balanced
-- Fails if reconciliation_status != 'BALANCED_PERFECT' or reconciliation_delta != 0

SELECT
    raw_trips_count,
    total_excluded_rows,
    fct_trips_count,
    reconciliation_delta,
    reconciliation_status
FROM {{ ref('reconcile_trip_lineage') }}
WHERE reconciliation_status != 'BALANCED_PERFECT'
   OR reconciliation_delta != 0
