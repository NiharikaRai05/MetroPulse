"""
dashboard/app.py
================
Main entrypoint for the MetroPulse NYC Multimodal Mobility Analytics Dashboard.
Features:
- Top Horizontal Executive Navigation Tabs (Executive, Temporal, Geographic, Fares, Weather, Data Quality)
- Glowing Glassmorphic KPI Cards
- Collapsible sidebar filter groups with Reset button & active filter chips
- Dynamic matching row count badge & CSV download options
- Header with "1 Apr to 30 Jun 2024" badge and "Last Refreshed" timestamp
- Zero-cost deployment, reads exclusively from cached Parquet files
"""

import sys
from pathlib import Path
from typing import List, Tuple

# Add root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import streamlit as st

from dashboard.data_loader import (
    filter_mart_cube,
    load_geojson,
    load_last_refresh,
    load_parquet,
)
from dashboard.pages_modules import (
    executive_view,
    fares_view,
    geographic_view,
    quality_view,
    temporal_view,
    weather_transit_view,
)
from dashboard.theme import apply_custom_css

# Page configuration
st.set_page_config(
    page_title="MetroPulse | NYC Mobility Analytics (Q2 2024)",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global executive styling
apply_custom_css()


def reset_filters():
    """Resets all filter selections to default state."""
    st.session_state["filter_dates"] = (pd.to_datetime("2024-04-01").date(), pd.to_datetime("2024-06-30").date())
    st.session_state["filter_dayparts"] = []
    st.session_state["filter_pickup_boroughs"] = []
    st.session_state["filter_dropoff_boroughs"] = []
    st.session_state["filter_payments"] = []
    st.session_state["filter_rates"] = []
    st.session_state["filter_airport"] = "All Trips"
    st.session_state["filter_weather"] = "All Weather"


def render_empty_state(active_filters: List[Tuple[str, str]]):
    """Renders a helpful and friendly empty state message when filters yield zero rows."""
    st.markdown(
        """
        <div class="empty-state-box">
            <h4 style="margin-top:0; color:#fbbf24;">⚠️ No trips match the current filter combination</h4>
            <p style="color:#94a3b8; font-size:0.88rem; margin-bottom:12px;">
                Your current query returned <strong>0 records</strong> because multiple restrictive criteria were applied simultaneously.
            </p>
        """,
        unsafe_allow_html=True,
    )

    if active_filters:
        st.markdown('<p style="font-size:0.82rem; color:#cbd5e1; margin-bottom:6px;"><strong>Active restrictive filters:</strong></p>', unsafe_allow_html=True)
        chips_html = "".join([f'<span class="filter-chip" style="margin-right:6px; margin-bottom:6px;">{name}: {val}</span>' for name, val in active_filters])
        st.markdown(f'<div class="chip-container">{chips_html}</div>', unsafe_allow_html=True)

        suggested = active_filters[-1][0]
        st.markdown(
            f"""
            <p style="font-size:0.82rem; color:#94a3b8; margin-top:8px;">
                💡 <em>Suggestion:</em> Try clearing <strong>{suggested}</strong> or click the reset button below to restore full market visibility.
            </p>
            """,
            unsafe_allow_html=True
        )

    if st.button("🔄 Reset All Filters", on_click=reset_filters, key="empty_reset_btn", type="primary"):
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def main():
    # Initialize session state for filters if missing
    if "filter_dates" not in st.session_state:
        st.session_state["filter_dates"] = (pd.to_datetime("2024-04-01").date(), pd.to_datetime("2024-06-30").date())
    if "filter_dayparts" not in st.session_state:
        st.session_state["filter_dayparts"] = []
    if "filter_pickup_boroughs" not in st.session_state:
        st.session_state["filter_pickup_boroughs"] = []
    if "filter_dropoff_boroughs" not in st.session_state:
        st.session_state["filter_dropoff_boroughs"] = []
    if "filter_payments" not in st.session_state:
        st.session_state["filter_payments"] = []
    if "filter_rates" not in st.session_state:
        st.session_state["filter_rates"] = []
    if "filter_airport" not in st.session_state:
        st.session_state["filter_airport"] = "All Trips"
    if "filter_weather" not in st.session_state:
        st.session_state["filter_weather"] = "All Weather"

    # Load refresh manifest
    last_refresh = load_last_refresh()
    build_time = last_refresh.get("build_timestamp_utc", "Live")[:19].replace("T", " ")

    # 1. Sidebar Architecture
    with st.sidebar:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                <span style="font-size:1.6rem;">🚕</span>
                <div>
                    <h3 style="margin:0; font-size:1.15rem; font-weight:800; color:#ffffff; letter-spacing:-0.02em;">MetroPulse</h3>
                    <span style="font-size:0.68rem; color:#38bdf8; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">NYC Multimodal Platform</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Top Filter Header with 1-Click Reset
        f_col1, f_col2 = st.columns([2, 1])
        with f_col1:
            st.markdown("<span style='font-size:0.85rem; font-weight:700; color:#f1f5f9;'>🎛️ Filter Panel</span>", unsafe_allow_html=True)
        with f_col2:
            if st.button("Reset", on_click=reset_filters, key="sidebar_reset_btn", use_container_width=True):
                st.rerun()

        # Collapsible Filter Group 1: Time & Calendar
        with st.expander("📅 Time & Calendar", expanded=True):
            min_date = pd.to_datetime("2024-04-01").date()
            max_date = pd.to_datetime("2024-06-30").date()
            date_selection = st.date_input(
                "Date Range",
                value=st.session_state["filter_dates"],
                min_value=min_date,
                max_value=max_date,
                key="input_date_range",
            )
            if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
                start_date, end_date = date_selection
                st.session_state["filter_dates"] = (start_date, end_date)
            else:
                start_date, end_date = min_date, max_date

            dayparts = [
                "Morning Rush (06:00 - 09:59)",
                "Midday (10:00 - 15:59)",
                "Evening Rush (16:00 - 19:59)",
                "Night (20:00 - 23:59)",
                "Late Night (00:00 - 05:59)",
            ]
            selected_dayparts = st.multiselect(
                "Dayparts (TLC Windows)",
                dayparts,
                default=st.session_state["filter_dayparts"],
                key="input_dayparts",
            )
            st.session_state["filter_dayparts"] = selected_dayparts

        # Collapsible Filter Group 2: Geography & Corridors
        with st.expander("📍 Geography & Corridors", expanded=True):
            all_boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", "EWR"]
            pickup_boroughs = st.multiselect(
                "Pickup Borough",
                all_boroughs,
                default=st.session_state["filter_pickup_boroughs"],
                key="input_pickup_boroughs",
            )
            st.session_state["filter_pickup_boroughs"] = pickup_boroughs

            dropoff_boroughs = st.multiselect(
                "Drop-off Borough",
                all_boroughs,
                default=st.session_state["filter_dropoff_boroughs"],
                key="input_dropoff_boroughs",
            )
            st.session_state["filter_dropoff_boroughs"] = dropoff_boroughs

            airport_filter = st.selectbox(
                "Airport Corridor",
                ["All Trips", "Airport Trips Only", "Non-Airport Trips Only"],
                index=["All Trips", "Airport Trips Only", "Non-Airport Trips Only"].index(st.session_state["filter_airport"]),
                key="input_airport_filter",
            )
            st.session_state["filter_airport"] = airport_filter

        # Collapsible Filter Group 3: Fares, Rates & Weather
        with st.expander("💳 Fares, Rates & Weather", expanded=False):
            payment_options = {1: "Credit Card", 2: "Cash", 3: "No Charge", 4: "Dispute"}
            selected_payments = st.multiselect(
                "Payment Method",
                list(payment_options.keys()),
                format_func=lambda k: payment_options[k],
                default=st.session_state["filter_payments"],
                key="input_payments",
            )
            st.session_state["filter_payments"] = selected_payments

            rate_options = {1: "Standard Meter", 2: "JFK Airport Flat", 3: "Newark", 4: "Nassau/Westchester"}
            selected_rates = st.multiselect(
                "Rate Code Type",
                list(rate_options.keys()),
                format_func=lambda k: rate_options[k],
                default=st.session_state["filter_rates"],
                key="input_rates",
            )
            st.session_state["filter_rates"] = selected_rates

            weather_filter = st.selectbox(
                "Weather Condition",
                ["All Weather", "Rain Only", "Heavy Rain Only", "Clear / Dry Only"],
                index=["All Weather", "Rain Only", "Heavy Rain Only", "Clear / Dry Only"].index(st.session_state["filter_weather"]),
                key="input_weather_filter",
            )
            st.session_state["filter_weather"] = weather_filter

        st.markdown("---")
        st.markdown(
            f"""
            <div style="font-size: 0.72rem; color: #64748b; line-height: 1.45;">
                <div>⚡ Refresh: <span style="color: #cbd5e1;">{build_time} UTC</span></div>
                <div>📦 Storage: <span style="color: #34d399;">Parquet (zstd)</span></div>
                <div>🛡️ Engine: <span style="color: #38bdf8;">DuckDB / dbt</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Data Loading (Parquet Only with Cache & Column Projection)
        mart_cube = load_parquet("mart_cube")
        dim_zone = load_parquet("dim_zone")
        mart_zone = load_parquet("mart_zone")
        mart_time = load_parquet("mart_time")
        mart_weather = load_parquet("mart_weather")
        mart_route_pairs = load_parquet("mart_route_pairs")
        mart_executive = load_parquet("mart_executive")
        mart_quality = load_parquet("mart_quality")
        dim_payment = load_parquet("dim_payment")
        dim_rate = load_parquet("dim_rate")
        geojson_gdf = load_geojson()

    # 3. Apply Multi-dimensional Filter Slice
    filtered_cube = filter_mart_cube(
        df=mart_cube,
        start_date=pd.Timestamp(start_date) if start_date else None,
        end_date=pd.Timestamp(end_date) if end_date else None,
        selected_dayparts=selected_dayparts,
        pickup_boroughs=pickup_boroughs,
        dropoff_boroughs=dropoff_boroughs,
        payment_types=selected_payments,
        rate_codes=selected_rates,
        airport_filter=airport_filter,
        weather_filter=weather_filter,
    )

    # Track active filter chips
    active_filters: List[Tuple[str, str]] = []
    if start_date != min_date or end_date != max_date:
        active_filters.append(("Date", f"{start_date} to {end_date}"))
    if selected_dayparts:
        active_filters.append(("Daypart", ", ".join([d.split(" ")[0] for d in selected_dayparts])))
    if pickup_boroughs:
        active_filters.append(("Pickup", ", ".join(pickup_boroughs)))
    if dropoff_boroughs:
        active_filters.append(("Dropoff", ", ".join(dropoff_boroughs)))
    if airport_filter != "All Trips":
        active_filters.append(("Airport", airport_filter))
    if selected_payments:
        pay_labels = [payment_options.get(p, str(p)) for p in selected_payments]
        active_filters.append(("Payment", ", ".join(pay_labels)))
    if selected_rates:
        rate_labels = [rate_options.get(r, str(r)) for r in selected_rates]
        active_filters.append(("Rate", ", ".join(rate_labels)))
    if weather_filter != "All Weather":
        active_filters.append(("Weather", weather_filter))

    matching_rows = len(filtered_cube)
    total_trips_matched = int(filtered_cube["trip_count"].sum()) if not filtered_cube.empty and "trip_count" in filtered_cube.columns else 0

    # 4. Global Header & Badges
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; margin-bottom:8px;">
            <div>
                <h1 style="margin:0; font-size:1.75rem; font-weight:800; color:#ffffff; letter-spacing:-0.02em;">
                    🚕 MetroPulse: NYC Multimodal Mobility Platform
                </h1>
                <div class="header-badge-container">
                    <span class="header-badge header-badge-cyan">🗓️ 1 Apr to 30 Jun 2024</span>
                    <span class="header-badge">⏱️ Last Refreshed: {build_time} UTC</span>
                    <span class="header-badge header-badge-emerald">📊 Filtered: {matching_rows:,} cube slices ({total_trips_matched:,} trips)</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Active filter chips display
    if active_filters:
        chips_html = "".join([f'<span class="filter-chip">🏷️ {name}: {val}</span>' for name, val in active_filters])
        st.markdown(f'<div class="chip-container">{chips_html}</div>', unsafe_allow_html=True)

    # Check for empty state
    if filtered_cube.empty or total_trips_matched == 0:
        render_empty_state(active_filters)
        return

    # 5. Top Horizontal Navigation Tabs
    tab_exec, tab_temp, tab_geo, tab_fares, tab_weather, tab_quality = st.tabs([
        "📊 Executive Pulse",
        "⏰ Temporal Dynamics",
        "🗺️ Geographic & Map",
        "💳 Fares & Payments",
        "🌦️ Weather & Transit",
        "🛡️ Data Quality",
    ])

    with tab_exec:
        executive_view.render(
            filtered_cube=filtered_cube,
            exec_df=mart_executive,
            time_df=mart_time,
            weather_df=mart_weather,
        )

    with tab_temp:
        temporal_view.render(
            filtered_cube=filtered_cube,
            time_df=mart_time,
        )

    with tab_geo:
        geographic_view.render(
            zone_df=mart_zone,
            routes_df=mart_route_pairs,
            geojson_gdf=geojson_gdf,
        )

    with tab_fares:
        fares_view.render(
            filtered_cube=filtered_cube,
            payment_df=dim_payment,
            rate_df=dim_rate,
        )

    with tab_weather:
        weather_transit_view.render(
            weather_df=mart_weather,
            transit_df=load_parquet("mart_transit"),
        )

    with tab_quality:
        quality_view.render(
            quality_df=mart_quality,
            last_refresh=last_refresh,
        )


if __name__ == "__main__":
    main()
