"""Advanced Solana panels for the multi-asset dashboard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.solana_client import get_block, latest_network_snapshot
from modules.dashboard_theme import (
    apply_plotly_theme,
    current_accent,
    current_accent_glow,
    current_accent_soft,
    render_kpi,
)
from modules.sol_live import _performance_df


def _snapshot() -> dict:
    state_key = "sol_advanced_snapshot"
    snapshot = st.session_state.get(state_key)
    live = latest_network_snapshot()
    if snapshot is None or snapshot["blockhash"] != live["blockhash"]:
        live["last_update"] = datetime.now(UTC).strftime("%H:%M:%S UTC")
        st.session_state[state_key] = live
        return live
    return snapshot


def _linear_forecast(values: list[float]) -> float:
    x_values = list(range(len(values)))
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(values) / len(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    slope = numerator / denominator if denominator else 0.0
    intercept = y_mean - slope * x_mean
    return max(intercept + slope * len(values), 0.0)


def _exp_smoothing(values: list[float], alpha: float) -> float:
    smoothed = values[0]
    for value in values[1:]:
        smoothed = alpha * value + (1 - alpha) * smoothed
    return max(smoothed, 0.0)


def _mae(values: list[float], method: str, alpha: float) -> float | None:
    if len(values) < 8:
        return None
    errors = []
    for end in range(6, len(values)):
        train = values[:end]
        prediction = _linear_forecast(train) if method == "linear" else _exp_smoothing(train, alpha)
        errors.append(abs(prediction - values[end]))
    return sum(errors) / len(errors) if errors else None


def render_m5() -> None:
    """Render a Solana slot-chain verifier."""
    snapshot = _snapshot()
    latest_block = snapshot["latest_block"]
    accent = current_accent()

    st.subheader("Merkle Proof Verifier")
    st.caption("Verify the current finalized slot against its parent blockhash.")

    parent_slot = latest_block.get("parentSlot")
    previous_hash = latest_block.get("previousBlockhash", "—")
    parent_block = get_block(parent_slot) if parent_slot is not None else {}
    parent_hash = parent_block.get("blockhash", "—")
    verified = previous_hash == parent_hash
    skipped_slots = max(snapshot["slot"] - int(parent_slot or snapshot["slot"]) - 1, 0)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Finalized Slot", f"{snapshot['slot']:,}")
    with c2:
        render_kpi("Parent Slot", f"{int(parent_slot or 0):,}")
    with c3:
        render_kpi("Verified", "YES" if verified else "NO")

    st.write(f"Current blockhash: `{latest_block.get('blockhash', '—')}`")
    st.write(f"Previous blockhash declared: `{previous_hash}`")
    st.write(f"Parent slot blockhash: `{parent_hash}`")

    steps = [
        ("Read finalized slot", f"slot = {snapshot['slot']:,}"),
        ("Read parent slot", f"parentSlot = {int(parent_slot or 0):,}"),
        ("Skipped slot gap", f"{skipped_slots} skipped slot(s) between parent and child"),
        ("Compare hashes", f"previousBlockhash == parent.blockhash -> {verified}"),
    ]
    for label, value in steps:
        st.markdown(
            f"<div style='border-left:2px solid {accent};padding:0.32rem 0.75rem;"
            f"margin:0.42rem 0;color:#D1D5DB;'><b>{label}</b><br><code>{value}</code></div>",
            unsafe_allow_html=True,
        )

    st.caption(f"Last update: {snapshot['last_update']}")


def render_m6() -> None:
    """Render a Solana stability/security score."""
    snapshot = _snapshot()
    accent = current_accent()
    accent_glow = current_accent_glow(0.18)

    st.subheader("Security Score")
    st.caption("Score finality health from skip rate, confirmation depth, and slot timing.")

    target_slot_time = st.slider("Target slot time (seconds)", 0.30, 0.80, 0.40, 0.05)
    skip_penalty = min(snapshot["avg_skip_rate"] * 220, 45)
    depth_penalty = min(snapshot["confirmation_depth"] * 5, 25)
    timing_penalty = min(abs(snapshot["avg_block_time"] - target_slot_time) / target_slot_time * 35, 30)
    score = max(0, 100 - skip_penalty - depth_penalty - timing_penalty)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Security Score", f"{score:,.0f}/100")
    with c2:
        render_kpi("Skip Rate", f"{snapshot['avg_skip_rate'] * 100:,.2f}%")
    with c3:
        render_kpi("Depth", snapshot["confirmation_depth"])

    depths = list(range(1, 33))
    residual = [
        min(1.0, (snapshot["avg_skip_rate"] + 0.01) * (0.82 ** depth) + snapshot["confirmation_depth"] / 1000)
        for depth in depths
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=depths,
            y=residual,
            mode="lines+markers",
            line=dict(color=accent, width=3, shape="spline", smoothing=0.8),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x} slots<br>Residual risk %{y:.3%}<extra></extra>",
        )
    )
    apply_plotly_theme(fig, height=330, xaxis_title="Additional finalized slots", yaxis_title="Residual risk")
    fig.update_yaxes(tickformat=".2%")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("The curve is an operational stability proxy based on live RPC performance samples.")


def render_m7() -> None:
    """Render a second Solana TPS model comparison."""
    snapshot = _snapshot()
    accent = current_accent()
    accent_soft = current_accent_soft()
    df = _performance_df(snapshot)
    values = df["TPS"].tolist()

    st.subheader("Second AI approach")
    st.caption("Compare linear TPS extrapolation with exponential smoothing.")

    alpha = st.slider("Smoothing alpha", 0.05, 0.95, 0.35, 0.05, key="sol_m7_alpha")
    linear_prediction = _linear_forecast(values)
    smoothing_prediction = _exp_smoothing(values, alpha)
    linear_mae = _mae(values, "linear", alpha)
    smoothing_mae = _mae(values, "smoothing", alpha)
    latest = values[-1]
    next_time = df["Date"].iloc[-1] + timedelta(seconds=snapshot["avg_block_time"] or 0.4)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Linear Forecast", f"{linear_prediction:,.0f} TPS", f"{linear_prediction / latest - 1:+.2%}" if latest else "")
    with c2:
        render_kpi("Smoothing Forecast", f"{smoothing_prediction:,.0f} TPS", f"{smoothing_prediction / latest - 1:+.2%}" if latest else "")
    with c3:
        winner = "Smoothing" if smoothing_mae is not None and linear_mae is not None and smoothing_mae < linear_mae else "Linear"
        render_kpi("Lower MAE", winner)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["TPS"], mode="lines", line=dict(color=accent, width=3), name="Historical"))
    fig.add_trace(go.Scatter(x=[df["Date"].iloc[-1], next_time], y=[latest, linear_prediction], mode="lines+markers", line=dict(color=accent_soft, dash="dot", width=2), name="Linear"))
    fig.add_trace(go.Scatter(x=[df["Date"].iloc[-1], next_time], y=[latest, smoothing_prediction], mode="lines+markers", line=dict(color="#22C55E", dash="dash", width=2), name="Smoothing"))
    apply_plotly_theme(fig, height=360, xaxis_title="", yaxis_title="TPS")
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.05, x=0))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.dataframe(
        pd.DataFrame(
            [
                {"Method": "Linear", "Forecast": linear_prediction, "Backtest MAE": linear_mae},
                {"Method": "Exponential smoothing", "Forecast": smoothing_prediction, "Backtest MAE": smoothing_mae},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
