import json
import tempfile
import unittest
from pathlib import Path
import duckdb
import pandas as pd

from ingestion.common import (
    IngestionManifestManager,
    compute_schema_fingerprint,
    compute_sha256,
    ingest_file_with_manifest,
)

class TestIngestionCommon(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.duckdb_path = self.base_path / "test.duckdb"
        self.manifest_dir = self.base_path / "manifests"
        self.manager = IngestionManifestManager(
            duckdb_path=self.duckdb_path,
            json_manifest_dir=self.manifest_dir,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compute_sha256_and_fingerprint_csv(self):
        sample_csv = self.base_path / "sample.csv"
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", "B", "C"],
            "value": [10.5, 20.0, 30.2]
        })
        df.to_csv(sample_csv, index=False)

        file_hash = compute_sha256(sample_csv)
        self.assertIsInstance(file_hash, str)
        self.assertEqual(len(file_hash), 64)

        fingerprint = compute_schema_fingerprint(sample_csv)
        self.assertEqual(fingerprint["format"], "csv")
        self.assertEqual(fingerprint["row_count"], 3)
        self.assertEqual(len(fingerprint["schema"]), 3)

    def test_record_manifest_and_skip_duplicate(self):
        sample_parquet = self.base_path / "sample.parquet"
        df = pd.DataFrame({"col1": [100, 200, 300, 400]})
        df.to_parquet(sample_parquet, index=False)

        manifest = self.manager.record_manifest(
            source_name="test_taxi",
            source_period="2024-04",
            url="https://example.com/test.parquet",
            file_path=sample_parquet,
        )

        self.assertEqual(manifest["source_name"], "test_taxi")
        self.assertEqual(manifest["row_count"], 4)

        # Verify DuckDB persistence
        with duckdb.connect(str(self.duckdb_path)) as con:
            rows = con.execute("SELECT * FROM raw.ingestion_manifest").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "test_taxi")
            self.assertEqual(rows[0][5], 4)

        # Check skip logic
        is_ingested = self.manager.is_file_already_ingested(sample_parquet)
        self.assertTrue(is_ingested)

        # Ingest with manifest wrapper (should skip)
        _, res_entry = ingest_file_with_manifest(
            source_name="test_taxi",
            source_period="2024-04",
            url="https://example.com/test.parquet",
            dest_path=sample_parquet,
            manifest_mgr=self.manager,
            force=False,
        )
        self.assertTrue(res_entry.get("skipped", False))

if __name__ == "__main__":
    unittest.main()
