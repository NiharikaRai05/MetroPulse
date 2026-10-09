import logging
from pathlib import Path
import yaml
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("metropulse.ingestion")

def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def load_sources_config() -> dict:
    config_path = get_project_root() / "config" / "sources.yml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_data_dir(subpath: str = "") -> Path:
    base = get_project_root() / "data" / subpath
    base.mkdir(parents=True, exist_ok=True)
    return base

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError)),
    reraise=True
)
def download_file(url: str, dest_path: Path, chunk_size: int = 1024 * 1024, force: bool = False) -> Path:
    """
    Downloads remote file with stream chunking and exponential backoff retry.
    Raw layer is immutable: skips download if file already exists with non-zero size.
    """
    if dest_path.exists() and dest_path.stat().st_size > 0 and not force:
        logger.info(f"Immutable raw file exists, skipping: {dest_path.name}")
        return dest_path

    logger.info(f"Downloading {url} -> {dest_path}...")
    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    
    with requests.get(url, stream=True, timeout=90) as resp:
        resp.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    
    temp_path.replace(dest_path)
    logger.info(f"Completed download: {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")
    return dest_path
