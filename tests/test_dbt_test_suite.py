import unittest
from pathlib import Path
import yaml

class TestDbtAutomatedTestsSuite(unittest.TestCase):
    def test_schema_yml_tests_count(self):
        schema_path = Path("dbt_project/models/marts/schema.yml")
        self.assertTrue(schema_path.exists())
        with open(schema_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # Count generic tests in schema.yml
        generic_test_count = 0
        for model in cfg.get("models", []):
            for col in model.get("columns", []):
                generic_test_count += len(col.get("tests", []))
        
        # We configured 18+ generic tests in schema.yml alone
        self.assertGreaterEqual(generic_test_count, 15)

    def test_singular_test_files_exist(self):
        tests_dir = Path("dbt_project/tests")
        expected_singular_tests = [
            "test_reconciliation_balance.sql",
            "test_no_join_duplication.sql",
            "test_non_negative_amounts.sql",
            "test_speed_bounds.sql",
            "test_date_range_bounds.sql",
            "test_mart_totals_match_fct.sql",
        ]
        for t in expected_singular_tests:
            self.assertTrue((tests_dir / t).exists(), f"Singular test {t} must exist")

    def test_reconciliation_test_content(self):
        sql = Path("dbt_project/tests/test_reconciliation_balance.sql").read_text(encoding="utf-8")
        self.assertIn("reconcile_trip_lineage", sql)
        self.assertIn("BALANCED_PERFECT", sql)

    def test_no_join_duplication_test_content(self):
        sql = Path("dbt_project/tests/test_no_join_duplication.sql").read_text(encoding="utf-8")
        self.assertIn("int_hourly_demand", sql)
        self.assertIn("generate_series", sql)

    def test_mart_totals_match_fct_test_content(self):
        sql = Path("dbt_project/tests/test_mart_totals_match_fct.sql").read_text(encoding="utf-8")
        self.assertIn("fct_trips", sql)
        self.assertIn("mart_zone", sql)
        self.assertIn("mart_time", sql)
        self.assertIn("zone_total_pickups", sql)

if __name__ == "__main__":
    unittest.main()
