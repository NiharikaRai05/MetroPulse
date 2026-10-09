# MetroPulse Analytical Engineering Metric Dictionary (Q2 2024)

> Comprehensive governance document and metric specification for all calculated dimensions, facts, aggregates, and executive KPIs across the **MetroPulse NYC Multimodal Mobility Analytics Platform**.

---

## 🏛️ Metric Classification & Epistemic Taxonomy

Every metric exposed in the MetroPulse data warehouse and Streamlit visualization layer is cataloged with an explicit epistemic status:
1. **Observed Fact:** Directly metered, counted, or recorded at point of engagement (e.g. metered base fare, hardware turnstile event, digital card tip).
2. **Derived Fact:** Directly aggregated from observed facts without statistical modeling (e.g. trip counts, total expenditure).
3. **Estimate / Proxy:** Derived via deterministic physical formulas or spatial approximations (e.g. trip duration, transit distance speed, imputed passenger counts).
4. **Policy / Heuristic Assumption:** Heuristics, thresholds, and business logic applied for classification and elasticity analyses (e.g. underserved zone criteria, Lag-1 / Lag-2 weather lag assumptions).

All weather and transit relationships represent observational **Association** rather than causation.


---

## 📊 Core Mobility & Fact Metrics

### 1. Clean Trip Count (`trip_count` / `total_clean_trips`)
- **Epistemic Classification:** **Observed Fact**
- **SQL Definition:**
  ```sql
  COUNT(*)
  ```
- **Grain:** Model dependent (1 row per valid trip in `fct_trips`, or grouped by date/hour/zone).
- **Filters & Exclusions Applied:**
  - Pickup timestamp strictly within `2024-04-01 00:00:00` to `2024-06-30 23:59:59`.
  - Excludes trips where `dropoff_datetime <= pickup_datetime`.
  - Excludes duration anomalies ($< 60\text{ seconds}$ or $> 360\text{ minutes}$).
  - Excludes distance anomalies ($< 0.1\text{ miles}$ with non-zero fare, or $> 100.0\text{ miles}$).
  - Excludes impossible velocity ($> 85.0\text{ mph}$).
  - Excludes negative, zero, or outlier fares ($< \$3.00$ base fare or $> \$500.00$).
- **Limitations:** Only captures medallion Yellow Taxis; does not measure Green Boro Taxis, FHV (Uber/Lyft), or micro-mobility.

---

### 2. Passenger Spending (`total_passenger_spending`)
- **Epistemic Classification:** **Observed Fact**
- **SQL Definition:**
  ```sql
  SUM(total_amount)
  ```
- **Grain:** Grouped across spatial and temporal dimensions.
- **Filters & Exclusions:** Excludes refunded, voided, negative, or unmetered trips ($< \$3.00$ or $> \$1,000.00$ total).
- **Interview Defense & Financial Governance:**
  > [!IMPORTANT]
  > **Market Activity vs. Company Revenue:** `total_passenger_spending` represents gross consumer mobility expenditure across the NYC taxi market. It **never** represents company revenue, platform margin, or driver net take-home pay, as it includes municipal taxes, MTA surcharges, airport fees, bridge/tunnel tolls, and driver tips.

---

### 3. Credit Card Tip Percentage (`tip_percentage` / `tip_pct`)
- **Epistemic Classification:** **Observed Fact** (Conditional on payment medium: `payment_type = 1`)
- **SQL Definition:**
  ```sql
  -- Downstream aggregated calculation
  (SUM(CASE WHEN payment_type_id = 1 THEN tip_amount ELSE 0 END) / 
   NULLIF(SUM(CASE WHEN payment_type_id = 1 THEN fare_amount ELSE 0 END), 0)) * 100.0
  ```
- **Grain:** Individual credit card trip in `fct_trips` or aggregate across slices.
- **Filters & Exclusions:**
  - **Payment Filter:** Strictly computed where `payment_type = 1` or `payment_type_id = 1` (Credit Card).
  - **Cash Exclusion:** Cash trips (`payment_type = 2`), dispute, no-charge, and unknown payments are excluded from the tip denominator.
- **Limitations & Rationale:**
  - In NYC TLC data, drivers/meters do not record cash gratuity (cash tips default to \$0.00). Including cash trips in the denominator causes severe downward bias. Tip percentage is therefore explicitly defined as **Credit Card Tip / Credit Card Base Fare**.

---

### 4. Trip Duration (`duration_minutes` & `duration_seconds`)
- **Epistemic Classification:** **Estimate / Model Output**
- **SQL Definition:**
  ```sql
  CAST(date_diff('second', pickup_datetime, dropoff_datetime) AS BIGINT) AS duration_seconds,
  ROUND(date_diff('second', pickup_datetime, dropoff_datetime) / 60.0, 2) AS duration_minutes
  ```
- **Grain:** 1 row per trip (`fct_trips`).
- **Filters & Exclusions:**
  - Bounded strictly between $60\text{ seconds}$ ($1.0\text{ minute}$) and $21,600\text{ seconds}$ ($360.0\text{ minutes}$).
- **Limitations:** Dependent on taximeter clock accuracy and GPS hardware synchronization.

---

### 5. Effective Trip Average Speed (`speed_mph`)
- **Epistemic Classification:** **Estimate / Proxy**
- **SQL Definition:**
  ```sql
  CASE 
      WHEN duration_seconds >= 60 AND trip_distance_miles > 0 
      THEN ROUND(trip_distance_miles / (duration_seconds / 3600.0), 2)
      ELSE NULL 
  END
  ```
- **Grain:** 1 row per trip (`fct_trips`).
- **Filters & Exclusions:**
  - Trips with `duration_seconds < 60` or speed $> 85.0\text{ mph}` (`speed_mph > 85.0`) are treated as physical anomalies and excluded from clean marts.
- **Limitations:** Implied average speed over the total trip path; does not reflect instantaneous acceleration or idle traffic dwell time.


---

### 6. Passenger Count (`passenger_count`)
- **Epistemic Classification:** **Estimate / Model Output** (with Imputation Policy)
- **SQL Definition:**
  ```sql
  COALESCE(
      CASE WHEN passenger_count BETWEEN 1 AND 6 THEN passenger_count ELSE NULL END,
      1
  )
  ```
- **Grain:** 1 row per trip (`fct_trips`).
- **Filters & Exclusions:** Driver-entered zeros or nulls are imputed to $1$ passenger (labeled as `is_passenger_count_imputed = TRUE`) to ensure conservative capacity estimation. Counts $> 6$ are capped/excluded.

---

## 🗺️ Spatial & Transit Metrics

### 7. Underserved Zone Indicator (`is_underserved`)
- **Epistemic Classification:** **Assumption / Policy Rule**
- **SQL Definition:**
  ```sql
  CASE
      WHEN z.borough IN ('Unknown', 'EWR') THEN FALSE
      WHEN COALESCE(p.pickup_trip_count, 0) < 1000 THEN TRUE
      WHEN COALESCE(d.dropoff_trip_count, 0) > 2000 
           AND (CAST(COALESCE(p.pickup_trip_count, 0) AS DOUBLE) / NULLIF(d.dropoff_trip_count, 0)) < 0.20 
      THEN TRUE
      ELSE FALSE
  END
  ```
- **Grain:** 1 row per TLC Taxi Zone (`LocationID 1..265` in `mart_zone`).
- **Filters & Exclusions:** Newark Airport (`EWR`) and unknown geographic centroids are excluded.
- **Rationale & Behavioral Definition:**
  - A residential/commercial NYC zone is classified as **underserved by Yellow Taxis** if either:
    1. It experiences acute overall lack of supply ($< 1,000$ total pickups across the entire 91 days of Q2 2024, representing bottom quartile volume), OR
    2. It exhibits an asymmetric "drop-off sink" pattern ($> 2,000$ dropoffs, but pickup-to-dropoff ratio $< 0.20$), indicating that passengers arrive by taxi but cannot hail an outbound vehicle.

---

### 8. Subway Ridership / Turnstile Entries (`subway_ridership`)
- **Epistemic Classification:** **Observed Fact**
- **SQL Definition:**
  ```sql
  COALESCE(SUM(ridership), 0)
  ```
- **Grain:** Hourly station complex in `mart_transit`, or borough-level pivot in `int_subway_hourly`.
- **Filters & Exclusions:** Validated against MTA Socrata open data feed; missing hours coalesce to $0$.
- **Limitations:** Counts physical turnstile tap-ins; does not capture Omni/fare evasion rates or transfers within station turnstile boundaries.

---

## 🌦️ Weather & Dynamic Elasticity Metrics

### 9. Weather Impact Lag Assumptions (`taxi_trip_count_lag1`, `precipitation_mm_lag1`, etc.)
- **Epistemic Classification:** **Assumption / Policy Rule**
- **SQL Definition:**
  ```sql
  LAG(taxi_trip_count, 1) OVER (ORDER BY hour_timestamp) AS taxi_trip_count_lag1,
  LAG(taxi_trip_count, 2) OVER (ORDER BY hour_timestamp) AS taxi_trip_count_lag2,
  LAG(precipitation_mm, 1) OVER (ORDER BY hour_timestamp) AS precipitation_mm_lag1
  ```
- **Grain:** 1 row per calendar hour in `mart_weather`.
- **Methodological Justification & Lag Hypothesis:**
  - Rain elasticity does not operate instantaneously; commuter behavioral adaptation exhibits physical inertia:
    - **Lag 0 (T0):** Immediate shelter-seeking behavior and surge in localized hails.
    - **Lag 1 (T+1 hour):** Commuters altering mode choice (switching between walking/subway and hailing) as storm cells persist.
    - **Lag 2 (T+2 hours):** Return to baseline mobility or extended post-storm congestion dampening total throughput.

---

## 📐 Downstream Ratio & Additive Recomputation Rules

To prevent **Simpson's Paradox** and mathematical distortion across multidimensional slices (e.g. slicing `mart_cube` by Borough, Date, or Hour), all dbt mart models store **strictly additive base sums and counts**:

| Desired Downstream Metric | Correct Dynamic SQL Formula | ❌ Prohibited Anti-Pattern |
| :--- | :--- | :--- |
| **Average Fare** | `SUM(total_fare_amount) / NULLIF(SUM(trip_count), 0)` | `AVG(avg_fare)` |
| **Average Trip Distance** | `SUM(total_distance_miles) / NULLIF(SUM(trip_count), 0)` | `AVG(avg_distance)` |
| **Average Trip Duration** | `SUM(total_duration_minutes) / NULLIF(SUM(trip_count), 0)` | `AVG(avg_duration)` |
| **Credit Card Tip %** | `(SUM(total_tip_amount) / NULLIF(SUM(total_fare_amount), 0)) * 100.0` | `AVG(tip_pct)` |
| **Average Speed** | `SUM(total_distance_miles) / NULLIF(SUM(total_duration_seconds) / 3600.0, 0)` | `AVG(speed_mph)` |
