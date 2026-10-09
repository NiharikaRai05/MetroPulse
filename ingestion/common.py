import datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import duckdb
import pandas as pd
import pyarrow.parquet as pq
import requests
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("metropulse.ingestion.common")


def get_project_root() -> Path:
    """Returns absolute path to repository root."""
    return Path(__file__).resolve().parent.parent


def get_data_dir(subpath: str = "") -> Path:
    """Returns absolute path to data subdirectory, creating it if missing."""
    p = get_project_root() / "data" / subpath
    p.mkdir(parents=True, exist_ok=True)
    return p


def compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Computes SHA-256 hex digest of a local file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_schema_fingerprint(file_path: Path) -> Dict[str, Any]:
    """
    Computes schema metadata and row count for parquet, csv, or json files.
    Returns dictionary with:
      - schema: list of column definitions {name: type}
      - row_count: integer count of records
      - format: string format
    """
    suffix = file_path.suffix.lower()
    
    if suffix == ".parquet":
        parquet_file = pq.ParquetFile(file_path)
        schema = [
            {"name": field.name, "type": str(field.type)}
            for field in parquet_file.schema_arrow
        ]
        row_count = parquet_file.metadata.num_rows
        return {"format": "parquet", "schema": schema, "row_count": row_count}
    
    elif suffix == ".csv":
        df_sample = pd.read_csv(file_path, nrows=100)
        schema = [{"name": col, "type": str(dtype)} for col, dtype in df_sample.dtypes.items()]
        # Fast line count for CSV
        with open(file_path, "rb") as f:
            row_count = sum(1 for _ in f) - 1  # exclude header
        return {"format": "csv", "schema": schema, "row_count": max(0, row_count)}
        
    elif suffix == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            row_count = len(data)
            sample = data[0] if data else {}
            schema = [{"name": k, "type": type(v).__name__} for k, v in sample.items()]
        elif isinstance(data, dict):
            # If weather dict with 'hourly'
            if "hourly" in data and isinstance(data["hourly"], dict):
                first_key = next(iter(data["hourly"]), None)
                row_count = len(data["hourly"][first_key]) if first_key else 1
                schema = [{"name": k, "type": "list"} for k in data["hourly"].keys()]
            else:
                row_count = 1
                schema = [{"name": k, "type": type(v).__name__} for k, v in data.items()]
        else:
            row_count = 1
            schema = []
        return {"format": "json", "schema": schema, "row_count": row_count}
        
    elif suffix == ".zip":
        return {"format": "zip", "schema": [], "row_count": 0}
        
    return {"format": suffix.lstrip("."), "schema": [], "row_count": 0}


def _log_retry_failure(retry_state: RetryCallState):
    """Custom tenacity callback providing clear diagnostic messages on failure."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    args = retry_state.args
    url = args[0] if args else "unknown URL"
    logger.warning(
        f"[Retry Attempt {attempt}] Failed fetching {url}. "
        f"Reason: {type(exc).__name__} - {exc}. Retrying..."
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1.5, min=2, max=30),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError, TimeoutError)),
    before_sleep=_log_retry_failure,
    reraise=True,
)
def download_stream(
    url: str,
    dest_path: Path,
    chunk_size: int = 1024 * 1024,
    timeout: int = 90
) -> Path:
    """
    Resilient streaming download with chunking and exponential backoff retry.
    Writes first to a .tmp file and replaces atomically upon complete stream.
    """
    logger.info(f"Downloading stream: {url} -> {dest_path.name}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")

    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
        temp_path.replace(dest_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Download failed definitively for {url}: {e}")
        raise e

    return dest_path


class IngestionManifestManager:
    """
    Manages raw ingestion manifest across both JSON files and DuckDB raw.ingestion_manifest.
    Provides SHA-256 duplicate verification to skip downloads when hash matches.
    """

    def __init__(
        self,
        duckdb_path: Optional[Union[str, Path]] = None,
        json_manifest_dir: Optional[Union[str, Path]] = None,
    ):
        if duckdb_path is None:
            duckdb_path = get_data_dir() / "metropulse.duckdb"
        if json_manifest_dir is None:
            json_manifest_dir = get_data_dir("manifests")

        self.duckdb_path = Path(duckdb_path)
        self.json_manifest_dir = Path(json_manifest_dir)
        self.json_manifest_dir.mkdir(parents=True, exist_ok=True)
        self._init_duckdb_schema()

    def _init_duckdb_schema(self):
        """Initializes raw schema and raw.ingestion_manifest table in DuckDB."""
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(self.duckdb_path)) as con:
            con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS raw.ingestion_manifest (
                    source_name VARCHAR,
                    source_period VARCHAR,
                    url VARCHAR,
                    file_path VARCHAR,
                    file_hash_sha256 VARCHAR,
                    row_count BIGINT,
                    schema_fingerprint JSON,
                    file_size_bytes BIGINT,
                    extracted_at TIMESTAMP,
                    PRIMARY KEY (url, source_period)
                );
                """
            )

    def is_file_already_ingested(
        self,
        file_path: Path,
        expected_hash: Optional[str] = None
    ) -> bool:
        """
        Checks if the file exists locally and matches the recorded hash.
        If expected_hash is not provided, computes the current hash and checks DuckDB.
        """
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False

        current_hash = expected_hash or compute_sha256(file_path)

        with duckdb.connect(str(self.duckdb_path)) as con:
            res = con.execute(
                """
                SELECT COUNT(*) FROM raw.ingestion_manifest 
                WHERE file_hash_sha256 = ? AND file_path = ?
                """,
                [current_hash, str(file_path.resolve())],
            ).fetchone()
            return bool(res and res[0] > 0)

    def record_manifest(
        self,
        source_name: str,
        source_period: str,
        url: str,
        file_path: Path,
        custom_row_count: Optional[int] = None,
        custom_schema: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Calculates SHA-256, extracts schema fingerprint and row count,
        and writes the entry to both a local JSON manifest and raw.ingestion_manifest in DuckDB.
        """
        file_path = file_path.resolve()
        file_hash = compute_sha256(file_path)
        file_size = file_path.stat().st_size
        extracted_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        fingerprint = compute_schema_fingerprint(file_path)
        row_count = custom_row_count if custom_row_count is not None else fingerprint["row_count"]
        schema = custom_schema if custom_schema is not None else fingerprint["schema"]

        manifest_entry = {
            "source_name": source_name,
            "source_period": source_period,
            "url": url,
            "file_path": str(file_path),
            "file_hash_sha256": file_hash,
            "row_count": row_count,
            "schema_fingerprint": schema,
            "file_size_bytes": file_size,
            "extracted_at": extracted_at,
        }

        # 1. Write individual JSON manifest
        json_filename = f"{source_name}_{source_period.replace('-', '_')}_manifest.json"
        json_path = self.json_manifest_dir / json_filename
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(manifest_entry, f, indent=2)

        # 2. Write to DuckDB raw.ingestion_manifest table (UPSERT)
        with duckdb.connect(str(self.duckdb_path)) as con:
            schema_json_str = json.dumps(schema)
            con.execute(
                """
                INSERT OR REPLACE INTO raw.ingestion_manifest (
                    source_name,
                    source_period,
                    url,
                    file_path,
                    file_hash_sha256,
                    row_count,
                    schema_fingerprint,
                    file_size_bytes,
                    extracted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?::JSON, ?, ?::TIMESTAMP);
                """,
                [
                    source_name,
                    source_period,
                    url,
                    str(file_path),
                    file_hash,
                    row_count,
                    schema_json_str,
                    file_size,
                    extracted_at,
                ],
            )

        logger.info(
            f"Recorded manifest for {source_name} ({source_period}): "
            f"{row_count:,} rows, SHA256={file_hash[:10]}..."
        )
        return manifest_entry


def ingest_file_with_manifest(
    source_name: str,
    source_period: str,
    url: str,
    dest_path: Path,
    manifest_mgr: Optional[IngestionManifestManager] = None,
    force: bool = False,
    custom_row_count: Optional[int] = None,
    custom_schema: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """
    Full ingestion workflow with deduplication check:
    1. Check if file exists and hash is already recorded in manifest (skip if yes).
    2. Download stream with tenacity retries.
    3. Compute SHA-256 and schema fingerprint.
    4. Write manifest to JSON and DuckDB raw.ingestion_manifest.
    """
    if manifest_mgr is None:
        manifest_mgr = IngestionManifestManager()

    if not force and dest_path.exists() and dest_path.stat().st_size > 0:
        if manifest_mgr.is_file_already_ingested(dest_path):
            logger.info(f"File {dest_path.name} already ingested and hash verified. Skipping download.")
            current_hash = compute_sha256(dest_path)
            fingerprint = compute_schema_fingerprint(dest_path)
            entry = {
                "source_name": source_name,
                "source_period": source_period,
                "url": url,
                "file_path": str(dest_path.resolve()),
                "file_hash_sha256": current_hash,
                "row_count": fingerprint["row_count"],
                "schema_fingerprint": fingerprint["schema"],
                "file_size_bytes": dest_path.stat().st_size,
                "extracted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "skipped": True,
            }
            return dest_path, entry

    # Download
    downloaded_path = download_stream(url=url, dest_path=dest_path)

    # Record manifest
    manifest_entry = manifest_mgr.record_manifest(
        source_name=source_name,
        source_period=source_period,
        url=url,
        file_path=downloaded_path,
        custom_row_count=custom_row_count,
        custom_schema=custom_schema,
    )

    return downloaded_path, manifest_entry
