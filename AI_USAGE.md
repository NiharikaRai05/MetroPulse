# AI Usage & Independent Verification Log

This document provides a transparent accounting of the AI tools utilized during the construction of the **MetroPulse** platform, the specific architectural areas where AI assistance was incorporated, representative prompts, and the validation procedures independently performed to ensure correctness, reproducibility, and analytical rigor.

---

## 🛠️ AI Tools Used

- **Antigravity AI / Gemini 3.7 Flash & Claude 3.5 Sonnet**: Used as pair programming assistants within the IDE for boilerplate scaffolding, SQL refactoring, dbt model syntax validation, Streamlit UI components, and unit test generation.
- **GitHub Copilot**: Used for in-line autocomplete and repetitive dictionary/schema typing.

---

## 🧩 Areas of AI Assistance & Representative Prompts

### 1. Ingestion & Resilience Logic
- **Scope:** Drafting retry logic with `tenacity`, calculating streaming SHA-256 digests, and building chunked downloads for NYC Socrata & Open-Meteo APIs.
- **Representative Prompt:**
  > *"Write an idempotent Python ingestion script using `requests` and `tenacity` to download NYC TLC Yellow Taxi parquet files for 2024-04 through 2024-06. Include SHA-256 checksumming, exponential backoff with jitter, and manifest logging into DuckDB."*

### 2. dbt SQL Modeling & Spatial Joins
- **Scope:** Generating DuckDB SQL syntax for date spines (`generate_series`), WMO weather classification CASE statements, and dimensional models (`dim_zone`, `mart_cube`).
- **Representative Prompt:**
  > *"Write a dbt marts model `mart_cube.sql` aggregating Q2 2024 taxi trips across date, hour, pickup borough, dropoff borough, payment type, and airport flags. Ensure it stores purely additive sums and counts with no pre-computed division ratios to avoid Simpson's Paradox downstream."*

### 3. Streamlit Multi-Page UI & Visualization
- **Scope:** Scaffolding the 6-page dashboard layout, custom CSS glassmorphic cards, and Plotly figure templates.
- **Representative Prompt:**
  > *"Build a dark-mode Streamlit dashboard with a 6-page navigation selector, sidebar dimensional filters, and dynamic ratio recomputations reading exclusively from compressed parquet files."*

---

## 🔍 Independent Human Verification

Every AI-generated component was subjected to manual review, execution, and verification:

1. **SQL Logic & Mathematical Precision**:
   - Manually checked that all financial and operational rates (e.g., `avg_fare_per_trip`, `avg_tip_pct`, `avg_speed_mph`) are calculated as **weighted averages from additive sums** (`SUM(fare_amount) / COUNT(*)`) rather than taking unweighted averages of averages.
   - Verified that cash trips (`payment_type_id = 2`) are segregated from electronic tip calculations.

2. **Data Sanitation & Filter Thresholds**:
   - Verified that trip durations < 60 seconds, trip distances > 100 miles, speeds > 85 mph, and negative fare amounts are flagged and quarantined in staging/intermediate layers.
   - Checked that timestamp boundaries are restricted to `2024-04-01 00:00:00` through `2024-06-30 23:59:59`.

3. **Execution & CI Test Passing**:
   - Ran `make build` and `pytest tests/` locally and verified that all dbt schema tests, custom data quality checks, and unit tests pass with zero failures.
   - Verified that `.github/workflows/ci.yml` runs successfully on GitHub Actions.

4. **Zero Secrets & INR 0 Verification**:
   - Inspected all code and configuration files to confirm that no proprietary API keys, passwords, or paid SaaS tokens are required.
