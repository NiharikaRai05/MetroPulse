import unittest
from pathlib import Path

class TestDbtStagingModels(unittest.TestCase):
    def test_staging_model_files_exist(self):
        staging_dir = Path("dbt_project/models/staging")
        expected_files = [
            "sources.yml",
            "stg_trips.sql",
            "stg_zones.sql",
            "stg_zone_geo.sql",
            "stg_weather.sql",
            "stg_subway.sql",
        ]
        for f in expected_files:
            file_path = staging_dir / f
            self.assertTrue(file_path.exists(), f"Staging file {f} must exist")

    def test_stg_trips_has_surrogate_key_and_no_row_filtering(self):
        sql = Path("dbt_project/models/staging/stg_trips.sql").read_text(encoding="utf-8")
        self.assertIn("md5(", sql)
        self.assertIn("AS trip_id", sql)
        self.assertNotIn("WHERE ", sql)  # No rows removed in staging

    def test_stg_weather_has_all_hourly_variables(self):
        sql = Path("dbt_project/models/staging/stg_weather.sql").read_text(encoding="utf-8")
        self.assertIn("temperature_celsius", sql)
        self.assertIn("precipitation_mm", sql)
        self.assertIn("rain_mm", sql)
        self.assertIn("snowfall_cm", sql)
        self.assertIn("wind_speed_kmh", sql)
        self.assertIn("cloud_cover_pct", sql)
        self.assertIn("weather_code", sql)
        self.assertNotIn("WHERE ", sql)

    def test_stg_subway_has_station_and_ridership(self):
        sql = Path("dbt_project/models/staging/stg_subway.sql").read_text(encoding="utf-8")
        self.assertIn("station_complex_id", sql)
        self.assertIn("ridership", sql)
        self.assertNotIn("WHERE ", sql)

if __name__ == "__main__":
    unittest.main()
