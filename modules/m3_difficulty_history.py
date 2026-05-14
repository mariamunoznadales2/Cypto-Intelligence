"""Streamlit module for visualizing Bitcoin difficulty history."""

from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_difficulty_history, get_recent_blocks
from modules.dashboard_theme import GREEN, GREEN_GLOW, apply_plotly_theme, render_kpi


def build_dataframe(values: list[dict]) -> pd.DataFrame:
    """Convert raw difficulty history values into a clean dataframe."""
    if not values:
        raise ValueError("No difficulty history data was returned by the API.")

    df = pd.DataFrame(values)
    required_columns = {"x", "y"}
    if not required_columns.issubset(df.columns):
        raise ValueError("Difficulty history response is missing expected columns.")

    df = df.rename(columns={"x": "Date", "y": "Difficulty"})
    df["Date"] = pd.to_datetime(df["Date"], unit="s", utc=True)
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def render_summary_metrics(df: pd.DataFrame) -> None:
    """Render key metrics about the fetched difficulty history."""
    latest_value = df["Difficulty"].iloc[-1]
    previous_value = df["Difficulty"].iloc[-2] if len(df) > 1 else latest_value
    change_pct = ((latest_value - previous_value) / previous_value * 100) if previous_value else 0.0
    min_value = df["Difficulty"].min()
    max_value = df["Difficulty"].max()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi("Latest Difficulty", f"{latest_value:,.2f}")
    with col2:
        render_kpi("Previous Point", f"{previous_value:,.2f}", f"{change_pct:+.2f}%")
    with col3:
        render_kpi("Minimum", f"{min_value:,.2f}")
    with col4:
        render_kpi("Maximum", f"{max_value:,.2f}")


def render_chart(df: pd.DataFrame) -> None:
    """Render the difficulty history chart."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Difficulty"],
            mode="lines",
            name="Difficulty",
            line=dict(color=GREEN, width=3, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=GREEN_GLOW,
            hovertemplate="Date %{x|%d %b %Y}<br>Difficulty %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df["Date"].iloc[-1]],
            y=[df["Difficulty"].iloc[-1]],
            mode="markers",
            name="Latest",
            marker=dict(color=GREEN, size=8, line=dict(color="rgba(134, 239, 172, 0.55)", width=1)),
            hovertemplate="Latest point<br>Date %{x|%d %b %Y}<br>Difficulty %{y:,.2f}<extra></extra>",
        )
    )
    apply_plotly_theme(fig, height=360, xaxis_title="Date", yaxis_title="Difficulty")
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )


def compute_recent_block_time_ratio() -> float | None:
    """Compare recent average block time against the 600s Bitcoin target."""
    blocks = get_recent_blocks(10)
    if len(blocks) < 2:
        return None

    intervals = []
    for index in range(1, len(blocks)):
        current_time = blocks[index - 1].get("mediantime", blocks[index - 1]["timestamp"])
        previous_time = blocks[index].get("mediantime", blocks[index]["timestamp"])
        intervals.append(current_time - previous_time)

    if not intervals:
        return None
    return (sum(intervals) / len(intervals)) / 600


def render() -> None:
    """Render the M3 panel."""
    latest_blocks = get_recent_blocks(1)
    current_hash = latest_blocks[0]["id"] if latest_blocks else "unknown"
    state_key = "m3_snapshot"

    snapshot = st.session_state.get(state_key)
    if snapshot is None or snapshot["hash"] != current_hash:
        values = get_difficulty_history(180)
        df = build_dataframe(values)
        ratio_vs_target = compute_recent_block_time_ratio()
        snapshot = {
            "hash": current_hash,
            "df": df,
            "ratio_vs_target": ratio_vs_target,
            "last_update": datetime.now(UTC).strftime("%H:%M:%S UTC"),
        }
        st.session_state[state_key] = snapshot

    st.subheader("Difficulty History")
    st.caption("How difficulty is moving versus its recent history.")

    try:
        df = snapshot["df"]
        ratio_vs_target = snapshot["ratio_vs_target"]

        render_summary_metrics(df)
        st.markdown("<br>", unsafe_allow_html=True)

        render_chart(df)

        st.markdown("<br>", unsafe_allow_html=True)

        insight_col1, insight_col2 = st.columns(2)
        with insight_col1:
            latest_value = df["Difficulty"].iloc[-1]
            baseline = df["Difficulty"].iloc[max(len(df) - 30, 0)]
            month_change = ((latest_value - baseline) / baseline * 100) if baseline else 0.0
            render_kpi("Vs recent history", f"{month_change:+.2f}%")
        with insight_col2:
            render_kpi(
                "Recent block time vs 600s",
                f"{ratio_vs_target:.2f}x" if ratio_vs_target is not None else "N/A",
            )

        st.caption(f"Last update: {snapshot['last_update']}")
    except Exception as exc:
        st.error(f"Error loading network evolution: {exc}")
