import logging
import zipfile
from pathlib import Path
from typing import Tuple

from ingestion.common import (
    IngestionManifestManager,
    get_data_dir,
    ingest_file_with_manifest,
)
from ingestion.utils import load_sources_config

logger = logging.getLogger("metropulse.ingestion.zones")


def ingest_tlc_zones(force: bool = False) -> Tuple[Path, Path, Path]:
    """
    Ingests official NYC TLC Taxi Zone Lookup CSV and Taxi Zones Shapefile ZIP
    from config/sources.yml. Computes SHA-256 and schema fingerprint,
    extracts the shapefile components, and logs to JSON & DuckDB manifest.
    """
    config = load_sources_config()
    period = f"{config['period']['start_date']}_to_{config['period']['end_date']}"
    lookup_cfg = config["sources"]["tlc_zone_lookup"]
    shape_cfg = config["sources"]["tlc_zone_shapefile"]

    dest_dir = get_data_dir("raw/zones")
    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest_mgr = IngestionManifestManager()

    logger.info("=== Starting TLC Taxi Zones Ingestion ===")

    # 1. Download Lookup CSV
    csv_path = dest_dir / lookup_cfg["dest_filename"]
    csv_file, _ = ingest_file_with_manifest(
        source_name="tlc_zone_lookup",
        source_period=period,
        url=lookup_cfg["url"],
        dest_path=csv_path,
        manifest_mgr=manifest_mgr,
        force=force,
    )

    # 2. Download Shapefile ZIP
    zip_path = dest_dir / shape_cfg["dest_filename"]
    zip_file, _ = ingest_file_with_manifest(
        source_name="tlc_zone_shapefile",
        source_period=period,
        url=shape_cfg["url"],
        dest_path=zip_path,
        manifest_mgr=manifest_mgr,
        force=force,
    )

    # 3. Extract Shapefile contents
    extract_dir = dest_dir / "shapefile"
    if not extract_dir.exists() or force or not any(extract_dir.iterdir()):
        extract_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Extracting {zip_path.name} to {extract_dir}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        logger.info(f"Extracted shapefiles: {[f.name for f in extract_dir.iterdir()]}")
    else:
        logger.info(f"Extracted shapefiles already present in {extract_dir}")

    logger.info("=== Completed TLC Taxi Zones Ingestion ===")
    return csv_file, zip_file, extract_dir


if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    ingest_tlc_zones(force=force_flag)
