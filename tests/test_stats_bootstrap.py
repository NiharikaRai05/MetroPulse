import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from analysis.stats_bootstrap import (
    compute_bootstrap_ci,
    run_mann_whitney_and_permutation,
    analyze_statistical_comparisons,
)

class TestStatisticalBootstrap(unittest.TestCase):
    def test_compute_bootstrap_ci_coverage(self):
        # Generate normal distribution with true median = 50.0
        np.random.seed(42)
        data = np.random.normal(loc=50.0, scale=5.0, size=500)
        pt, low, high = compute_bootstrap_ci(data, stat_func=np.median, n_bootstraps=1000)
        
        self.assertAlmostEqual(pt, 50.0, delta=1.0)
        self.assertTrue(low < pt < high)
        self.assertAlmostEqual(low, 49.0, delta=1.5)
        self.assertAlmostEqual(high, 51.0, delta=1.5)

    def test_mann_whitney_and_permutation_significance(self):
        np.random.seed(42)
        group_a = np.random.normal(loc=20.0, scale=2.0, size=200)
        group_b = np.random.normal(loc=10.0, scale=2.0, size=200)

        res = run_mann_whitney_and_permutation(group_a, group_b, n_permutations=500)
        
        self.assertLess(res["p_value_mwu"], 0.001)
        self.assertLess(res["p_value_permutation"], 0.01)
        self.assertGreater(abs(res["cliffs_delta"]), 0.80)  # Large effect size
        self.assertAlmostEqual(res["median_difference"], 10.0, delta=1.0)

    def test_analyze_statistical_comparisons_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_db = Path(temp_dir) / "fake.duckdb"
            df_boot, df_hypo = analyze_statistical_comparisons(
                duckdb_path=str(fake_db),
                sample_size_per_group=500,
                n_bootstraps=500,
            )

            self.assertEqual(len(df_boot), 4)
            self.assertEqual(len(df_hypo), 2)
            
            # Check required columns
            self.assertIn("ci_lower_95", df_boot.columns)
            self.assertIn("ci_upper_95", df_boot.columns)
            self.assertIn("epistemic_label", df_boot.columns)
            
            self.assertIn("cliffs_delta_effect_size", df_hypo.columns)
            self.assertIn("p_value_mwu", df_hypo.columns)
            self.assertIn("p_value_permutation", df_hypo.columns)
            self.assertIn("analytical_limitations", df_hypo.columns)

if __name__ == "__main__":
    unittest.main()
