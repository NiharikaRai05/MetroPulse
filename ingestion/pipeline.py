import logging
import sys
from ingestion.common import get_project_root
from ingestion.ingest_tlc_zones import ingest_tlc_zones
from ingestion.ingest_tlc_trips import ingest_tlc_trips
from ingestion.ingest_weather import ingest_weather
from ingestion.ingest_mta import ingest_mta
from ingestion.load_raw import load_all_raw
from ingestion.utils import load_sources_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("metropulse.ingestion.pipeline")


def run_pipeline(force: bool = False):
    config = load_sources_config()
    start_date = config["period"]["start_date"]
    end_date = config["period"]["end_date"]
    logger.info(f"=== Running MetroPulse Day 1 Ingestion Pipeline ({start_date} to {end_date}) ===")

    # 1. TLC Taxi Zones (Lookup CSV + Shapefile)
    logger.info("--- [1/4] Ingesting TLC Zones ---")
    ingest_tlc_zones(force=force)

    # 2. Open-Meteo Weather (Hourly Q2 2024)
    logger.info("--- [2/4] Ingesting Open-Meteo Weather ---")
    ingest_weather(force=force)

    # 3. MTA Subway Hourly Ridership (Socrata wujg-7c2s)
    logger.info("--- [3/4] Ingesting MTA Subway Hourly Ridership ---")
    ingest_mta(force=force)

    # 4. TLC Yellow Taxi Trips (Parquet Apr/May/Jun 2024)
    logger.info("--- [4/4] Ingesting TLC Yellow Taxi Trips ---")
    ingest_tlc_trips(force=force)

    # 5. Load raw data into DuckDB raw.* schema idempotently
    logger.info("--- [5/5] Loading Raw Data into DuckDB raw.* ---")
    load_all_raw()

    logger.info("=== Full Day 1 Ingestion Pipeline Successfully Executed! ===")


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    run_pipeline(force=force_flag)
