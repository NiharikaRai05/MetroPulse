# MetroPulse Architecture & Milestone Plan

## 1. Project Overview
**MetroPulse** is an end-to-end NYC mobility analytics platform built on DuckDB, dbt, Python, and Streamlit, covering April 1, 2024 to June 30, 2024 (Q2 2024).

### Key Ground Rules & Defense Principles
1. **Raw Layer Immutability:** Raw data landing zone (`data/raw/`) is write-once and partitioned cleanly.
2. **Zero Paid Services (INR 0):** Uses public endpoints without API keys (TLC CloudFront, Open-Meteo Historical API, NY Open Data Socrata API).
3. **Reproducibility:** A single entry point (`make build` / `make all`) runs the entire ingestion, transformation, data quality tests, and generates mart tables in DuckDB.
4. **Analytical Rigor:** 
   - Taxi metrics reflect *market activity & passenger trip expenditure*, not company profit/revenue.
   - All correlations vs weather/subway ridership are framed strictly as *associations/correlations*, never causal claims.
   - Zero hardcoded numbers in dashboards or documentation.

---

## 2. Directory Structure

```
MetroPulse/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Automated test & build validation
├── data/
│   ├── raw/                       # Immutable raw downloads (.parquet, .csv, .json, .zip)
│   │   ├── taxi/
│   │   ├── zones/
│   │   ├── weather/
│   │   └── mta/
│   ├── processed/                 # DuckDB database storage
│   └── docs/                      # Generated artifacts
├── dbt_metropulse/                # dbt-duckdb project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/               # Staging models (schema casting, cleaning)
│   │   │   ├── stg_taxi_trips.sql
│   │   │   ├── stg_taxi_zones.sql
│   │   │   ├── stg_weather_hourly.sql
│   │   │   └── stg_mta_ridership_hourly.sql
│   │   ├── intermediate/          # Joins & rollups
│   │   └── marts/                 # Business metrics & dimensional marts
│   │       ├── fct_mobility_hourly.sql
│   │       ├── fct_taxi_market_activity.sql
│   │       ├── dim_zones.sql
│   │       └── dim_dates.sql
│   └── tests/                     # Schema & custom DQ tests
├── src/
│   ├── ingestion/
│   │   ├── download_taxi.py       # TLC Yellow Taxi (Apr-Jun 2024)
│   │   ├── download_zones.py      # TLC Taxi Zone CSV & Shapefile
│   │   ├── download_weather.py    # Open-Meteo Historical API (Apr-Jun 2024)
│   │   ├── download_mta.py        # Socrata MTA Subway Hourly Ridership
│   │   └── utils.py               # Retry logic (tenacity), logging, HTTP session
│   ├── analytics/                 # Statistical modeling & correlation analysis
│   └── dashboard/                 # Streamlit application
│       ├── app.py
│       ├── components/
│       └── pages/
├── tests/                         # Python unit tests
├── Makefile                       # One-command orchestration
├── requirements.txt               # Dependencies (DuckDB, dbt-duckdb, streamlit, etc.)
└── README.md
```

---

## 3. Timeline Breakdown

- **Day 1: Ingestion Pipeline & Raw Landings**
  - Resilient ingestion with `requests` + `tenacity` (retry, backoff, checksum/size validation).
  - Raw storage for TLC Yellow Parquet (Apr/May/Jun 2024), Zone Lookup CSV + Shapefile ZIP, Open-Meteo Weather JSON/Parquet, and MTA Subway Socrata JSON/Parquet.
- **Day 2: Staging & Data Quality (DQ)**
  - DuckDB raw tables setup and staging SQL schemas.
  - Data sanitation: filtering trip timestamps to exact 2024-04-01 to 2024-06-30 range, handling negative fares, zero distances, and invalid zone IDs.
- **Day 3: Core Marts, SQL Metrics & dbt Tests**
  - Hour-zone mobility aggregates (taxi trips, passenger counts, subway station taps, precipitation, temperature).
  - dbt generic and singular tests (no null primary keys, positive trip durations, referential integrity).
- **Day 4: Statistical Analysis**
  - Weather sensitivity (rain vs taxi demand vs subway ridership).
  - Spatial and temporal peak congestion & market activity metrics.
- **Day 5: Streamlit Dashboard**
  - High-aesthetic interactive dashboard with PyDeck/Plotly visualizations, KPI summary cards, filter bars, and zero hardcoded metrics.
- **Day 6: Memo, README & GitHub Actions CI**
  - Executive defense memo with technical decisions, methodology, and limitations.
- **Day 7: Walkthrough & Delivery Validation**
