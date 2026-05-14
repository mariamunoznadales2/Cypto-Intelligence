"""Bitcoin adapter — delegates to the existing live data layer."""
from __future__ import annotations

from datetime import UTC, datetime

from adapters.base import AssetIdentity, ModuleSpec, TopMetric
from api.blockchain_client import (
    get_blockstream_block,
    get_difficulty_history,
    get_block_header_hex,
    get_latest_block_hash,
    get_recent_blocks,
)
import streamlit as st
from modules.m1_pow_monitor import render as render_m1
from modules.m2_block_header import render as render_m2
from modules.m3_difficulty_history import render as render_m3
from modules.m4_ai_component import render as render_m4
from modules.m5_merkle_proof import render as render_m5
from modules.m6_security_score import render as render_m6
from modules.m7_second_ai import render as render_m7
from modules.m8_risk_radar import render_btc as render_m8


IDENTITY = AssetIdentity(
    code="BTC",
    name="Bitcoin",
    symbol="BTC",
    kicker="BITCOIN MARKET INFRASTRUCTURE",
    accent="#22C55E",
    accent_soft="#F7931A",
    available=True,
)


def _format_hash_rate(value: float | None) -> str:
    if value is None:
        return "—"
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s", "ZH/s"]
    i = 0
    while value >= 1000 and i < len(units) - 1:
        value /= 1000
        i += 1
    return f"{value:,.2f} {units[i]}"


def _block_times(blocks: list[dict]) -> list[int]:
    return [
        blocks[i - 1].get("mediantime", blocks[i - 1]["timestamp"])
        - blocks[i].get("mediantime", blocks[i]["timestamp"])
        for i in range(1, len(blocks))
    ]


@st.cache_data(ttl=30, show_spinner=False)
def _cached_top_metrics(asset_code: str = "BTC") -> list[TopMetric]:
    latest_hash = get_latest_block_hash()
    latest_block = get_blockstream_block(latest_hash)
    recent = get_recent_blocks(10)
    times = _block_times(recent)
    avg = sum(times) / len(times) if times else None
    difficulty = float(latest_block["difficulty"])
    hash_rate = difficulty * (2**32) / avg if avg and avg > 0 else None
    return [
        TopMetric("Block Height", f"{latest_block['height']:,}"),
        TopMetric("Difficulty", f"{difficulty:,.2f}"),
        TopMetric("Hash Rate", _format_hash_rate(hash_rate)),
        TopMetric("Block Time", f"{avg:,.0f} s" if avg else "—"),
    ]


class BtcAdapter:
    identity = IDENTITY
    state_renderer = staticmethod(render_m1)
    mechanism_renderer = staticmethod(render_m2)
    evolution_renderer = staticmethod(render_m3)
    forecast_renderer = staticmethod(render_m4)
    optional_renderers = [render_m5, render_m6, render_m7, render_m8]

    def top_metrics(self) -> list[TopMetric]:
        try:
            return _cached_top_metrics("BTC")
        except Exception:
            return [
                TopMetric("Block Height", "—"),
                TopMetric("Difficulty", "—"),
                TopMetric("Hash Rate", "—"),
                TopMetric("Block Time", "—"),
            ]

    def state_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Proof of Work Monitor",
            title="Proof of Work Monitor",
            caption="Live mining activity.",
        )

    def mechanism_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Block Header Analyzer",
            title="Block Header Analyzer",
            caption="80-byte header decoded.",
        )

    def evolution_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="Difficulty History",
            title="Difficulty History",
            caption="Adjustments over time.",
        )

    def forecast_module(self) -> ModuleSpec:
        return ModuleSpec(
            panel_label="AI Component",
            title="AI Component",
            caption="Next difficulty move.",
        )

    def optional_modules(self) -> list[ModuleSpec]:
        return [
            ModuleSpec(
                panel_label="Merkle Proof Verifier",
                title="Merkle Proof Verifier",
                caption="Transaction inclusion proof.",
            ),
            ModuleSpec(
                panel_label="Security Score",
                title="Security Score",
                caption="51% attack economics.",
            ),
            ModuleSpec(
                panel_label="Second AI approach",
                title="Second AI approach",
                caption="Model comparison.",
            ),
            ModuleSpec(
                panel_label="Live Risk Radar",
                title="Live Risk Radar",
                caption="Five-factor network health.",
            ),
        ]

    def last_update(self) -> str:
        return datetime.now(UTC).strftime("%H:%M:%S UTC")

    def warm_cache(self) -> None:
        latest_hash = get_latest_block_hash()
        get_blockstream_block(latest_hash)
        get_recent_blocks(10)
        get_difficulty_history(180)
        get_block_header_hex(latest_hash)
        _cached_top_metrics("BTC")
