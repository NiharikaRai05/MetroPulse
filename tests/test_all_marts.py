import unittest
from pathlib import Path

class TestAllDbtMarts(unittest.TestCase):
    def test_all_marts_files_exist(self):
        marts_dir = Path("dbt_project/models/marts")
        expected_marts = [
            "mart_executive.sql",
            "mart_zone.sql",
            "mart_time.sql",
            "mart_weather.sql",
            "mart_transit.sql",
            "mart_quality.sql",
            "mart_route_pairs.sql",
            "mart_cube.sql",
        ]
        for m in expected_marts:
            self.assertTrue((marts_dir / m).exists(), f"Marts model {m} must exist")

    def test_mart_zone_has_underserved_indicator(self):
        sql = Path("dbt_project/models/marts/mart_zone.sql").read_text(encoding="utf-8")
        self.assertIn("is_underserved", sql)
        self.assertIn("pickup_trip_count", sql)
        self.assertIn("dropoff_trip_count", sql)

    def test_mart_cube_purely_additive_and_weather_joined(self):
        sql = Path("dbt_project/models/marts/mart_cube.sql").read_text(encoding="utf-8")
        self.assertIn("date_day", sql)
        self.assertIn("hour_of_day", sql)
        self.assertIn("pickup_borough", sql)
        self.assertIn("dropoff_borough", sql)
        self.assertIn("is_airport_trip", sql)
        self.assertIn("SUM(t.total_amount)", sql)
        self.assertIn("weather_precipitation_mm", sql)
        # Verify query body contains SUM and COUNT aggregations
        self.assertIn("COUNT(*)", sql)
        self.assertIn("SUM(t.fare_amount)", sql)

    def test_mart_route_pairs_matrix(self):
        sql = Path("dbt_project/models/marts/mart_route_pairs.sql").read_text(encoding="utf-8")
        self.assertIn("pickup_location_id", sql)
        self.assertIn("dropoff_location_id", sql)
        self.assertIn("route_flow_type", sql)
        self.assertIn("is_airport_corridor", sql)

if __name__ == "__main__":
    unittest.main()
