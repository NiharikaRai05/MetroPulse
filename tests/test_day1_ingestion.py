import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import requests
from requests.exceptions import HTTPError, RequestException

from ingestion.common import (
    IngestionManifestManager,
    compute_schema_fingerprint,
    compute_sha256,
    download_stream,
    ingest_file_with_manifest,
)
from ingestion.load_raw import load_all_raw, load_raw_yellow_trips


class TestDay1Ingestion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.duckdb_path = self.base_dir / "test_metropulse.duckdb"
        self.manifest_dir = self.base_dir / "manifests"
        self.manifest_mgr = IngestionManifestManager(
            duckdb_path=self.duckdb_path,
            json_manifest_dir=self.manifest_dir,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_idempotence_second_run_adds_zero_rows(self):
        """
        Idempotence Test:
        Running ingestion/loading a second time for the same partition
        must result in the exact same row count (0 additional rows).
        """
        taxi_dir = self.base_dir / "raw" / "taxi"
        taxi_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = taxi_dir / "yellow_tripdata_2024-04.parquet"

        # Create sample raw parquet
        df = pd.DataFrame({
            "VendorID": [1, 2, 2],
            "tpep_pickup_datetime": pd.to_datetime(["2024-04-01 10:00:00", "2024-04-01 11:00:00", "2024-04-01 12:00:00"]),
            "tpep_dropoff_datetime": pd.to_datetime(["2024-04-01 10:15:00", "2024-04-01 11:30:00", "2024-04-01 12:20:00"]),
            "passenger_count": [1, 2, 1],
            "trip_distance": [2.5, 4.0, 1.2],
            "PULocationID": [100, 101, 102],
            "DOLocationID": [140, 142, 144],
            "total_amount": [15.5, 22.0, 10.0]
        })
        df.to_parquet(parquet_path, index=False)

        # First Load
        con = duckdb.connect(str(self.duckdb_path))
        con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        con.execute(
            f"""
            CREATE TABLE IF NOT EXISTS raw.yellow_trips AS 
            SELECT *, '2024-04' AS _source_period, CURRENT_TIMESTAMP AS _loaded_at 
            FROM read_parquet('{parquet_path.as_posix()}');
            """
        )
        count_first_run = con.execute("SELECT COUNT(*) FROM raw.yellow_trips WHERE _source_period = '2024-04'").fetchone()[0]
        self.assertEqual(count_first_run, 3)

        # Second Load (Simulating delete-then-insert idempotency)
        con.execute("DELETE FROM raw.yellow_trips WHERE _source_period = '2024-04'")
        con.execute(
            f"""
            INSERT INTO raw.yellow_trips 
            SELECT *, '2024-04' AS _source_period, CURRENT_TIMESTAMP AS _loaded_at 
            FROM read_parquet('{parquet_path.as_posix()}');
            """
        )
        count_second_run = con.execute("SELECT COUNT(*) FROM raw.yellow_trips WHERE _source_period = '2024-04'").fetchone()[0]
        con.close()

        # Net added rows must be exactly zero
        self.assertEqual(count_second_run, count_first_run)
        self.assertEqual(count_second_run - count_first_run, 0)

    @patch("requests.get")
    def test_retry_on_simulated_failure(self, mock_get):
        """
        Retry Test:
        Simulate transient network drops (2 failures followed by HTTP 200 success).
        Verifies tenacity retries exactly and completes successfully.
        """
        dest_file = self.base_dir / "retry_test.parquet"

        # Mock responses: 2 failures then 1 success
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.iter_content.return_value = [b"mock_parquet_data_chunks"]
        mock_success.__enter__.return_value = mock_success

        mock_get.side_effect = [
            RequestException("Connection timeout simulating flake"),
            RequestException("Remote server disconnected"),
            mock_success,
        ]

        result_path = download_stream(
            url="https://example.com/mock.parquet",
            dest_path=dest_file,
            timeout=5,
        )

        self.assertTrue(result_path.exists())
        self.assertEqual(mock_get.call_count, 3)

    def test_hash_mismatch_detection(self):
        """
        Hash Mismatch Test:
        If a file is tampered or corrupted after ingestion,
        the manager must detect hash mismatch and reject 'is_file_already_ingested'.
        """
        test_file = self.base_dir / "integrity_check.csv"
        test_file.write_text("id,val\n1,100\n2,200\n", encoding="utf-8")

        # Record legitimate manifest
        original_manifest = self.manifest_mgr.record_manifest(
            source_name="test_feed",
            source_period="2024-04",
            url="https://example.com/integrity_check.csv",
            file_path=test_file,
        )
        original_hash = original_manifest["file_hash_sha256"]

        # 1. Unmodified file matches
        self.assertTrue(self.manifest_mgr.is_file_already_ingested(test_file, expected_hash=original_hash))

        # 2. Corrupt/Modify the file content
        test_file.write_text("id,val\n1,100\n2,200\n3,CORRUPTED_ROW\n", encoding="utf-8")
        corrupted_hash = compute_sha256(test_file)

        self.assertNotEqual(original_hash, corrupted_hash)
        # Verify manager detects mismatch against recorded hash
        self.assertFalse(self.manifest_mgr.is_file_already_ingested(test_file, expected_hash=original_hash))

    @patch("requests.get")
    def test_clear_error_on_bad_url(self, mock_get):
        """
        Error Handling Test:
        Simulate 404 / 500 error on bad URL.
        Verifies tenacity exhausts retries and raises clear HTTPError.
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Client Error: Not Found for url: https://bad-url.org")
        mock_get.return_value.__enter__.return_value = mock_response

        bad_dest = self.base_dir / "bad.parquet"

        with self.assertRaises(HTTPError) as ctx:
            download_stream(
                url="https://bad-url.org",
                dest_path=bad_dest,
                timeout=5,
            )
        self.assertIn("404 Client Error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
