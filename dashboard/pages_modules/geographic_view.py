"""
dashboard/pages_modules/geographic_view.py
==========================================
Page 3: Geographic Spatial Intelligence & Zone Map
- Choropleth Map with dynamic Metric Selector (Pickups, Dropoffs, Spending, Underserved)
- Top-10 ranking leaderboard table
- Takeaway title Plotly figures
- "What this means" observational insight notes
"""

import json
from pathlib import Path
try:
    import geopandas as gpd
except ImportError:
    gpd = None

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import (
    ACCENT_AMBER,
    ACCENT_CYAN,
    ACCENT_EMERALD,
    ACCENT_INDIGO,
    ACCENT_ROSE,
    format_currency,
    format_number,
    get_plotly_layout,
    render_insight_note,
    render_kpi_card,
)


def render(zone_df: pd.DataFrame, routes_df: pd.DataFrame, geojson_gdf=None):
    st.markdown("### 🗺️ Geographic & Spatial Intelligence")

    if zone_df.empty:
        st.warning("⚠️ Zone mart data not available.")
        return

    # Summary calculations
    total_zones = len(zone_df)
    underserved_zones = zone_df[zone_df["is_underserved"] == True]["location_id"].count() if "is_underserved" in zone_df.columns else 0
    top_zone = zone_df.sort_values(by="pickup_trip_count", ascending=False).iloc[0] if "pickup_trip_count" in zone_df.columns else None
    airport_volume = zone_df[zone_df["is_airport_zone"] == True]["pickup_trip_count"].sum() if "is_airport_zone" in zone_df.columns else 0

    # 1. Row of 5 KPI Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi_card(
            title="Active Taxi Zones",
            value=str(total_zones),
            subtext="TLC 1..265 Registry",
            tooltip="Official NYC Taxi & Limousine Commission zones across 5 boroughs.",
            badge="Zones",
            badge_color=ACCENT_CYAN
        )
    with c2:
        render_kpi_card(
            title="Underserved Zones",
            value=str(underserved_zones),
            subtext=f"{(underserved_zones/max(total_zones,1)*100):.1f}% of total zones",
            tooltip="Outer-borough zones with <1,000 pickups or pickup/dropoff ratio < 0.20.",
            badge="Deserts",
            badge_color=ACCENT_ROSE
        )
    with c3:
        top_name = top_zone["zone_name"] if top_zone is not None else "N/A"
        top_cnt = format_number(top_zone["pickup_trip_count"]) if top_zone is not None else "0"
        render_kpi_card(
            title="Peak Pickup Hub",
            value=top_name[:17],
            subtext=f"{top_cnt} departures",
            tooltip="Single highest-demand pickup zone in NYC during Q2 2024.",
            badge="Hub #1",
            badge_color=ACCENT_EMERALD
        )
    with c4:
        render_kpi_card(
            title="Airport Pickups",
            value=format_number(airport_volume),
            subtext="JFK, LGA & Newark",
            tooltip="Total taxi passenger trips originating from NYC area airports.",
            badge="Airports",
            badge_color=ACCENT_INDIGO
        )
    with c5:
        total_p_spending = zone_df["pickup_passenger_spending"].sum() if "pickup_passenger_spending" in zone_df.columns else 0.0
        render_kpi_card(
            title="Zone Gross Volume",
            value=format_currency(total_p_spending),
            subtext="All spatial origins",
            tooltip="Total gross passenger expenditure aggregated across all departure zones.",
            badge="Spending",
            badge_color=ACCENT_AMBER
        )

    st.markdown("---")

    # 2. Map Section with Metric Selector
    col_map_ctrl, col_map_title = st.columns([1, 3])
    with col_map_ctrl:
        metric_option = st.selectbox(
            "🗺️ Map Metric Selector",
            ["Pickups", "Drop-offs", "Passenger Spending", "Underserved Flag"],
            index=0,
            key="geo_metric_select"
        )

    metric_col_map = {
        "Pickups": "pickup_trip_count",
        "Drop-offs": "dropoff_trip_count",
        "Passenger Spending": "pickup_passenger_spending",
        "Underserved Flag": "is_underserved",
    }
    selected_col = metric_col_map[metric_option]

    # Map Rendering
    if geojson_gdf is not None and not geojson_gdf.empty:
        merged_geo = geojson_gdf.merge(
            zone_df[["location_id", "pickup_trip_count", "dropoff_trip_count", "is_underserved", "pickup_passenger_spending"]],
            on="location_id",
            how="left"
        ).fillna(0)

        try:
            fig_map = px.choropleth_mapbox(
                merged_geo,
                geojson=json.loads(merged_geo.to_json()),
                locations=merged_geo.index,
                color=selected_col,
                hover_name="zone_name" if "zone_name" in merged_geo.columns else "location_id",
                hover_data=["borough", "pickup_trip_count", "dropoff_trip_count", "is_underserved"],
                color_continuous_scale="Blues" if metric_option != "Underserved Flag" else ["#111827", "#f87171"],
                mapbox_style="carto-darkmatter",
                zoom=9.8,
                center={"lat": 40.730610, "lon": -73.935242},
                opacity=0.75
            )
            fig_map.update_layout(
                **get_plotly_layout(
                    height=450,
                    takeaway_title=f"Spatial density across NYC zones by {metric_option.lower()}"
                ),
                margin=dict(l=0, r=0, t=35, b=0),
                coloraxis_colorbar=dict(title=metric_option)
            )
            st.plotly_chart(fig_map, use_container_width=True)
            render_insight_note(f"Demand is heavily concentrated in Midtown and Lower Manhattan, with outer-borough activity primarily focused on airport and inter-borough arterial connections.")
        except Exception:
            # Fallback bar chart
            st.info("Choropleth rendered as zone ranking view:")
            fig_bar = px.bar(
                zone_df.sort_values(by=selected_col, ascending=False).head(15),
                x="zone_name",
                y=selected_col,
                color="borough",
                color_discrete_sequence=[ACCENT_CYAN, ACCENT_INDIGO, ACCENT_EMERALD, ACCENT_AMBER]
            )
            fig_bar.update_layout(**get_plotly_layout(height=380, takeaway_title=f"Top 15 zones by {metric_option.lower()}"), xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        fig_bar = px.bar(
            zone_df.sort_values(by=selected_col, ascending=False).head(15),
            x="zone_name",
            y=selected_col,
            color="borough",
            color_discrete_sequence=[ACCENT_CYAN, ACCENT_INDIGO, ACCENT_EMERALD, ACCENT_AMBER]
        )
        fig_bar.update_layout(**get_plotly_layout(height=380, takeaway_title=f"Top 15 zones by {metric_option.lower()}"), xaxis_tickangle=-45)
        st.plotly_chart(fig_bar, use_container_width=True)

    # 3. Top-10 Origin-Destination Corridors & Top-10 Zones Table
    col_l, col_r = st.columns([3, 2])

    with col_l:
        if not routes_df.empty:
            top_routes = routes_df.sort_values(by="trip_count", ascending=False).head(10).copy()
            top_routes["corridor"] = top_routes["pickup_zone_name"] + " ➔ " + top_routes["dropoff_zone_name"]

            fig_routes = px.bar(
                top_routes,
                x="trip_count",
                y="corridor",
                orientation="h",
                color="route_flow_type" if "route_flow_type" in top_routes.columns else None,
                color_discrete_map={"Intra-Borough": ACCENT_CYAN, "Inter-Borough": ACCENT_AMBER}
            )
            fig_routes.update_layout(
                **get_plotly_layout(
                    height=340,
                    takeaway_title="Upper East Side and Midtown corridors dominate top Origin-Destination pairs"
                ),
                yaxis=dict(autorange="reversed"),
                xaxis_title="Trip Volume",
                yaxis_title=""
            )
            st.plotly_chart(fig_routes, use_container_width=True)
            render_insight_note("The vast majority of top-volume routes are short-distance intra-Manhattan movements connecting residential neighborhoods to commercial centers.")

    with col_r:
        st.markdown("##### 🏆 Top 10 High-Demand Zones")
        top_10_table = zone_df.sort_values(by="pickup_trip_count", ascending=False).head(10)[[
            "location_id", "zone_name", "borough", "pickup_trip_count", "dropoff_trip_count"
        ]].rename(columns={
            "location_id": "ID",
            "zone_name": "Zone Name",
            "borough": "Borough",
            "pickup_trip_count": "Pickups",
            "dropoff_trip_count": "Drop-offs"
        })
        st.dataframe(top_10_table, hide_index=True, use_container_width=True, height=330)
