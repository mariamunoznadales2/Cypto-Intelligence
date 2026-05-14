"""Ethereum adapter backed by live public RPC data."""
from __future__ import annotations

import streamlit as st

from adapters.base import AssetIdentity, ModuleSpec, TopMetric
from api.ethereum_client import latest_block_snapshot
from modules.eth_live import (
    render_evolution,
    render_forecast,
    render_mechanism,
    render_state,
)
from modules.eth_advanced import (
    render_m5,
    render_m6,
    render_m7,
)
from modules.m8_risk_radar import render_eth as render_m8


@st.cache_data(ttl=30, show_spinner=False)
def _cached_top_metrics(asset_code: str = "ETH") -> list[TopMetric]:
    snapshot = latest_block_snapshot(asset_code)
    return [
        TopMetric("Block Height", f"{snapshot['block_number']:,}"),
        TopMetric("Base Fee", f"{snapshot['base_fee_gwei']:,.2f} gwei"),
        TopMetric("Gas Used", f"{snapshot['gas_ratio'] * 100:,.1f}%"),
        TopMetric("Block Time", f"{snapshot['block_time']:.1f} s" if snapshot["block_time"] else "—"),
    ]


IDENTITY = AssetIdentity(
    code="ETH",
    name="Ethereum",
    symbol="ETH",
    kicker="ETHEREUM SMART CONTRACT LAYER",
    accent="#627EEA",
    accent_soft="#B794F4",
    available=True,
)


class EthAdapter:
    identity = IDENTITY
    state_renderer = staticmethod(render_state)
    mechanism_renderer = staticmethod(render_mechanism)
    evolution_renderer = staticmethod(render_evolution)
    forecast_renderer = staticmethod(render_forecast)
    optional_renderers = [render_m5, render_m6, render_m7, render_m8]

    def top_metrics(self) -> list[TopMetric]:
        try:
            return _cached_top_metrics("ETH")
        except Exception:
            return [
                TopMetric("Block Height", "—"),
                TopMetric("Base Fee", "—"),
                TopMetric("Gas Used", "—"),
                TopMetric("Block Time", "—"),
            ]

    def state_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Proof of Work Monitor",
            title="Proof of Work Monitor",
            caption="Live Ethereum block demand.",
        )

    def mechanism_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Block Header Analyzer",
            title="Block Header Analyzer",
            caption="Slot, gas and base fee breakdown.",
        )

    def evolution_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Difficulty History",
            title="Difficulty History",
            caption="EIP-1559 fee evolution.",
        )

    def forecast_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="AI Component",
            title="AI Component",
            caption="Next-block fee expectation.",
        )

    def optional_modules(self) -> list[ModuleSpec]:
        return [
            ModuleSpec(
                panel_label="Merkle Proof Verifier",
                title="Merkle Proof Verifier",
                caption="EIP-1559 fee rule check.",
            ),
            ModuleSpec(
                panel_label="Security Score",
                title="Security Score",
                caption="PoS economic security estimate.",
            ),
            ModuleSpec(
                panel_label="Second AI approach",
                title="Second AI approach",
                caption="Fee model comparison.",
            ),
            ModuleSpec(
                panel_label="Live Risk Radar",
                title="Live Risk Radar",
                caption="Five-factor network health.",
            ),
        ]

    def warm_cache(self) -> None:
        latest_block_snapshot("ETH")
        _cached_top_metrics("ETH")
