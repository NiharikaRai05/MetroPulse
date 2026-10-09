import unittest
from pathlib import Path
import yaml

class TestDbtIntermediateCleaning(unittest.TestCase):
    def test_thresholds_yaml_exists(self):
        p = Path("config/thresholds.yml")
        self.assertTrue(p.exists())
        with open(p, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.assertEqual(cfg["thresholds"]["duration"]["min_seconds"], 60)
        self.assertEqual(cfg["thresholds"]["speed"]["max_mph"], 85.0)

    def test_intermediate_models_exist(self):
        int_dir = Path("dbt_project/models/intermediate")
        expected = ["int_trips_flagged.sql", "int_trips_clean.sql", "int_trips_rule_impact.sql"]
        for f in expected:
            self.assertTrue((int_dir / f).exists(), f"File {f} must exist in intermediate models")

    def test_flagged_model_references_dbt_vars(self):
        sql = Path("dbt_project/models/intermediate/int_trips_flagged.sql").read_text(encoding="utf-8")
        self.assertIn("var(\"min_pickup_timestamp\")", sql)
        self.assertIn("var(\"max_speed_mph\")", sql)
        self.assertIn("flag_outside_period", sql)
        self.assertIn("flag_dropoff_before_pickup", sql)
        self.assertIn("flag_duration_anomaly", sql)
        self.assertIn("flag_distance_anomaly", sql)
        self.assertIn("flag_impossible_speed", sql)
        self.assertIn("flag_fare_anomaly", sql)

    def test_clean_model_has_governance_policy(self):
        sql = Path("dbt_project/models/intermediate/int_trips_clean.sql").read_text(encoding="utf-8")
        self.assertIn("NOT flag_outside_period", sql)
        self.assertIn("NOT flag_dropoff_before_pickup", sql)
        self.assertIn("NOT flag_duration_anomaly", sql)
        self.assertIn("NOT flag_impossible_speed", sql)
        self.assertIn("is_unknown_zone", sql)
        self.assertIn("is_passenger_count_imputed", sql)

    def test_rule_impact_model_measures_deltas(self):
        sql = Path("dbt_project/models/intermediate/int_trips_rule_impact.sql").read_text(encoding="utf-8")
        self.assertIn("delta_avg_fare", sql)
        self.assertIn("delta_fare_per_mile", sql)
        self.assertIn("pct_rows_removed", sql)

if __name__ == "__main__":
    unittest.main()
