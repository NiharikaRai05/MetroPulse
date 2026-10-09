import json
import logging
import time
from pathlib import Path
from typing import List, Tuple

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

logger = logging.getLogger("metropulse.ingestion.mta")


def _log_mta_retry(retry_state: RetryCallState):
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    args = retry_state.args
    offset = args[3] if len(args) > 3 else "unknown"
    logger.warning(
        f"[Socrata MTA Retry Attempt {attempt} (offset {offset})] "
        f"Request failed: {type(exc).__name__} - {exc}. Retrying..."
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=3, max=30),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError, TimeoutError)),
    before_sleep=_log_mta_retry,
    reraise=True,
)
def _fetch_socrata_page(
    endpoint: str,
    start_ts: str,
    end_ts: str,
    offset: int,
    limit: int = 50000,
    timeout: int = 60,
) -> List[dict]:
    """
    Queries NY State Socrata endpoint (wujg-7c2s) with SQL $where filter on transit_timestamp
    and deterministic $order for pagination stability.
    """
    params = {
        "$where": f"transit_timestamp >= '{start_ts}' AND transit_timestamp <= '{end_ts}'",
        "$limit": limit,
        "$offset": offset,
        "$order": "transit_timestamp ASC, station_complex_id ASC",
    }
    resp = requests.get(endpoint, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def ingest_mta(force: bool = False, page_limit: int = 50000) -> Tuple[Path, Path]:
    """
    Ingests MTA Subway Hourly Ridership for 2024-04-01 to 2024-06-30
    from NY Open Data Socrata API (wujg-7c2s).
    
    Features:
      - Paginated extraction using $limit and $offset with deterministic ordering
      - Tenacity retry with exponential backoff on network/rate errors
      - Courteous rate-limiting sleep between pages
      - Outputs raw JSON and columnar Parquet
      - Idempotent manifest recording to JSON and DuckDB raw.ingestion_manifest
    """
    config = load_sources_config()
    mta_cfg = config["sources"]["mta_subway_ridership"]
    period_cfg = config["period"]
    
    start_date = period_cfg["start_date"]
    end_date = period_cfg["end_date"]
    source_period = f"{start_date}_to_{end_date}"
    
    start_ts = mta_cfg["filter"]["start_timestamp"]
    end_ts = mta_cfg["filter"]["end_timestamp"]
    endpoint = mta_cfg["api_endpoint"]

    dest_dir = get_data_dir(f"raw/{mta_cfg['dest_subpath']}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = dest_dir / "mta_subway_hourly_2024_q2.json"
    parquet_path = dest_dir / "mta_subway_hourly_2024_q2.parquet"
    
    manifest_mgr = IngestionManifestManager()

    # Idempotent skip check
    if not force and parquet_path.exists() and parquet_path.stat().st_size > 0:
        if manifest_mgr.is_file_already_ingested(parquet_path):
            logger.info("MTA Subway data already ingested and manifest verified. Skipping fetch.")
            return json_path, parquet_path

    logger.info(f"=== Starting MTA Subway Ridership Ingestion ({start_ts} to {end_ts}) ===")

    offset = 0
    all_records = []
    
    while True:
        logger.info(f"Fetching Socrata page at offset {offset:,} (limit {page_limit:,})...")
        records = _fetch_socrata_page(
            endpoint=endpoint,
            start_ts=start_ts,
            end_ts=end_ts,
            offset=offset,
            limit=page_limit,
        )
        
        if not records:
            logger.info("Received empty response. Pagination complete.")
            break
            
        all_records.extend(records)
        logger.info(f"Retrieved {len(records):,} records (Accumulated total: {len(all_records):,})")

        if len(records) < page_limit:
            logger.info("Final page reached.")
            break

        offset += page_limit
        time.sleep(0.2)  # Courteous throttling for public Socrata API

    # 1. Save raw JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f)
    logger.info(f"Saved raw JSON: {json_path.name} ({json_path.stat().st_size / (1024*1024):.2f} MB)")

    # 2. Save structured Parquet
    df = pd.DataFrame(all_records)
    # Ensure numeric columns are cast appropriately if present
    if "ridership" in df.columns:
        df["ridership"] = pd.to_numeric(df["ridership"], errors="coerce")
    if "transit_timestamp" in df.columns:
        df["transit_timestamp"] = pd.to_datetime(df["transit_timestamp"])

    df.to_parquet(parquet_path, index=False)
    logger.info(f"Saved Parquet: {parquet_path.name} ({len(df):,} total records)")

    # 3. Record manifests
    manifest_mgr.record_manifest(
        source_name="mta_subway_ridership_json",
        source_period=source_period,
        url=f"{endpoint}?dataset=wujg-7c2s&start={start_date}&end={end_date}",
        file_path=json_path,
        custom_row_count=len(df),
    )

    manifest_mgr.record_manifest(
        source_name="mta_subway_ridership_parquet",
        source_period=source_period,
        url=f"{endpoint}?dataset=wujg-7c2s&start={start_date}&end={end_date}",
        file_path=parquet_path,
        custom_row_count=len(df),
    )

    logger.info("=== Completed MTA Subway Ridership Ingestion ===")
    return json_path, parquet_path


if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    ingest_mta(force=force_flag)
