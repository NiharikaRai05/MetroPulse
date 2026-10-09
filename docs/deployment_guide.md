# MetroPulse Deployment & Public Verification Guide

This guide provides step-by-step instructions to deploy the **MetroPulse NYC Mobility Analytics Platform** to **Streamlit Community Cloud** (primary) and **Hugging Face Spaces** (fallback) directly from your public GitHub repository with **INR 0 cost, zero login gates, and no secret keys required**.

---

## 1. Prerequisites (Pre-Flight Check)

Ensure your repository contains the exported parquet assets and dependencies:

1. **Verify `requirements.txt`** at repository root contains:
   ```text
   streamlit>=1.35.0
   pandas>=2.2.0
   pyarrow>=15.0.0
   plotly>=5.22.0
   geopandas>=0.14.0
   shapely>=2.0.0
   duckdb>=1.0.0
   ```
2. **Commit exported data assets** (total bundle < 100 MB):
   - `dashboard/data/*.parquet`
   - `dashboard/data/taxi_zones_simplified.geojson`
   - `dashboard/data/last_refresh.json`
3. **Ensure public visibility**: Repository must be set to **Public** on GitHub.

---

## 2. Option A: Streamlit Community Cloud (Recommended)

### Step-by-Step Deployment:
1. Log in to [share.streamlit.io](https://share.streamlit.io/) with your GitHub account.
2. Click **"New app"** (or **"Create app"**).
3. Select **"I already have an app"** and configure:
   - **Repository:** `NiharikaRai05/MetroPulse` (select your public repository)
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
   - **App URL (optional):** `metropulse` (or default generated slug)
4. Click **"Advanced settings"** (if needed):
   - **Python version:** Select `3.10` or `3.11`
   - **Secrets:** Leave empty (MetroPulse requires zero secrets or API tokens).
5. Click **"Deploy!"**.
6. Wait 1–2 minutes for container build and package installation.

---

## 3. Option B: Hugging Face Spaces (Fallback)

If you prefer Hugging Face Spaces:

1. Log in to [huggingface.co](https://huggingface.co/) and click **"New Space"**.
2. Configure your Space:
   - **Space name:** `metropulse-nyc-mobility`
   - **License:** `mit` or `apache-2.0`
   - **Space SDK:** Select **Streamlit**
   - **Space hardware:** `CPU Basic · 2 vCPU · 16GB · Free`
   - **Visibility:** `Public`
3. Click **"Create Space"**.
4. In Space Settings / Repository, sync with your GitHub repo or add remote:
   ```bash
   git remote add hf https://huggingface.co/spaces/NiharikaRai05/metropulse-nyc-mobility
   git push hf main
   ```
5. If creating a custom root entrypoint, ensure `app.py` at root imports or forwards to `dashboard/app.py`:
   ```python
   # app.py (Space root wrapper)
   from dashboard.app import main
   if __name__ == "__main__":
       main()
   ```

---

## 4. Incognito / Public Verification Checklist

Perform these tests in a fresh **Private / Incognito Window** without being logged in to any account to guarantee zero-friction public evaluation:

| # | Check Item | Expected Result | Pass/Fail |
|---|---|---|:---:|
| 1 | **URL Access** | App loads immediately with no login wall, auth prompt, or email gate. | [ ] |
| 2 | **Sidebar Branding** | MetroPulse branding, date range `2024-04-01 to 2024-06-30`, and last refresh timestamp visible. | [ ] |
| 3 | **Executive Pulse (Page 1)** | 4 macro KPI cards render (Clean Taxi Trips, Passenger Expenditure, Subway Entries, Tip Ratio) without NaN/Error. | [ ] |
| 4 | **Temporal Dynamics (Page 2)** | Day-of-week × Hour heatmap and diurnal speed curves render smoothly with interactive hover states. | [ ] |
| 5 | **Geographic Map (Page 3)** | Zone map / choropleth and underserved zones leaderboard render without WebGL or projection errors. | [ ] |
| 6 | **Fares & Payments (Page 4)** | Fare component waterfall and payment method breakdown show accurate totals and percentages. | [ ] |
| 7 | **Weather & Transit (Page 5)** | Scatter plot of precipitation vs demand loads; methodology disclaimer banner is displayed. | [ ] |
| 8 | **Data Quality (Page 6)** | Anomaly profile audit table and data yield rate show clean hygiene metrics. | [ ] |
| 9 | **Multi-Filter Interaction** | Change date range or select a borough; verify all ratios and weighted averages dynamically recompute. | [ ] |
| 10 | **Zero Errors / Clean Logs** | No red `StreamlitAPIException` or Python traceback boxes appear on any view. | [ ] |
