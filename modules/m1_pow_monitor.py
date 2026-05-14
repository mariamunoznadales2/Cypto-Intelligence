"""Streamlit module for the Bitcoin Proof of Work monitor."""

from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import (
    get_blockstream_block,
    get_latest_block_hash,
    get_recent_blocks,
)
from modules.dashboard_theme import GREEN, GREEN_GLOW, apply_plotly_theme, render_kpi


def compute_block_times(blocks: list[dict]) -> list[int]:
    """Compute time differences between consecutive blocks.

    Prefer median time past because raw block timestamps are not guaranteed
    to increase monotonically in Bitcoin.
    """
    times = []
    for i in range(1, len(blocks)):
        current_timestamp = blocks[i - 1].get("mediantime", blocks[i - 1]["timestamp"])
        previous_timestamp = blocks[i].get("mediantime", blocks[i]["timestamp"])
        times.append(current_timestamp - previous_timestamp)
    return times


def format_timestamp(timestamp: int) -> str:
    """Format a UNIX timestamp for display."""
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def estimate_hash_rate(difficulty: float, avg_block_time: float) -> float:
    """Estimate network hash rate from difficulty and average block time."""
    return difficulty * (2**32) / avg_block_time


def compute_network_stress(avg_time: float | None) -> tuple[str, str]:
    """Classify network stress from the recent block-time deviation."""
    if avg_time is None:
        return "—", "No live block-time sample yet."

    if avg_time >= 780:
        return "HIGH", "Block time above normal. Confirmation flow is slowing down."
    if avg_time >= 660:
        return "MEDIUM", "Block production is running above target."
    return "LOW", "Block production is near the Bitcoin target."


def render() -> None:
    """Render the M1 panel."""
    current_hash = get_latest_block_hash()
    state_key = "m1_snapshot"

    snapshot = st.session_state.get(state_key)
    if snapshot is None or snapshot["hash"] != current_hash:
        latest_block = get_blockstream_block(current_hash)
        blocks = get_recent_blocks(10)
        block_times = compute_block_times(blocks)
        avg_time = sum(block_times) / len(block_times) if block_times else None
        difficulty = float(latest_block["difficulty"])
        hash_rate = estimate_hash_rate(difficulty, avg_time) if avg_time else None
        snapshot = {
            "hash": current_hash,
            "latest_block": latest_block,
            "block_times": block_times,
            "avg_time": avg_time,
            "difficulty": difficulty,
            "hash_rate": hash_rate,
            "last_update": datetime.now(UTC).strftime("%H:%M:%S UTC"),
        }
        st.session_state[state_key] = snapshot

    st.subheader("Proof of Work Monitor")
    st.caption("What the Bitcoin network is doing right now.")
    try:
        latest_block = snapshot["latest_block"]
        block_times = snapshot["block_times"]
        avg_time = snapshot["avg_time"]
        difficulty = snapshot["difficulty"]
        hash_rate = snapshot["hash_rate"]
        stress_level, stress_message = compute_network_stress(avg_time)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            render_kpi("Block Height", f"{latest_block['height']:,}")
        with kpi2:
            render_kpi("Difficulty", f"{difficulty:,.2f}")
        with kpi3:
            render_kpi("Hash Rate", f"{hash_rate:.2e} H/s" if hash_rate is not None else "N/A")
        with kpi4:
            render_kpi("Block Time", f"{avg_time:.2f} s" if avg_time is not None else "N/A")

        st.markdown("<br>", unsafe_allow_html=True)
        detail1, detail2 = st.columns([1.2, 1])
        with detail1:
            st.write(f"Hash: `{latest_block['id']}`")
            st.write(f"Timestamp: {format_timestamp(latest_block['timestamp'])}")
        with detail2:
            st.write(f"Transactions: `{latest_block['tx_count']}`")
            st.write(f"Nonce: `{latest_block['nonce']}`")

        st.markdown("<br>", unsafe_allow_html=True)

        alert_col1, alert_col2 = st.columns([1.3, 1])
        with alert_col1:
            if avg_time is not None and avg_time > 660:
                st.warning("Block time above normal")
            else:
                st.success("Block production is within normal range")
        with alert_col2:
            render_kpi("Network stress", stress_level)
        st.caption(stress_message)

        if avg_time is None:
            st.warning("Not enough recent blocks were returned to compute block times.")
        else:
            insight1, insight2 = st.columns(2)
            with insight1:
                render_kpi("Vs 600s target", f"{avg_time / 600:.2f}x")
            with insight2:
                render_kpi("Sample size", f"{len(block_times)} intervals")
            chart_df = pd.DataFrame(
                {
                    "Interval": list(range(1, len(block_times) + 1)),
                    "Seconds": list(reversed(block_times)),
                }
            )
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=chart_df["Interval"],
                    y=chart_df["Seconds"],
                    mode="lines",
                    name="Block Time",
                    line=dict(color=GREEN, width=3, shape="spline", smoothing=1.0),
                    fill="tozeroy",
                    fillcolor=GREEN_GLOW,
                    hovertemplate="Interval %{x}<br>%{y:.0f} s<extra></extra>",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=chart_df["Interval"],
                    y=[600] * len(chart_df),
                    mode="lines",
                    name="Target",
                    line=dict(color="rgba(107, 114, 128, 0.5)", width=1.2, dash="dot"),
                    hoverinfo="skip",
                )
            )
            apply_plotly_theme(
                fig,
                height=320,
                xaxis_title="Most recent intervals",
                yaxis_title="Seconds",
            )
            fig.update_xaxes(dtick=1)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
            st.caption(
                f"600 seconds is the Bitcoin production target. Last update: {snapshot['last_update']}"
            )
    except Exception as exc:
        st.error(f"Error loading network snapshot: {exc}")
