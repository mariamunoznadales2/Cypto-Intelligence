"""Ethereum API client backed by public JSON-RPC endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import requests
import streamlit as st


ETH_RPC_URL = "https://ethereum-rpc.publicnode.com"


def _rpc(method: str, params: list | None = None) -> dict | list | str:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": 1,
    }
    response = requests.post(ETH_RPC_URL, json=payload, timeout=12)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Ethereum RPC error for {method}: {data['error']}")
    return data["result"]


def _hex_to_int(value: str | None) -> int:
    if not value:
        return 0
    return int(value, 16)


def _to_gwei(wei: int) -> float:
    return wei / 1_000_000_000


def _format_ts(timestamp_hex: str) -> str:
    return datetime.fromtimestamp(_hex_to_int(timestamp_hex), UTC).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


@st.cache_data(ttl=10, show_spinner=False)
def get_block_number() -> int:
    return _hex_to_int(_rpc("eth_blockNumber"))


@st.cache_data(ttl=10, show_spinner=False)
def get_latest_block(full_transactions: bool = False) -> dict:
    return _rpc("eth_getBlockByNumber", ["latest", full_transactions])


@st.cache_data(ttl=15, show_spinner=False)
def get_block_by_number(block_number: int, full_transactions: bool = False) -> dict:
    return _rpc(
        "eth_getBlockByNumber",
        [hex(block_number), full_transactions],
    )


@st.cache_data(ttl=15, show_spinner=False)
def get_recent_blocks(n_blocks: int = 10) -> list[dict]:
    latest = get_block_number()
    start = max(latest - n_blocks + 1, 0)
    return [
        get_block_by_number(block_number)
        for block_number in range(latest, start - 1, -1)
    ]


@st.cache_data(ttl=20, show_spinner=False)
def get_fee_history(block_count: int = 40) -> dict:
    return _rpc(
        "eth_feeHistory",
        [hex(block_count), "latest", []],
    )


@st.cache_data(ttl=20, show_spinner=False)
def get_gas_price() -> int:
    return _hex_to_int(_rpc("eth_gasPrice"))


def compute_block_time(blocks: list[dict]) -> float | None:
    if len(blocks) < 2:
        return None
    timestamps = [_hex_to_int(block["timestamp"]) for block in blocks]
    intervals = [
        timestamps[index] - timestamps[index + 1]
        for index in range(len(timestamps) - 1)
        if timestamps[index] >= timestamps[index + 1]
    ]
    if not intervals:
        return None
    return sum(intervals) / len(intervals)


def compute_next_base_fee(block: dict) -> int:
    """Estimate the next Ethereum base fee using the EIP-1559 update rule."""
    base_fee = _hex_to_int(block.get("baseFeePerGas"))
    gas_used = _hex_to_int(block.get("gasUsed"))
    gas_limit = _hex_to_int(block.get("gasLimit"))
    if not base_fee or not gas_limit:
        return 0

    gas_target = gas_limit // 2
    if gas_target == 0:
        return base_fee

    if gas_used == gas_target:
        return base_fee

    if gas_used > gas_target:
        delta = gas_used - gas_target
        fee_delta = max(base_fee * delta // gas_target // 8, 1)
        return base_fee + fee_delta

    delta = gas_target - gas_used
    fee_delta = base_fee * delta // gas_target // 8
    return max(base_fee - fee_delta, 0)


def build_fee_history_points(block_count: int = 40) -> list[dict]:
    history = get_fee_history(block_count)
    oldest_block = _hex_to_int(history["oldestBlock"])
    base_fees = history.get("baseFeePerGas", [])
    ratios = history.get("gasUsedRatio", [])

    points: list[dict] = []
    latest = get_block_number()
    for index, base_fee in enumerate(base_fees[:-1]):
        number = oldest_block + index
        remaining = latest - number
        timestamp = datetime.now(UTC).timestamp() - max(remaining, 0) * 12
        points.append(
            {
                "block": number,
                "timestamp": int(timestamp),
                "base_fee_gwei": _to_gwei(_hex_to_int(base_fee)),
                "gas_used_ratio": float(ratios[index]) if index < len(ratios) else 0.0,
            }
        )
    return points


@st.cache_data(ttl=30, show_spinner=False)
def latest_block_snapshot(asset_code: str = "ETH") -> dict:
    latest = get_latest_block(full_transactions=False)
    recent = get_recent_blocks(10)
    fee_history = build_fee_history_points(40)
    base_fee = _hex_to_int(latest.get("baseFeePerGas"))
    next_base_fee = compute_next_base_fee(latest)
    gas_used = _hex_to_int(latest.get("gasUsed"))
    gas_limit = _hex_to_int(latest.get("gasLimit"))
    gas_target = gas_limit / 2 if gas_limit else 0
    gas_ratio = gas_used / gas_limit if gas_limit else 0
    target_ratio = gas_used / gas_target if gas_target else 0

    return {
        "block_number": _hex_to_int(latest.get("number")),
        "hash": latest.get("hash", "—"),
        "parent_hash": latest.get("parentHash", "—"),
        "timestamp": _format_ts(latest.get("timestamp", "0x0")),
        "transactions": len(latest.get("transactions", [])),
        "gas_used": gas_used,
        "gas_limit": gas_limit,
        "gas_target": gas_target,
        "gas_ratio": gas_ratio,
        "target_ratio": target_ratio,
        "base_fee_wei": base_fee,
        "base_fee_gwei": _to_gwei(base_fee),
        "next_base_fee_wei": next_base_fee,
        "next_base_fee_gwei": _to_gwei(next_base_fee),
        "block_time": compute_block_time(recent),
        "fee_history": fee_history,
        "gas_price_gwei": _to_gwei(get_gas_price()),
    }
