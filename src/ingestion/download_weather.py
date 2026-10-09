import logging
import json
from pathlib import Path
import requests
import pandas as pd
from src.ingestion.utils import get_data_dir

logger = logging.getLogger("metropulse.ingestion.weather")

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# NYC Coordinates (Central Park / Manhattan centroid approx 40.7128, -74.0060)
NYC_LAT = 40.7128
NYC_LON = -74.0060
TIMEZONE = "America/New_York"
START_DATE = "2024-04-01"
END_DATE = "2024-06-30"

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "surface_pressure",
    "wind_speed_10m"
]

def download_weather_data(force: bool = False) -> Path:
    """
    Downloads historical hourly weather for NYC (Q2 2024) from Open-Meteo.
    Saves as both raw JSON and Parquet for efficient DuckDB ingestion.
    """
    dest_dir = get_data_dir("raw/weather")
    json_path = dest_dir / "weather_nyc_2024_q2.json"
    parquet_path = dest_dir / "weather_nyc_2024_q2.parquet"

    if parquet_path.exists() and not force:
        logger.info(f"Weather parquet already exists: {parquet_path}")
        return parquet_path

    params = {
        "latitude": NYC_LAT,
        "longitude": NYC_LON,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": TIMEZONE
    }

    logger.info(f"Fetching Open-Meteo weather data ({START_DATE} to {END_DATE})...")
    resp = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Save raw JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Convert to tabular Parquet
    hourly_dict = data.get("hourly", {})
    df = pd.DataFrame(hourly_dict)
    df["timestamp"] = pd.to_datetime(df["time"])
    df.to_parquet(parquet_path, index=False)
    logger.info(f"Saved weather data to {parquet_path} ({len(df)} hourly records).")

    return parquet_path

if __name__ == "__main__":
    download_weather_data()
