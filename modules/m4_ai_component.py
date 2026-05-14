"""Streamlit module for the AI prediction component."""
from datetime import UTC, datetime, timedelta
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_difficulty_history, get_recent_blocks
from modules.dashboard_theme import GREEN, GREEN_GLOW, GREEN_SOFT, apply_plotly_theme, render_kpi


def build_dataframe(values: list[dict]) -> pd.DataFrame:
    """Convert raw API values into a clean dataframe."""
    if not values:
        raise ValueError("No difficulty history data was returned by the API.")

    df = pd.DataFrame(values)
    if not {"x", "y"}.issubset(df.columns):
        raise ValueError("Difficulty history response is missing expected columns.")

    df = df.rename(columns={"x": "Date", "y": "Difficulty"})
    df["Date"] = pd.to_datetime(df["Date"], unit="s", utc=True)
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def linear_regression_forecast(values: list[float]) -> tuple[float, float]:
    """Predict the next value with a simple linear regression."""
    x_values = list(range(len(values)))
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(values) / len(values)

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    slope = numerator / denominator if denominator else 0.0
    intercept = y_mean - slope * x_mean
    prediction = intercept + slope * len(values)
    return prediction, slope


def add_prediction_row(df: pd.DataFrame, prediction: float) -> pd.DataFrame:
    """Append the next predicted point to the dataframe."""
    if len(df) > 1:
        step = df["Date"].iloc[-1] - df["Date"].iloc[-2]
    else:
        step = timedelta(days=1)

    next_date = df["Date"].iloc[-1] + step
    prediction_row = pd.DataFrame(
        [{"Date": next_date, "Difficulty": prediction, "Series": "Prediction"}]
    )

    history_df = df.copy()
    history_df["Series"] = "Historical"
    return pd.concat([history_df, prediction_row], ignore_index=True)


def backtest_prediction(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """Compare a one-step forecast against the latest real value."""
    if len(df) < 3:
        return None, None

    train_values = df["Difficulty"].iloc[:-1].tolist()
    predicted_value, _ = linear_regression_forecast(train_values)
    actual_value = float(df["Difficulty"].iloc[-1])
    return predicted_value, actual_value


def build_forecast_chart(
    chart_df: pd.DataFrame,
    include_forecast: bool,
    confidence_pct: float = 0.0,
) -> go.Figure:
    """Render the forecast chart in progressive stages."""
    history_df = chart_df[chart_df["Series"] == "Historical"]
    forecast_df = chart_df[chart_df["Series"] == "Prediction"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history_df["Date"],
            y=history_df["Difficulty"],
            mode="lines",
            name="Historical",
            legendgroup="historical",
            line=dict(color=GREEN, width=2.5, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor=GREEN_GLOW,
            hovertemplate="<b>Historical</b><br>%{x|%d %b %Y}<br>Difficulty %{y:,.2f}<extra></extra>",
        )
    )

    if include_forecast and len(forecast_df) > 0:
        bridge_x = pd.concat([history_df["Date"].tail(1), forecast_df["Date"]])
        bridge_y = pd.concat([history_df["Difficulty"].tail(1), forecast_df["Difficulty"]])

        band = max(abs(confidence_pct), 0.4) / 100.0
        upper = bridge_y * (1 + band)
        lower = bridge_y * (1 - band)

        fig.add_trace(
            go.Scatter(
                x=pd.concat([bridge_x, bridge_x[::-1]]),
                y=pd.concat([upper, lower[::-1]]),
                fill="toself",
                fillcolor="rgba(134, 239, 172, 0.14)",
                line=dict(color="rgba(0,0,0,0)"),
                hoverinfo="skip",
                name="Confidence band",
                legendgroup="confidence",
                showlegend=True,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=bridge_x,
                y=bridge_y,
                mode="lines+markers",
                name="Forecast",
                legendgroup="forecast",
                line=dict(color=GREEN_SOFT, width=2, dash="dot", shape="spline"),
                marker=dict(color=GREEN_SOFT, size=7, line=dict(color=GREEN, width=0.5)),
                hovertemplate="<b>Forecast</b><br>%{x|%d %b %Y}<br>Difficulty %{y:,.2f}<extra></extra>",
            )
        )

        forecast_point = forecast_df.iloc[-1]
        fig.add_annotation(
            x=forecast_point["Date"],
            y=forecast_point["Difficulty"],
            text="next adjustment",
            showarrow=True,
            arrowhead=0,
            arrowcolor=GREEN_SOFT,
            arrowwidth=1,
            ax=-40,
            ay=-30,
            font=dict(color="#D1D5DB", size=10),
            bgcolor="rgba(11,15,12,0.85)",
            bordercolor="rgba(34,197,94,0.4)",
            borderwidth=1,
            borderpad=4,
        )

    if len(history_df) > 5:
        peak_idx = history_df["Difficulty"].idxmax()
        peak_row = history_df.loc[peak_idx]
        fig.add_annotation(
            x=peak_row["Date"],
            y=peak_row["Difficulty"],
            text="peak",
            showarrow=True,
            arrowhead=0,
            arrowcolor="rgba(107,114,128,0.6)",
            arrowwidth=1,
            ax=0,
            ay=-22,
            font=dict(color="#9CA3AF", size=10),
            bgcolor="rgba(0,0,0,0)",
        )

    apply_plotly_theme(fig, height=460, xaxis_title="", yaxis_title="")
    fig.update_layout(
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(11,15,12,0.96)",
            bordercolor="rgba(34,197,94,0.4)",
            font=dict(color="#F3F4F6", size=12, family="ui-monospace, monospace"),
            namelength=-1,
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#9CA3AF", size=11),
            bgcolor="rgba(0,0,0,0)",
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        dragmode="pan",
    )
    fig.update_xaxes(
        showspikes=True,
        spikecolor="rgba(134,239,172,0.55)",
        spikethickness=1,
        spikedash="dot",
        spikemode="across",
        spikesnap="cursor",
        rangeslider=dict(visible=False),
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(step="all", label="ALL"),
            ],
            bgcolor="rgba(17,24,21,0.85)",
            activecolor="rgba(34,197,94,0.35)",
            bordercolor="rgba(107,114,128,0.25)",
            borderwidth=1,
            font=dict(color="#D1D5DB", size=11),
            x=0,
            y=1.08,
        ),
    )
    fig.update_yaxes(showspikes=False)
    return fig


def render_forecast_kpis(snapshot: dict) -> None:
    """Render the three core forecast KPIs."""
    col1, col2, col3 = st.columns(3)
    with col1:
        render_kpi("Expected Difficulty", f"{snapshot['prediction']:,.2f}", f"{snapshot['change_pct']:+.2f}%")
    with col2:
        render_kpi("Trend", snapshot["trend"])
    with col3:
        render_kpi("Confidence", snapshot["confidence"])


def build_insight(snapshot: dict) -> str:
    """Build a one-line analyst note describing the forecast."""
    change_pct = snapshot["change_pct"]
    trend = snapshot["trend"]
    if abs(change_pct) < 0.15:
        return "Network difficulty stable — block production matches the current target."
    if trend == "Increasing":
        return "Slight upward adjustment expected as block production accelerates."
    if trend == "Decreasing":
        return "Slight downward adjustment expected due to slower block production."
    return "Difficulty holding flat across the recent epoch."


PROCESS_STEPS = [
    "Loading historical data",
    "Normalizing block times",
    "Estimating difficulty trend",
    "Computing next adjustment",
]


def render_process(placeholder, active_index: int) -> None:
    """Render the live pipeline of model steps."""
    lines = []
    for idx, label in enumerate(PROCESS_STEPS):
        if idx < active_index:
            lines.append(
                f"<div style='color:{GREEN};font-size:12px;letter-spacing:.02em;"
                f"margin:2px 0;'>✓ {label}</div>"
            )
        elif idx == active_index:
            lines.append(
                f"<div style='color:#E5E7EB;font-size:12px;letter-spacing:.02em;"
                f"margin:2px 0;'>▸ {label}<span style='color:{GREEN};"
                f"animation:pulse 1s infinite;'> …</span></div>"
            )
        else:
            lines.append(
                f"<div style='color:#4B5563;font-size:12px;letter-spacing:.02em;"
                f"margin:2px 0;'>· {label}</div>"
            )
    placeholder.markdown("".join(lines), unsafe_allow_html=True)


def render() -> None:
    """Render the M4 panel."""
    latest_blocks = get_recent_blocks(1)
    current_hash = latest_blocks[0]["id"] if latest_blocks else "unknown"
    state_key = "m4_snapshot"

    snapshot = st.session_state.get(state_key)
    if snapshot is None or snapshot["hash"] != current_hash:
        df = build_dataframe(get_difficulty_history(180))
        prediction, slope = linear_regression_forecast(df["Difficulty"].tolist())
        latest_value = df["Difficulty"].iloc[-1]
        change = prediction - latest_value
        change_pct = (change / latest_value * 100) if latest_value else 0.0
        backtest_predicted, backtest_actual = backtest_prediction(df)
        chart_df = add_prediction_row(df, prediction)
        if abs(change_pct) < 0.25:
            confidence = "High"
        elif abs(change_pct) < 1:
            confidence = "Medium"
        else:
            confidence = "Low"

        trend = "Increasing" if slope > 0 else "Decreasing" if slope < 0 else "Flat"
        snapshot = {
            "hash": current_hash,
            "df": df,
            "prediction": prediction,
            "slope": slope,
            "latest_value": latest_value,
            "change_pct": change_pct,
            "backtest_predicted": backtest_predicted,
            "backtest_actual": backtest_actual,
            "chart_df": chart_df,
            "confidence": confidence,
            "trend": trend,
            "last_update": datetime.now(UTC).strftime("%H:%M:%S UTC"),
        }
        st.session_state[state_key] = snapshot

    st.subheader("AI Component")
    st.caption("Live difficulty forecast model.")

    try:
        chart_df = snapshot["chart_df"]
        confidence_pct = abs(snapshot["change_pct"]) + 0.4
        animation_key = "m4_animated_hash"
        should_animate = st.session_state.get(animation_key) != current_hash

        process_placeholder = st.empty()
        chart_placeholder = st.empty()
        metrics_placeholder = st.empty()
        insight_placeholder = st.empty()

        chart_config = {
            "displayModeBar": True,
            "displaylogo": False,
            "responsive": True,
            "scrollZoom": True,
            "modeBarButtonsToRemove": [
                "toImage", "select2d", "lasso2d", "autoScale2d",
                "hoverCompareCartesian", "hoverClosestCartesian",
                "toggleSpikelines",
            ],
            "modeBarButtonsToAdd": [],
        }

        def render_chart(include_forecast: bool) -> None:
            with chart_placeholder.container():
                st.plotly_chart(
                    build_forecast_chart(chart_df, include_forecast, confidence_pct),
                    use_container_width=True,
                    config=chart_config,
                )

        def render_insight() -> None:
            insight_placeholder.markdown(
                f"<div style='border-left:2px solid {GREEN};padding:6px 12px;"
                f"margin-top:14px;color:#D1D5DB;font-size:13px;font-style:italic;"
                f"background:rgba(34,197,94,0.04);'>{build_insight(snapshot)}</div>",
                unsafe_allow_html=True,
            )

        if should_animate:
            render_process(process_placeholder, 0)
            time.sleep(0.5)

            render_process(process_placeholder, 1)
            render_chart(include_forecast=False)
            time.sleep(0.55)

            render_process(process_placeholder, 2)
            time.sleep(0.5)

            render_process(process_placeholder, 3)
            render_chart(include_forecast=True)
            time.sleep(0.55)

            render_process(process_placeholder, len(PROCESS_STEPS))
            with metrics_placeholder.container():
                render_forecast_kpis(snapshot)
            time.sleep(0.3)
            render_insight()

            st.session_state[animation_key] = current_hash
        else:
            render_process(process_placeholder, len(PROCESS_STEPS))
            render_chart(include_forecast=True)
            with metrics_placeholder.container():
                render_forecast_kpis(snapshot)
            render_insight()
    except Exception as exc:
        st.error(f"Error loading forecast: {exc}")
