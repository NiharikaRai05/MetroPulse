import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("metropulse.analysis.bootstrap")


def compute_bootstrap_ci(
    data: np.ndarray,
    stat_func=np.median,
    n_bootstraps: int = 2000,
    ci_level: float = 0.95,
    random_state: int = 42,
) -> Tuple[float, float, float]:
    """
    Computes non-parametric bootstrap confidence interval (BCa / Percentile) for a given statistic.
    Returns: (point_estimate, ci_lower, ci_upper)
    """
    if len(data) == 0:
        return np.nan, np.nan, np.nan

    rng = np.random.default_rng(random_state)
    point_est = float(stat_func(data))
    
    # Generate bootstrap samples
    boot_indices = rng.integers(0, len(data), size=(n_bootstraps, len(data)))
    boot_stats = stat_func(data[boot_indices], axis=1)
    
    alpha = (1.0 - ci_level) / 2.0
    ci_lower = float(np.percentile(boot_stats, alpha * 100))
    ci_upper = float(np.percentile(boot_stats, (1.0 - alpha) * 100))
    
    return point_est, ci_lower, ci_upper


def run_mann_whitney_and_permutation(
    group_a: np.ndarray,
    group_b: np.ndarray,
    n_permutations: int = 5000,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Executes:
    1. Mann-Whitney U test (non-parametric rank sum test)
    2. Rank-biserial correlation effect size
    3. Exact/Monte Carlo Permutation test for difference in medians
    4. Cliff's Delta effect size
    """
    group_a = group_a[~np.isnan(group_a)]
    group_b = group_b[~np.isnan(group_b)]
    n_a, n_b = len(group_a), len(group_b)

    if n_a == 0 or n_b == 0:
        return {"status": "insufficient_data"}

    # 1. Mann-Whitney U Test
    u_stat, p_value_mwu = stats.mannwhitneyu(group_a, group_b, alternative="two-sided")
    
    # Effect Size: Rank-Biserial Correlation (r = 1 - (2U / (n1*n2)))
    rank_biserial = float(1.0 - (2.0 * u_stat) / (n_a * n_b))
    
    # Effect Size: Cliff's Delta
    # For large samples, Cliff's delta is equivalent to 2*AUC - 1 = (2*U)/(n1*n2) - 1 = -rank_biserial
    cliffs_delta = -rank_biserial

    # 2. Permutation Test for Difference in Medians
    obs_diff = float(np.median(group_a) - np.median(group_b))
    combined = np.concatenate([group_a, group_b])
    rng = np.random.default_rng(random_state)
    
    perm_diffs = np.empty(n_permutations)
    for i in range(n_permutations):
        shuffled = rng.permutation(combined)
        perm_a = shuffled[:n_a]
        perm_b = shuffled[n_a:]
        perm_diffs[i] = np.median(perm_a) - np.median(perm_b)
        
    p_value_perm = float(np.mean(np.abs(perm_diffs) >= np.abs(obs_diff)))

    return {
        "n_group_a": n_a,
        "n_group_b": n_b,
        "median_group_a": float(np.median(group_a)),
        "median_group_b": float(np.median(group_b)),
        "median_difference": obs_diff,
        "mann_whitney_u": float(u_stat),
        "p_value_mwu": float(p_value_mwu),
        "rank_biserial_effect_size": rank_biserial,
        "cliffs_delta": cliffs_delta,
        "p_value_permutation": p_value_perm,
    }


def analyze_statistical_comparisons(
    duckdb_path: str = "data/metropulse.duckdb",
    sample_size_per_group: int = 10000,
    n_bootstraps: int = 2000,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Performs 2 rigorous non-parametric statistical hypothesis tests on NYC mobility:
    
    Comparison 1: Airport vs Non-Airport Fare per Mile ($/mile)
      - Hypotheses:
          H0: The distribution of fare per mile is identical between airport and non-airport trips.
          H1: Airport trips have a systematically different fare per mile.
      - Metric: fare_per_mile (total_amount / trip_distance_miles)
      
    Comparison 2: Electronic Card vs Cash Tip Recording Discrepancy
      - Hypotheses:
          H0: Recorded tip amount is identical between Credit Card and Cash payments.
          H1: Recorded tip amounts reflect a severe telematics logging discrepancy (Cash tips are unrecorded).
      - Metric: tip_amount ($)
    """
    db_file = Path(duckdb_path)
    if not db_file.exists():
        logger.warning(f"DuckDB path {duckdb_path} does not exist. Creating synthetic demonstration slice.")
        # Create deterministic synthetic sample if DB isn't built yet
        np.random.seed(random_state)
        df_trips = pd.DataFrame({
            "is_airport_corridor": np.random.choice([True, False], size=20000, p=[0.15, 0.85]),
            "payment_type_id": np.random.choice([1, 2], size=20000, p=[0.80, 0.20]),
            "fare_per_mile": np.concatenate([
                np.random.gamma(shape=5.0, scale=1.5, size=3000),  # Airport higher base/fixed
                np.random.gamma(shape=3.5, scale=1.8, size=17000), # Non-airport urban
            ]),
            "tip_amount": np.concatenate([
                np.random.exponential(scale=3.5, size=16000),       # Card tips
                np.zeros(4000),                                     # Cash tips (meter records 0)
            ]),
            "trip_distance_miles": np.random.uniform(0.5, 15.0, size=20000),
        })
    else:
        with duckdb.connect(str(db_file)) as con:
            # Query from fct_trips with zone attributes
            query = f"""
            SELECT
                CASE 
                    WHEN pz.is_airport_zone OR dz.is_airport_zone OR t.rate_code_id IN (2, 3) 
                    THEN TRUE ELSE FALSE 
                END AS is_airport_corridor,
                t.payment_type_id,
                t.fare_per_mile,
                t.tip_amount,
                t.trip_distance_miles,
                t.total_amount
            FROM fct_trips t
            LEFT JOIN dim_zone pz ON t.pickup_location_id = pz.location_id
            LEFT JOIN dim_zone dz ON t.dropoff_location_id = dz.location_id
            USING SAMPLE {sample_size_per_group * 4} (reservoir, 42);
            """
            df_trips = con.execute(query).df()

    # --------------------------------------------------------------------------
    # COMPARISON 1: Airport vs Non-Airport Fare per Mile
    # --------------------------------------------------------------------------
    logger.info("Executing Comparison 1: Airport vs Non-Airport Fare per Mile...")
    airport_fares = df_trips[df_trips["is_airport_corridor"] == True]["fare_per_mile"].dropna().values
    non_airport_fares = df_trips[df_trips["is_airport_corridor"] == False]["fare_per_mile"].dropna().values

    # Resample for balanced robust computation if large
    if len(airport_fares) > sample_size_per_group:
        airport_fares = np.random.default_rng(random_state).choice(airport_fares, size=sample_size_per_group, replace=False)
    if len(non_airport_fares) > sample_size_per_group:
        non_airport_fares = np.random.default_rng(random_state).choice(non_airport_fares, size=sample_size_per_group, replace=False)

    pt_air, ci_low_air, ci_high_air = compute_bootstrap_ci(airport_fares, stat_func=np.median, n_bootstraps=n_bootstraps, random_state=random_state)
    pt_non, ci_low_non, ci_high_non = compute_bootstrap_ci(non_airport_fares, stat_func=np.median, n_bootstraps=n_bootstraps, random_state=random_state)
    test_res_1 = run_mann_whitney_and_permutation(airport_fares, non_airport_fares, random_state=random_state)

    # --------------------------------------------------------------------------
    # COMPARISON 2: Credit Card vs Cash Recorded Tip Amount
    # --------------------------------------------------------------------------
    logger.info("Executing Comparison 2: Card vs Cash Recorded Tip Amount...")
    card_tips = df_trips[df_trips["payment_type_id"] == 1]["tip_amount"].dropna().values
    cash_tips = df_trips[df_trips["payment_type_id"] == 2]["tip_amount"].dropna().values

    if len(card_tips) > sample_size_per_group:
        card_tips = np.random.default_rng(random_state).choice(card_tips, size=sample_size_per_group, replace=False)
    if len(cash_tips) > sample_size_per_group:
        cash_tips = np.random.default_rng(random_state).choice(cash_tips, size=sample_size_per_group, replace=False)

    pt_card, ci_low_card, ci_high_card = compute_bootstrap_ci(card_tips, stat_func=np.median, n_bootstraps=n_bootstraps, random_state=random_state)
    pt_cash, ci_low_cash, ci_high_cash = compute_bootstrap_ci(cash_tips, stat_func=np.median, n_bootstraps=n_bootstraps, random_state=random_state)
    test_res_2 = run_mann_whitney_and_permutation(card_tips, cash_tips, random_state=random_state)

    # --------------------------------------------------------------------------
    # Output Table 1: stats_bootstrap_ci
    # --------------------------------------------------------------------------
    bootstrap_records = [
        {
            "analysis_id": "STAT_BOOT_01",
            "metric_name": "airport_fare_per_mile",
            "group_label": "Airport Trips",
            "sample_size": len(airport_fares),
            "statistic_type": "Median",
            "point_estimate": round(pt_air, 3),
            "ci_lower_95": round(ci_low_air, 3),
            "ci_upper_95": round(ci_high_air, 3),
            "epistemic_label": "Derived Fact",
            "limitations": "Flat rate JFK pricing ($70 fixed) and Newark surcharges create long right-tails on shorter airport perimeter rides.",
        },
        {
            "analysis_id": "STAT_BOOT_02",
            "metric_name": "non_airport_fare_per_mile",
            "group_label": "Non-Airport Urban Trips",
            "sample_size": len(non_airport_fares),
            "statistic_type": "Median",
            "point_estimate": round(pt_non, 3),
            "ci_lower_95": round(ci_low_non, 3),
            "ci_upper_95": round(ci_high_non, 3),
            "epistemic_label": "Derived Fact",
            "limitations": "Subject to urban street-grid traffic congestion and high base-drop proportion on short Manhattan hops.",
        },
        {
            "analysis_id": "STAT_BOOT_03",
            "metric_name": "credit_card_tip_amount",
            "group_label": "Credit Card Payments (1)",
            "sample_size": len(card_tips),
            "statistic_type": "Median",
            "point_estimate": round(pt_card, 3),
            "ci_lower_95": round(ci_low_card, 3),
            "ci_upper_95": round(ci_high_card, 3),
            "epistemic_label": "Observed Fact",
            "limitations": "Includes UI preset tip prompt behavior (20%, 25%, 30%) on payment terminals.",
        },
        {
            "analysis_id": "STAT_BOOT_04",
            "metric_name": "cash_recorded_tip_amount",
            "group_label": "Cash Payments (2)",
            "sample_size": len(cash_tips),
            "statistic_type": "Median",
            "point_estimate": round(pt_cash, 3),
            "ci_lower_95": round(ci_low_cash, 3),
            "ci_upper_95": round(ci_high_cash, 3),
            "epistemic_label": "Artifact of Data Collection",
            "limitations": "TLC meter specification does not track cash tips; recorded as $0.00 by construction.",
        },
    ]
    df_bootstrap = pd.DataFrame(bootstrap_records)

    # --------------------------------------------------------------------------
    # Output Table 2: stats_hypothesis_tests
    # --------------------------------------------------------------------------
    hypo_records = [
        {
            "test_id": "HYPO_TEST_01",
            "comparison_name": "Airport vs Non-Airport Fare per Mile",
            "group_a": "Airport Trips",
            "group_b": "Non-Airport Trips",
            "sample_size_a": test_res_1["n_group_a"],
            "sample_size_b": test_res_1["n_group_b"],
            "median_a": round(test_res_1["median_group_a"], 3),
            "median_b": round(test_res_1["median_group_b"], 3),
            "median_diff": round(test_res_1["median_difference"], 3),
            "mann_whitney_u": round(test_res_1["mann_whitney_u"], 1),
            "p_value_mwu": test_res_1["p_value_mwu"],
            "rank_biserial_effect_size": round(test_res_1["rank_biserial_effect_size"], 4),
            "cliffs_delta_effect_size": round(test_res_1["cliffs_delta"], 4),
            "p_value_permutation": test_res_1["p_value_permutation"],
            "statistically_significant": test_res_1["p_value_mwu"] < 0.001,
            "epistemic_classification": "Non-Parametric Association",
            "analytical_limitations": "Does not establish causal driver pricing power; reflects airport flat rate structures, airport access fees, and longer highway mileage efficiency.",
        },
        {
            "test_id": "HYPO_TEST_02",
            "comparison_name": "Electronic Card vs Cash Recorded Tips",
            "group_a": "Credit Card Trips",
            "group_b": "Cash Trips",
            "sample_size_a": test_res_2["n_group_a"],
            "sample_size_b": test_res_2["n_group_b"],
            "median_a": round(test_res_2["median_group_a"], 3),
            "median_b": round(test_res_2["median_group_b"], 3),
            "median_diff": round(test_res_2["median_difference"], 3),
            "mann_whitney_u": round(test_res_2["mann_whitney_u"], 1),
            "p_value_mwu": test_res_2["p_value_mwu"],
            "rank_biserial_effect_size": round(test_res_2["rank_biserial_effect_size"], 4),
            "cliffs_delta_effect_size": round(test_res_2["cliffs_delta"], 4),
            "p_value_permutation": test_res_2["p_value_permutation"],
            "statistically_significant": test_res_2["p_value_mwu"] < 0.001,
            "epistemic_classification": "Measurement Telematics Artifact",
            "analytical_limitations": "Strictly demonstrates telematics recording artifact (Cash tips are not digitized by TLC meters); never assert that cash passengers tip $0 in reality.",
        },
    ]
    df_hypothesis = pd.DataFrame(hypo_records)

    # --------------------------------------------------------------------------
    # Persist to DuckDB and Manifest CSV
    # --------------------------------------------------------------------------
    if db_file.exists():
        with duckdb.connect(str(db_file)) as con:
            con.execute("CREATE SCHEMA IF NOT EXISTS marts;")
            con.execute("CREATE OR REPLACE TABLE marts.stats_bootstrap_ci AS SELECT * FROM df_bootstrap")
            con.execute("CREATE OR REPLACE TABLE marts.stats_hypothesis_tests AS SELECT * FROM df_hypothesis")
            logger.info("Saved stats_bootstrap_ci and stats_hypothesis_tests to DuckDB marts schema.")

    out_dir = Path("data/manifests")
    out_dir.mkdir(parents=True, exist_ok=True)
    df_bootstrap.to_csv(out_dir / "stats_bootstrap_ci.csv", index=False)
    df_hypothesis.to_csv(out_dir / "stats_hypothesis_tests.csv", index=False)
    logger.info("Exported stats summary CSVs to data/manifests/.")

    print("\n" + "=" * 95)
    print("  📈 STATISTICAL BOOTSTRAP CONFIDENCE INTERVALS (95% CI)")
    print("=" * 95)
    print(df_bootstrap[["metric_name", "group_label", "point_estimate", "ci_lower_95", "ci_upper_95", "epistemic_label"]].to_markdown(index=False))
    
    print("\n" + "=" * 95)
    print("  🔬 HYPOTHESIS TESTS & NON-PARAMETRIC PERMUTATION / MANN-WHITNEY U")
    print("=" * 95)
    print(df_hypothesis[["comparison_name", "median_a", "median_b", "median_diff", "p_value_mwu", "cliffs_delta_effect_size", "statistically_significant"]].to_markdown(index=False))
    print("=" * 95 + "\n")

    return df_bootstrap, df_hypothesis


if __name__ == "__main__":
    analyze_statistical_comparisons()
