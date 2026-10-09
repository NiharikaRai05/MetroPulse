import logging
from pathlib import Path
from typing import Dict, Tuple

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("metropulse.analysis.subway")


def run_subway_cross_elasticity_analysis(
    duckdb_path: str = "data/metropulse.duckdb",
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Analyzes the multimodal relationship between NYC Yellow Taxi demand and MTA Subway ridership:
    1. Regresses hourly Subway Ridership on Hour-of-Day, Day-of-Week, Linear Trend, and Weather
    2. Regresses hourly Taxi Trips on Hour-of-Day, Day-of-Week, Linear Trend, and Weather
    3. Correlates the orthogonalized demand residuals across Lags 0, 1, and 2 hours
    4. Classifies multimodal relationship into:
         - Substitute (Negative cross-elasticity correlation in residuals)
         - Complement / Co-Moving (Positive correlation in residuals due to shared unobserved activity shocks)
         - Unrelated (Near-zero residual correlation |r| < 0.05)
    5. Formulates explicit non-causal confounding caveats and defense arguments.
    """
    db_file = Path(duckdb_path)
    if not db_file.exists():
        logger.warning(f"DuckDB database at {duckdb_path} not found. Generating synthetic hourly multimodal dataset.")
        np.random.seed(random_state)
        n_hours = 2184  # Q2 2024 hours
        hour_timestamps = pd.date_range("2024-04-01 00:00:00", periods=n_hours, freq="h")
        
        hours = hour_timestamps.hour
        dows = hour_timestamps.dayofweek
        trend = np.arange(n_hours)
        precip = np.random.exponential(scale=0.5, size=n_hours) * (np.random.random(n_hours) < 0.15)
        
        # Shared diurnal rhythm
        diurnal = np.sin(2 * np.pi * (hours - 7) / 24)
        subway = 150000 + 120000 * diurnal - 40000 * (dows >= 5) - 5000 * precip + np.random.normal(0, 10000, n_hours)
        taxi = 1500 + 600 * diurnal + 300 * (dows >= 4) + 120 * precip + np.random.normal(0, 100, n_hours)
        
        df_demand = pd.DataFrame({
            "hour_timestamp": hour_timestamps,
            "taxi_trip_count": np.maximum(taxi, 50),
            "total_subway_ridership": np.maximum(subway, 1000),
            "subway_ridership_manhattan": np.maximum(subway * 0.55, 500),
            "subway_ridership_brooklyn": np.maximum(subway * 0.22, 200),
            "subway_ridership_queens": np.maximum(subway * 0.15, 150),
            "subway_ridership_bronx": np.maximum(subway * 0.08, 100),
            "precipitation_mm": precip,
            "hour_of_day": hours,
            "day_of_week": dows,
            "trend_index": trend,
        })
    else:
        with duckdb.connect(str(db_file)) as con:
            df_demand = con.execute(
                """
                SELECT
                    hour_timestamp,
                    taxi_trip_count,
                    total_subway_ridership,
                    subway_ridership_manhattan,
                    subway_ridership_brooklyn,
                    subway_ridership_queens,
                    subway_ridership_bronx,
                    precipitation_mm,
                    hour_of_day,
                    day_of_week,
                    ROW_NUMBER() OVER (ORDER BY hour_timestamp ASC) AS trend_index
                FROM int_hourly_demand
                ORDER BY hour_timestamp ASC;
                """
            ).df()

    # Log-transform demand metrics
    df_demand["log_taxi"] = np.log1p(df_demand["taxi_trip_count"])
    df_demand["log_subway"] = np.log1p(df_demand["total_subway_ridership"])

    # 1. Regress Taxi on Controls
    taxi_model = ols(
        "log_taxi ~ precipitation_mm + C(hour_of_day) + C(day_of_week) + trend_index",
        data=df_demand
    ).fit(cov_type="HC1")
    df_demand["taxi_resid"] = taxi_model.resid

    # 2. Regress Subway on Controls
    subway_model = ols(
        "log_subway ~ precipitation_mm + C(hour_of_day) + C(day_of_week) + trend_index",
        data=df_demand
    ).fit(cov_type="HC1")
    df_demand["subway_resid"] = subway_model.resid

    # 3. Residual Cross-Correlations across Lags 0, 1, 2
    r_lag0 = df_demand["taxi_resid"].corr(df_demand["subway_resid"])
    r_lag1 = df_demand["taxi_resid"].corr(df_demand["subway_resid"].shift(1))
    r_lag2 = df_demand["taxi_resid"].corr(df_demand["subway_resid"].shift(2))
    r_lead1 = df_demand["taxi_resid"].corr(df_demand["subway_resid"].shift(-1))

    # 4. Mode Relationship Classification Logic
    if r_lag0 < -0.08:
        mode_classification = "Substitute (Mode Switching / Displacement)"
        classification_rationale = "Negative residual cross-correlation indicates riders switch between taxi and subway when shocks occur."
    elif r_lag0 > 0.08:
        mode_classification = "Complementary / Jointly-Driven (Shared Activity Pulse)"
        classification_rationale = (
            "Positive residual cross-correlation indicates both modes surge and contract simultaneously "
            "in response to unmeasured macro activity shocks (e.g. major sports events, concerts, citywide tourism peaks, holiday weekend getaways)."
        )
    else:
        mode_classification = "Largely Unrelated / Segment-Specific"
        classification_rationale = "Near-zero residual correlation indicates the two modes serve largely decoupled commuter segments at the margin."

    # --------------------------------------------------------------------------
    # Output Table 1: stats_subway_elasticity
    # --------------------------------------------------------------------------
    elasticity_records = [
        {
            "analysis_id": "SUBWAY_TAXI_MODAL_01",
            "relationship_classification": mode_classification,
            "residual_corr_lag0": round(r_lag0, 4),
            "residual_corr_lag1": round(r_lag1, 4),
            "residual_corr_lag2": round(r_lag2, 4),
            "residual_corr_subway_lead1": round(r_lead1, 4),
            "taxi_r2_controlled": round(taxi_model.rsquared_adj, 4),
            "subway_r2_controlled": round(subway_model.rsquared_adj, 4),
            "classification_rationale": classification_rationale,
            "epistemic_classification": "Empirical Multimodal Residual Association",
            "confounding_caveats": (
                "1. Omitted Variable Bias: Major citywide events (e.g., Pride Parade, Fleet Week, Mets/Yankees games) "
                "drive simultaneous demand spikes across both transit systems. "
                "2. Spatial Aggregation Masking: Citywide aggregation can mask localized substitution (e.g., subway line delays triggering local taxi surges in Brooklyn while Manhattan remains stable). "
                "3. Capacity Constraints: Subway has virtually elastic per-train capacity, whereas Yellow Taxi supply is strictly hard-capped by physical vehicle fleet size (13,587 medallions). "
                "4. No Causal Claim: Residual correlations describe joint observational co-movement, NOT causal cross-price elasticity."
            ),
        }
    ]
    df_subway_elasticity = pd.DataFrame(elasticity_records)

    # --------------------------------------------------------------------------
    # Output Table 2: stats_subway_borough_correlations
    # --------------------------------------------------------------------------
    borough_records = []
    boroughs = ["manhattan", "brooklyn", "queens", "bronx"]
    for b in boroughs:
        col = f"subway_ridership_{b}"
        if col in df_demand.columns:
            df_demand[f"log_sub_{b}"] = np.log1p(df_demand[col])
            b_model = ols(
                f"log_sub_{b} ~ precipitation_mm + C(hour_of_day) + C(day_of_week) + trend_index",
                data=df_demand
            ).fit(cov_type="HC1")
            b_resid = b_model.resid
            b_corr = df_demand["taxi_resid"].corr(b_resid)
            borough_records.append({
                "borough": b.capitalize(),
                "residual_correlation_with_taxi": round(b_corr, 4),
                "sample_hours": int(b_model.nobs),
                "interpretation": f"Residual demand correlation between citywide taxi activity and {b.capitalize()} subway entries.",
            })
    df_borough_corrs = pd.DataFrame(borough_records)

    # Persist to DuckDB & CSV
    if db_file.exists():
        with duckdb.connect(str(db_file)) as con:
            con.execute("CREATE SCHEMA IF NOT EXISTS marts;")
            con.execute("CREATE OR REPLACE TABLE marts.stats_subway_elasticity AS SELECT * FROM df_subway_elasticity")
            con.execute("CREATE OR REPLACE TABLE marts.stats_subway_borough_corrs AS SELECT * FROM df_borough_corrs")
            logger.info("Saved stats_subway_elasticity and stats_subway_borough_corrs to DuckDB marts.")

    out_dir = Path("data/manifests")
    out_dir.mkdir(parents=True, exist_ok=True)
    df_subway_elasticity.to_csv(out_dir / "stats_subway_elasticity.csv", index=False)
    df_borough_corrs.to_csv(out_dir / "stats_subway_borough_corrs.csv", index=False)

    print("\n" + "=" * 95)
    print("  🚇 MULTIMODAL DEMAND CO-MOVEMENT: TAXI VS SUBWAY (HOURLY Q2 2024)")
    print("=" * 95)
    print(df_subway_elasticity[["relationship_classification", "residual_corr_lag0", "residual_corr_lag1", "residual_corr_lag2"]].to_markdown(index=False))
    print("\n  📍 Borough-Level Subway Residual Correlations:")
    print(df_borough_corrs.to_markdown(index=False))
    print("=" * 95 + "\n")

    return df_subway_elasticity, df_borough_corrs


if __name__ == "__main__":
    run_subway_cross_elasticity_analysis()
