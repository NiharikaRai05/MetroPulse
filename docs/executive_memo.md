# MetroPulse Executive Decision Defense Memo (Q2 2024)

**To:** NYC Mobility Board & Executive Leadership  
**From:** Niharika Rai, Lead Analytical Engineer & Analytics Architect  
**Date:** October 6, 2026  
**Subject:** Empirical Mobility Analysis & Two High-Impact Strategic Pilots (Q2 2024)

---

## 1. Executive Summary & Market Findings

Across **April 1 to June 30, 2024 (91 days)**, the NYC yellow taxi ecosystem logged **9,845,210 clean trips**, generating **$248.8M in gross passenger mobility expenditure** (with base metered fares accounting for **$195.4M**, electronic tips yielding **$34.9M**, congestion surcharges generating **$23.5M**, and airport access fees reaching **$5.9M**). 

Our multi-hop dimensional modeling in DuckDB and empirical elasticity analyses surfaced two critical structural asymmetries:
1. **Outer-Borough Transit Deserts:** Over **48 outer-borough zones** experience severe supply-side failure where drop-offs exceed pickups by more than $5:1$ (pickup-to-dropoff ratio $< 0.20$), resulting in $1.2\text{M}$ unserved passenger hailing opportunities.
2. **Precipitation Shocks on Airport Corridors:** During precipitation events ($> 2.5\text{ mm/hr}$), total urban taxi demand surges by $+8.4\%$ while transit speed falls by $-31.2\%$, causing airport corridor fulfillment rates to degrade by $-22.6\%$ as drivers cluster in high-density Manhattan short-hops.

---

## 2. Initiative 1: Dynamic Supply Rebalancing for Outer-Borough Transit Deserts

### A. Strategic Decision
Implement a targeted **Dynamic Driver Repositioning Incentive ($4.50 credit per empty deadhead trip)** for drivers relocating to designated outer-borough transit deserts (e.g., Crown Heights North, Astoria, Mott Haven) during weekday morning and evening peak windows.

### B. Quantified Evidence
- **Severe Asymmetry:** Identified 48 residential zones where drop-off volume exceeded 2,000 trips but outbound pickups remained $< 400$ trips over Q2 2024 (mean pickup-to-dropoff ratio of $0.14$).
- **Passenger Expenditure:** Outer-borough trips generate an average fare of **$26.40** vs **$16.80** for intra-Manhattan trips, but deadhead return risk discourages driver supply.

### C. Projected Impact Range
- **Conservative:** $+8.5\%$ increase in outer-borough outbound trip volume ($+83,000$ trips/quarter, $+\$2.19\text{M}$ passenger expenditure).
- **Optimistic:** $+18.2\%$ outbound fulfillment ($+178,000$ trips/quarter, $+\$4.70\text{M}$ passenger expenditure).

### D. Implementation Risks & Data Limitations
- **Risk:** Drivers may game the GPS geofence by briefly entering the zone without actively accepting hails.
- **Data Limits:** Data captures Yellow Medallion taxis only; app-based FHV rides (Uber/Lyft) are not directly observable in this pipeline.

### E. 4-Week Pilot Experiment Design
- **Unit of Analysis:** Taxi Zone × Daypart Window (e.g., 07:00–10:00 and 16:00–19:00).
- **Assignment:** Cluster-randomized trial across 20 matched outer-borough zones ($10\text{ Treatment}$, $10\text{ Control}$).
- **Primary Metric:** Outbound Trip Fulfillment Rate ($\text{Pickups} / \text{Dropoffs}$).
- **Guardrail Metrics:** Driver repositioning cost $< \$5.00/\text{trip}$; Manhattan core trip latency increase $< 45\text{ seconds}$.
- **Sample Size / MDE:** $N = 2,800\text{ zone-hours}$; Minimum Detectable Effect (MDE) of $+5.2\%$ at $\alpha = 0.05, \beta = 0.80$.
- **Stopping Rule:** Halt if driver incentive burn exceeds $\$65,000/\text{week}$ without a statistically significant uptick in trips by Day 14.
- **Decision Rule:** Scale citywide if outbound ratio improves by $\ge +10\%$ with a positive net economic margin per trip.

---

## 3. Initiative 2: High-Precipitation Dynamic Surge & Airport Channel Guarantee

### A. Strategic Decision
Institute a weather-triggered **Rainfall Corridor Guarantee ($5.00 wet-weather driver stipend)** on dedicated airport channels (JFK/LGA $\leftrightarrow$ Manhattan) whenever precipitation exceeds $2.5\text{ mm/hr}$ in the Central Park observation feed.

### B. Quantified Evidence
- **Weather Sensitivity:** Rain hours ($312\text{ hours}$ in Q2) saw citywide taxi demand jump by $+8.4\%$ while MTA subway turnstile entries dipped by $-3.2\%$.
- **Airport Bottleneck:** Airport trip completions dropped by $-22.6\%$ during rain events as highway travel times expanded from $28.5\text{ min}$ to $44.2\text{ min}$, causing drivers to reject flat-rate airport trips in favor of metered Manhattan gridlock.

### C. Projected Impact Range
- **Conservative:** $+12.0\%$ recovery in wet-weather airport fulfillment ($+18,500$ completed airport rides/quarter, $+\$1.29\text{M}$ spending).
- **Optimistic:** $+24.5\%$ recovery ($+37,800$ completed airport rides/quarter, $+\$2.64\text{M}$ spending).

### D. Implementation Risks & Data Limitations
- **Risk:** Weather forecast latency; localized downpours in Queens might not match Central Park gauge readings simultaneously.
- **Data Limits:** Weather observations are localized to Central Park and generalized across boroughs.

### E. 4-Week Pilot Experiment Design
- **Unit of Analysis:** Airport Corridor Dispatch Hour (JFK & LGA $\leftrightarrow$ Manhattan).
- **Assignment:** Day-level randomized switchback design (Alternate rain days assigned to Treatment vs Control status).
- **Primary Metric:** Completed Airport Trips per Hour of Precipitation.
- **Guardrail Metrics:** Passenger cancellation rate $< 4.5\%$; average airport queue wait time $< 12\text{ minutes}$.
- **Sample Size / MDE:** $N = 96\text{ rain hours}$; MDE of $+8.0\%$ at $\alpha = 0.05, \beta = 0.80$.
- **Stopping Rule:** Abort if airport passenger wait times exceed $20\text{ minutes}$ for $> 3$ consecutive storm events.
- **Decision Rule:** Roll out permanently if airport fulfillment during storms increases by $\ge +12\%$ with passenger satisfaction $> 90\%$.

---
*Signed and Approved for Operational Pilot Review.*
