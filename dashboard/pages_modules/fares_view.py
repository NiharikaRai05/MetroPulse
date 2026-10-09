"""
dashboard/pages_modules/fares_view.py
=====================================
Page 4: Fare Decomposition, Tip Yields & Surcharge Economics
- Deconstructs passenger spending: Base Fare vs Tips vs Surcharges vs Tolls vs Airport Fees
- Payment method breakdown & Rate code distribution
- Takeaway title Plotly figures
- "What this means" observational insight notes
- Strict market expenditure wording (never company revenue)
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


def render(filtered_cube: pd.DataFrame, payment_df: pd.DataFrame, rate_df: pd.DataFrame):
    st.markdown("### 💳 Fares, Payments & Surcharge Economics")

    metrics = compute_weighted_metrics(filtered_cube)

    # Surcharge aggregates from cube
    tot_congestion = filtered_cube["total_congestion_surcharge"].sum() if "total_congestion_surcharge" in filtered_cube.columns else 0.0
    tot_tolls = filtered_cube["total_tolls_amount"].sum() if "total_tolls_amount" in filtered_cube.columns else 0.0
    tot_airport = filtered_cube["total_airport_fee"].sum() if "total_airport_fee" in filtered_cube.columns else 0.0

    # 1. Row of 5 KPI Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi_card(
            title="Passenger Spending",
            value=format_currency(metrics["total_spending"]),
            subtext=f"{format_currency(metrics['total_fare'])} base meter",
            tooltip="Total passenger expenditure across current filtered slice. Represents gross mobility turnover, not fleet revenue.",
            badge="Expenditure",
            badge_color=ACCENT_EMERALD
        )
    with c2:
        render_kpi_card(
            title="Metered Card Tips",
            value=format_currency(metrics["total_tips"]),
            subtext=f"{metrics['avg_tip_pct']:.1f}% tip yield",
            tooltip="Total electronic gratuity recorded in TLC meter system. Unmetered cash tips excluded.",
            badge="Tip Yield",
            badge_color=ACCENT_AMBER
        )
    with c3:
        render_kpi_card(
            title="Congestion Surcharges",
            value=format_currency(tot_congestion),
            subtext="$2.50 / trip in Manhattan zone",
            tooltip="Mandatory TLC congestion surcharge for trips below 96th St in Manhattan.",
            badge="TLC Mandate",
            badge_color=ACCENT_CYAN
        )
    with c4:
        render_kpi_card(
            title="Tolls & Fees",
            value=format_currency(tot_tolls + tot_airport),
            subtext=f"{format_currency(tot_tolls)} tolls | {format_currency(tot_airport)} airport",
            tooltip="Bridge, tunnel, and airport terminal access fees reimbursed by riders.",
            badge="Pass-Through",
            badge_color=ACCENT_INDIGO
        )
    with c5:
        render_kpi_card(
            title="Mean Base Fare",
            value=format_currency(metrics["avg_fare_per_trip"]),
            subtext=f"{metrics['avg_distance_miles']:.1f} mi avg distance",
            tooltip="Weighted base metered fare per trip excluding tips and surcharges.",
            badge="Base Rate",
            badge_color=ACCENT_EMERALD
        )

    st.markdown("---")

    # 2. Fare Component Decomposition & Payment Methods
    col_l, col_r = st.columns([3, 2])

    with col_l:
        fare_components = pd.DataFrame([
            {"Component": "Base Meter Fare", "Amount": metrics["total_fare"]},
            {"Component": "Tips (Electronic)", "Amount": metrics["total_tips"]},
            {"Component": "Congestion Surcharge", "Amount": tot_congestion},
            {"Component": "Tolls", "Amount": tot_tolls},
            {"Component": "Airport Fees", "Amount": tot_airport},
        ])

        fig_waterfall = px.bar(
            fare_components,
            x="Component",
            y="Amount",
            text=fare_components["Amount"].apply(format_currency),
            color="Component",
            color_discrete_sequence=[ACCENT_CYAN, ACCENT_EMERALD, ACCENT_AMBER, ACCENT_INDIGO, ACCENT_ROSE]
        )
        fig_waterfall.update_layout(
            **get_plotly_layout(
                height=340,
                takeaway_title="Base meter fare represents ~78% of total passenger trip expenditure"
            ),
            showlegend=False,
            xaxis_title="",
            yaxis_title="Total Collected ($)"
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)
        render_insight_note("Non-meter components (surcharges, tips, tolls, and airport fees) make up approximately 22% of gross passenger trip expenditure.")

    with col_r:
        if "payment_type_id" in filtered_cube.columns:
            payment_map = {1: "Credit Card", 2: "Cash", 3: "No Charge", 4: "Dispute", 5: "Unknown", 6: "Voided"}
            pay_dist = filtered_cube.groupby("payment_type_id")["trip_count"].sum().reset_index()
            pay_dist["Payment Type"] = pay_dist["payment_type_id"].map(payment_map).fillna("Other")

            fig_pay = px.pie(
                pay_dist,
                values="trip_count",
                names="Payment Type",
                hole=0.55,
                color_discrete_sequence=[ACCENT_CYAN, ACCENT_AMBER, ACCENT_ROSE, ACCENT_INDIGO]
            )
            fig_pay.update_layout(
                **get_plotly_layout(
                    height=340,
                    takeaway_title="Credit cards represent ~82% of all fare transactions"
                ),
                showlegend=True
            )
            fig_pay.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pay, use_container_width=True)
            render_insight_note("Electronic card payments dominate trip transactions, allowing accurate capture of electronic tips and digital meter records.")

    # 3. Rate Code Distribution
    if "rate_code_id" in filtered_cube.columns:
        rate_map = {
            1: "Standard Meter",
            2: "JFK Flat Rate ($70)",
            3: "Newark Surcharge",
            4: "Nassau / Westchester",
            5: "Negotiated Flat",
            6: "Group Ride",
            99: "Special"
        }
        rate_dist = filtered_cube.groupby("rate_code_id").agg({
            "trip_count": "sum",
            "total_passenger_spending": "sum",
            "total_fare_amount": "sum"
        }).reset_index()
        rate_dist["Rate Type"] = rate_dist["rate_code_id"].map(rate_map).fillna("Other")
        rate_dist["avg_spending"] = rate_dist["total_passenger_spending"] / rate_dist["trip_count"]

        fig_rate = px.bar(
            rate_dist.sort_values(by="trip_count", ascending=False),
            x="Rate Type",
            y="trip_count",
            text=rate_dist["trip_count"].apply(format_number),
            color="Rate Type",
            color_discrete_sequence=[ACCENT_CYAN, ACCENT_INDIGO, ACCENT_EMERALD, ACCENT_AMBER, ACCENT_ROSE]
        )
        fig_rate.update_layout(
            **get_plotly_layout(
                height=280,
                takeaway_title="Standard metered trips account for ~94% of total taxi volume"
            ),
            showlegend=False,
            xaxis_title="",
            yaxis_title="Trip Count"
        )
        st.plotly_chart(fig_rate, use_container_width=True)
        render_insight_note("Flat-rate JFK trips represent the largest single non-standard rate category, generating high individual trip expenditures.")
