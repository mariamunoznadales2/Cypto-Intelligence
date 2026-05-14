"""Advanced Ethereum panels for the multi-asset dashboard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.ethereum_client import compute_next_base_fee, latest_block_snapshot
from modules.dashboard_theme import (
    apply_plotly_theme,
    current_accent,
    current_accent_glow,
    current_accent_soft,
    render_kpi,
)
from modules.eth_live import _build_fee_df


def _snapshot() -> dict:
    state_key = "eth_advanced_snapshot"
    snapshot = st.session_state.get(state_key)
    live = latest_block_snapshot()
    if snapshot is None or snapshot["hash"] != live["hash"]:
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
    """Render an Ethereum protocol-rule verifier."""
    snapshot = _snapshot()
    accent = current_accent()

    st.subheader("Merkle Proof Verifier")
    st.caption("Recompute the EIP-1559 next-base-fee update step by step.")

    recomputed = compute_next_base_fee(
        {
            "baseFeePerGas": hex(snapshot["base_fee_wei"]),
            "gasUsed": hex(snapshot["gas_used"]),
            "gasLimit": hex(snapshot["gas_limit"]),
        }
    )
    verified = recomputed == snapshot["next_base_fee_wei"]
    gas_target = int(snapshot["gas_target"])
    delta = snapshot["gas_used"] - gas_target
    direction = "increase" if delta > 0 else "decrease" if delta < 0 else "hold"

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Gas Target", f"{gas_target:,}")
    with c2:
        render_kpi("Gas Delta", f"{delta:+,}")
    with c3:
        render_kpi("Verified", "YES" if verified else "NO")

    st.write(f"Block: `{snapshot['block_number']:,}`")
    st.write(f"Block hash: `{snapshot['hash']}`")
    st.write(f"Parent hash: `{snapshot['parent_hash']}`")

    steps = [
        ("Base fee", f"{snapshot['base_fee_wei']} wei"),
        ("Gas target", f"gasLimit / 2 = {snapshot['gas_limit']:,} / 2 = {gas_target:,}"),
        ("Gas used delta", f"{snapshot['gas_used']:,} - {gas_target:,} = {delta:+,}"),
        ("Adjustment direction", direction),
        ("Protocol result", f"{recomputed} wei = {recomputed / 1_000_000_000:.4f} gwei"),
    ]
    for label, value in steps:
        st.markdown(
            f"<div style='border-left:2px solid {accent};padding:0.32rem 0.75rem;"
            f"margin:0.42rem 0;color:#D1D5DB;'><b>{label}</b><br><code>{value}</code></div>",
            unsafe_allow_html=True,
        )

    st.caption(f"Last update: {snapshot['last_update']}")


def render_m6() -> None:
    """Render an Ethereum economic security estimator."""
    snapshot = _snapshot()
    accent = current_accent()
    accent_glow = current_accent_glow(0.18)

    st.subheader("Security Score")
    st.caption("Estimate proof-of-stake attack cost under transparent assumptions.")

    eth_price = st.slider("ETH price assumption ($)", 500, 10000, 3000, 100)
    total_staked_m = st.slider("Total ETH staked (millions)", 10.0, 60.0, 34.0, 1.0)
    slashing_pct = st.slider("Effective slashing / loss (%)", 5, 100, 33, 5)

    total_staked = total_staked_m * 1_000_000
    one_third_cost = total_staked / 3 * eth_price
    two_thirds_cost = total_staked * 2 / 3 * eth_price
    expected_loss = one_third_cost * (slashing_pct / 100)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("33% Stake Cost", f"${one_third_cost / 1e9:,.1f}B")
    with c2:
        render_kpi("66% Stake Cost", f"${two_thirds_cost / 1e9:,.1f}B")
    with c3:
        render_kpi("Expected Loss", f"${expected_loss / 1e9:,.1f}B")

    score = max(0, min(100, 100 - snapshot["target_ratio"] * 12 + min(expected_loss / 1e9, 40)))
    render_kpi("Security Score", f"{score:,.0f}/100")

    depths = list(range(1, 13))
    risk = [min(1.0, snapshot["target_ratio"] / (depth * 24)) for depth in depths]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=depths,
            y=risk,
            mode="lines+markers",
            line=dict(color=accent, width=3, shape="spline", smoothing=0.8),
            fill="tozeroy",
            fillcolor=accent_glow,
            hovertemplate="%{x} blocks<br>Residual risk %{y:.3%}<extra></extra>",
        )
    )
    apply_plotly_theme(fig, height=330, xaxis_title="Block confirmations", yaxis_title="Residual risk")
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(tickformat=".2%")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Cost model is assumption-driven; live chain stress uses current gas utilization.")


def render_m7() -> None:
    """Render a second Ethereum fee model comparison."""
    snapshot = _snapshot()
    accent = current_accent()
    accent_soft = current_accent_soft()
    df = _build_fee_df(snapshot)
    values = df["base_fee_gwei"].tolist()

    st.subheader("Second AI approach")
    st.caption("Compare linear fee extrapolation with exponential smoothing.")

    alpha = st.slider("Smoothing alpha", 0.05, 0.95, 0.35, 0.05, key="eth_m7_alpha")
    linear_prediction = _linear_forecast(values)
    smoothing_prediction = _exp_smoothing(values, alpha)
    linear_mae = _mae(values, "linear", alpha)
    smoothing_mae = _mae(values, "smoothing", alpha)
    latest = values[-1]
    next_date = df["Date"].iloc[-1] + timedelta(seconds=snapshot["block_time"] or 12)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Linear Forecast", f"{linear_prediction:,.2f} gwei", f"{linear_prediction / latest - 1:+.2%}")
    with c2:
        render_kpi("Smoothing Forecast", f"{smoothing_prediction:,.2f} gwei", f"{smoothing_prediction / latest - 1:+.2%}")
    with c3:
        winner = "Smoothing" if smoothing_mae is not None and linear_mae is not None and smoothing_mae < linear_mae else "Linear"
        render_kpi("Lower MAE", winner)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["base_fee_gwei"], mode="lines", line=dict(color=accent, width=3), name="Historical"))
    fig.add_trace(go.Scatter(x=[df["Date"].iloc[-1], next_date], y=[latest, linear_prediction], mode="lines+markers", line=dict(color=accent_soft, dash="dot", width=2), name="Linear"))
    fig.add_trace(go.Scatter(x=[df["Date"].iloc[-1], next_date], y=[latest, smoothing_prediction], mode="lines+markers", line=dict(color="#F7931A", dash="dash", width=2), name="Smoothing"))
    apply_plotly_theme(fig, height=360, xaxis_title="", yaxis_title="gwei")
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
