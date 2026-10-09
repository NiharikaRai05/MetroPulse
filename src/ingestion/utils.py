import logging
import os
from pathlib import Path
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("metropulse.ingestion")

def get_data_dir(subdir: str = "") -> Path:
    """Returns absolute path to a data subdirectory inside the project root."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "data" / subdir
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError)),
    reraise=True
)
def download_file(url: str, dest_path: Path, chunk_size: int = 1024 * 1024, force: bool = False) -> Path:
    """
    Downloads a remote file with streaming and exponential backoff retry.
    Ensures raw immutability by skipping download if file exists and has content unless force=True.
    """
    if dest_path.exists() and dest_path.stat().st_size > 0 and not force:
        logger.info(f"File already exists, skipping: {dest_path}")
        return dest_path

    logger.info(f"Downloading from {url} to {dest_path}...")
    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    
    temp_path.replace(dest_path)
    logger.info(f"Successfully downloaded: {dest_path} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")
    return dest_path
