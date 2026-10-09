import argparse
import logging
from pathlib import Path
import duckdb
import pandas as pd
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("metropulse.analysis.profiler")

def run_profiling(duckdb_path: str = "data/metropulse.duckdb", output_csv: str = "data/manifests/dq_profile_summary.csv"):
    """
    Executes DuckDB data quality profiling on TLC Yellow Trips (Q2 2024),
    prints a formatted markdown table of the 12 issues, and saves the result to CSV.
    """
    db_file = Path(duckdb_path)
    if not db_file.exists():
        logger.error(f"DuckDB database not found at {db_file}. Please run 'make ingest' first.")
        return None

    profiling_query = """
    WITH base_trips AS (
        SELECT
            md5(concat_ws('||', coalesce(cast(VendorID as varchar), ''), coalesce(cast(tpep_pickup_datetime as varchar), ''), coalesce(cast(tpep_dropoff_datetime as varchar), ''), coalesce(cast(PULocationID as varchar), ''), coalesce(cast(DOLocationID as varchar), ''), coalesce(cast(fare_amount as varchar), ''), coalesce(cast(trip_distance as varchar), ''))) AS trip_id,
            cast(VendorID as integer) AS vendor_id,
            cast(RatecodeID as integer) AS rate_code_id,
            cast(payment_type as integer) AS payment_type,
            cast(tpep_pickup_datetime as timestamp) AS pickup_datetime,
            cast(tpep_dropoff_datetime as timestamp) AS dropoff_datetime,
            cast(PULocationID as integer) AS pickup_location_id,
            cast(DOLocationID as integer) AS dropoff_location_id,
            cast(passenger_count as integer) AS passenger_count,
            cast(trip_distance as double) AS trip_distance_miles,
            cast(fare_amount as double) AS fare_amount,
            cast(extra as double) AS extra_amount,
            cast(mta_tax as double) AS mta_tax_amount,
            cast(tip_amount as double) AS tip_amount,
            cast(tolls_amount as double) AS tolls_amount,
            cast(improvement_surcharge as double) AS improvement_surcharge,
            cast(congestion_surcharge as double) AS congestion_surcharge,
            cast(Airport_fee as double) AS airport_fee,
            cast(total_amount as double) AS total_amount,
            date_diff('second', cast(tpep_pickup_datetime as timestamp), cast(tpep_dropoff_datetime as timestamp)) AS duration_seconds,
            date_diff('minute', cast(tpep_pickup_datetime as timestamp), cast(tpep_dropoff_datetime as timestamp)) AS duration_minutes,
            CASE 
                WHEN date_diff('second', cast(tpep_pickup_datetime as timestamp), cast(tpep_dropoff_datetime as timestamp)) > 0 
                THEN cast(trip_distance as double) / (date_diff('second', cast(tpep_pickup_datetime as timestamp), cast(tpep_dropoff_datetime as timestamp)) / 3600.0)
                ELSE NULL 
            END AS calculated_speed_mph
        FROM raw.yellow_trips
    ),
    total_stats AS (
        SELECT count(*) AS total_rows FROM base_trips
    ),
    profile_checks AS (
        SELECT 1 AS issue_id, 'pickup_outside_target_period' AS issue_name, 'CRITICAL' AS severity, 'Pickup outside 2024-04-01 to 2024-06-30' AS issue_description, count(*) AS affected_rows
        FROM base_trips WHERE pickup_datetime < '2024-04-01 00:00:00' OR pickup_datetime > '2024-06-30 23:59:59'
        UNION ALL
        SELECT 2, 'dropoff_before_or_equal_pickup', 'CRITICAL', 'Dropoff <= pickup timestamp (duration <= 0)', count(*)
        FROM base_trips WHERE dropoff_datetime <= pickup_datetime
        UNION ALL
        SELECT 3, 'excessive_trip_duration', 'WARNING', 'Trip duration > 12 hours (> 720 minutes)', count(*)
        FROM base_trips WHERE duration_minutes > 720
        UNION ALL
        SELECT 4, 'distance_anomalies', 'WARNING', 'Zero distance (<= 0 mi) with fare > $0, or distance > 100 mi', count(*)
        FROM base_trips WHERE (trip_distance_miles <= 0.0 AND fare_amount > 0) OR trip_distance_miles > 100.0
        UNION ALL
        SELECT 5, 'impossible_speed', 'WARNING', 'Calculated speed > 85 mph with duration >= 60s', count(*)
        FROM base_trips WHERE calculated_speed_mph > 85.0 AND duration_seconds >= 60
        UNION ALL
        SELECT 6, 'fare_amount_anomalies', 'CRITICAL', 'Fare amount <= $0 or extreme (> $1,000)', count(*)
        FROM base_trips WHERE fare_amount <= 0.0 OR fare_amount > 1000.0
        UNION ALL
        SELECT 7, 'unknown_or_invalid_location_ids', 'INFO', 'Location ID is Unknown/NV (264/265), NULL, or outside [1, 265]', count(*)
        FROM base_trips WHERE pickup_location_id IN (264, 265) OR dropoff_location_id IN (264, 265) OR pickup_location_id IS NULL OR dropoff_location_id IS NULL OR pickup_location_id < 1 OR pickup_location_id > 265 OR dropoff_location_id < 1 OR dropoff_location_id > 265
        UNION ALL
        SELECT 8, 'duplicate_trip_records', 'WARNING', 'Exact duplicate trip records matching composite key', coalesce(sum(dup_count - 1), 0)
        FROM (SELECT trip_id, count(*) AS dup_count FROM base_trips GROUP BY trip_id HAVING count(*) > 1) sub
        UNION ALL
        SELECT 9, 'passenger_count_anomalies', 'WARNING', 'Passenger count <= 0, > 6, or NULL', count(*)
        FROM base_trips WHERE passenger_count <= 0 OR passenger_count > 6 OR passenger_count IS NULL
        UNION ALL
        SELECT 10, 'unrecognized_rate_or_payment_codes', 'WARNING', 'RateCodeID not in (1..6) or payment_type not in (1..6)', count(*)
        FROM base_trips WHERE rate_code_id NOT IN (1, 2, 3, 4, 5, 6) OR payment_type NOT IN (1, 2, 3, 4, 5, 6)
        UNION ALL
        SELECT 11, 'cash_tip_greater_than_zero', 'INFO', 'Cash payment (2) with recorded tip_amount > $0', count(*)
        FROM base_trips WHERE payment_type = 2 AND tip_amount > 0.0
        UNION ALL
        SELECT 12, 'null_surcharge_fields', 'WARNING', 'Null congestion_surcharge, airport_fee, improvement, tax, or tolls', count(*)
        FROM base_trips WHERE congestion_surcharge IS NULL OR airport_fee IS NULL OR improvement_surcharge IS NULL OR mta_tax_amount IS NULL OR tolls_amount IS NULL
    )
    SELECT
        p.issue_id,
        p.issue_name,
        p.severity,
        p.issue_description,
        p.affected_rows,
        t.total_rows AS total_dataset_rows,
        ROUND((p.affected_rows * 100.0) / NULLIF(t.total_rows, 0), 4) AS pct_of_dataset
    FROM profile_checks p
    CROSS JOIN total_stats t
    ORDER BY p.issue_id ASC;
    """

    with duckdb.connect(str(db_file)) as con:
        df = con.execute(profiling_query).df()

    out_file = Path(output_csv)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False)
    logger.info(f"Saved profiling summary to {out_file}")

    print("\n" + "=" * 90)
    print("  📊 METROPULSE DATA QUALITY PROFILING SUMMARY (TLC YELLOW TAXI Q2 2024)")
    print("=" * 90)
    print(df.to_markdown(index=False))
    print("=" * 90 + "\n")

    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run DuckDB Data Quality Profiler")
    parser.add_argument("--db", default="data/metropulse.duckdb", help="Path to DuckDB database")
    parser.add_argument("--out", default="data/manifests/dq_profile_summary.csv", help="Output CSV path")
    args = parser.parse_args()
    run_profiling(duckdb_path=args.db, output_csv=args.out)
