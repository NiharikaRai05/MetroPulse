import logging
import zipfile
from pathlib import Path
from src.ingestion.utils import download_file, get_data_dir

logger = logging.getLogger("metropulse.ingestion.zones")

ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
ZONE_SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"

def download_zone_data(force: bool = False):
    """
    Downloads TLC Zone lookup CSV and Shapefile zip.
    Extracts shapefiles into data/raw/zones/shapefile/
    """
    dest_dir = get_data_dir("raw/zones")
    
    # 1. Download Lookup CSV
    csv_path = dest_dir / "taxi_zone_lookup.csv"
    download_file(ZONE_LOOKUP_URL, csv_path, force=force)
    
    # 2. Download Shapefile ZIP
    zip_path = dest_dir / "taxi_zones.zip"
    download_file(ZONE_SHAPEFILE_URL, zip_path, force=force)
    
    # Extract Shapefile
    extract_dir = dest_dir / "shapefile"
    if not extract_dir.exists() or force:
        extract_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Extracting {zip_path} to {extract_dir}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        logger.info("Extraction complete.")

if __name__ == "__main__":
    download_zone_data()
