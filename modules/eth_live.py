"""Live Ethereum panels for the multi-asset dashboard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.ethereum_client import latest_block_snapshot
from modules.dashboard_theme import (
    apply_plotly_theme,
    current_accent,
    current_accent_glow,
    current_accent_soft,
    render_kpi,
)


def _snapshot() -> dict:
    state_key = "eth_live_snapshot"
    snapshot = st.session_state.get(state_key)
    live = latest_block_snapshot()
    if snapshot is None or snapshot["hash"] != live["hash"]:
        live["last_update"] = datetime.now(UTC).strftime("%H:%M:%S UTC")
        st.session_state[state_key] = live
        return live
    return snapshot


def _build_fee_df(snapshot: dict) -> pd.DataFrame:
    df = pd.DataFrame(snapshot["fee_history"])
    df["Date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    return df.sort_values("Date").reset_index(drop=True)


def _forecast_base_fee(df: pd.DataFrame) -> tuple[float, float]:
    values = df["base_fee_gwei"].tolist()
    if len(values) < 2:
        return values[-1], 0.0
    last_step = values[-1] - values[-2]
    prediction = max(values[-1] + last_step * 0.6, 0.0)
    return prediction, last_step


def render_state() -> None:
    snapshot = _snapshot()
    accent = current_accent()
    accent_glow = current_accent_glow(0.2)

    st.subheader("Proof of Work Monitor")
    st.caption("What Ethereum is doing right now.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi("Block Height", f"{snapshot['block_number']:,}")
    with col2:
        render_kpi("Base Fee", f"{snapshot['base_fee_gwei']:,.2f} gwei")
    with col3:
        render_kpi("Gas Used", f"{snapshot['gas_ratio'] * 100:,.1f}%")
    with col4:
        render_kpi("Block Time", f"{snapshot['block_time']:.1f} s" if snapshot["block_time"] else "—")

    left, right = st.columns([1.2, 1])
    with left:
        st.write(f"Hash: `{snapshot['hash']}`")
        st.write(f"Timestamp: {snapshot['timestamp']}")
    with right:
        st.write(f"Transactions: `{snapshot['transactions']:,}`")
        st.write(f"Gas price: `{snapshot['gas_price_gwei']:.2f} gwei`")

    load_state = "HIGH" if snapshot["target_ratio"] > 1.15 else "MEDIUM" if snapshot["target_ratio"] > 0.9 else "LOW"
    message = {
        "HIGH": "Block demand is running above the target gas budget.",
        "MEDIUM": "Demand is close to the target gas budget.",
        "LOW": "Block demand is below Ethereum's target gas load.",
    }[load_state]

    a, b = st.columns([1.35, 1])
    with a:
        if load_state == "HIGH":
            st.warning("Gas demand above target")
        else:
            st.success("Gas demand inside normal range")
    with b:
        render_kpi("Network stress", load_state)
    st.caption(message)

    df = _build_fee_df(snapshot).tail(20)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["gas_used_ratio"] * 100,
            mode="lines",
            line=dict(color=accent, width=3, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x|%d %b %H:%M}<br>Gas used %{y:.1f}%<extra></extra>",
            name="Gas used",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=[50] * len(df),
            mode="lines",
            line=dict(color="rgba(148, 163, 184, 0.38)", width=1.2, dash="dot"),
            hoverinfo="skip",
            name="Target",
        )
    )
    apply_plotly_theme(fig, height=320, xaxis_title="", yaxis_title="Gas used %")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
    st.caption(f"50% is the EIP-1559 target utilization. Last update: {snapshot['last_update']}")


def render_mechanism() -> None:
    snapshot = _snapshot()
    st.subheader("Block Header Analyzer")
    st.caption("How the latest Ethereum block is assembled.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi("Block Height", f"{snapshot['block_number']:,}")
    with col2:
        render_kpi("Base Fee", f"{snapshot['base_fee_gwei']:,.2f} gwei")
    with col3:
        render_kpi("Gas Limit", f"{snapshot['gas_limit'] / 1_000_000:,.1f}M")
    with col4:
        render_kpi("Next Base Fee", f"{snapshot['next_base_fee_gwei']:,.2f} gwei")

    st.write(f"Block hash: `{snapshot['hash']}`")
    st.write(f"Parent hash: `{snapshot['parent_hash']}`")
    st.write(f"Timestamp: {snapshot['timestamp']}")

    d1, d2 = st.columns(2)
    with d1:
        st.write(f"Gas used: `{snapshot['gas_used']:,}`")
        st.write(f"Gas target: `{snapshot['gas_target']:,.0f}`")
        st.write(f"Transactions: `{snapshot['transactions']:,}`")
    with d2:
        st.write(f"Utilization vs target: `{snapshot['target_ratio']:.2f}x`")
        st.write(f"Gas utilization vs limit: `{snapshot['gas_ratio'] * 100:.1f}%`")
        st.write("Status: `Valid`")

    st.code(
        "\n".join(
            [
                f"baseFeePerGas = {snapshot['base_fee_wei']}",
                f"gasUsed = {snapshot['gas_used']}",
                f"gasLimit = {snapshot['gas_limit']}",
                f"predictedNextBaseFee = {snapshot['next_base_fee_wei']}",
            ]
        ),
        language="text",
    )


def render_evolution() -> None:
    snapshot = _snapshot()
    accent = current_accent()
    accent_soft = current_accent_soft()
    accent_glow = current_accent_glow(0.18)
    df = _build_fee_df(snapshot)

    st.subheader("Difficulty History")
    st.caption("How Ethereum fees have evolved across recent blocks.")

    current_fee = df["base_fee_gwei"].iloc[-1]
    previous_fee = df["base_fee_gwei"].iloc[-2] if len(df) > 1 else current_fee
    change_pct = ((current_fee - previous_fee) / previous_fee * 100) if previous_fee else 0.0
    avg_ratio = df["gas_used_ratio"].tail(10).mean() * 100 if not df.empty else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Current Base Fee", f"{current_fee:,.2f} gwei", f"{change_pct:+.2f}%")
    with c2:
        render_kpi("Recent Avg Gas", f"{avg_ratio:,.1f}%")
    with c3:
        render_kpi("Last update", snapshot["last_update"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["base_fee_gwei"],
            mode="lines",
            line=dict(color=accent, width=3, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x|%d %b %H:%M}<br>Base fee %{y:.2f} gwei<extra></extra>",
            name="Base fee",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["Date"].tail(1),
            y=df["base_fee_gwei"].tail(1),
            mode="markers",
            marker=dict(color=accent_soft, size=8),
            hovertemplate="%{x|%d %b %H:%M}<br>Latest %{y:.2f} gwei<extra></extra>",
            name="Latest",
        )
    )
    apply_plotly_theme(fig, height=420, xaxis_title="", yaxis_title="gwei")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def render_forecast() -> None:
    snapshot = _snapshot()
    accent = current_accent()
    accent_soft = current_accent_soft()
    accent_glow = current_accent_glow(0.14)
    df = _build_fee_df(snapshot)
    prediction, slope = _forecast_base_fee(df)
    next_date = df["Date"].iloc[-1] + timedelta(seconds=snapshot["block_time"] or 12)
    forecast_df = pd.concat(
        [
            df[["Date", "base_fee_gwei"]].rename(columns={"base_fee_gwei": "Value"}).assign(Series="Historical"),
            pd.DataFrame([{"Date": next_date, "Value": prediction, "Series": "Forecast"}]),
        ],
        ignore_index=True,
    )

    trend = "Increasing" if prediction > snapshot["base_fee_gwei"] else "Decreasing" if prediction < snapshot["base_fee_gwei"] else "Flat"
    confidence = "High" if abs(prediction - snapshot["next_base_fee_gwei"]) < 0.15 else "Medium" if abs(prediction - snapshot["next_base_fee_gwei"]) < 0.6 else "Low"

    st.subheader("AI Component")
    st.caption("What the next Ethereum block fee likely looks like.")

    fig = go.Figure()
    hist = forecast_df[forecast_df["Series"] == "Historical"]
    fc = forecast_df[forecast_df["Series"] == "Forecast"]
    fig.add_trace(
        go.Scatter(
            x=hist["Date"],
            y=hist["Value"],
            mode="lines",
            line=dict(color=accent, width=3, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x|%d %b %H:%M}<br>%{y:.2f} gwei<extra></extra>",
            name="Historical",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pd.concat([hist["Date"].tail(1), fc["Date"]]),
            y=pd.concat([hist["Value"].tail(1), fc["Value"]]),
            mode="lines+markers",
            line=dict(color=accent_soft, width=2.2, dash="dot", shape="spline"),
            marker=dict(color=accent_soft, size=7),
            hovertemplate="%{x|%d %b %H:%M}<br>%{y:.2f} gwei<extra></extra>",
            name="Forecast",
        )
    )
    apply_plotly_theme(fig, height=390, xaxis_title="", yaxis_title="gwei")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

    k1, k2, k3 = st.columns(3)
    with k1:
        render_kpi("Expected Base Fee", f"{prediction:,.2f} gwei")
    with k2:
        render_kpi("Trend", trend)
    with k3:
        render_kpi("Confidence", confidence)

    st.caption(
        f"Protocol estimate: {snapshot['next_base_fee_gwei']:.2f} gwei. "
        f"Observed short-term fee slope: {slope:+.2f} gwei per block. "
        f"Last update: {snapshot['last_update']}"
    )
