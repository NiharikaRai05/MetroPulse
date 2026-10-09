import unittest
from pathlib import Path

class TestDbtMartsModels(unittest.TestCase):
    def test_marts_files_exist(self):
        marts_dir = Path("dbt_project/models/marts")
        expected_models = [
            "fct_trips.sql",
            "dim_zone.sql",
            "dim_date.sql",
            "dim_hour.sql",
            "dim_payment.sql",
            "dim_rate.sql",
            "dim_weather.sql",
            "reconcile_trip_lineage.sql",
        ]
        for m in expected_models:
            self.assertTrue((marts_dir / m).exists(), f"Marts model {m} must exist")

    def test_dim_zone_has_spatial_deduplication(self):
        sql = Path("dbt_project/models/marts/dim_zone.sql").read_text(encoding="utf-8")
        self.assertIn("PARTITION BY location_id", sql)
        self.assertIn("geo_rank = 1", sql)
        self.assertIn("is_congestion_zone", sql)
        self.assertIn("is_airport_zone", sql)

    def test_dim_date_has_calendar_and_holidays(self):
        sql = Path("dbt_project/models/marts/dim_date.sql").read_text(encoding="utf-8")
        self.assertIn("2024-04-01", sql)
        self.assertIn("2024-06-30", sql)
        self.assertIn("Memorial Day", sql)
        self.assertIn("Juneteenth", sql)
        self.assertIn("is_weekend", sql)

    def test_reconcile_lineage_has_balance_assertion(self):
        sql = Path("dbt_project/models/marts/reconcile_trip_lineage.sql").read_text(encoding="utf-8")
        self.assertIn("BALANCED_PERFECT", sql)
        self.assertIn("reconciliation_delta", sql)
        self.assertIn("r.raw_trips_count - r.total_excluded_rows", sql)

    def test_fct_trips_has_surrogate_key_and_metrics(self):
        sql = Path("dbt_project/models/marts/fct_trips.sql").read_text(encoding="utf-8")
        self.assertIn("trip_id", sql)
        self.assertIn("pickup_location_id", sql)
        self.assertIn("dropoff_location_id", sql)
        self.assertIn("pickup_date_key", sql)
        self.assertIn("fare_amount", sql)
        self.assertIn("total_amount", sql)
        self.assertIn("tip_percentage", sql)

if __name__ == "__main__":
    unittest.main()
