import logging
import json
import time
from pathlib import Path
import requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.ingestion.utils import get_data_dir

logger = logging.getLogger("metropulse.ingestion.mta")

# Socrata endpoint for MTA Subway Hourly Ridership
# Dataset identifier: wujg-7c2s
SOCRATA_ENDPOINT = "https://data.ny.gov/resource/wujg-7c2s.json"
START_TS = "2024-04-01T00:00:00.000"
END_TS = "2024-06-30T23:59:59.999"

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=3, max=30),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError)),
    reraise=True
)
def fetch_mta_page(offset: int, limit: int = 50000) -> list[dict]:
    query_params = {
        "$where": f"transit_timestamp >= '{START_TS}' AND transit_timestamp <= '{END_TS}'",
        "$limit": limit,
        "$offset": offset,
        "$order": "transit_timestamp ASC, station_complex_id ASC"
    }
    resp = requests.get(SOCRATA_ENDPOINT, params=query_params, timeout=60)
    resp.raise_for_status()
    return resp.json()

def download_mta_data(force: bool = False) -> Path:
    """
    Downloads MTA Subway Hourly Ridership records for Q2 2024 via Socrata SQL pagination.
    Saves raw partitioned parquet locally.
    """
    dest_dir = get_data_dir("raw/mta")
    parquet_path = dest_dir / "mta_subway_hourly_2024_q2.parquet"

    if parquet_path.exists() and not force:
        logger.info(f"MTA parquet already exists: {parquet_path}")
        return parquet_path

    limit = 50000
    offset = 0
    all_records = []
    
    logger.info(f"Starting MTA Subway Ridership extraction ({START_TS} to {END_TS})...")
    
    while True:
        logger.info(f"Fetching MTA records offset={offset}, limit={limit}...")
        records = fetch_mta_page(offset, limit)
        if not records:
            break
        all_records.extend(records)
        logger.info(f"Retrieved {len(records)} records (Total accumulated: {len(all_records)})")
        if len(records) < limit:
            break
        offset += limit
        time.sleep(0.2)  # courteous throttling for Socrata free tier

    df = pd.DataFrame(all_records)
    logger.info(f"Total MTA records fetched: {len(df)}. Saving to {parquet_path}...")
    df.to_parquet(parquet_path, index=False)
    logger.info("MTA Subway ingestion complete.")
    return parquet_path

if __name__ == "__main__":
    download_mta_data()
