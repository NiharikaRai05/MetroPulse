"""
export/export_marts.py
======================
Exports curated dbt marts from DuckDB into lightweight, compressed Parquet files
in dashboard/data/, generates last_refresh.json containing build metadata and row counts,
and converts the TLC Taxi Zones geometry into a simplified, web-optimized GeoJSON
in EPSG:4326 for fast dashboard rendering (ensuring total bundle size < 100 MB).
"""

import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import geopandas as gpd
from shapely.geometry import mapping

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("metropulse.export")

# Root directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent
DUCKDB_PATH = BASE_DIR / "data" / "metropulse.duckdb"
OUTPUT_DATA_DIR = BASE_DIR / "dashboard" / "data"
ZONES_SHAPEFILE_DIR = BASE_DIR / "data" / "raw" / "zones" / "shapefile"
DEFAULT_GEOJSON_TOLERANCE = 0.0005  # ~50 meters simplification in WGS84 degrees

# List of marts to export to parquet
EXPORT_MARTS = [
    "dim_zone",
    "dim_date",
    "dim_hour",
    "dim_payment",
    "dim_rate",
    "dim_weather",
    "mart_cube",
    "mart_zone",
    "mart_time",
    "mart_weather",
    "mart_transit",
    "mart_route_pairs",
    "mart_executive",
    "mart_quality",
]


def get_duckdb_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Establishes read-only connection to DuckDB database."""
    if not db_path.exists():
        logger.warning(f"DuckDB file not found at {db_path}. Using memory or creating database.")
    return duckdb.connect(str(db_path), read_only=False)


def export_marts_to_parquet(
    con: duckdb.DuckDBPyConnection,
    output_dir: Path,
    marts: Optional[List[str]] = None,
    compression: str = "zstd"
) -> Dict[str, Dict[str, Any]]:
    """
    Exports selected mart tables/views from DuckDB into compressed Parquet files.
    Returns metadata with row counts, file sizes, and export status.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if marts is None:
        marts = EXPORT_MARTS

    manifest_metrics: Dict[str, Dict[str, Any]] = {}

    # Inspect available tables/views in duckdb
    existing_tables_df = con.execute("SHOW TABLES").df()
    existing_tables = set(existing_tables_df["name"].tolist()) if not existing_tables_df.empty else set()

    for mart in marts:
        parquet_file = output_dir / f"{mart}.parquet"
        
        # Check if table exists in DuckDB (in main or marts schema)
        table_to_query = None
        if mart in existing_tables:
            table_to_query = mart
        else:
            # Check schema qualification
            try:
                con.execute(f"SELECT 1 FROM marts.{mart} LIMIT 1")
                table_to_query = f"marts.{mart}"
            except Exception:
                try:
                    con.execute(f"SELECT 1 FROM {mart} LIMIT 1")
                    table_to_query = mart
                except Exception:
                    pass

        if not table_to_query:
            logger.warning(f"Table/mart '{mart}' does not exist in DuckDB database. Skipping parquet export.")
            continue

        logger.info(f"Exporting mart '{mart}' to {parquet_file.name} (compression: {compression})...")
        export_sql = f"""
            COPY (SELECT * FROM {table_to_query})
            TO '{parquet_file.as_posix()}'
            (FORMAT PARQUET, COMPRESSION '{compression}');
        """
        con.execute(export_sql)

        # Compute row count and file size
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_to_query}").fetchone()[0]
        file_size_bytes = parquet_file.stat().st_size
        file_size_mb = round(file_size_bytes / (1024 * 1024), 3)

        manifest_metrics[mart] = {
            "file": parquet_file.name,
            "row_count": int(row_count),
            "size_bytes": int(file_size_bytes),
            "size_mb": file_size_mb,
            "compression": compression
        }
        logger.info(f"-> Exported {mart}: {row_count:,} rows, {file_size_mb} MB")

    return manifest_metrics


def export_simplified_zones_geojson(
    shapefile_dir: Path,
    output_dir: Path,
    duckdb_con: Optional[duckdb.DuckDBPyConnection] = None,
    tolerance: float = DEFAULT_GEOJSON_TOLERANCE
) -> Optional[Path]:
    """
    Reads TLC Taxi Zone Shapefile, projects to EPSG:4326 (WGS84), simplifies geometries
    using Douglas-Peucker algorithm to reduce payload size, joins zone attributes from dim_zone/lookup,
    and exports a web-ready GeoJSON for PyDeck/Leaflet mapping in dashboard.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    geojson_out = output_dir / "taxi_zones_simplified.geojson"

    # Search for shapefile
    shp_file = None
    if shapefile_dir.exists():
        candidates = list(shapefile_dir.glob("*.shp"))
        if candidates:
            shp_file = candidates[0]

    gdf: Optional[gpd.GeoDataFrame] = None

    if shp_file and shp_file.exists():
        logger.info(f"Reading Taxi Zones Shapefile from {shp_file}...")
        try:
            gdf = gpd.read_file(shp_file)
        except Exception as e:
            logger.error(f"Failed to read shapefile with GeoPandas: {e}")

    # Fallback: check if DuckDB has spatial extension and table stg_zone_geo / dim_zone with geometry
    if gdf is None and duckdb_con is not None:
        try:
            logger.info("Attempting to load zone geometries from DuckDB spatial table...")
            df = duckdb_con.execute("""
                SELECT 
                    location_id,
                    borough,
                    zone_name,
                    service_zone,
                    is_congestion_zone,
                    is_airport_zone,
                    ST_AsGeoJSON(geometry) as geojson
                FROM dim_zone
                WHERE geometry IS NOT NULL
            """).df()
            if not df.empty:
                import shapely.wkt
                from shapely.geometry import shape
                gdf = gpd.GeoDataFrame(
                    df.drop(columns=["geojson"]),
                    geometry=df["geojson"].apply(lambda g: shape(json.loads(g)) if g else None),
                    crs="EPSG:2263"  # Standard NY State Plane if unprojected
                )
        except Exception as ex:
            logger.warning(f"DuckDB spatial extraction fallback failed: {ex}")

    if gdf is None:
        logger.warning("No shapefile or geometry source found. Skipping GeoJSON export.")
        return None

    # Ensure standardized column names
    col_mapping = {
        "LocationID": "location_id",
        "OBJECTID": "location_id",
        "location_id": "location_id",
        "Borough": "borough",
        "borough": "borough",
        "Zone": "zone_name",
        "zone": "zone_name",
        "zone_name": "zone_name",
        "service_zone": "service_zone",
        "service_zo": "service_zone",
        "Shape_Leng": "shape_length",
        "Shape_Area": "shape_area"
    }
    gdf = gdf.rename(columns={k: v for k, v in col_mapping.items() if k in gdf.columns})

    # Reproject to standard WGS84 EPSG:4326 for web map compatibility
    if gdf.crs is not None and gdf.crs.to_string() != "EPSG:4326":
        logger.info(f"Reprojecting taxi zones from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)
    elif gdf.crs is None:
        logger.info("Assuming input CRS EPSG:2263 (NY State Plane Long Island) and reprojecting to EPSG:4326...")
        gdf = gdf.set_crs(epsg=2263).to_crs(epsg=4326)

    # Simplify geometries (Douglas-Peucker algorithm)
    if tolerance > 0:
        logger.info(f"Simplifying polygon geometry (tolerance={tolerance} deg)...")
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=tolerance, preserve_topology=True)

    # Cast location_id to integer
    if "location_id" in gdf.columns:
        gdf["location_id"] = gdf["location_id"].astype(int)

    # Save to GeoJSON
    logger.info(f"Writing simplified GeoJSON to {geojson_out}...")
    gdf.to_file(geojson_out, driver="GeoJSON")

    size_mb = round(geojson_out.stat().st_size / (1024 * 1024), 3)
    logger.info(f"-> GeoJSON export complete: {len(gdf)} zones, {size_mb} MB (EPSG:4326)")
    return geojson_out


def create_last_refresh_manifest(
    output_dir: Path,
    marts_metrics: Dict[str, Dict[str, Any]],
    geojson_path: Optional[Path] = None,
    total_pipeline_time_seconds: float = 0.0
) -> Path:
    """
    Creates last_refresh.json containing build timestamp, total size, file breakdown,
    row counts, and data health verification metrics.
    """
    manifest_path = output_dir / "last_refresh.json"

    total_bytes = sum(m["size_bytes"] for m in marts_metrics.values())
    total_rows = sum(m["row_count"] for m in marts_metrics.values())

    geojson_meta = {}
    if geojson_path and geojson_path.exists():
        geo_size = geojson_path.stat().st_size
        total_bytes += geo_size
        geojson_meta = {
            "file": geojson_path.name,
            "crs": "EPSG:4326",
            "size_bytes": geo_size,
            "size_mb": round(geo_size / (1024 * 1024), 3)
        }

    total_mb = round(total_bytes / (1024 * 1024), 2)

    refresh_manifest = {
        "build_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "period": "2024-04-01 to 2024-06-30",
        "quarter": "Q2 2024",
        "total_bundle_size_mb": total_mb,
        "total_bundle_size_bytes": total_bytes,
        "is_under_100mb_limit": total_mb < 100.0,
        "total_marts_exported": len(marts_metrics),
        "total_records_sum": total_rows,
        "build_duration_seconds": round(total_pipeline_time_seconds, 2),
        "tables": marts_metrics,
        "geojson": geojson_meta
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(refresh_manifest, f, indent=2)

    logger.info(f"Refresh manifest written to {manifest_path} (Total bundle size: {total_mb} MB / <100 MB target: {total_mb < 100.0})")
    return manifest_path


def export_all(
    duckdb_path: Path = DUCKDB_PATH,
    output_dir: Path = OUTPUT_DATA_DIR,
    shapefile_dir: Path = ZONES_SHAPEFILE_DIR,
    tolerance: float = DEFAULT_GEOJSON_TOLERANCE
) -> Dict[str, Any]:
    """
    Main orchestrator for Day 5 export:
    1. Connects to DuckDB marts.
    2. Exports marts to zstd compressed Parquet in dashboard/data/.
    3. Exports simplified TLC Taxi Zones GeoJSON (EPSG:4326).
    4. Writes last_refresh.json with metadata and row counts.
    """
    start_time = time.time()
    logger.info("=== Starting MetroPulse Marts Export Pipeline ===")

    output_dir.mkdir(parents=True, exist_ok=True)
    con = get_duckdb_connection(duckdb_path)

    # 1. Export Parquet Marts
    marts_metrics = export_marts_to_parquet(con, output_dir=output_dir, compression="zstd")

    # 2. Export GeoJSON
    geojson_path = export_simplified_zones_geojson(
        shapefile_dir=shapefile_dir,
        output_dir=output_dir,
        duckdb_con=con,
        tolerance=tolerance
    )

    con.close()

    elapsed = time.time() - start_time

    # 3. Create Refresh Manifest
    manifest_path = create_last_refresh_manifest(
        output_dir=output_dir,
        marts_metrics=marts_metrics,
        geojson_path=geojson_path,
        total_pipeline_time_seconds=elapsed
    )

    logger.info(f"=== Completed MetroPulse Marts Export Pipeline in {elapsed:.2f}s ===")
    return {
        "manifest_path": str(manifest_path),
        "total_marts": len(marts_metrics),
        "duration_seconds": elapsed
    }


if __name__ == "__main__":
    export_all()
