"""Live Solana panels for the multi-asset dashboard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.solana_client import latest_network_snapshot
from modules.dashboard_theme import (
    apply_plotly_theme,
    current_accent,
    current_accent_glow,
    current_accent_soft,
    render_kpi,
)


def _snapshot() -> dict:
    state_key = "sol_live_snapshot"
    snapshot = st.session_state.get(state_key)
    live = latest_network_snapshot()
    if snapshot is None or snapshot["blockhash"] != live["blockhash"]:
        live["last_update"] = datetime.now(UTC).strftime("%H:%M:%S UTC")
        st.session_state[state_key] = live
        return live
    return snapshot


def _performance_df(snapshot: dict) -> pd.DataFrame:
    rows = []
    now = datetime.now(UTC)
    samples = list(reversed(snapshot["performance"]))
    for index, sample in enumerate(samples):
        rows.append(
            {
                "Date": now - timedelta(seconds=(len(samples) - index) * sample.get("samplePeriodSecs", 60)),
                "TPS": (sample.get("numTransactions", 0) / sample.get("samplePeriodSecs", 1)),
                "SlotTime": sample.get("samplePeriodSecs", 0) / max(sample.get("numSlots", 1), 1),
                "Slots": sample.get("numSlots", 0),
            }
        )
    return pd.DataFrame(rows)


def render_state() -> None:
    snapshot = _snapshot()
    accent = current_accent()
    accent_glow = current_accent_glow(0.2)
    df = _performance_df(snapshot)

    st.subheader("Proof of Work Monitor")
    st.caption("What Solana is doing right now.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Slot", f"{snapshot['slot']:,}")
    with c2:
        render_kpi("TPS", f"{snapshot['avg_tps']:,.0f}")
    with c3:
        render_kpi("Skip Rate", f"{snapshot['avg_skip_rate'] * 100:,.1f}%")
    with c4:
        render_kpi("Block Time", f"{snapshot['avg_block_time']:.2f} s")

    l1, l2 = st.columns([1.2, 1])
    with l1:
        st.write(f"Blockhash: `{snapshot['blockhash']}`")
        st.write(f"Timestamp: {snapshot['timestamp']}")
    with l2:
        st.write(f"Block height: `{snapshot['block_height']:,}`")
        st.write(f"Confirmation depth: `{snapshot['confirmation_depth']}`")

    network_state = (
        "HIGH" if snapshot["avg_skip_rate"] > 0.15 else
        "MEDIUM" if snapshot["avg_skip_rate"] > 0.07 else
        "LOW"
    )
    note = {
        "HIGH": "Slot production is losing continuity and validators are skipping more leader slots.",
        "MEDIUM": "Throughput is healthy, but slot consistency is softer than ideal.",
        "LOW": "Validators are sustaining stable slot production.",
    }[network_state]

    a, b = st.columns([1.35, 1])
    with a:
        if network_state == "HIGH":
            st.warning("Skip rate above normal")
        else:
            st.success("Slot production is stable")
    with b:
        render_kpi("Network stress", network_state)
    st.caption(note)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["TPS"],
            mode="lines",
            line=dict(color=accent, width=3, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x|%H:%M}<br>TPS %{y:,.0f}<extra></extra>",
            name="TPS",
        )
    )
    apply_plotly_theme(fig, height=320, xaxis_title="", yaxis_title="TPS")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
    st.caption(f"Recent performance samples from Solana RPC. Last update: {snapshot['last_update']}")


def render_mechanism() -> None:
    snapshot = _snapshot()
    latest_block = snapshot["latest_block"]
    tx_count = len(latest_block.get("transactions", []))

    st.subheader("Block Header Analyzer")
    st.caption("How the latest Solana slot is finalized.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Slot", f"{snapshot['slot']:,}")
    with c2:
        render_kpi("Parent Slot", f"{latest_block.get('parentSlot', 0):,}")
    with c3:
        render_kpi("Transactions", f"{tx_count:,}")
    with c4:
        render_kpi("Status", "Finalized")

    st.write(f"Blockhash: `{latest_block.get('blockhash', '—')}`")
    st.write(f"Previous blockhash: `{latest_block.get('previousBlockhash', '—')}`")
    st.write(f"Timestamp: {snapshot['timestamp']}")

    d1, d2 = st.columns(2)
    with d1:
        st.write(f"Block height: `{latest_block.get('blockHeight', 0):,}`")
        st.write(f"Signatures observed: `{tx_count:,}`")
    with d2:
        st.write(f"Rewards entries: `{len(latest_block.get('rewards', []))}`")
        st.write(f"Confirmation depth: `{snapshot['confirmation_depth']}`")


def render_evolution() -> None:
    snapshot = _snapshot()
    accent = current_accent()
    accent_soft = current_accent_soft()
    accent_glow = current_accent_glow(0.18)
    df = _performance_df(snapshot)

    st.subheader("Difficulty History")
    st.caption("How Solana throughput and slot timing are evolving.")

    avg_tps = df["TPS"].mean() if not df.empty else 0.0
    latest_tps = df["TPS"].iloc[-1] if not df.empty else 0.0
    avg_slot = df["SlotTime"].mean() if not df.empty else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Latest TPS", f"{latest_tps:,.0f}")
    with c2:
        render_kpi("Recent Avg TPS", f"{avg_tps:,.0f}")
    with c3:
        render_kpi("Avg Slot Time", f"{avg_slot:.2f} s")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["TPS"],
            mode="lines",
            line=dict(color=accent, width=3, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x|%H:%M}<br>TPS %{y:,.0f}<extra></extra>",
            name="TPS",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["Date"].tail(1),
            y=df["TPS"].tail(1),
            mode="markers",
            marker=dict(color=accent_soft, size=8),
            hovertemplate="%{x|%H:%M}<br>Latest %{y:,.0f}<extra></extra>",
            name="Latest",
        )
    )
    apply_plotly_theme(fig, height=420, xaxis_title="", yaxis_title="TPS")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def render_forecast() -> None:
    snapshot = _snapshot()
    accent = current_accent()
    accent_soft = current_accent_soft()
    accent_glow = current_accent_glow(0.14)
    df = _performance_df(snapshot)
    latest_tps = df["TPS"].iloc[-1] if not df.empty else 0.0
    recent_avg = df["TPS"].tail(8).mean() if not df.empty else 0.0
    slope = latest_tps - df["TPS"].iloc[-2] if len(df) > 1 else 0.0
    prediction = max(recent_avg + slope * 0.35, 0.0)
    next_time = df["Date"].iloc[-1] + timedelta(seconds=snapshot["avg_block_time"] or 0.4) if not df.empty else datetime.now(UTC)
    trend = "Increasing" if prediction > latest_tps else "Decreasing" if prediction < latest_tps else "Flat"
    confidence = "High" if snapshot["avg_skip_rate"] < 0.05 else "Medium" if snapshot["avg_skip_rate"] < 0.12 else "Low"

    st.subheader("AI Component")
    st.caption("What Solana throughput likely looks like next.")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["TPS"],
            mode="lines",
            line=dict(color=accent, width=3, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x|%H:%M}<br>TPS %{y:,.0f}<extra></extra>",
            name="Historical",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df["Date"].iloc[-1], next_time] if not df.empty else [datetime.now(UTC), next_time],
            y=[latest_tps, prediction],
            mode="lines+markers",
            line=dict(color=accent_soft, width=2.2, dash="dot", shape="spline"),
            marker=dict(color=accent_soft, size=7),
            hovertemplate="%{x|%H:%M}<br>TPS %{y:,.0f}<extra></extra>",
            name="Forecast",
        )
    )
    apply_plotly_theme(fig, height=390, xaxis_title="", yaxis_title="TPS")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Expected TPS", f"{prediction:,.0f}")
    with c2:
        render_kpi("Trend", trend)
    with c3:
        render_kpi("Confidence", confidence)

    st.caption(
        f"Recent average TPS: {recent_avg:,.0f}. "
        f"Current skip rate: {snapshot['avg_skip_rate'] * 100:.1f}%. "
        f"Last update: {snapshot['last_update']}"
    )
