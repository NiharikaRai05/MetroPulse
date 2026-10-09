import unittest
import pandas as pd
from pathlib import Path
from dashboard.data_loader import (
    compute_weighted_metrics,
    filter_mart_cube,
    load_parquet,
    load_last_refresh,
)

class TestDashboardComponents(unittest.TestCase):
    def test_weighted_metrics_recomputation(self):
        # Sample additive cube slice
        df = pd.DataFrame([
            {"trip_count": 100, "total_passenger_count": 120, "total_fare_amount": 2000.0, "total_tip_amount": 400.0, "total_passenger_spending": 2700.0, "total_distance_miles": 250.0, "total_duration_minutes": 1500.0},
            {"trip_count": 200, "total_passenger_count": 280, "total_fare_amount": 3000.0, "total_tip_amount": 300.0, "total_passenger_spending": 3900.0, "total_distance_miles": 350.0, "total_duration_minutes": 2100.0}
        ])
        metrics = compute_weighted_metrics(df)
        
        self.assertEqual(metrics["total_trips"], 300)
        self.assertEqual(metrics["total_passengers"], 400)
        self.assertEqual(metrics["total_fare"], 5000.0)
        self.assertEqual(metrics["total_tips"], 700.0)
        # Avg fare = 5000 / 300 = 16.67
        self.assertAlmostEqual(metrics["avg_fare_per_trip"], 16.67, places=2)
        # Tip pct = 700 / 5000 * 100 = 14.0%
        self.assertAlmostEqual(metrics["avg_tip_pct"], 14.0, places=2)
        # Avg distance = 600 / 300 = 2.0 miles
        self.assertEqual(metrics["avg_distance_miles"], 2.0)

    def test_empty_dataframe_handled_safely(self):
        empty_df = pd.DataFrame()
        metrics = compute_weighted_metrics(empty_df)
        self.assertEqual(metrics["total_trips"], 0)
        self.assertEqual(metrics["avg_fare_per_trip"], 0.0)
        self.assertEqual(metrics["avg_tip_pct"], 0.0)

    def test_filter_mart_cube_filtering(self):
        df = pd.DataFrame([
            {"date_day": pd.to_datetime("2024-04-10").date(), "hour_of_day": 8, "pickup_borough": "Manhattan", "dropoff_borough": "Brooklyn", "payment_type_id": 1, "rate_code_id": 1, "is_airport_trip": False, "weather_is_raining": 0, "weather_is_heavy_rain": 0, "trip_count": 50},
            {"date_day": pd.to_datetime("2024-05-15").date(), "hour_of_day": 18, "pickup_borough": "Queens", "dropoff_borough": "Manhattan", "payment_type_id": 1, "rate_code_id": 2, "is_airport_trip": True, "weather_is_raining": 1, "weather_is_heavy_rain": 1, "trip_count": 80}
        ])
        
        # Test airport filter
        filtered_airport = filter_mart_cube(df, airport_filter="Airport Trips Only")
        self.assertEqual(len(filtered_airport), 1)
        self.assertEqual(filtered_airport.iloc[0]["pickup_borough"], "Queens")

        # Test borough filter
        filtered_boro = filter_mart_cube(df, pickup_boroughs=["Manhattan"])
        self.assertEqual(len(filtered_boro), 1)
        self.assertEqual(filtered_boro.iloc[0]["pickup_borough"], "Manhattan")

        # Test daypart filter
        filtered_dp = filter_mart_cube(df, selected_dayparts=["Evening Rush (16:00 - 19:59)"])
        self.assertEqual(len(filtered_dp), 1)
        self.assertEqual(filtered_dp.iloc[0]["hour_of_day"], 18)

    def test_parquet_marts_loading(self):
        df_cube = load_parquet("mart_cube")
        self.assertFalse(df_cube.empty)
        df_zone = load_parquet("dim_zone")
        self.assertFalse(df_zone.empty)
        manifest = load_last_refresh()
        self.assertIn("period", manifest)

if __name__ == "__main__":
    unittest.main()
