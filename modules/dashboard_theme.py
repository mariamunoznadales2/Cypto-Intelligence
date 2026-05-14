"""Shared visual helpers for dashboard charts and tables."""

from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st


BG_TRANSPARENT = "rgba(0, 0, 0, 0)"
TEXT_COLOR = "#D1D5DB"
MUTED_TEXT = "#6B7280"
GREEN = "#22C55E"
GREEN_GLOW = "rgba(34, 197, 94, 0.22)"
GREEN_SOFT = "rgba(134, 239, 172, 0.95)"
GRID = "rgba(107, 114, 128, 0.14)"
TABLE_BG = "rgba(11, 15, 12, 0.72)"
TABLE_ALT = "rgba(17, 24, 21, 0.92)"
TABLE_BORDER = "rgba(107, 114, 128, 0.18)"
TOOLTIP_BG = "rgba(11, 15, 12, 0.96)"


_PALETTES: dict[str, dict[str, str]] = {
    "BTC": {"accent": "#22C55E", "accent_soft": "#F7931A", "glow": "rgba(34, 197, 94, 0.22)"},
    "ETH": {"accent": "#627EEA", "accent_soft": "#B794F4", "glow": "rgba(98, 126, 234, 0.22)"},
    "SOL": {"accent": "#FF3B6B", "accent_soft": "#F472B6", "glow": "rgba(255, 59, 107, 0.22)"},
}


def _hex_to_rgba(color: str, alpha: float) -> str:
    color = color.lstrip("#")
    if len(color) != 6:
        return color
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def current_palette() -> dict[str, str]:
    """Return the active palette based on the asset selected in session state."""
    code = st.session_state.get("selected_asset", "BTC")
    return _PALETTES.get(code, _PALETTES["BTC"])


def current_accent() -> str:
    return current_palette()["accent"]


def current_accent_soft() -> str:
    return current_palette()["accent_soft"]


def current_accent_glow(alpha: float = 0.22) -> str:
    return _hex_to_rgba(current_accent(), alpha)


def apply_plotly_theme(
    fig: go.Figure,
    *,
    height: int = 360,
    xaxis_title: str = "",
    yaxis_title: str = "",
) -> go.Figure:
    """Apply the dashboard's plotly look and feel."""
    fig.update_layout(
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_TRANSPARENT,
        margin=dict(l=10, r=10, t=36, b=10),
        height=height,
        title_text="",
        showlegend=False,
        font=dict(color=TEXT_COLOR, size=12),
        title=dict(font=dict(color=TEXT_COLOR, size=18), x=0.02),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor=TOOLTIP_BG,
            bordercolor="rgba(34, 197, 94, 0.28)",
            font=dict(color="#F3F4F6", size=12),
            namelength=-1,
        ),
    )
    fig.update_xaxes(
        title=xaxis_title,
        showgrid=True,
        gridcolor=GRID,
        gridwidth=1,
        zeroline=False,
        showline=False,
        ticks="outside",
        tickcolor="rgba(107, 114, 128, 0.22)",
        tickfont=dict(color=MUTED_TEXT, size=11),
        title_font=dict(color=MUTED_TEXT, size=11),
        automargin=True,
    )
    fig.update_yaxes(
        title=yaxis_title,
        showgrid=True,
        gridcolor=GRID,
        gridwidth=0.8,
        zeroline=False,
        showline=False,
        ticks="outside",
        tickcolor="rgba(107, 114, 128, 0.22)",
        tickfont=dict(color=MUTED_TEXT, size=11),
        title_font=dict(color=MUTED_TEXT, size=11),
        automargin=True,
    )
    return fig


def render_kpi(label: str, value: str | int | float, delta: str | None = None) -> None:
    """Render a stable KPI card without relying on Streamlit's metric DOM."""
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    delta_html = ""
    if delta is not None and str(delta).strip():
        safe_delta = html.escape(str(delta))
        delta_html = f'<div class="kpi-delta">{safe_delta}</div>'

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{safe_label}</div>
            <div class="kpi-value" title="{safe_value}">{safe_value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
