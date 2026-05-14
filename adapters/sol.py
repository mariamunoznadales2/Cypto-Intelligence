"""Solana adapter backed by live public RPC data."""
from __future__ import annotations

import streamlit as st

from adapters.base import AssetIdentity, ModuleSpec, TopMetric
from api.solana_client import latest_network_snapshot
from modules.sol_live import (
    render_evolution,
    render_forecast,
    render_mechanism,
    render_state,
)
from modules.sol_advanced import (
    render_m5,
    render_m6,
    render_m7,
)
from modules.m8_risk_radar import render_sol as render_m8


@st.cache_data(ttl=30, show_spinner=False)
def _cached_top_metrics(asset_code: str = "SOL") -> list[TopMetric]:
    snapshot = latest_network_snapshot(asset_code)
    return [
        TopMetric("Slot", f"{snapshot['slot']:,}"),
        TopMetric("TPS", f"{snapshot['avg_tps']:,.0f}"),
        TopMetric("Skip Rate", f"{snapshot['avg_skip_rate'] * 100:,.1f}%"),
        TopMetric("Block Time", f"{snapshot['avg_block_time']:.2f} s"),
    ]


IDENTITY = AssetIdentity(
    code="SOL",
    name="Solana",
    symbol="SOL",
    kicker="SOLANA HIGH-THROUGHPUT NETWORK",
    accent="#FF3B6B",
    accent_soft="#F472B6",
    available=True,
)


class SolAdapter:
    identity = IDENTITY
    state_renderer = staticmethod(render_state)
    mechanism_renderer = staticmethod(render_mechanism)
    evolution_renderer = staticmethod(render_evolution)
    forecast_renderer = staticmethod(render_forecast)
    optional_renderers = [render_m5, render_m6, render_m7, render_m8]

    def top_metrics(self) -> list[TopMetric]:
        try:
            return _cached_top_metrics("SOL")
        except Exception:
            return [
                TopMetric("Slot", "—"),
                TopMetric("TPS", "—"),
                TopMetric("Skip Rate", "—"),
                TopMetric("Block Time", "—"),
            ]

    def state_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Proof of Work Monitor",
            title="Proof of Work Monitor",
            caption="Live Solana slots and TPS.",
        )

    def mechanism_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Block Header Analyzer",
            title="Block Header Analyzer",
            caption="Leader, slot, and confirmation depth.",
        )

    def evolution_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Difficulty History",
            title="Difficulty History",
            caption="Throughput and finalization trend.",
        )

    def forecast_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="AI Component",
            title="AI Component",
            caption="Expected congestion window.",
        )

    def optional_modules(self) -> list[ModuleSpec]:
        return [
            ModuleSpec(
                panel_label="Merkle Proof Verifier",
                title="Merkle Proof Verifier",
                caption="Parent blockhash check.",
            ),
            ModuleSpec(
                panel_label="Security Score",
                title="Security Score",
                caption="Finality stability score.",
            ),
            ModuleSpec(
                panel_label="Second AI approach",
                title="Second AI approach",
                caption="TPS model comparison.",
            ),
            ModuleSpec(
                panel_label="Live Risk Radar",
                title="Live Risk Radar",
                caption="Five-factor network health.",
            ),
        ]

    def warm_cache(self) -> None:
        latest_network_snapshot("SOL")
        _cached_top_metrics("SOL")
