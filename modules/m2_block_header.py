"""Streamlit module for analyzing a Bitcoin block header."""

from datetime import UTC, datetime
import hashlib

import streamlit as st

from api.blockchain_client import (
    get_block_header_hex,
    get_blockstream_block,
    get_latest_block_hash,
)
from modules.dashboard_theme import render_kpi


HEADER_LENGTH_BYTES = 80


def double_sha256(header_hex: str) -> str:
    """Compute the Bitcoin double-SHA256 hash for a block header."""
    header_bytes = bytes.fromhex(header_hex)
    return hashlib.sha256(hashlib.sha256(header_bytes).digest()).digest()[::-1].hex()


def bits_to_target(bits: int) -> int:
    """Convert Bitcoin compact bits representation into the full target."""
    exponent = bits >> 24
    coefficient = bits & 0xFFFFFF
    return coefficient * (1 << (8 * (exponent - 3)))


def count_leading_zero_bits(hex_hash: str) -> int:
    """Count leading zero bits in a 256-bit hash."""
    binary = bin(int(hex_hash, 16))[2:].zfill(256)
    return len(binary) - len(binary.lstrip("0"))


def format_timestamp(timestamp: int) -> str:
    """Format a UNIX timestamp for display."""
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def reverse_hex_bytes(hex_value: str) -> str:
    """Reverse a hex string byte-by-byte."""
    raw_bytes = bytes.fromhex(hex_value)
    return raw_bytes[::-1].hex()


def parse_header_fields(header_hex: str) -> dict:
    """Parse the 80-byte Bitcoin header into human-readable fields."""
    header_bytes = bytes.fromhex(header_hex)
    if len(header_bytes) != HEADER_LENGTH_BYTES:
        raise ValueError(
            f"Bitcoin block headers must be {HEADER_LENGTH_BYTES} bytes, "
            f"received {len(header_bytes)} bytes."
        )

    return {
        "version": int.from_bytes(header_bytes[0:4], "little", signed=True),
        "previous_block_hash": reverse_hex_bytes(header_bytes[4:36].hex()),
        "merkle_root": reverse_hex_bytes(header_bytes[36:68].hex()),
        "timestamp": int.from_bytes(header_bytes[68:72], "little"),
        "bits": int.from_bytes(header_bytes[72:76], "little"),
        "nonce": int.from_bytes(header_bytes[76:80], "little"),
    }


def render() -> None:
    """Render the M2 Block Header Analyzer panel."""
    current_hash = get_latest_block_hash()
    state_key = "m2_snapshot"

    snapshot = st.session_state.get(state_key)
    if snapshot is None or snapshot["hash"] != current_hash:
        block = get_blockstream_block(current_hash)
        header_hex = get_block_header_hex(current_hash)
        header_fields = parse_header_fields(header_hex)
        computed_hash = double_sha256(header_hex)
        target = bits_to_target(header_fields["bits"])
        hash_int = int(computed_hash, 16)
        leading_zero_bits = count_leading_zero_bits(computed_hash)
        snapshot = {
            "hash": current_hash,
            "block": block,
            "header_hex": header_hex,
            "header_fields": header_fields,
            "computed_hash": computed_hash,
            "target": target,
            "hash_int": hash_int,
            "leading_zero_bits": leading_zero_bits,
            "header_matches_api": computed_hash == current_hash,
            "nonce_matches_api": header_fields["nonce"] == block["nonce"],
            "bits_match_api": header_fields["bits"] == block["bits"],
            "timestamp_matches_api": header_fields["timestamp"] == block["timestamp"],
            "pow_valid": hash_int <= target,
            "last_update": datetime.now(UTC).strftime("%H:%M:%S UTC"),
        }
        st.session_state[state_key] = snapshot

    st.subheader("Block Header Analyzer")
    st.caption("How the current block proves its validity.")
    try:
        block_hash = snapshot["hash"]
        block = snapshot["block"]
        header_hex = snapshot["header_hex"]
        header_fields = snapshot["header_fields"]
        computed_hash = snapshot["computed_hash"]
        target = snapshot["target"]
        hash_int = snapshot["hash_int"]
        leading_zero_bits = snapshot["leading_zero_bits"]
        header_matches_api = snapshot["header_matches_api"]
        nonce_matches_api = snapshot["nonce_matches_api"]
        bits_match_api = snapshot["bits_match_api"]
        timestamp_matches_api = snapshot["timestamp_matches_api"]
        pow_valid = snapshot["pow_valid"]
    except Exception as exc:
        st.error(f"Error loading block analysis: {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi("Block Height", block["height"])
    with col2:
        render_kpi("Nonce", header_fields["nonce"])
    with col3:
        render_kpi("Leading Zero Bits", leading_zero_bits)
    with col4:
        render_kpi("PoW Status", "Valid" if pow_valid else "Invalid")

    st.markdown("<br>", unsafe_allow_html=True)

    block_col1, block_col2 = st.columns(2)
    with block_col1:
        st.write(f"Hash: `{block_hash}`")
        st.write(f"Target: `{target}`")
        st.write(f"Nonce: `{header_fields['nonce']}`")
    with block_col2:
        st.write(f"Bits: `{header_fields['bits']}`")
        st.write(f"Timestamp: {format_timestamp(header_fields['timestamp'])}")
        st.write(f"Header size: `{len(bytes.fromhex(header_hex))}` bytes")

        st.markdown("<br>", unsafe_allow_html=True)

    field_col1, field_col2 = st.columns(2)
    with field_col1:
        st.write(f"Version: `{header_fields['version']}`")
        st.write(f"Previous Block: `{header_fields['previous_block_hash']}`")
        st.write(f"Bits: `{header_fields['bits']}`")
    with field_col2:
        st.write(f"Merkle Root: `{header_fields['merkle_root']}`")
        st.write(f"Timestamp: `{format_timestamp(header_fields['timestamp'])}`")
        st.write(f"Nonce: `{header_fields['nonce']}`")

    st.markdown("<br>", unsafe_allow_html=True)

    flow1, flow2, flow3 = st.columns(3)
    flow1.code("Header\n80 bytes", language="text")
    flow2.code("SHA256\nthen SHA256", language="text")
    flow3.code(f"Final hash\n{computed_hash}", language="text")

    st.markdown("<br>", unsafe_allow_html=True)

    validation_col1, validation_col2 = st.columns(2)
    with validation_col1:
        st.write(f"Target: `{target}`")
        st.write(f"Hash integer: `{hash_int}`")
    with validation_col2:
        st.write(f"Leading zero bits: `{leading_zero_bits}`")
        st.write(f"Computed hash: `{computed_hash}`")

    status_col1, status_col2, status_col3 = st.columns(3)
    with status_col1:
        render_kpi("Hash Match", "Yes" if header_matches_api else "No")
    with status_col2:
        render_kpi(
            "Header Match",
            "Yes" if nonce_matches_api and bits_match_api and timestamp_matches_api else "No",
        )
    with status_col3:
        render_kpi("Valid / Invalid", "Valid" if pow_valid else "Invalid")

    st.caption(f"Last update: {snapshot['last_update']}")

    st.code(header_hex, language="text")
