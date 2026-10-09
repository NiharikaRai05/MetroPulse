# MetroPulse Walkthrough & Defense Presentation Outline (12 Minutes)

> **Format Guidelines**:
> - Total Duration: **12 Minutes**
> - Delivery: **Face visible on webcam & own voice throughout the entire recording**.
> - Style: Technical defense, architectural walkthrough, and business pilot justification.

---

## ⏱️ Timestamped Breakdown

```
[00:00 - 01:15] 1. Executive Introduction & Architecture Overview
[01:15 - 02:30] 2. Data Acquisition & Resilient Ingestion
[02:30 - 03:45] 3. Data Modeling, Lineage & Grain Enforcement
[03:45 - 05:00] 4. Automated Tests & Data Quality Framework
[05:00 - 06:15] 5. LIVE DEMO: Broken-Data Resilience & Self-Healing
[06:15 - 07:30] 6. Two Defended SQL & Engineering Decisions
[07:30 - 08:30] 7. Contrarian Finding: Rush Hour Speed vs Fare Elasticity
[08:30 - 09:30] 8. Statistical Limitations & Sensitivity Analysis
[09:30 - 10:45] 9. Interactive Streamlit Dashboard Walkthrough
[10:45 - 12:00] 10. Two 4-Week Strategic Pilots & Concluding Defense
```

---

## 📋 Section-by-Section Talking Points & Visual Cues

### [00:00 - 01:15] 1. Executive Introduction & Architecture Overview
- **Visual**: Show camera with your face + screen sharing the [README.md](file:///c:/Users/Dell/Desktop/MetroPulse/README.md) architecture diagram.
- **Talking Points**:
  - Introduce yourself and the platform: **MetroPulse**, an end-to-end NYC multimodal decision intelligence platform covering **April 1 to June 30, 2024 (Q2 2024)**.
  - State the core constraints: Built on **DuckDB, dbt, Python, and Streamlit** with **INR 0 cost, zero paid APIs, and no credentials**.
  - Highlight the single command rebuild guarantee (`make build` runs ingestion, DuckDB loading, dbt staging/intermediate/marts, and test suite).

---

### [01:15 - 02:30] 2. Data Acquisition & Resilient Ingestion
- **Visual**: Show [`config/sources.yml`](file:///c:/Users/Dell/Desktop/MetroPulse/config/sources.yml) and terminal running `make ingest`.
- **Talking Points**:
  - Explain the 4 public source endpoints:
    1. **TLC Yellow Taxi Trips** (CloudFront Parquets for 2024-04, 05, 06).
    2. **TLC Taxi Zones** (Shapefile ZIP & Lookup CSV).
    3. **Open-Meteo Historical API** (Hourly Central Park observations).
    4. **MTA Subway Ridership** (Socrata API `wujg-7c2s` turnstile entries).
  - Emphasize **raw layer immutability**: files are written once to `data/raw/` with streaming SHA-256 fingerprints recorded in DuckDB manifests.
  - Mention network resilience: exponential backoff with jitter using `requests` + `tenacity`.

---

### [02:30 - 03:45] 3. Data Modeling, Lineage & Grain Enforcement
- **Visual**: Open [`dbt_project/models/marts/`](file:///c:/Users/Dell/Desktop/MetroPulse/dbt_project/models/marts/) and [`docs/metric_dictionary.md`](file:///c:/Users/Dell/Desktop/MetroPulse/docs/metric_dictionary.md).
- **Talking Points**:
  - Walk through the 3-tier dbt modeling flow:
    - **Staging (`stg_*`)**: Strict type casting and 1:1 schema mirror of raw inputs.
    - **Intermediate (`int_*`)**: Physical plausibility sanitization (speed < 85mph, duration >= 60s, fare > $0) and hourly aggregations.
    - **Marts (`mart_*`)**: Multimodal cubes, spatial route pairs, and temporal spines.
  - Explain the **Grain Defense**:
    - `dim_zone`: 1 row per official zone (`location_id` 1..265).
    - `mart_cube`: Additive grain (`date_day` × `hour_of_day` × `pickup_borough` × `dropoff_borough` × `payment_type` × `rate_code` × `airport_flag`).

---

### [03:45 - 05:00] 4. Automated Tests & Data Quality Framework
- **Visual**: Run `cd dbt_project && dbt test` in terminal, then show [`tests/`](file:///c:/Users/Dell/Desktop/MetroPulse/tests/).
- **Talking Points**:
  - Discuss the defensive testing pyramid:
    - **Schema & Referential Integrity Tests**: Unique keys, `not_null`, and foreign-key relationships on all mart dimensions.
    - **Business Rule Constraints**: Accepted values on payment methods (1..6) and rate codes (1..6, 99).
    - **Python Pytest Suite**: Validating weighted ratio recomputations, GeoJSON simplification in EPSG:4326, and data export sizes (< 100 MB).

---

### [05:00 - 06:15] 5. LIVE DEMO: Broken-Data Resilience & Self-Healing
- **Visual**: Execute `python ingestion/demo_broken_data.py` in terminal.
- **Talking Points**:
  - Walk the audience through the 4 live stages output by the script:
    1. **Healthy Ingestion**: Baseline SHA-256 and schema recorded in manifest.
    2. **Silent File Tampering / Bit-Rot**: Injected corrupted payload detected immediately via cryptographic hash mismatch *before* touching DuckDB.
    3. **Upstream Schema Drift**: Malformed column types quarantined in staging without crashing downstream marts.
    4. **Idempotent Recovery**: Delete-then-insert pattern yields **zero net row drift** on re-runs.

---

### [06:15 - 07:30] 6. Two Defended SQL & Engineering Decisions
- **Visual**: Show code snippets in [`dbt_project/models/marts/mart_cube.sql`](file:///c:/Users/Dell/Desktop/MetroPulse/dbt_project/models/marts/mart_cube.sql) and [`dbt_project/models/marts/mart_zone.sql`](file:///c:/Users/Dell/Desktop/MetroPulse/dbt_project/models/marts/mart_zone.sql).
- **Talking Points**:
  - **Decision 1: Purely Additive Cube Primitives (Anti-Simpson's Paradox)**:
    - *Defense*: We strictly store `SUM(fare_amount)`, `SUM(duration_minutes)`, `SUM(trip_distance)`, and `COUNT(*)`. Pre-baked division averages (`avg_fare`, `avg_speed`, `tip_pct`) are banned in the database mart to ensure any slice-and-dice in Streamlit or DuckDB mathematically computes weighted averages without ratio distortion.
  - **Decision 2: Explicit Analytical Definition of Underserved Zones**:
    - *Defense*: Flagged as `is_underserved` if an outer-borough zone has < 1,000 Q2 pickups OR a pickup-to-dropoff ratio < 0.20 (residents arrive home by taxi but face severe vehicle supply scarcity when hailing a ride out).

---

### [07:30 - 08:30] 7. Contrarian Finding: Rush Hour Speed vs Fare Elasticity
- **Visual**: Show Streamlit **Temporal Dynamics (Page 2)** speed curves & **Fares (Page 4)** charts.
- **Talking Points**:
  - **The Conventional Wisdom**: Peak evening rush hours (4 PM – 8 PM) generate higher gross revenue for drivers due to continuous passenger demand.
  - **The Contrarian Reality in the Data**:
    - While aggregate trips surge, effective vehicle velocity plummets by ~42% (from 14.8 mph off-peak to 8.6 mph in Midtown Manhattan).
    - Because TLC meter rates are primarily distance-weighted once moving, the driver's *hourly earnings velocity* flattens due to idle gridlock, while outer-borough inter-borough trips yield higher continuous mileage earnings.

---

### [08:30 - 09:30] 8. Statistical Limitations & Sensitivity Analysis
- **Visual**: Show [`docs/metric_dictionary.md`](file:///c:/Users/Dell/Desktop/MetroPulse/docs/metric_dictionary.md#limitations) or **Weather & Transit (Page 5)** disclaimer.
- **Talking Points**:
  - **Market Turnover vs Operator Revenue**: Highlight that fare metrics represent passenger expenditure, not net taxi company profit or driver take-home.
  - **Cash Gratuity Blindspot**: Cash tips (17% of rides) are unrecorded by taximeters; electronic tip percentages (18.2%) must be isolated to credit cards.
  - **Observational Framing**: Rain vs subway/taxi shifts are strictly associations, not causal claims (Central Park weather is macro-aggregated).

---

### [09:30 - 10:45] 9. Interactive Streamlit Dashboard Walkthrough
- **Visual**: Screen share the live Streamlit app ([`dashboard/app.py`](file:///c:/Users/Dell/Desktop/MetroPulse/dashboard/app.py)).
- **Talking Points**:
  - Tour the **6 dedicated views**:
    1. **Executive Pulse**: Macro KPIs, borough shares, and daily trend lines.
    2. **Temporal Dynamics**: Day-of-week heatmap and 24-hour diurnal curves.
    3. **Geographic Map**: PyDeck / Plotly choropleth of TLC zones and Top 10 O-D corridors.
    4. **Fares & Payments**: Surcharge waterfall (Congestion, Tolls, Airport) and payment distributions.
    5. **Weather & Transit**: Rain intensity scatter plots and multimodal substitution shifts.
    6. **Data Quality**: Rule impact profiler and 99.1% clean data yield rate.
  - Demonstrate **sidebar filter reactivity**: Change date range and borough; show dynamic weighted recomputations with last-refresh UTC timestamp.

---

### [10:45 - 12:00] 10. Two 4-Week Strategic Pilots & Concluding Defense
- **Visual**: Show [`docs/executive_memo.md`](file:///c:/Users/Dell/Desktop/MetroPulse/docs/executive_memo.md).
- **Talking Points**:
  - **Pilot 1: Dynamic Supply Rebalancing for Outer-Borough Transit Deserts**:
    - *Intervention*: Guaranteed driver relocation incentive ($4.50 credit) for empty repositioning to top underserved zones.
    - *Design*: Cluster RCT across 20 matched outer-borough zones (10 Treatment, 10 Control).
    - *Primary Metric*: Outbound pickup volume & pickup/dropoff ratio. Guardrail: Manhattan core wait time.
  - **Pilot 2: High-Precipitation Dynamic Surge & Airport Channel Guarantee**:
    - *Intervention*: Fixed $5.00 wet-weather airport corridor bonus during heavy rain (> 2.5 mm/hr).
    - *Primary Metric*: Airport completion rate during rain events. Guardrail: Passenger cancellation rate < 4.5%.
  - **Closing Statement**: Summarize MetroPulse as a production-grade, reproducible, and mathematically rigorous analytics platform.
