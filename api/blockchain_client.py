"""
Blockchain API client.

Provides helper functions to fetch blockchain data from public APIs.
"""

from __future__ import annotations

import requests
import streamlit as st

BLOCKCHAIN_INFO_URL = "https://blockchain.info"
BLOCKCHAIN_CHARTS_URL = "https://api.blockchain.info"
BLOCKSTREAM_URL = "https://blockstream.info/api"


_LAST_GOOD: dict[str, object] = {}


def _remember(key: str, value: object) -> object:
    _LAST_GOOD[key] = value
    return value


def _cached_fallback(key: str) -> object:
    if key in _LAST_GOOD:
        return _LAST_GOOD[key]
    raise RuntimeError(f"No cached fallback available for {key}.")


def _request_json(url: str, *, timeout: int = 10, params: dict | None = None) -> dict | list:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _request_text(url: str, *, timeout: int = 10) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text.strip()


def _is_rate_limited(exc: Exception) -> bool:
    if not isinstance(exc, requests.HTTPError):
        return False
    response = exc.response
    return response is not None and response.status_code == 429


def _bits_to_target(bits: int) -> int:
    exponent = bits >> 24
    coefficient = bits & 0xFFFFFF
    return coefficient * (1 << (8 * (exponent - 3)))


def _difficulty_from_bits(bits: int) -> float:
    if bits <= 0:
        return 0.0
    max_target = 0xFFFF * (1 << (8 * (0x1D - 3)))
    target = _bits_to_target(bits)
    if target <= 0:
        return 0.0
    return max_target / target


def _to_blockstream_shape(block: dict) -> dict:
    """Normalize a blockchain.info raw block into the Blockstream-like shape we use."""
    transactions = block.get("tx", [])
    bits = int(block.get("bits", 0))
    difficulty = float(block.get("difficulty") or 0)
    if difficulty <= 0 and bits > 0:
        difficulty = _difficulty_from_bits(bits)
    return {
        "id": block.get("hash", "—"),
        "height": block.get("height", 0),
        "timestamp": block.get("time", 0),
        "difficulty": difficulty,
        "tx_count": len(transactions),
        "nonce": block.get("nonce", 0),
        "bits": bits,
        "mediantime": block.get("time", 0),
    }


def _recent_blocks_from_blockchain_info(n_blocks: int) -> list[dict]:
    """Build a recent-block list by walking backwards from the latest raw block."""
    latest = get_latest_block()
    current_hash = latest.get("hash")
    if not current_hash:
        raise RuntimeError("Latest block hash is unavailable from blockchain.info.")

    blocks: list[dict] = []
    while current_hash and len(blocks) < n_blocks:
        raw_block = get_block(current_hash)
        blocks.append(_to_blockstream_shape(raw_block))
        current_hash = raw_block.get("prev_block")
    return blocks


def _int_to_little_endian_hex(value: int, byte_length: int, *, signed: bool = False) -> str:
    return value.to_bytes(byte_length, byteorder="little", signed=signed).hex()


def _reverse_hex(hex_value: str) -> str:
    return bytes.fromhex(hex_value)[::-1].hex()


def _build_header_hex_from_block(block: dict) -> str:
    """Reconstruct the 80-byte Bitcoin block header from raw block fields."""
    version = _int_to_little_endian_hex(int(block.get("ver", 0)), 4, signed=True)
    previous_block = _reverse_hex(block.get("prev_block", "00" * 32))
    merkle_root = _reverse_hex(block.get("mrkl_root", "00" * 32))
    timestamp = _int_to_little_endian_hex(int(block.get("time", 0)), 4)
    bits = _int_to_little_endian_hex(int(block.get("bits", 0)), 4)
    nonce = _int_to_little_endian_hex(int(block.get("nonce", 0)), 4)
    return f"{version}{previous_block}{merkle_root}{timestamp}{bits}{nonce}"


@st.cache_data(ttl=30, show_spinner=False)
def get_latest_block() -> dict:
    """Return the latest block summary."""
    data = _request_json(f"{BLOCKCHAIN_INFO_URL}/latestblock")
    return _remember("latest_block", data)


@st.cache_data(ttl=300, show_spinner=False)
def get_block(block_hash: str) -> dict:
    """Return full details for a block identified by *block_hash*."""
    cache_key = f"rawblock:{block_hash}"
    try:
        data = _request_json(f"{BLOCKCHAIN_INFO_URL}/rawblock/{block_hash}")
        return _remember(cache_key, data)
    except Exception:
        return _cached_fallback(cache_key)


@st.cache_data(ttl=30, show_spinner=False)
def get_latest_block_hash() -> str:
    """Return the hash of the latest block with a resilient fallback strategy."""
    try:
        block_hash = get_latest_block().get("hash")
        if block_hash:
            return _remember("latest_block_hash", block_hash)
        block_hash = _request_text(f"{BLOCKSTREAM_URL}/blocks/tip/hash")
        return _remember("latest_block_hash", block_hash)
    except Exception as exc:
        if _is_rate_limited(exc):
            latest = get_latest_block()
            fallback_hash = latest.get("hash")
            if fallback_hash:
                return _remember("latest_block_hash", fallback_hash)
            return _cached_fallback("latest_block_hash")
        return _cached_fallback("latest_block_hash")


@st.cache_data(ttl=30, show_spinner=False)
def get_blockstream_block(block_hash: str) -> dict:
    """Return block metadata in the Blockstream-like shape used by the UI."""
    cache_key = f"blockstream_block:{block_hash}"
    try:
        fallback = _to_blockstream_shape(get_block(block_hash))
        return _remember(cache_key, fallback)
    except Exception as exc:
        if _is_rate_limited(exc):
            fallback = _to_blockstream_shape(get_block(block_hash))
            return _remember(cache_key, fallback)
        try:
            data = _request_json(f"{BLOCKSTREAM_URL}/block/{block_hash}")
            return _remember(cache_key, data)
        except Exception:
            return _cached_fallback(cache_key)


@st.cache_data(ttl=300, show_spinner=False)
def get_block_transaction_ids(block_hash: str) -> list[str]:
    """Return transaction ids for a block in their displayed big-endian form."""
    cache_key = f"block_txids:{block_hash}"
    try:
        data = _request_json(f"{BLOCKSTREAM_URL}/block/{block_hash}/txids", timeout=15)
        return _remember(cache_key, data)
    except Exception:
        try:
            raw_block = get_block(block_hash)
            txids = [tx.get("hash") for tx in raw_block.get("tx", []) if tx.get("hash")]
            return _remember(cache_key, txids)
        except Exception:
            return _cached_fallback(cache_key)


@st.cache_data(ttl=300, show_spinner=False)
def get_block_merkle_root(block_hash: str) -> str:
    """Return the block Merkle root in displayed big-endian form."""
    cache_key = f"block_merkle_root:{block_hash}"
    try:
        raw_block = get_block(block_hash)
        merkle_root = raw_block.get("mrkl_root")
        if merkle_root:
            return _remember(cache_key, merkle_root)
    except Exception:
        pass

    try:
        block = _request_json(f"{BLOCKSTREAM_URL}/block/{block_hash}")
        merkle_root = block.get("merkle_root")
        if merkle_root:
            return _remember(cache_key, merkle_root)
        return _cached_fallback(cache_key)
    except Exception:
        return _cached_fallback(cache_key)


@st.cache_data(ttl=60, show_spinner=False)
def get_block_header_hex(block_hash: str) -> str:
    """Return the raw 80-byte block header for a specific block as hex."""
    cache_key = f"block_header_hex:{block_hash}"
    try:
        data = _request_text(f"{BLOCKSTREAM_URL}/block/{block_hash}/header")
        return _remember(cache_key, data)
    except Exception:
        try:
            fallback = _build_header_hex_from_block(get_block(block_hash))
            return _remember(cache_key, fallback)
        except Exception:
            return _cached_fallback(cache_key)


@st.cache_data(ttl=30, show_spinner=False)
def get_recent_blocks(n_blocks: int = 10) -> list[dict]:
    """Return the most recent blocks from Blockstream."""
    cache_key = f"recent_blocks:{n_blocks}"
    try:
        data = _request_json(f"{BLOCKSTREAM_URL}/blocks")[:n_blocks]
        return _remember(cache_key, data)
    except Exception:
        try:
            fallback = _recent_blocks_from_blockchain_info(n_blocks)
            return _remember(cache_key, fallback)
        except Exception:
            return _cached_fallback(cache_key)


@st.cache_data(ttl=60, show_spinner=False)
def get_difficulty_history(n_points: int = 100) -> list[dict]:
    """Return the last *n_points* difficulty values as a list of dicts."""
    cache_key = f"difficulty_history:{n_points}"
    try:
        data = _request_json(
            f"{BLOCKCHAIN_CHARTS_URL}/charts/difficulty",
            params={"timespan": "1year", "format": "json", "sampled": "true"},
        )
        return _remember(cache_key, data.get("values", [])[-n_points:])
    except Exception:
        return _cached_fallback(cache_key)


@st.cache_data(ttl=120, show_spinner=False)
def get_btc_usd_price() -> float:
    """Return the latest BTC/USD quote from blockchain.info."""
    cache_key = "btc_usd_price"
    try:
        data = _request_json(f"{BLOCKCHAIN_INFO_URL}/ticker")
        usd_price = float(data["USD"]["last"])
        return _remember(cache_key, usd_price)
    except Exception:
        return _cached_fallback(cache_key)
