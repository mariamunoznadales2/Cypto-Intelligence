"""Optional M7 module: second AI forecast method and comparison."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_difficulty_history, get_recent_blocks
from modules.dashboard_theme import GREEN, GREEN_SOFT, apply_plotly_theme, render_kpi
from modules.m4_ai_component import build_dataframe, linear_regression_forecast


def exponential_smoothing_forecast(values: list[float], alpha: float) -> float:
    """Predict the next value with simple exponential smoothing."""
    if not values:
        raise ValueError("No values were provided.")
    smoothed = values[0]
    for value in values[1:]:
        smoothed = alpha * value + (1 - alpha) * smoothed
    return smoothed


def backtest_mae(values: list[float], method: str, alpha: float = 0.35) -> float | None:
    """Backtest one-step forecasts over a rolling window and return MAE."""
    min_train = 8
    errors: list[float] = []
    for end in range(min_train, len(values)):
        train = values[:end]
        actual = values[end]
        if method == "linear":
            predicted, _ = linear_regression_forecast(train)
        else:
            predicted = exponential_smoothing_forecast(train, alpha)
        errors.append(abs(predicted - actual))
    if not errors:
        return None
    return sum(errors) / len(errors)


def build_comparison_chart(df: pd.DataFrame, linear_prediction: float, smoothing_prediction: float) -> go.Figure:
    """Build a chart comparing the two one-step forecasts."""
    if len(df) > 1:
        step = df["Date"].iloc[-1] - df["Date"].iloc[-2]
    else:
        step = timedelta(days=1)
    next_date = df["Date"].iloc[-1] + step

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Difficulty"],
            mode="lines",
            name="Historical",
            line=dict(color=GREEN, width=2.5, shape="spline", smoothing=1.0),
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df["Date"].iloc[-1], next_date],
            y=[df["Difficulty"].iloc[-1], linear_prediction],
            mode="lines+markers",
            name="Linear regression",
            line=dict(color=GREEN_SOFT, width=2, dash="dot"),
            hovertemplate="Linear<br>%{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df["Date"].iloc[-1], next_date],
            y=[df["Difficulty"].iloc[-1], smoothing_prediction],
            mode="lines+markers",
            name="Exponential smoothing",
            line=dict(color="#F7931A", width=2, dash="dash"),
            hovertemplate="Smoothing<br>%{y:,.2f}<extra></extra>",
        )
    )
    apply_plotly_theme(fig, height=380, xaxis_title="", yaxis_title="Difficulty")
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.05, x=0))
    return fig


def render() -> None:
    """Render the M7 panel."""
    st.subheader("Second AI approach")
    st.caption("Compare linear regression with exponential smoothing.")

    try:
        latest_blocks = get_recent_blocks(1)
        current_hash = latest_blocks[0]["id"] if latest_blocks else "unknown"
        state_key = "m7_snapshot"
        alpha = st.slider("Smoothing alpha", 0.05, 0.95, 0.35, 0.05)

        snapshot = st.session_state.get(state_key)
        if snapshot is None or snapshot["hash"] != current_hash or snapshot["alpha"] != alpha:
            df = build_dataframe(get_difficulty_history(180))
            values = df["Difficulty"].tolist()
            linear_prediction, _ = linear_regression_forecast(values)
            smoothing_prediction = exponential_smoothing_forecast(values, alpha)
            linear_mae = backtest_mae(values, "linear", alpha)
            smoothing_mae = backtest_mae(values, "smoothing", alpha)
            latest_value = float(values[-1])
            snapshot = {
                "hash": current_hash,
                "alpha": alpha,
                "df": df,
                "linear_prediction": linear_prediction,
                "smoothing_prediction": smoothing_prediction,
                "linear_mae": linear_mae,
                "smoothing_mae": smoothing_mae,
                "latest_value": latest_value,
                "last_update": datetime.now(UTC).strftime("%H:%M:%S UTC"),
            }
            st.session_state[state_key] = snapshot

        linear_change = (snapshot["linear_prediction"] / snapshot["latest_value"] - 1) * 100
        smoothing_change = (snapshot["smoothing_prediction"] / snapshot["latest_value"] - 1) * 100
        winner = (
            "Exponential smoothing"
            if snapshot["smoothing_mae"] is not None
            and snapshot["linear_mae"] is not None
            and snapshot["smoothing_mae"] < snapshot["linear_mae"]
            else "Linear regression"
        )

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            render_kpi("Linear Forecast", f"{snapshot['linear_prediction']:,.2f}", f"{linear_change:+.2f}%")
        with kpi2:
            render_kpi("Smoothing Forecast", f"{snapshot['smoothing_prediction']:,.2f}", f"{smoothing_change:+.2f}%")
        with kpi3:
            render_kpi("Lower Backtest MAE", winner)

        st.plotly_chart(
            build_comparison_chart(
                snapshot["df"],
                snapshot["linear_prediction"],
                snapshot["smoothing_prediction"],
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )

        comparison_df = pd.DataFrame(
            [
                {
                    "Method": "Linear regression",
                    "Next forecast": snapshot["linear_prediction"],
                    "Change": f"{linear_change:+.2f}%",
                    "Backtest MAE": snapshot["linear_mae"],
                },
                {
                    "Method": "Exponential smoothing",
                    "Next forecast": snapshot["smoothing_prediction"],
                    "Change": f"{smoothing_change:+.2f}%",
                    "Backtest MAE": snapshot["smoothing_mae"],
                },
            ]
        )
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        st.caption(f"Last update: {snapshot['last_update']}")
    except Exception as exc:
        st.error(f"Error comparing AI methods: {exc}")
