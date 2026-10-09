import unittest
import json
import tempfile
from pathlib import Path
import duckdb
import geopandas as gpd
from shapely.geometry import Polygon

from export.export_marts import (
    export_marts_to_parquet,
    export_simplified_zones_geojson,
    create_last_refresh_manifest,
    export_all,
)

class TestExportMarts(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        self.db_path = self.test_dir / "test.duckdb"
        self.out_dir = self.test_dir / "dashboard_data"
        self.shapefile_dir = self.test_dir / "shapefiles"
        self.shapefile_dir.mkdir(parents=True, exist_ok=True)

        # Populate a mock DuckDB with sample mart tables
        self.con = duckdb.connect(str(self.db_path))
        self.con.execute("""
            CREATE TABLE dim_zone AS 
            SELECT 1 AS location_id, 'Manhattan' AS borough, 'Newark' AS zone_name, TRUE AS is_airport_zone;
            
            CREATE TABLE mart_executive AS 
            SELECT '2024-04-01 to 2024-06-30' AS analysis_period, 91 AS active_service_days, 1000 AS total_clean_trips;
            
            CREATE TABLE mart_time AS 
            SELECT TIMESTAMP '2024-04-01 00:00:00' AS hour_timestamp, 50 AS trip_count;
        """)

        # Create mock taxi zone shapefile
        poly1 = Polygon([(-74.01, 40.71), (-74.00, 40.71), (-74.00, 40.72), (-74.01, 40.72), (-74.01, 40.71)])
        gdf = gpd.GeoDataFrame({
            "LocationID": [1],
            "Borough": ["Manhattan"],
            "Zone": ["Newark"],
            "service_zone": ["Airports"],
            "Shape_Leng": [0.04],
            "Shape_Area": [0.0001],
            "geometry": [poly1]
        }, crs="EPSG:4326")
        gdf.to_file(self.shapefile_dir / "taxi_zones.shp")

    def tearDown(self):
        self.con.close()
        self.temp_dir.cleanup()

    def test_parquet_export_and_compression(self):
        metrics = export_marts_to_parquet(
            self.con,
            output_dir=self.out_dir,
            marts=["dim_zone", "mart_executive", "mart_time"],
            compression="zstd"
        )
        self.assertIn("dim_zone", metrics)
        self.assertIn("mart_executive", metrics)
        self.assertIn("mart_time", metrics)
        self.assertTrue((self.out_dir / "dim_zone.parquet").exists())
        self.assertEqual(metrics["dim_zone"]["row_count"], 1)

    def test_geojson_simplification_and_crs(self):
        geojson_path = export_simplified_zones_geojson(
            shapefile_dir=self.shapefile_dir,
            output_dir=self.out_dir,
            tolerance=0.001
        )
        self.assertIsNotNone(geojson_path)
        self.assertTrue(geojson_path.exists())
        
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 1)
        self.assertEqual(data["features"][0]["properties"]["location_id"], 1)

    def test_last_refresh_manifest_generation(self):
        metrics = export_marts_to_parquet(
            self.con,
            output_dir=self.out_dir,
            marts=["dim_zone"],
            compression="zstd"
        )
        geojson_path = export_simplified_zones_geojson(
            shapefile_dir=self.shapefile_dir,
            output_dir=self.out_dir
        )
        manifest_path = create_last_refresh_manifest(
            output_dir=self.out_dir,
            marts_metrics=metrics,
            geojson_path=geojson_path,
            total_pipeline_time_seconds=1.5
        )
        self.assertTrue(manifest_path.exists())
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertIn("build_timestamp_utc", manifest)
        self.assertIn("total_bundle_size_mb", manifest)
        self.assertTrue(manifest["is_under_100mb_limit"])
        self.assertEqual(manifest["total_marts_exported"], 1)
        self.assertEqual(manifest["tables"]["dim_zone"]["row_count"], 1)
        self.assertEqual(manifest["geojson"]["crs"], "EPSG:4326")

    def test_export_all_orchestrator(self):
        res = export_all(
            duckdb_path=self.db_path,
            output_dir=self.out_dir,
            shapefile_dir=self.shapefile_dir
        )
        self.assertTrue(Path(res["manifest_path"]).exists())
        self.assertEqual(res["total_marts"], 3)

if __name__ == "__main__":
    unittest.main()
