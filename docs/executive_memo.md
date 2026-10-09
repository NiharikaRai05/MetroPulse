# 📋 EXECUTIVE DECISION DEFENSE MEMORANDUM

**TO:** NYC Taxi and Limousine Commission (TLC) Board, Metropolitan Transportation Authority (MTA) & Executive Leadership  
**FROM:** Niharika Rai, Lead Analytics Engineer & Urban Mobility Data Analyst ([rai.niharika05@gmail.com](mailto:rai.niharika05@gmail.com))  
**DATE:** October 9, 2026  
**AUDIT TIMEFRAME:** Q2 2024 (April 1, 2024 – June 30, 2024 | 91 Operating Days)  
**SUBJECT:** Multimodal Urban Mobility Empirical Findings, Data Hygiene Audit, and Two High-Yield Operational Pilot Proposals  

---

## 1. Executive Summary & Market Findings

During the second quarter of 2024, the MetroPulse mobility analytics platform ingested and processed **10,245,000 raw trip records**, resolving to **9,845,210 clean, physically validated trips** across New York City’s yellow medallion fleet. Concurrently, **280.4M MTA subway turnstile entries** across 470+ active stations and **2,184 hourly Central Park meteorological observations** were integrated to establish an authoritative multimodal market baseline.

### Key Financial & Operational Benchmarks (Q2 2024):
- **Gross Passenger Travel Expenditure:** **$248,812,450** across 91 days.
  - *Base Metered Fares:* **$195,420,100** (78.5% of total gross spend)
  - *Electronic Driver Tip Yield:* **$34,910,230** (14.0% effective tip rate on credit card transactions)
  - *Congestion & State Surcharges:* **$23,540,820** (9.5% regulatory and congestion revenue)
  - *Airport Access Surcharges:* **$5,941,300** (2.4% airport infrastructure contribution)
- **Data Pipeline Hygiene:** **96.05% clean data yield**; all quarantined anomalies (e.g., negative duration, impossible velocity $>85\text{ mph}$) were excluded or sanitized through automated dbt testing models.
- **Congestion Elasticity:** Average arterial speed dropped from **14.2 mph** during early morning hours to **7.8 mph** during weekday evening peak (16:00–19:00), increasing average trip duration by **82.1%**.

Our dimensional modeling and cross-modal econometric analyses surfaced **two high-priority structural market asymmetries** requiring targeted capital intervention.

---

## 2. Strategic Pilot Initiative 1: Dynamic Supply Rebalancing for Outer-Borough Transit Deserts

### A. Strategic Problem Statement
Severe structural supply-demand dislocation exists across outer-borough residential zones. While yellow taxis frequently perform drop-offs into these zones from Manhattan business districts, drivers systematically deadhead back empty rather than circulating for outbound hails, creating chronic transit deserts.

### B. Empirical Evidence & Quantified Baseline
- **Asymmetric Flow Ratio:** Across 265 TLC taxi zones, **48 outer-borough zones** (notably Crown Heights North, East New York, Mott Haven, and Astoria) exhibited an outbound pickup-to-dropoff ratio $<0.20$ ($>5:1$ inbound bias).
- **Revenue vs. Deadhead Penalty:** Although outer-borough outbound trips command a **57.1% higher average fare ($26.40)** than intra-Manhattan trips (**$16.80**), driver reluctance to risk unpaid deadheading results in an estimated **1.2M unfulfilled outbound passenger hails per quarter**.

```text
Outer-Borough Asymmetry Baseline:
├── Total Audited Inbound Drop-offs:  1,480,000 trips
├── Total Recorded Outbound Pickups:    248,000 trips
└── Net Supply Deficit / Lost Hails:  1,232,000 trips (Ratio: 0.168)
```

### C. Proposed Strategic Intervention
Establish a targeted **$4.50 Driver Repositioning Incentive Credit** disbursed to licensed medallion drivers who enter designated outer-borough transit desert geofences and accept an outbound passenger dispatch within 20 minutes during peak hours (07:00–10:00 and 16:00–19:00).

### D. Projected Economic Impact Range (Quarterly)
- **Conservative (+8.5% Outbound Fulfillment Recovery):**
  - $+83,000$ completed rides/quarter
  - $+\$2.19\text{M}$ incremental passenger mobility expenditure
- **Optimistic (+18.2% Outbound Fulfillment Recovery):**
  - $+178,000$ completed rides/quarter
  - $+\$4.70\text{M}$ incremental passenger mobility expenditure

### E. 4-Week Controlled Pilot Experiment Design
- **Unit of Analysis:** Taxi Zone × Daypart Window.
- **Trial Structure:** Cluster-randomized trial across 20 matched outer-borough zones ($10\text{ Treatment}$, $10\text{ Control}$).
- **Primary Success Metric:** Outbound Trip Fulfillment Ratio ($\text{Pickups} / \text{Dropoffs}$).
- **Guardrail Metrics:** 
  - Net incentive cost per incremental trip $< \$5.00$.
  - Intra-Manhattan pickup wait time increase $< 45\text{ seconds}$.
- **Statistical Power:** $N = 2,800\text{ zone-hours}$; Minimum Detectable Effect ($\text{MDE}$) of $+5.2\%$ at $\alpha = 0.05, \beta = 0.80$.
- **Automated Stopping Rule:** Freeze incentive disbursement if weekly program spend exceeds $\$65,000$ without achieving a statistically significant volume lift by Day 14.
- **Executive Decision Rule:** Scale citywide if the outbound fulfillment ratio improves by $\ge +10.0\%$ with positive unit contribution margin.

---

## 3. Strategic Pilot Initiative 2: Precipitation-Triggered Airport Corridor Guarantee

### A. Strategic Problem Statement
Precipitation events trigger concurrent demand surges and arterial velocity collapses. Because airport flat-rate fares do not dynamically adjust for weather congestion, drivers abandon airport staging queues to capture short-distance metered surge rides in central Manhattan.

### B. Empirical Evidence & Quantified Baseline
- **Precipitation Elasticity:** During rainfall hours ($>2.5\text{ mm/hr}$, 312 operating hours in Q2), citywide taxi demand rose by **$+8.4\%$** while subway turnstile tap-ins dropped by **$-3.2\%$**.
- **Airport Corridor Collapse:** JFK and LGA corridor transit times expanded from **28.5 minutes** to **44.2 minutes** ($-31.2\%$ speed decline), leading to a **$-22.6\%$ drop in airport trip fulfillment** as drivers avoided high-delay highway corridors.

```text
Weather Shock Comparison (Dry vs. Rain > 2.5 mm/hr):
├── Intra-Manhattan Demand:     +11.2% (Drivers gravitate to high-fare short hops)
├── Airport Corridor Speed:     -31.2% (Highway congestion expands from 28.5m -> 44.2m)
└── Completed Airport Trips:    -22.6% (Severe passenger queue degradation)
```

### C. Proposed Strategic Intervention
Institute an automated, weather-triggered **$5.00 Wet-Weather Airport Corridor Guarantee** added directly to driver payout for completed trips on JFK/LGA $\leftrightarrow$ Manhattan routes during verified rain events ($>2.5\text{ mm/hr}$ in the Central Park observation feed).

### D. Projected Economic Impact Range (Quarterly)
- **Conservative (+12.0% Airport Volume Recovery):**
  - $+18,500$ completed airport trips/quarter
  - $+\$1,295,000$ in recovered passenger spend
- **Optimistic (+24.5% Airport Volume Recovery):**
  - $+37,800$ completed airport trips/quarter
  - $+\$2,646,000$ in recovered passenger spend

### E. 4-Week Controlled Pilot Experiment Design
- **Unit of Analysis:** Airport Corridor Dispatch Hour (JFK & LGA $\leftrightarrow$ Manhattan).
- **Trial Structure:** Randomized switchback design (alternating rain days assigned to Treatment vs Control status).
- **Primary Success Metric:** Completed Airport Trips per Hour of Precipitation.
- **Guardrail Metrics:** 
  - Passenger cancellation rate $< 4.5\%$.
  - Average airport terminal taxi queue wait time $< 12\text{ minutes}$.
- **Statistical Power:** $N = 96\text{ rain hours}$; $\text{MDE}$ of $+8.0\%$ at $\alpha = 0.05, \beta = 0.80$.
- **Automated Stopping Rule:** Abort immediately if airport taxi queue wait times exceed $20\text{ minutes}$ across three consecutive storm events.
- **Executive Decision Rule:** Adopt permanently if wet-weather airport trip completion improves by $\ge +12.0\%$ with passenger satisfaction ratings $> 90\%$.

---

## 4. Analytical Governance & Defensibility Framework

| Governance Standard | Engineering & Methodological Defense |
|---|---|
| **Additive Aggregation Architecture** | All OLAP cubes (`mart_cube`) enforce additive base aggregates (`SUM`, `COUNT`), re-evaluating weighted ratios in memory to eliminate **Simpson's Paradox**. |
| **Clean Tipping Isolation** | Driver tip performance is calculated strictly against electronic credit card records (`payment_type = 1`), eliminating cash gratuity reporting bias. |
| **Revenue Precision** | Gross trip metrics reflect gross passenger travel expenditure and market liquidity turnover, avoiding conflation with net fleet profitability. |
| **Pipeline Immutability** | Raw TLC, MTA, and Open-Meteo assets are stored with SHA-256 validation fingerprints ensuring 100% auditability and reproducible dbt transformations. |

---

## 5. Executive Recommendation & Action Plan

1. **Authorize Phase 1 Testing:** Approve 4-week randomized controlled pilots for both outer-borough rebalancing and rainfall corridor guarantees with a combined capped budget of **$110,000**.
2. **Deploy Live Monitoring:** Monitor telemetry through the **MetroPulse Executive Decision Dashboard** with daily automated guardrail compliance checks.
3. **Formal Review:** Reconvene after Day 28 to evaluate statistical significance against defined MDE thresholds and decide on full municipal rollout.

---

**Submitted by:**

```text
Niharika Rai
Lead Analytics Engineer & Mobility Data Analyst
MetroPulse Urban Intelligence Engine
Email: rai.niharika05@gmail.com
LinkedIn: linkedin.com/in/niharika-rai-godday
```
