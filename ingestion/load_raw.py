import glob
import logging
from pathlib import Path
from typing import Optional, Union

import duckdb
from ingestion.common import get_data_dir, get_project_root
from ingestion.utils import load_sources_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("metropulse.ingestion.load_raw")


def get_duckdb_connection(duckdb_path: Optional[Union[str, Path]] = None) -> duckdb.DuckDBPyConnection:
    if duckdb_path is None:
        duckdb_path = get_data_dir() / "metropulse.duckdb"
    duckdb_path = Path(duckdb_path)
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(duckdb_path))


def load_raw_tlc_zones(con: duckdb.DuckDBPyConnection):
    """
    Loads TLC Taxi Zone lookup CSV into raw.tlc_zones idempotently (data unchanged).
    """
    zones_csv = get_data_dir("raw/zones/taxi_zone_lookup.csv")
    if not zones_csv.exists():
        logger.warning(f"Zone CSV not found at {zones_csv}. Skipping load_raw_tlc_zones.")
        return

    logger.info("Loading raw.tlc_zones into DuckDB...")
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    
    # Check if table exists; if not, create it directly from CSV
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS raw.tlc_zones AS 
        SELECT 
            LocationID,
            Borough,
            Zone,
            service_zone,
            CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
        FROM read_csv_auto('{zones_csv.as_posix()}', header=True)
        WHERE 1=0;
        """
    )

    # Idempotent refresh: Replace entire raw.tlc_zones dataset cleanly
    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.tlc_zones AS 
        SELECT 
            LocationID,
            Borough,
            Zone,
            service_zone,
            CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
        FROM read_csv_auto('{zones_csv.as_posix()}', header=True);
        """
    )
    count = con.execute("SELECT COUNT(*) FROM raw.tlc_zones").fetchone()[0]
    logger.info(f"Loaded raw.tlc_zones: {count:,} records.")


def load_raw_yellow_trips(con: duckdb.DuckDBPyConnection):
    """
    Loads TLC Yellow Taxi Parquet files for 2024-04, 2024-05, and 2024-06
    into raw.yellow_trips idempotently using a delete-then-insert pattern per source period.
    The underlying trip data is loaded completely unchanged with partition lineage metadata.
    """
    config = load_sources_config()
    taxi_files = config["sources"]["tlc_yellow_taxi"]["files"]
    taxi_dir = get_data_dir("raw/taxi")

    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    # Initialize empty target table if not exists based on schema of first parquet file
    first_parquet = taxi_dir / taxi_files[0]["filename"]
    if not first_parquet.exists():
        logger.warning(f"Initial parquet file {first_parquet} not found. Skipping yellow trips load.")
        return

    # Check or create table
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS raw.yellow_trips AS 
        SELECT 
            *, 
            CAST('' AS VARCHAR) AS _source_period,
            CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
        FROM read_parquet('{first_parquet.as_posix()}')
        WHERE 1=0;
        """
    )

    for file_info in taxi_files:
        filename = file_info["filename"]
        period = file_info["period"]
        parquet_path = taxi_dir / filename

        if not parquet_path.exists():
            logger.warning(f"File {parquet_path} does not exist. Skipping period {period}.")
            continue

        logger.info(f"Loading raw.yellow_trips for period {period} ({filename})...")

        # Idempotent step 1: Delete existing records for this source period
        con.execute(
            "DELETE FROM raw.yellow_trips WHERE _source_period = ?",
            [period]
        )

        # Idempotent step 2: Insert raw parquet records unchanged
        con.execute(
            f"""
            INSERT INTO raw.yellow_trips
            SELECT 
                *, 
                '{period}' AS _source_period,
                CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
            FROM read_parquet('{parquet_path.as_posix()}');
            """
        )

        count = con.execute(
            "SELECT COUNT(*) FROM raw.yellow_trips WHERE _source_period = ?",
            [period]
        ).fetchone()[0]
        logger.info(f"Loaded period {period} into raw.yellow_trips: {count:,} rows.")


def load_raw_weather(con: duckdb.DuckDBPyConnection):
    """
    Loads Open-Meteo hourly weather Parquet into raw.weather_hourly idempotently.
    """
    weather_parquet = get_data_dir("raw/weather/weather_nyc_2024_q2.parquet")
    if not weather_parquet.exists():
        logger.warning(f"Weather parquet not found at {weather_parquet}. Skipping weather load.")
        return

    period = "2024-04_to_2024-06"
    logger.info("Loading raw.weather_hourly into DuckDB...")
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS raw.weather_hourly AS
        SELECT 
            *, 
            CAST('' AS VARCHAR) AS _source_period,
            CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
        FROM read_parquet('{weather_parquet.as_posix()}')
        WHERE 1=0;
        """
    )

    con.execute("DELETE FROM raw.weather_hourly WHERE _source_period = ?", [period])
    con.execute(
        f"""
        INSERT INTO raw.weather_hourly
        SELECT 
            *, 
            '{period}' AS _source_period,
            CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
        FROM read_parquet('{weather_parquet.as_posix()}');
        """
    )
    count = con.execute("SELECT COUNT(*) FROM raw.weather_hourly").fetchone()[0]
    logger.info(f"Loaded raw.weather_hourly: {count:,} hourly weather observations.")


def load_raw_mta_subway(con: duckdb.DuckDBPyConnection):
    """
    Loads MTA Subway hourly ridership Parquet into raw.mta_subway_hourly idempotently.
    """
    mta_parquet = get_data_dir("raw/mta/mta_subway_hourly_2024_q2.parquet")
    if not mta_parquet.exists():
        logger.warning(f"MTA parquet not found at {mta_parquet}. Skipping MTA load.")
        return

    period = "2024-04_to_2024-06"
    logger.info("Loading raw.mta_subway_hourly into DuckDB...")
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS raw.mta_subway_hourly AS
        SELECT 
            *, 
            CAST('' AS VARCHAR) AS _source_period,
            CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
        FROM read_parquet('{mta_parquet.as_posix()}')
        WHERE 1=0;
        """
    )

    con.execute("DELETE FROM raw.mta_subway_hourly WHERE _source_period = ?", [period])
    con.execute(
        f"""
        INSERT INTO raw.mta_subway_hourly
        SELECT 
            *, 
            '{period}' AS _source_period,
            CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS _loaded_at
        FROM read_parquet('{mta_parquet.as_posix()}');
        """
    )
    count = con.execute("SELECT COUNT(*) FROM raw.mta_subway_hourly").fetchone()[0]
    logger.info(f"Loaded raw.mta_subway_hourly: {count:,} ridership records.")


def load_all_raw(duckdb_path: Optional[Union[str, Path]] = None):
    """
    Loads all raw datasets into DuckDB raw.* tables idempotently.
    """
    logger.info("=== Loading All Raw Datasets Into DuckDB (raw.*) ===")
    with get_duckdb_connection(duckdb_path) as con:
        load_raw_tlc_zones(con)
        load_raw_weather(con)
        load_raw_mta_subway(con)
        load_raw_yellow_trips(con)
    logger.info("=== Completed Loading All Raw Tables ===")


if __name__ == "__main__":
    load_all_raw()
