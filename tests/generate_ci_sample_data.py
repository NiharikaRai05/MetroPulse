"""
tests/generate_ci_sample_data.py
================================
Lightweight script executed during CI workflow to generate minimal realistic sample
datasets in data/raw/ and load them into DuckDB so that 'dbt build' and full pipeline
tests can execute rapidly (in < 30 seconds) within GitHub Actions Free Tier limits.
"""

import os
from pathlib import Path
import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"


def generate_ci_sample_data():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "taxi").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "zones").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "zones" / "shapefile").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "weather").mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "mta").mkdir(parents=True, exist_ok=True)

    # 1. Zone lookup CSV
    zones_list = []
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", "EWR"]
    for i in range(1, 266):
        b = boroughs[i % 5] if i != 1 else "EWR"
        zones_list.append({
            "LocationID": i,
            "Borough": b,
            "Zone": f"Sample Zone {i}",
            "service_zone": "Yellow Zone" if b == "Manhattan" else "Boro Zone"
        })
    pd.DataFrame(zones_list).to_csv(RAW_DIR / "zones" / "taxi_zone_lookup.csv", index=False)

    # 2. Zone Shapefile (for ST_Read / GeoPandas)
    poly = Polygon([(-74.01, 40.71), (-74.00, 40.71), (-74.00, 40.72), (-74.01, 40.72), (-74.01, 40.71)])
    gdf = gpd.GeoDataFrame({
        "LocationID": list(range(1, 266)),
        "Borough": [z["Borough"] for z in zones_list],
        "Zone": [z["Zone"] for z in zones_list],
        "service_zo": [z["service_zone"] for z in zones_list],
        "Shape_Leng": [0.04] * 265,
        "Shape_Area": [0.0001] * 265,
        "geometry": [poly] * 265
    }, crs="EPSG:4326")
    gdf.to_file(RAW_DIR / "zones" / "shapefile" / "taxi_zones.shp")

    # 3. Weather Hourly Parquet
    w_hours = pd.date_range("2024-04-01 00:00:00", "2024-06-30 23:00:00", freq="h")
    weather_df = pd.DataFrame({
        "time": w_hours.strftime("%Y-%m-%d %H:%M:%S"),
        "temperature_2m": np.random.uniform(10.0, 30.0, size=len(w_hours)),
        "precipitation": np.where(np.random.rand(len(w_hours)) > 0.85, np.random.uniform(0.5, 8.0, size=len(w_hours)), 0.0),
        "rain": np.where(np.random.rand(len(w_hours)) > 0.85, np.random.uniform(0.5, 8.0, size=len(w_hours)), 0.0),
        "snowfall": [0.0] * len(w_hours),
        "wind_speed_10m": np.random.uniform(5.0, 25.0, size=len(w_hours)),
        "cloud_cover": np.random.uniform(0.0, 100.0, size=len(w_hours)),
        "weather_code": [0] * len(w_hours)
    })
    weather_df.to_parquet(RAW_DIR / "weather" / "weather_nyc_2024_q2.parquet", compression="zstd")

    # 4. MTA Subway Ridership Parquet
    mta_rows = []
    for h in pd.date_range("2024-04-01", "2024-04-05", freq="h"):
        for st_id in ["R101", "R102", "R103"]:
            mta_rows.append({
                "transit_timestamp": h.isoformat(),
                "station_complex_id": st_id,
                "station_complex": f"Complex {st_id}",
                "borough": "Manhattan" if st_id == "R101" else "Brooklyn",
                "ridership": int(np.random.uniform(500, 3500)),
                "latitude": 40.75,
                "longitude": -73.98
            })
    pd.DataFrame(mta_rows).to_parquet(RAW_DIR / "mta" / "mta_subway_hourly_2024_q2.parquet", compression="zstd")

    # 5. Taxi Trip Sample Parquet files (Apr, May, Jun 2024)
    months = ["2024-04", "2024-05", "2024-06"]
    for m in months:
        t_start = pd.Timestamp(f"{m}-01 00:00:00")
        t_dates = pd.date_range(t_start, periods=100, freq="6h")
        trips = []
        for i, dt in enumerate(t_dates):
            trips.append({
                "VendorID": 1,
                "tpep_pickup_datetime": dt,
                "tpep_dropoff_datetime": dt + pd.Timedelta(minutes=15),
                "passenger_count": 1,
                "trip_distance": 2.5,
                "RatecodeID": 1,
                "store_and_fwd_flag": "N",
                "PULocationID": (i % 50) + 1,
                "DOLocationID": ((i + 5) % 50) + 1,
                "payment_type": 1 if i % 4 != 0 else 2,
                "fare_amount": 15.0,
                "extra": 1.0,
                "mta_tax": 0.5,
                "tip_amount": 3.0 if i % 4 != 0 else 0.0,
                "tolls_amount": 0.0,
                "improvement_surcharge": 1.0,
                "total_amount": 20.5 if i % 4 != 0 else 17.5,
                "congestion_surcharge": 2.5,
                "Airport_fee": 0.0
            })
        pd.DataFrame(trips).to_parquet(RAW_DIR / "taxi" / f"yellow_tripdata_{m}.parquet", compression="zstd")

    print(f"Generated CI sample datasets successfully in {RAW_DIR}")

    # Load raw tables into DuckDB
    from ingestion.load_raw import load_all_raw
    db_path = DATA_DIR / "metropulse.duckdb"
    load_all_raw(db_path)
    print(f"Loaded raw sample tables into {db_path}")


if __name__ == "__main__":
    generate_ci_sample_data()
