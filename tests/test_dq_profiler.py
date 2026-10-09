import tempfile
import unittest
from pathlib import Path
import duckdb
import pandas as pd
from analysis.profile_quality import run_profiling

class TestDataQualityProfiling(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.duckdb_path = self.base_dir / "test.duckdb"
        self.output_csv = self.base_dir / "profile.csv"

        # Create mock raw.yellow_trips containing all 12 issue variations
        con = duckdb.connect(str(self.duckdb_path))
        con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        
        # 10 test rows with intentional DQ anomalies
        mock_data = pd.DataFrame([
            # Row 0: Valid clean row
            {"VendorID": 1, "tpep_pickup_datetime": "2024-05-01 10:00:00", "tpep_dropoff_datetime": "2024-05-01 10:15:00", "passenger_count": 1, "trip_distance": 2.5, "RatecodeID": 1, "payment_type": 1, "fare_amount": 15.0, "extra": 1.0, "mta_tax": 0.5, "tip_amount": 3.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 23.0, "PULocationID": 161, "DOLocationID": 236},
            # Row 1: Issue 1 (Outside target period: 2024-03-31)
            {"VendorID": 1, "tpep_pickup_datetime": "2024-03-31 23:59:00", "tpep_dropoff_datetime": "2024-04-01 00:10:00", "passenger_count": 1, "trip_distance": 1.5, "RatecodeID": 1, "payment_type": 1, "fare_amount": 10.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 2.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 16.0, "PULocationID": 100, "DOLocationID": 101},
            # Row 2: Issue 2 (Dropoff <= Pickup)
            {"VendorID": 2, "tpep_pickup_datetime": "2024-05-01 12:00:00", "tpep_dropoff_datetime": "2024-05-01 11:55:00", "passenger_count": 1, "trip_distance": 1.0, "RatecodeID": 1, "payment_type": 1, "fare_amount": 8.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 1.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 13.0, "PULocationID": 100, "DOLocationID": 101},
            # Row 3: Issue 3 (Excessive duration: 15 hours)
            {"VendorID": 2, "tpep_pickup_datetime": "2024-05-01 08:00:00", "tpep_dropoff_datetime": "2024-05-01 23:30:00", "passenger_count": 1, "trip_distance": 5.0, "RatecodeID": 1, "payment_type": 1, "fare_amount": 30.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 5.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 39.0, "PULocationID": 100, "DOLocationID": 101},
            # Row 4: Issue 4 (Zero distance with positive fare)
            {"VendorID": 1, "tpep_pickup_datetime": "2024-05-02 14:00:00", "tpep_dropoff_datetime": "2024-05-02 14:10:00", "passenger_count": 1, "trip_distance": 0.0, "RatecodeID": 1, "payment_type": 1, "fare_amount": 20.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 0.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 24.0, "PULocationID": 100, "DOLocationID": 101},
            # Row 5: Issue 5 (Impossible speed: 20 miles in 2 minutes = 600 mph)
            {"VendorID": 2, "tpep_pickup_datetime": "2024-05-03 10:00:00", "tpep_dropoff_datetime": "2024-05-03 10:02:00", "passenger_count": 1, "trip_distance": 20.0, "RatecodeID": 1, "payment_type": 1, "fare_amount": 50.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 0.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 54.0, "PULocationID": 100, "DOLocationID": 101},
            # Row 6: Issue 6 (Negative fare amount: -$15)
            {"VendorID": 1, "tpep_pickup_datetime": "2024-05-04 10:00:00", "tpep_dropoff_datetime": "2024-05-04 10:15:00", "passenger_count": 1, "trip_distance": 2.0, "RatecodeID": 1, "payment_type": 1, "fare_amount": -15.0, "extra": 0.0, "mta_tax": -0.5, "tip_amount": 0.0, "tolls_amount": 0.0, "improvement_surcharge": -1.0, "congestion_surcharge": -2.5, "Airport_fee": 0.0, "total_amount": -19.0, "PULocationID": 100, "DOLocationID": 101},
            # Row 7: Issue 7 (Unknown zone: PULocationID=264)
            {"VendorID": 1, "tpep_pickup_datetime": "2024-05-05 10:00:00", "tpep_dropoff_datetime": "2024-05-05 10:15:00", "passenger_count": 1, "trip_distance": 2.0, "RatecodeID": 1, "payment_type": 1, "fare_amount": 12.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 2.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 18.0, "PULocationID": 264, "DOLocationID": 101},
            # Row 8: Issue 9 (Passenger count = 0)
            {"VendorID": 2, "tpep_pickup_datetime": "2024-05-06 10:00:00", "tpep_dropoff_datetime": "2024-05-06 10:15:00", "passenger_count": 0, "trip_distance": 2.0, "RatecodeID": 1, "payment_type": 1, "fare_amount": 12.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 2.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 18.0, "PULocationID": 100, "DOLocationID": 101},
            # Row 9: Issue 11 (Cash payment 2 with tip > $0)
            {"VendorID": 2, "tpep_pickup_datetime": "2024-05-07 10:00:00", "tpep_dropoff_datetime": "2024-05-07 10:15:00", "passenger_count": 1, "trip_distance": 2.0, "RatecodeID": 1, "payment_type": 2, "fare_amount": 12.0, "extra": 0.0, "mta_tax": 0.5, "tip_amount": 5.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0, "congestion_surcharge": 2.5, "Airport_fee": 0.0, "total_amount": 21.0, "PULocationID": 100, "DOLocationID": 101},
        ])
        
        con.execute("CREATE TABLE raw.yellow_trips AS SELECT * FROM mock_data;")
        con.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_profiling_detects_all_issues(self):
        df_result = run_profiling(duckdb_path=str(self.duckdb_path), output_csv=str(self.output_csv))
        self.assertIsNotNone(df_result)
        self.assertEqual(len(df_result), 12)  # 12 issues verified

        # Check required columns
        expected_cols = ["issue_id", "issue_name", "severity", "issue_description", "affected_rows", "total_dataset_rows", "pct_of_dataset"]
        for col in expected_cols:
            self.assertIn(col, df_result.columns)

        # Check specific issue detection counts
        issues_dict = dict(zip(df_result["issue_name"], df_result["affected_rows"]))
        self.assertEqual(issues_dict["pickup_outside_target_period"], 1)
        self.assertEqual(issues_dict["dropoff_before_or_equal_pickup"], 1)
        self.assertEqual(issues_dict["excessive_trip_duration"], 1)
        self.assertEqual(issues_dict["distance_anomalies"], 1)
        self.assertEqual(issues_dict["impossible_speed"], 1)
        self.assertEqual(issues_dict["fare_amount_anomalies"], 1)
        self.assertEqual(issues_dict["unknown_or_invalid_location_ids"], 1)
        self.assertEqual(issues_dict["passenger_count_anomalies"], 1)
        self.assertEqual(issues_dict["cash_tip_greater_than_zero"], 1)

if __name__ == "__main__":
    unittest.main()
