import logging
from pathlib import Path
from src.ingestion.utils import download_file, get_data_dir

logger = logging.getLogger("metropulse.ingestion.taxi")

TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
MONTHS = ["2024-04", "2024-05", "2024-06"]

def download_taxi_data(force: bool = False) -> list[Path]:
    """
    Downloads Yellow Taxi Parquet files for Q2 2024 (Apr, May, Jun).
    Zero sampling - downloads all records.
    """
    dest_dir = get_data_dir("raw/taxi")
    downloaded_files = []
    
    for month in MONTHS:
        filename = f"yellow_tripdata_{month}.parquet"
        url = f"{TLC_BASE_URL}/{filename}"
        dest_path = dest_dir / filename
        file_path = download_file(url, dest_path, force=force)
        downloaded_files.append(file_path)
        
    return downloaded_files

if __name__ == "__main__":
    download_taxi_data()
