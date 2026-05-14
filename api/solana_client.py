"""Solana API client backed by the public mainnet RPC endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import requests
import streamlit as st


SOL_RPC_URL = "https://api.mainnet-beta.solana.com"


def _rpc(method: str, params: list | None = None) -> object:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }
    response = requests.post(SOL_RPC_URL, json=payload, timeout=12)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(f"Solana RPC error for {method}: {data['error']}")
    return data["result"]


def _format_ts(timestamp: int | None) -> str:
    if timestamp is None:
        return "—"
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


@st.cache_data(ttl=10, show_spinner=False)
def get_slot(commitment: str = "finalized") -> int:
    return int(_rpc("getSlot", [{"commitment": commitment}]))


@st.cache_data(ttl=10, show_spinner=False)
def get_block_height() -> int:
    return int(_rpc("getBlockHeight"))


@st.cache_data(ttl=10, show_spinner=False)
def get_latest_blockhash() -> dict:
    return _rpc("getLatestBlockhash", [{"commitment": "finalized"}])


@st.cache_data(ttl=15, show_spinner=False)
def get_block(slot: int) -> dict:
    return _rpc(
        "getBlock",
        [
            slot,
            {
                "commitment": "finalized",
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "rewards": False,
                "transactionDetails": "signatures",
            },
        ],
    )


@st.cache_data(ttl=20, show_spinner=False)
def get_recent_performance_samples(limit: int = 60) -> list[dict]:
    return _rpc("getRecentPerformanceSamples", [limit])


@st.cache_data(ttl=20, show_spinner=False)
def get_recent_prioritization_fees() -> list[dict]:
    return _rpc("getRecentPrioritizationFees", [])


def compute_tps(sample: dict) -> float:
    period = sample.get("samplePeriodSecs") or 0
    if not period:
        return 0.0
    return sample.get("numTransactions", 0) / period


def compute_skip_rate(sample: dict) -> float:
    period = sample.get("samplePeriodSecs") or 0
    num_slots = sample.get("numSlots") or 0
    if not period or not num_slots:
        return 0.0
    expected_slots = period / 0.4
    if expected_slots <= 0:
        return 0.0
    skipped = max(expected_slots - num_slots, 0)
    return min(skipped / expected_slots, 1.0)


@st.cache_data(ttl=30, show_spinner=False)
def latest_network_snapshot(asset_code: str = "SOL") -> dict:
    finalized_slot = get_slot("finalized")
    confirmed_slot = get_slot("confirmed")
    block_height = get_block_height()
    latest_blockhash = get_latest_blockhash()
    latest_block = get_block(finalized_slot)
    performance = get_recent_performance_samples(60)
    fees = get_recent_prioritization_fees()[:40]

    latest_sample = performance[0] if performance else {}
    avg_tps = (
        sum(compute_tps(sample) for sample in performance[:12]) / min(len(performance[:12]), 12)
        if performance
        else 0.0
    )
    avg_block_time = (
        sum(sample.get("samplePeriodSecs", 0) / max(sample.get("numSlots", 1), 1) for sample in performance[:12])
        / min(len(performance[:12]), 12)
        if performance
        else 0.0
    )
    avg_skip_rate = (
        sum(compute_skip_rate(sample) for sample in performance[:12]) / min(len(performance[:12]), 12)
        if performance
        else 0.0
    )

    return {
        "slot": finalized_slot,
        "confirmed_slot": confirmed_slot,
        "block_height": block_height,
        "blockhash": latest_blockhash["value"]["blockhash"],
        "last_valid_block_height": latest_blockhash["value"]["lastValidBlockHeight"],
        "latest_block": latest_block,
        "performance": performance,
        "priority_fees": fees,
        "avg_tps": avg_tps,
        "latest_tps": compute_tps(latest_sample) if latest_sample else 0.0,
        "avg_block_time": avg_block_time,
        "avg_skip_rate": avg_skip_rate,
        "confirmation_depth": max(confirmed_slot - finalized_slot, 0),
        "timestamp": _format_ts(latest_block.get("blockTime")),
    }
