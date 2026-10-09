import unittest
from pathlib import Path
import yaml

class TestScaffold(unittest.TestCase):
    def test_sources_yaml_exists(self):
        sources_file = Path("config/sources.yml")
        self.assertTrue(sources_file.exists(), "config/sources.yml must exist")

    def test_sources_content(self):
        with open("config/sources.yml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        self.assertEqual(cfg["period"]["start_date"], "2024-04-01")
        self.assertEqual(cfg["period"]["end_date"], "2024-06-30")
        self.assertIn("tlc_yellow_taxi", cfg["sources"])
        self.assertIn("open_meteo_weather", cfg["sources"])
        self.assertIn("mta_subway_ridership", cfg["sources"])
        self.assertEqual(len(cfg["sources"]["tlc_yellow_taxi"]["files"]), 3)

        # Weather variables check
        expected_weather_vars = [
            "temperature_2m",
            "precipitation",
            "rain",
            "snowfall",
            "wind_speed_10m",
            "cloud_cover",
            "weather_code",
        ]
        actual_weather_vars = cfg["sources"]["open_meteo_weather"]["hourly_variables"]
        for v in expected_weather_vars:
            self.assertIn(v, actual_weather_vars)

    def test_directory_structure(self):
        required_dirs = [
            "ingestion",
            "dbt_project",
            "analysis",
            "export",
            "dashboard",
            "docs",
            "tests",
            "config",
            "data/raw",
            "data/samples",
            "data/manifests",
            ".github/workflows",
        ]
        for d in required_dirs:
            p = Path(d)
            self.assertTrue(p.exists(), f"Directory {d} must exist")

    def test_ingestion_scripts_exist(self):
        required_scripts = [
            "ingestion/common.py",
            "ingestion/ingest_tlc_trips.py",
            "ingestion/ingest_tlc_zones.py",
            "ingestion/ingest_weather.py",
            "ingestion/ingest_mta.py",
            "ingestion/load_raw.py",
            "ingestion/pipeline.py",
        ]
        for s in required_scripts:
            p = Path(s)
            self.assertTrue(p.exists(), f"Script {s} must exist")

if __name__ == "__main__":
    unittest.main()
