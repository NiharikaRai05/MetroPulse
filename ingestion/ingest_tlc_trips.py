import logging
from pathlib import Path
from typing import List

from ingestion.common import (
    IngestionManifestManager,
    get_data_dir,
    get_project_root,
    ingest_file_with_manifest,
)
from ingestion.utils import load_sources_config

logger = logging.getLogger("metropulse.ingestion.taxi")


def ingest_tlc_trips(force: bool = False) -> List[Path]:
    """
    Ingests official NYC TLC Yellow Taxi Parquet files for Q2 2024 (Apr, May, Jun)
    using config/sources.yml. Computes SHA-256 and records schema fingerprint in
    JSON & DuckDB raw.ingestion_manifest. Skips unchanged files.
    """
    config = load_sources_config()
    taxi_cfg = config["sources"]["tlc_yellow_taxi"]
    dest_dir = get_data_dir(f"raw/{taxi_cfg['dest_subpath']}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_mgr = IngestionManifestManager()
    downloaded_paths = []

    logger.info(f"=== Starting TLC Yellow Taxi Ingestion ({len(taxi_cfg['files'])} months) ===")

    for file_info in taxi_cfg["files"]:
        filename = file_info["filename"]
        url = file_info["url"]
        period = file_info["period"]
        dest_path = dest_dir / filename

        logger.info(f"Processing TLC Trip file: {filename} for period {period}")
        path, manifest_entry = ingest_file_with_manifest(
            source_name="tlc_yellow_taxi",
            source_period=period,
            url=url,
            dest_path=dest_path,
            manifest_mgr=manifest_mgr,
            force=force,
        )
        downloaded_paths.append(path)

    logger.info("=== Completed TLC Yellow Taxi Ingestion ===")
    return downloaded_paths


if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    ingest_tlc_trips(force=force_flag)
