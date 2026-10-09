import unittest
from pathlib import Path

class TestHourlyDemandModels(unittest.TestCase):
    def test_hourly_models_exist(self):
        int_dir = Path("dbt_project/models/intermediate")
        expected = ["int_weather_hourly.sql", "int_subway_hourly.sql", "int_hourly_demand.sql"]
        for f in expected:
            self.assertTrue((int_dir / f).exists(), f"Model {f} must exist")

    def test_int_weather_hourly_grain(self):
        sql = Path("dbt_project/models/intermediate/int_weather_hourly.sql").read_text(encoding="utf-8")
        self.assertIn("GROUP BY observation_hour", sql)
        self.assertIn("avg_temperature_celsius", sql)
        self.assertIn("max_precipitation_mm", sql)
        self.assertIn("is_raining", sql)

    def test_int_subway_hourly_borough_breakdown(self):
        sql = Path("dbt_project/models/intermediate/int_subway_hourly.sql").read_text(encoding="utf-8")
        self.assertIn("GROUP BY transit_hour", sql)
        self.assertIn("total_subway_ridership", sql)
        self.assertIn("subway_ridership_manhattan", sql)
        self.assertIn("subway_ridership_brooklyn", sql)

    def test_int_hourly_demand_lag_features(self):
        sql = Path("dbt_project/models/intermediate/int_hourly_demand.sql").read_text(encoding="utf-8")
        self.assertIn("LAG(taxi_trip_count, 1)", sql)
        self.assertIn("LAG(taxi_trip_count, 2)", sql)
        self.assertIn("LAG(total_subway_ridership, 1)", sql)
        self.assertIn("LAG(total_subway_ridership, 2)", sql)
        self.assertIn("LAG(precipitation_mm, 1)", sql)
        self.assertIn("LAG(precipitation_mm, 2)", sql)
        self.assertIn("taxi_demand_pct_change_1h", sql)

if __name__ == "__main__":
    unittest.main()
