import logging
import sys
from src.ingestion.download_taxi import download_taxi_data
from src.ingestion.download_zones import download_zone_data
from src.ingestion.download_weather import download_weather_data
from src.ingestion.download_mta import download_mta_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("metropulse.ingestion.pipeline")

def run_all(force: bool = False):
    logger.info("=== Starting MetroPulse Ingestion (Day 1) ===")
    
    # 1. TLC Zone Lookup & Shapefile
    logger.info("Step 1/4: TLC Taxi Zones...")
    download_zone_data(force=force)

    # 2. Weather
    logger.info("Step 2/4: Open-Meteo Weather...")
    download_weather_data(force=force)

    # 3. Yellow Taxi
    logger.info("Step 3/4: TLC Yellow Taxi (Q2 2024)...")
    download_taxi_data(force=force)

    # 4. MTA Subway Ridership
    logger.info("Step 4/4: MTA Subway Ridership (Q2 2024)...")
    download_mta_data(force=force)

    logger.info("=== Ingestion Pipeline Completed Successfully ===")

if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    run_all(force=force_flag)
