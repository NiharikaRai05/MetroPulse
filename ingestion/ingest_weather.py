import json
import logging
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ingestion.common import (
    IngestionManifestManager,
    compute_schema_fingerprint,
    compute_sha256,
    get_data_dir,
)
from ingestion.utils import load_sources_config

logger = logging.getLogger("metropulse.ingestion.weather")


def _log_weather_retry(retry_state: RetryCallState):
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    logger.warning(
        f"[Open-Meteo Retry Attempt {attempt}] API request failed: {type(exc).__name__} - {exc}. Retrying..."
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1.5, min=2, max=30),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError, TimeoutError)),
    before_sleep=_log_weather_retry,
    reraise=True,
)
def _fetch_open_meteo_archive(
    endpoint: str,
    params: dict,
    timeout: int = 45,
) -> dict:
    """Fetches archive weather data with tenacity retry."""
    logger.info(f"Calling Open-Meteo Archive API: {endpoint} with params {params}")
    resp = requests.get(endpoint, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def ingest_weather(force: bool = False) -> Tuple[Path, Path]:
    """
    Ingests NYC hourly weather data from Open-Meteo Historical Archive API
    for the exact period 2024-04-01 to 2024-06-30.
    
    Hourly variables requested:
      - temperature_2m
      - precipitation
      - rain
      - snowfall
      - wind_speed_10m
      - cloud_cover
      - weather_code
      - timezone: America/New_York
      
    Outputs:
      - raw/weather/weather_nyc_2024_q2.json (immutable raw payload)
      - raw/weather/weather_nyc_2024_q2.parquet (typed columnar format)
      
    Idempotent: Records manifest in JSON and DuckDB raw.ingestion_manifest; skips if already ingested.
    """
    config = load_sources_config()
    weather_cfg = config["sources"]["open_meteo_weather"]
    period_cfg = config["period"]
    
    start_date = period_cfg["start_date"]
    end_date = period_cfg["end_date"]
    timezone = weather_cfg["coordinates"]["timezone"]
    source_period = f"{start_date}_to_{end_date}"
    
    dest_dir = get_data_dir(f"raw/{weather_cfg['dest_subpath']}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = dest_dir / "weather_nyc_2024_q2.json"
    parquet_path = dest_dir / "weather_nyc_2024_q2.parquet"
    
    manifest_mgr = IngestionManifestManager()
    
    # Idempotent skip check
    if not force and parquet_path.exists() and json_path.exists() and parquet_path.stat().st_size > 0:
        if manifest_mgr.is_file_already_ingested(parquet_path):
            logger.info("Open-Meteo Weather data already ingested and manifest verified. Skipping fetch.")
            return json_path, parquet_path

    logger.info(f"=== Starting Open-Meteo Historical Weather Ingestion ({start_date} to {end_date}) ===")

    params = {
        "latitude": weather_cfg["coordinates"]["latitude"],
        "longitude": weather_cfg["coordinates"]["longitude"],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(weather_cfg["hourly_variables"]),
        "timezone": timezone,
    }

    raw_data = _fetch_open_meteo_archive(weather_cfg["api_endpoint"], params)

    # 1. Save raw immutable JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2)
    logger.info(f"Saved raw JSON payload: {json_path.name} ({json_path.stat().st_size / 1024:.1f} KB)")

    # 2. Convert to Parquet with standardized columns
    hourly_dict = raw_data.get("hourly", {})
    df = pd.DataFrame(hourly_dict)
    
    # Standardize timestamp
    df["time"] = pd.to_datetime(df["time"])
    df.to_parquet(parquet_path, index=False)
    logger.info(f"Saved Parquet: {parquet_path.name} ({len(df):,} hourly records)")

    # 3. Record manifests for both JSON and Parquet
    manifest_mgr.record_manifest(
        source_name="open_meteo_weather_json",
        source_period=source_period,
        url=f"{weather_cfg['api_endpoint']}?start={start_date}&end={end_date}",
        file_path=json_path,
        custom_row_count=len(df),
    )
    
    manifest_mgr.record_manifest(
        source_name="open_meteo_weather_parquet",
        source_period=source_period,
        url=f"{weather_cfg['api_endpoint']}?start={start_date}&end={end_date}",
        file_path=parquet_path,
        custom_row_count=len(df),
    )

    logger.info("=== Completed Open-Meteo Weather Ingestion ===")
    return json_path, parquet_path


if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    ingest_weather(force=force_flag)
