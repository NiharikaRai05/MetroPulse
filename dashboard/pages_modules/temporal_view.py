"""
dashboard/pages_modules/temporal_view.py
========================================
Page 2: Temporal Dynamics & Daypart Analysis
- Weekday x Hour heatmap matrix
- Takeaway title Plotly figures
- "What this means" observational insight notes
- 24-hour diurnal volume and congestion profiles
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.data_loader import compute_weighted_metrics
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


def render(filtered_cube: pd.DataFrame, time_df: pd.DataFrame):
    st.markdown("### ⏰ Temporal Dynamics & Daypart Pulse")

    metrics = compute_weighted_metrics(filtered_cube)
    total_trips = metrics["total_trips"]

    # Calculate specific daypart volumes
    rush_trips = filtered_cube[filtered_cube["hour_of_day"].isin(range(16, 20))]["trip_count"].sum() if "hour_of_day" in filtered_cube.columns else 0
    late_night_trips = filtered_cube[filtered_cube["hour_of_day"].isin(range(0, 6))]["trip_count"].sum() if "hour_of_day" in filtered_cube.columns else 0
    rush_share = (rush_trips / total_trips * 100.0) if total_trips > 0 else 0.0
    late_night_share = (late_night_trips / total_trips * 100.0) if total_trips > 0 else 0.0

    # 1. Row of KPI Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi_card(
            title="Window Trips",
            value=format_number(total_trips),
            subtext="Current slice volume",
            tooltip="Total trip count matching active temporal filters.",
            badge="Volume",
            badge_color=ACCENT_CYAN
        )
    with c2:
        render_kpi_card(
            title="Evening Rush Share",
            value=f"{rush_share:.1f}%",
            subtext=f"{format_number(rush_trips)} trips (16:00-19:59)",
            tooltip="Proportion of demand occurring during TLC weekday evening rush hours.",
            badge="Peak Window",
            badge_color=ACCENT_AMBER
        )
    with c3:
        render_kpi_card(
            title="Late Night Share",
            value=f"{late_night_share:.1f}%",
            subtext=f"{format_number(late_night_trips)} trips (00:00-05:59)",
            tooltip="Overnight mobility volume operating under TLC night surcharge rules.",
            badge="Night Shift",
            badge_color=ACCENT_INDIGO
        )
    with c4:
        render_kpi_card(
            title="Mean Window Velocity",
            value=f"{metrics['avg_speed_mph']:.1f} mph",
            subtext=f"{metrics['avg_duration_minutes']:.1f} min avg duration",
            tooltip="Weighted speed for this temporal segment.",
            badge="Speed",
            badge_color=ACCENT_EMERALD
        )
    with c5:
        render_kpi_card(
            title="Window Spending",
            value=format_currency(metrics["total_spending"]),
            subtext=f"Avg {format_currency(metrics['avg_fare_per_trip'])} / trip",
            tooltip="Gross passenger expenditure within active temporal filters.",
            badge="Spending",
            badge_color=ACCENT_CYAN
        )

    st.markdown("---")

    # 2. Weekday x Hour Demand Heatmap
    if not time_df.empty:
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        matrix = time_df.groupby(["day_name", "hour_of_day"])["trip_count"].sum().reset_index()
        matrix_pivot = matrix.pivot(index="day_name", columns="hour_of_day", values="trip_count").reindex(days_order)

        fig_heat = px.imshow(
            matrix_pivot,
            labels=dict(x="Hour of Day (24h)", y="Day of Week", color="Trips"),
            x=[f"{h:02d}:00" for h in range(24)],
            y=days_order,
            color_continuous_scale="Blues",
            aspect="auto"
        )
        fig_heat.update_layout(
            **get_plotly_layout(
                height=340,
                takeaway_title="Demand peaks 18:00 to 19:00 across Thursdays and Fridays"
            ),
            coloraxis_colorbar=dict(title="Trips")
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        render_insight_note("Mid-week and Friday evenings generate the most sustained taxi hailing density across all 24-hour periods, while Sunday mornings show the lowest activity.")

    # 3. 24-Hour Diurnal Volume & Speed Curves
    col_a, col_b = st.columns(2)

    with col_a:
        if "hour_of_day" in filtered_cube.columns and "pickup_borough" in filtered_cube.columns:
            hourly_boro = filtered_cube.groupby(["hour_of_day", "pickup_borough"])["trip_count"].sum().reset_index()
            fig_hourly = px.line(
                hourly_boro,
                x="hour_of_day",
                y="trip_count",
                color="pickup_borough",
                markers=True,
                color_discrete_sequence=[ACCENT_CYAN, ACCENT_INDIGO, ACCENT_EMERALD, ACCENT_AMBER]
            )
            fig_hourly.update_layout(
                **get_plotly_layout(
                    height=300,
                    takeaway_title="Manhattan volume climbs steadily from 06:00, cresting at 19:00"
                ),
                xaxis_title="Hour of Day (24h)",
                yaxis_title="Total Trips"
            )
            fig_hourly.update_xaxes(tickmode="linear", tick0=0, dtick=3)
            st.plotly_chart(fig_hourly, use_container_width=True)
            render_insight_note("Urban core pickup volume builds throughout the business day, maintaining high levels until midnight before declining into early morning hours.")

    with col_b:
        if "hour_of_day" in filtered_cube.columns and "total_distance_miles" in filtered_cube.columns:
            speed_agg = filtered_cube.groupby("hour_of_day").agg({
                "total_distance_miles": "sum",
                "total_duration_minutes": "sum",
                "total_fare_amount": "sum",
                "trip_count": "sum"
            }).reset_index()
            speed_agg["avg_speed_mph"] = speed_agg["total_distance_miles"] / (speed_agg["total_duration_minutes"] / 60.0)

            fig_speed = go.Figure()
            fig_speed.add_trace(go.Scatter(
                x=speed_agg["hour_of_day"],
                y=speed_agg["avg_speed_mph"],
                name="Avg Speed (mph)",
                mode="lines+markers",
                line=dict(color=ACCENT_EMERALD, width=2.5),
            ))
            fig_speed.update_layout(
                **get_plotly_layout(
                    height=300,
                    takeaway_title="Traffic speeds drop sharply between 08:00 and 19:00"
                ),
                xaxis_title="Hour of Day (24h)",
                yaxis_title="Effective Velocity (mph)"
            )
            fig_speed.update_xaxes(tickmode="linear", tick0=0, dtick=3)
            st.plotly_chart(fig_speed, use_container_width=True)
            render_insight_note("Average taxi speed peaks at over 15 mph during 04:00 to 05:00 and reaches its lowest point during the 17:00 to 18:00 rush hour window.")
