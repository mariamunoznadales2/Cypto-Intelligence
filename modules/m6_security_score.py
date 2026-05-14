"""Optional M6 module: Bitcoin 51% attack economics and confirmation risk."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_blockstream_block, get_btc_usd_price, get_latest_block_hash, get_recent_blocks
from modules.m1_pow_monitor import compute_block_times, estimate_hash_rate
from modules.dashboard_theme import GREEN, GREEN_GLOW, GREEN_SOFT, apply_plotly_theme, render_kpi


def format_hash_rate(value: float) -> str:
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s", "ZH/s"]
    unit_index = 0
    while value >= 1000 and unit_index < len(units) - 1:
        value /= 1000
        unit_index += 1
    return f"{value:,.2f} {units[unit_index]}"


def attack_probability(confirmations: int, attacker_share: float) -> float:
    """Nakamoto 2008 section 11 catch-up probability for q < p."""
    q = attacker_share
    p = 1 - q
    if confirmations <= 0:
        return 1.0
    if q <= 0:
        return 0.0
    if q >= p:
        return 1.0

    lam = confirmations * (q / p)
    cumulative = 0.0
    for k in range(confirmations + 1):
        poisson = math.exp(-lam) * (lam**k) / math.factorial(k)
        cumulative += poisson * (1 - (q / p) ** (confirmations - k))
    return max(0.0, min(1.0, 1 - cumulative))


def attack_cost_per_hour(
    network_hash_rate: float,
    efficiency_j_per_th: float,
    electricity_usd_per_kwh: float,
    hardware_usd_per_th: float,
    amortization_days: int,
) -> tuple[float, float, float]:
    """Estimate hourly cost to exceed the current network hash rate."""
    attacker_hash_rate = network_hash_rate * 1.01
    th_per_second = attacker_hash_rate / 1e12
    power_kw = th_per_second * efficiency_j_per_th / 1000
    electricity_cost = power_kw * electricity_usd_per_kwh
    hardware_hourly = th_per_second * hardware_usd_per_th / max(amortization_days * 24, 1)
    return attacker_hash_rate, electricity_cost, electricity_cost + hardware_hourly


def render() -> None:
    """Render the M6 panel."""
    st.subheader("Security Score")
    st.caption("51% attack cost estimate and Nakamoto confirmation-risk curve.")

    try:
        latest_hash = get_latest_block_hash()
        latest_block = get_blockstream_block(latest_hash)
        recent_blocks = get_recent_blocks(10)
        block_times = compute_block_times(recent_blocks)
        avg_time = sum(block_times) / len(block_times) if block_times else 600
        difficulty = float(latest_block["difficulty"])
        network_hash_rate = estimate_hash_rate(difficulty, avg_time)

        btc_usd = get_btc_usd_price()
        st.caption(f"BTC/USD reference: ${btc_usd:,.0f}")

        col_a, col_b = st.columns(2)
        with col_a:
            efficiency = st.slider("ASIC efficiency (J/TH)", 12.0, 45.0, 20.0, 1.0)
            electricity = st.slider("Electricity price ($/kWh)", 0.02, 0.25, 0.06, 0.01)
        with col_b:
            hardware = st.slider("Hardware cost ($/TH/s)", 8.0, 35.0, 18.0, 1.0)
            amortization = st.slider("Hardware amortization (days)", 30, 730, 365, 30)

        attacker_hash_rate, electric_hour, total_hour = attack_cost_per_hour(
            network_hash_rate,
            efficiency,
            electricity,
            hardware,
            amortization,
        )

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            render_kpi("Live Hash Rate", format_hash_rate(network_hash_rate))
        with kpi2:
            render_kpi("51% Hash Rate", format_hash_rate(attacker_hash_rate))
        with kpi3:
            render_kpi("Attack Cost", f"${total_hour:,.0f}/hour")

        st.write(
            f"Electricity-only component: `${electric_hour:,.0f}/hour`; "
            f"hardware-amortized estimate: `${total_hour:,.0f}/hour`."
        )

        attacker_share = st.slider("Attacker share q", 0.01, 0.49, 0.10, 0.01)
        rows = [
            {
                "Confirmations": z,
                "Attack probability": attack_probability(z, attacker_share),
            }
            for z in range(0, 13)
        ]
        risk_df = pd.DataFrame(rows)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=risk_df["Confirmations"],
                y=risk_df["Attack probability"],
                mode="lines+markers",
                name="Catch-up probability",
                line=dict(color=GREEN, width=3, shape="spline", smoothing=0.8),
                marker=dict(color=GREEN_SOFT, size=7),
                fill="tozeroy",
                fillcolor=GREEN_GLOW,
                hovertemplate="%{x} confirmations<br>%{y:.6%}<extra></extra>",
            )
        )
        apply_plotly_theme(
            fig,
            height=360,
            xaxis_title="Confirmations",
            yaxis_title="Attack probability",
        )
        fig.update_yaxes(tickformat=".2%")
        fig.update_xaxes(dtick=1)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(
            "Probability uses Nakamoto 2008 section 11 with p = 1 - q. "
            f"Last update: {datetime.now(UTC).strftime('%H:%M:%S UTC')}"
        )
    except Exception as exc:
        st.error(f"Error estimating security score: {exc}")
