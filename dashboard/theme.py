"""
dashboard/theme.py
==================
Ultra-premium, modern executive styling for MetroPulse:
- Glowing glassmorphic cards with neon border accents
- Top-level polished tabs with active cyan glow
- Integrated drilldown comparison containers
- Standardized Plotly figure templates with takeaway titles
- Status badges (PASS / WARN / FAIL)
"""

from typing import Optional
import streamlit as st
import plotly.graph_objects as go

# Single primary accent theme palette
ACCENT_CYAN = "#38bdf8"
ACCENT_INDIGO = "#818cf8"
ACCENT_EMERALD = "#34d399"
ACCENT_AMBER = "#fbbf24"
ACCENT_ROSE = "#f87171"

# Backward compatibility aliases
PRIMARY_ACCENT = ACCENT_CYAN
SECONDARY_ACCENT = ACCENT_INDIGO
SUCCESS_COLOR = ACCENT_EMERALD
WARNING_COLOR = ACCENT_AMBER
DANGER_COLOR = ACCENT_ROSE

BG_CONTAINER = "#111827"
BORDER_SUBTLE = "rgba(148, 163, 184, 0.14)"
TEXT_MUTED = "#94a3b8"


def apply_custom_css():
    """Injects high-end executive styling with glowing glassmorphism and top tabs."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Canvas Background */
    .stApp {
        background: radial-gradient(circle at 10% 10%, #172554 0%, #0b0f19 50%, #030712 100%);
        color: #f1f5f9;
    }

    /* Polished Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(13, 19, 34, 0.95) !important;
        backdrop-filter: blur(16px);
        border-right: 1px solid rgba(56, 189, 248, 0.15);
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stDateInput label {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #cbd5e1 !important;
        margin-bottom: 2px !important;
    }

    /* Glowing Glassmorphism KPI Cards */
    .kpi-card-v2 {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 10px;
        padding: 14px 16px;
        min-height: 102px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.25s ease-in-out;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
    }
    .kpi-card-v2:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.5);
        box-shadow: 0 8px 25px -4px rgba(56, 189, 248, 0.2);
    }
    .kpi-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
    }
    .kpi-num {
        font-size: 1.7rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin: 4px 0;
        line-height: 1.15;
    }
    .kpi-desc {
        font-size: 0.74rem;
        color: #64748b;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Header Badges */
    .header-badge-container {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 6px;
        margin-bottom: 16px;
    }
    .header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(17, 24, 39, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #94a3b8;
    }
    .header-badge-cyan {
        color: #38bdf8;
        border-color: rgba(56, 189, 248, 0.35);
        background: rgba(56, 189, 248, 0.1);
    }
    .header-badge-emerald {
        color: #34d399;
        border-color: rgba(52, 211, 153, 0.35);
        background: rgba(52, 211, 153, 0.1);
    }

    /* Top Horizontal Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: rgba(15, 23, 42, 0.75);
        backdrop-filter: blur(10px);
        padding: 6px;
        border-radius: 10px;
        border: 1px solid rgba(56, 189, 248, 0.2);
        margin-bottom: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0 16px;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #f1f5f9;
        background-color: rgba(56, 189, 248, 0.08);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(56, 189, 248, 0.18) !important;
        border-color: rgba(56, 189, 248, 0.4) !important;
        color: #38bdf8 !important;
        font-weight: 700;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
    }

    /* Active Filter Chips */
    .chip-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 4px;
        margin-bottom: 14px;
    }
    .filter-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 4px;
        padding: 3px 8px;
        font-size: 0.72rem;
        font-weight: 600;
    }

    /* Observational Insight Box */
    .insight-note {
        background: rgba(17, 24, 39, 0.85);
        border-left: 3px solid #38bdf8;
        border-radius: 0 8px 8px 0;
        padding: 10px 14px;
        margin-top: 8px;
        margin-bottom: 16px;
        font-size: 0.8rem;
        color: #cbd5e1;
        line-height: 1.45;
        border-top: 1px solid rgba(148, 163, 184, 0.08);
        border-right: 1px solid rgba(148, 163, 184, 0.08);
        border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    }
    .insight-note strong {
        color: #38bdf8;
    }

    /* Status Badges */
    .status-pass {
        display: inline-block;
        padding: 3px 8px;
        background: rgba(52, 211, 153, 0.15);
        border: 1px solid rgba(52, 211, 153, 0.4);
        color: #34d399;
        font-weight: 700;
        border-radius: 4px;
        font-size: 0.72rem;
    }
    .status-warn {
        display: inline-block;
        padding: 3px 8px;
        background: rgba(251, 191, 36, 0.15);
        border: 1px solid rgba(251, 191, 36, 0.4);
        color: #fbbf24;
        font-weight: 700;
        border-radius: 4px;
        font-size: 0.72rem;
    }
    .status-fail {
        display: inline-block;
        padding: 3px 8px;
        background: rgba(248, 113, 113, 0.15);
        border: 1px solid rgba(248, 113, 113, 0.4);
        color: #f87171;
        font-weight: 700;
        border-radius: 4px;
        font-size: 0.72rem;
    }

    /* Drilldown Panel Container */
    .drilldown-panel {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 8px;
        padding: 16px;
        margin-top: 12px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_kpi_card(
    title: str,
    value: str,
    subtext: str = "",
    tooltip: str = "",
    badge: str = "",
    badge_color: str = ACCENT_CYAN
):
    """Renders a clean, executive KPI card."""
    tooltip_attr = f'title="{tooltip}"' if tooltip else ""
    badge_elem = f'<span style="font-size:0.7rem; color:{badge_color}; font-weight:700;">{badge}</span>' if badge else ""
    html = f"""
    <div class="kpi-card-v2" {tooltip_attr}>
        <div class="kpi-header">
            <span>{title}</span>
            {badge_elem}
        </div>
        <div class="kpi-num">{value}</div>
        <div class="kpi-desc" {tooltip_attr}>{subtext}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_insight_note(text: str):
    """Renders a standard 'What this means' observational note."""
    st.markdown(
        f'<div class="insight-note"><strong>💡 What this means:</strong> {text}</div>',
        unsafe_allow_html=True
    )


def format_currency(val: float) -> str:
    """Formats dollar amounts cleanly."""
    if abs(val) >= 1e9:
        return f"${val / 1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val / 1e6:.2f}M"
    if abs(val) >= 1e3:
        return f"${val / 1e3:.1f}k"
    return f"${val:.2f}"


def format_number(val: float) -> str:
    """Formats integer counts with commas or abbreviations."""
    if abs(val) >= 1e9:
        return f"{val / 1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"{val / 1e6:.2f}M"
    if abs(val) >= 1e3:
        return f"{val / 1e3:.1f}k"
    return f"{int(val):,}"


def get_plotly_layout(
    height: int = 360,
    takeaway_title: str = "",
    **overrides
) -> dict:
    """Standardized shared template for all Plotly charts with takeaway title styling.
    
    Deep-merges custom keyword overrides (such as xaxis, yaxis, margin, legend)
    to prevent TypeError duplicate keyword argument collisions.
    """
    base_layout = {
        "height": height,
        "title": {
            "text": f"<b>{takeaway_title}</b>" if takeaway_title else "",
            "font": {"size": 13, "color": "#f1f5f9", "family": "Plus Jakarta Sans, sans-serif"},
            "x": 0.01,
            "y": 0.97
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(17, 24, 39, 0.45)",
        "font": {"color": "#94a3b8", "family": "Plus Jakarta Sans, sans-serif"},
        "margin": {"l": 35, "r": 25, "t": 45 if takeaway_title else 25, "b": 35},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 10, "color": "#cbd5e1"}
        },
        "hoverlabel": {
            "bgcolor": "#0d1322",
            "font_size": 11,
            "font_family": "Plus Jakarta Sans, sans-serif"
        }
    }

    # Deep merge overrides into base_layout
    for key, value in overrides.items():
        if key in base_layout and isinstance(base_layout[key], dict) and isinstance(value, dict):
            base_layout[key] = {**base_layout[key], **value}
        else:
            base_layout[key] = value

    return base_layout

