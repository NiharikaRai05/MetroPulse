import json
from pathlib import Path
from export.export_marts import export_all

def export_data(duckdb_path: str = "data/metropulse.duckdb", output_dir: str = "dashboard/data"):
    """
    Exports analytical datasets, marts to parquet, GeoJSON, and last_refresh.json.
    """
    return export_all(
        duckdb_path=Path(duckdb_path),
        output_dir=Path(output_dir)
    )

if __name__ == "__main__":
    export_data()

