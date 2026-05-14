"""Advanced M8 module: per-asset live risk radar."""

from __future__ import annotations

from datetime import UTC, datetime

import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_blockstream_block, get_latest_block_hash, get_recent_blocks as get_btc_blocks
from api.ethereum_client import latest_block_snapshot
from api.solana_client import latest_network_snapshot
from modules.dashboard_theme import current_accent, current_accent_glow, current_accent_soft, render_kpi
from modules.m1_pow_monitor import compute_block_times, estimate_hash_rate


RADAR_AXES = [
    "Security",
    "Finality",
    "Throughput",
    "Fee Health",
    "Stability",
]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _build_radar(values: dict[str, float], title: str) -> go.Figure:
    accent = current_accent()
    accent_soft = current_accent_soft()
    categories = RADAR_AXES + [RADAR_AXES[0]]
    scores = [values[key] for key in RADAR_AXES] + [values[RADAR_AXES[0]]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=scores,
            theta=categories,
            fill="toself",
            name=title,
            line=dict(color=accent, width=3),
            fillcolor=current_accent_glow(0.24),
            marker=dict(color=accent_soft, size=7),
            hovertemplate="%{theta}<br>%{r:.0f}/100<extra></extra>",
        )
    )
    fig.update_layout(
        height=430,
        margin=dict(l=20, r=20, t=38, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#D1D5DB", size=12),
        showlegend=False,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color="#6B7280", size=10),
                gridcolor="rgba(107, 114, 128, 0.20)",
                linecolor="rgba(107, 114, 128, 0.20)",
            ),
            angularaxis=dict(
                tickfont=dict(color="#D1D5DB", size=12),
                gridcolor="rgba(107, 114, 128, 0.20)",
                linecolor="rgba(107, 114, 128, 0.20)",
            ),
        ),
    )
    return fig


def _render_summary(scores: dict[str, float], note: str, last_update: str) -> None:
    overall = sum(scores.values()) / len(scores)
    weakest = min(scores, key=scores.get)
    strongest = max(scores, key=scores.get)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Health Index", f"{overall:,.0f}/100")
    with c2:
        render_kpi("Strongest", strongest)
    with c3:
        render_kpi("Watch", weakest)

    st.caption(note)
    st.caption(f"Last update: {last_update}")


def render_btc() -> None:
    """Render Bitcoin risk radar."""
    st.subheader("Live Risk Radar")
    st.caption("A 5-factor operational health view for Bitcoin.")

    try:
        latest_hash = get_latest_block_hash()
        latest_block = get_blockstream_block(latest_hash)
        blocks = get_btc_blocks(10)
        times = compute_block_times(blocks)
        avg_time = sum(times) / len(times) if times else 600
        difficulty = float(latest_block["difficulty"])
        hash_rate = estimate_hash_rate(difficulty, avg_time)
        target_deviation = abs(avg_time - 600) / 600

        scores = {
            "Security": _clamp(70 + min(hash_rate / 1e20, 25)),
            "Finality": _clamp(92 - target_deviation * 18),
            "Throughput": _clamp(45 + min(latest_block.get("tx_count", 0) / 90, 30)),
            "Fee Health": _clamp(82 - target_deviation * 35),
            "Stability": _clamp(95 - target_deviation * 45),
        }
        st.plotly_chart(_build_radar(scores, "Bitcoin"), use_container_width=True, config={"displayModeBar": False})
        _render_summary(
            scores,
            "Bitcoin prioritizes security and finality; throughput is intentionally conservative.",
            datetime.now(UTC).strftime("%H:%M:%S UTC"),
        )
    except Exception as exc:
        st.error(f"Error loading Bitcoin risk radar: {exc}")


def render_eth() -> None:
    """Render Ethereum risk radar."""
    st.subheader("Live Risk Radar")
    st.caption("A 5-factor operational health view for Ethereum.")

    try:
        snapshot = latest_block_snapshot("ETH")
        target_ratio = snapshot["target_ratio"]
        block_time = snapshot["block_time"] or 12
        fee_pressure = min(snapshot["base_fee_gwei"] / 80, 1)
        gas_near_target = abs(target_ratio - 1)

        scores = {
            "Security": _clamp(88 - gas_near_target * 6),
            "Finality": _clamp(86 - abs(block_time - 12) * 2),
            "Throughput": _clamp(60 + min(snapshot["gas_ratio"] * 35, 35)),
            "Fee Health": _clamp(92 - fee_pressure * 55),
            "Stability": _clamp(90 - gas_near_target * 22),
        }
        st.plotly_chart(_build_radar(scores, "Ethereum"), use_container_width=True, config={"displayModeBar": False})
        _render_summary(
            scores,
            "Ethereum's radar balances PoS finality, gas utilization, and current base-fee pressure.",
            datetime.now(UTC).strftime("%H:%M:%S UTC"),
        )
    except Exception as exc:
        st.error(f"Error loading Ethereum risk radar: {exc}")


def render_sol() -> None:
    """Render Solana risk radar."""
    st.subheader("Live Risk Radar")
    st.caption("A 5-factor operational health view for Solana.")

    try:
        snapshot = latest_network_snapshot("SOL")
        skip_rate = snapshot["avg_skip_rate"]
        block_time = snapshot["avg_block_time"] or 0.4
        tps = snapshot["avg_tps"]

        scores = {
            "Security": _clamp(82 - skip_rate * 120 - snapshot["confirmation_depth"] * 3),
            "Finality": _clamp(92 - snapshot["confirmation_depth"] * 8 - skip_rate * 70),
            "Throughput": _clamp(45 + min(tps / 80, 45)),
            "Fee Health": _clamp(88 - min(len(snapshot.get("priority_fees", [])) / 2, 18)),
            "Stability": _clamp(95 - skip_rate * 180 - abs(block_time - 0.4) * 50),
        }
        st.plotly_chart(_build_radar(scores, "Solana"), use_container_width=True, config={"displayModeBar": False})
        _render_summary(
            scores,
            "Solana's radar emphasizes throughput, skip-rate stability, and finalized-slot depth.",
            datetime.now(UTC).strftime("%H:%M:%S UTC"),
        )
    except Exception as exc:
        st.error(f"Error loading Solana risk radar: {exc}")
