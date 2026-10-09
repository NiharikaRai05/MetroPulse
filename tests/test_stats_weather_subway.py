import tempfile
import unittest
from pathlib import Path
import pandas as pd
from analysis.stats_weather import run_weather_regression_analysis
from analysis.stats_subway import run_subway_cross_elasticity_analysis

class TestWeatherAndSubwayStats(unittest.TestCase):
    def test_stats_weather_regression(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_db = Path(temp_dir) / "test.duckdb"
            df_reg, df_lags = run_weather_regression_analysis(duckdb_path=str(fake_db))
            
            self.assertEqual(len(df_reg), 1)
            self.assertEqual(len(df_lags), 3)
            
            # Check required fields
            self.assertIn("precip_mm_pct_effect", df_reg.columns)
            self.assertIn("adjusted_r_squared", df_reg.columns)
            self.assertIn("residual_corr_precip_lag0", df_reg.columns)
            self.assertIn("residual_corr_precip_lag1", df_reg.columns)
            self.assertIn("residual_corr_precip_lag2", df_reg.columns)
            self.assertIn("confounding_caveats", df_reg.columns)

    def test_stats_subway_elasticity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_db = Path(temp_dir) / "test.duckdb"
            df_elast, df_boroughs = run_subway_cross_elasticity_analysis(duckdb_path=str(fake_db))
            
            self.assertEqual(len(df_elast), 1)
            self.assertGreaterEqual(len(df_boroughs), 4)
            
            # Check classification
            classification = df_elast["relationship_classification"].iloc[0]
            self.assertTrue(
                "Substitute" in classification or 
                "Complementary" in classification or 
                "Unrelated" in classification
            )
            
            # Check required fields
            self.assertIn("residual_corr_lag0", df_elast.columns)
            self.assertIn("residual_corr_lag1", df_elast.columns)
            self.assertIn("residual_corr_lag2", df_elast.columns)
            self.assertIn("confounding_caveats", df_elast.columns)

if __name__ == "__main__":
    unittest.main()
