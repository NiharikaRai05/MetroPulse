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
logger = logging.getLogger("metropulse.analysis.weather")


def run_weather_regression_analysis(
    duckdb_path: str = "data/metropulse.duckdb",
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Regresses hourly taxi mobility demand on weather conditions controlling for:
      - Hour of day fixed effects (C(hour_of_day))
      - Day of week fixed effects (C(day_of_week))
      - Linear time trend (trend_index)
    
    Model Specification:
      log(taxi_trip_count + 1) ~ precipitation_mm + is_heavy_rain + avg_temperature_fahrenheit 
                                 + C(hour_of_day) + C(day_of_week) + trend_index
    
    Computes cross-correlations of demand residuals against precipitation at Lags 0, 1, and 2 hours.
    Strictly uses non-causal association terminology and documents confounding caveats.
    """
    db_file = Path(duckdb_path)
    if not db_file.exists():
        logger.warning(f"DuckDB database at {duckdb_path} not found. Generating synthetic hourly dataset for demonstration.")
        np.random.seed(random_state)
        n_hours = 2184  # Q2 2024 hours
        hour_timestamps = pd.date_range("2024-04-01 00:00:00", periods=n_hours, freq="h")
        
        hours = hour_timestamps.hour
        dows = hour_timestamps.dayofweek
        trend = np.arange(n_hours)
        precip = np.random.exponential(scale=0.5, size=n_hours) * (np.random.random(n_hours) < 0.15)
        temp = 60.0 + 15.0 * np.sin(2 * np.pi * trend / (24 * 90)) + np.random.normal(0, 3, n_hours)
        
        # Synthetic baseline demand
        base_demand = 1200 + 400 * np.sin(2 * np.pi * (hours - 8) / 24) + 150 * (dows >= 4) + 80 * precip + np.random.normal(0, 50, n_hours)
        df_hourly = pd.DataFrame({
            "hour_timestamp": hour_timestamps,
            "taxi_trip_count": np.maximum(base_demand, 50),
            "precipitation_mm": precip,
            "is_heavy_rain": (precip >= 2.5).astype(int),
            "avg_temperature_fahrenheit": temp,
            "hour_of_day": hours,
            "day_of_week": dows,
            "trend_index": trend,
        })
    else:
        with duckdb.connect(str(db_file)) as con:
            df_hourly = con.execute(
                """
                SELECT
                    hour_timestamp,
                    taxi_trip_count,
                    precipitation_mm,
                    is_heavy_rain,
                    avg_temperature_fahrenheit,
                    hour_of_day,
                    day_of_week,
                    ROW_NUMBER() OVER (ORDER BY hour_timestamp ASC) AS trend_index
                FROM int_hourly_demand
                ORDER BY hour_timestamp ASC;
                """
            ).df()

    df_hourly["log_taxi_demand"] = np.log1p(df_hourly["taxi_trip_count"])

    # 1. Fit OLS Regression with Fixed Effects & Trend
    formula = (
        "log_taxi_demand ~ precipitation_mm + is_heavy_rain + avg_temperature_fahrenheit "
        "+ C(hour_of_day) + C(day_of_week) + trend_index"
    )
    model = ols(formula, data=df_hourly).fit(cov_type="HC1")  # Heteroskedasticity-robust SE (Huber-White)
    logger.info("Fitted OLS weather regression model.")

    # Extract Key Coefficients
    coef_precip = model.params.get("precipitation_mm", 0.0)
    pval_precip = model.pvalues.get("precipitation_mm", 1.0)
    coef_heavy = model.params.get("is_heavy_rain", 0.0)
    pval_heavy = model.pvalues.get("is_heavy_rain", 1.0)
    coef_temp = model.params.get("avg_temperature_fahrenheit", 0.0)
    pval_temp = model.pvalues.get("avg_temperature_fahrenheit", 1.0)
    r2_adj = model.rsquared_adj

    # 2. Extract Residuals and Compute Cross-Correlations at Lags 0, 1, 2
    df_hourly["demand_residuals"] = model.resid
    
    corr_lag0 = df_hourly["demand_residuals"].corr(df_hourly["precipitation_mm"])
    corr_lag1 = df_hourly["demand_residuals"].corr(df_hourly["precipitation_mm"].shift(1))
    corr_lag2 = df_hourly["demand_residuals"].corr(df_hourly["precipitation_mm"].shift(2))

    # --------------------------------------------------------------------------
    # Output Table 1: stats_weather_regression
    # --------------------------------------------------------------------------
    regression_records = [
        {
            "model_id": "REG_WEATHER_01",
            "dependent_variable": "log(taxi_trip_count + 1)",
            "sample_size_hours": int(model.nobs),
            "adjusted_r_squared": round(r2_adj, 4),
            "f_statistic_pvalue": model.f_pvalue,
            "precip_mm_coefficient": round(coef_precip, 5),
            "precip_mm_pct_effect": round((np.exp(coef_precip) - 1) * 100.0, 3),
            "precip_mm_pvalue": pval_precip,
            "heavy_rain_coefficient": round(coef_heavy, 5),
            "heavy_rain_pct_effect": round((np.exp(coef_heavy) - 1) * 100.0, 3),
            "heavy_rain_pvalue": pval_heavy,
            "temp_f_coefficient": round(coef_temp, 5),
            "temp_f_pvalue": pval_temp,
            "residual_corr_precip_lag0": round(corr_lag0, 4),
            "residual_corr_precip_lag1": round(corr_lag1, 4),
            "residual_corr_precip_lag2": round(corr_lag2, 4),
            "epistemic_classification": "Econometric Fixed-Effects Association",
            "confounding_caveats": (
                "Correlations represent statistical associations, NOT direct causal laws. "
                "Unobserved confounders include concurrent subway service disruptions during severe storms, "
                "driver supply contraction (drivers going off-shift during downpours), and localized Manhattan vs Outer Borough cloudburst variations."
            ),
        }
    ]
    df_weather_reg = pd.DataFrame(regression_records)

    # --------------------------------------------------------------------------
    # Output Table 2: stats_weather_lag_residuals
    # --------------------------------------------------------------------------
    lag_records = [
        {
            "lag_hours": 0,
            "lag_name": "Lag 0h (Immediate Co-occurrence)",
            "residual_pearson_corr": round(corr_lag0, 4),
            "interpretation": "Immediate statistical association between precipitation onset and taxi demand residuals.",
            "confounding_caveat": "Simultaneous traffic congestion slow-down increases trip durations while rides are hailed.",
        },
        {
            "lag_hours": 1,
            "lag_name": "Lag 1h (Substitution / Delay Window)",
            "residual_pearson_corr": round(corr_lag1, 4),
            "interpretation": "Demand shift correlation 1 hour following precipitation onset.",
            "confounding_caveat": "Reflects delayed trip departures and modal switching after surface water pooling.",
        },
        {
            "lag_hours": 2,
            "lag_name": "Lag 2h (Dissipation / Clearance Phase)",
            "residual_pearson_corr": round(corr_lag2, 4),
            "interpretation": "Residual demand association 2 hours post-storm.",
            "confounding_caveat": "Captures post-storm clearing and residual traffic clearing backlogs.",
        },
    ]
    df_weather_lags = pd.DataFrame(lag_records)

    # Persist to DuckDB & CSV
    if db_file.exists():
        with duckdb.connect(str(db_file)) as con:
            con.execute("CREATE SCHEMA IF NOT EXISTS marts;")
            con.execute("CREATE OR REPLACE TABLE marts.stats_weather_regression AS SELECT * FROM df_weather_reg")
            con.execute("CREATE OR REPLACE TABLE marts.stats_weather_lags AS SELECT * FROM df_weather_lags")
            logger.info("Saved stats_weather_regression and stats_weather_lags to DuckDB marts.")

    out_dir = Path("data/manifests")
    out_dir.mkdir(parents=True, exist_ok=True)
    df_weather_reg.to_csv(out_dir / "stats_weather_regression.csv", index=False)
    df_weather_lags.to_csv(out_dir / "stats_weather_lags.csv", index=False)

    print("\n" + "=" * 95)
    print("  🌦️ WEATHER DEMAND REGRESSION WITH FIXED EFFECTS (HOURLY Q2 2024)")
    print("=" * 95)
    print(df_weather_reg[["dependent_variable", "adjusted_r_squared", "precip_mm_pct_effect", "heavy_rain_pct_effect", "residual_corr_precip_lag0", "residual_corr_precip_lag1"]].to_markdown(index=False))
    print("=" * 95 + "\n")

    return df_weather_reg, df_weather_lags


if __name__ == "__main__":
    run_weather_regression_analysis()
