"""Optional M5 module: Bitcoin Merkle proof verifier."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from api.blockchain_client import (
    get_block_merkle_root,
    get_block_transaction_ids,
    get_latest_block_hash,
)
from modules.dashboard_theme import GREEN, render_kpi


def double_sha256(payload: bytes) -> bytes:
    """Return Bitcoin's double-SHA256 digest."""
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()


def _display_to_internal(txid: str) -> bytes:
    return bytes.fromhex(txid)[::-1]


def _internal_to_display(value: bytes) -> str:
    return value[::-1].hex()


def build_merkle_proof(txids: list[str], target_index: int) -> tuple[list[dict], str]:
    """Build and verify a Merkle proof for one transaction id.

    Returned hashes are in the familiar displayed byte order. Concatenation and
    hashing use Bitcoin's internal little-endian byte order.
    """
    if not txids:
        raise ValueError("Cannot build a proof without transactions.")
    if target_index < 0 or target_index >= len(txids):
        raise ValueError("Target transaction index is outside the block.")

    level = [_display_to_internal(txid) for txid in txids]
    cursor = target_index
    proof: list[dict] = []

    while len(level) > 1:
        original_level_len = len(level)
        if len(level) % 2 == 1:
            level.append(level[-1])

        sibling_index = cursor ^ 1
        left_index = cursor - 1 if cursor % 2 else cursor
        right_index = cursor if cursor % 2 else cursor + 1
        left_hash = level[left_index]
        right_hash = level[right_index]
        parent = double_sha256(left_hash + right_hash)

        proof.append(
            {
                "level": len(proof) + 1,
                "position": "right" if cursor % 2 == 0 else "left",
                "left": _internal_to_display(left_hash),
                "right": _internal_to_display(right_hash),
                "sibling": _internal_to_display(level[sibling_index]),
                "computed_parent": _internal_to_display(parent),
                "duplicated": sibling_index >= original_level_len,
            }
        )

        next_level = []
        for idx in range(0, len(level), 2):
            next_level.append(double_sha256(level[idx] + level[idx + 1]))
        level = next_level
        cursor //= 2

    return proof, _internal_to_display(level[0])


def render() -> None:
    """Render the M5 panel."""
    st.subheader("Merkle Proof Verifier")
    st.caption("Pick a transaction in the latest block and recompute the Merkle path.")

    try:
        block_hash = get_latest_block_hash()
        txids = get_block_transaction_ids(block_hash)
        merkle_root = get_block_merkle_root(block_hash)

        if not txids:
            st.warning("No transactions were returned for this block.")
            return

        max_index = len(txids) - 1
        default_index = min(max_index, max(0, len(txids) // 2))
        target_index = st.number_input(
            "Transaction index",
            min_value=0,
            max_value=max_index,
            value=default_index,
            step=1,
            help="Index inside the current block's transaction list.",
        )

        target_txid = txids[int(target_index)]
        proof, computed_root = build_merkle_proof(txids, int(target_index))
        verified = computed_root == merkle_root

        col1, col2, col3 = st.columns(3)
        with col1:
            render_kpi("Transactions", f"{len(txids):,}")
        with col2:
            render_kpi("Proof Steps", len(proof))
        with col3:
            render_kpi("Verified", "YES" if verified else "NO")

        st.write(f"Block: `{block_hash}`")
        st.write(f"Target tx: `{target_txid}`")
        st.write(f"Expected root: `{merkle_root}`")
        st.write(f"Computed root: `{computed_root}`")

        if verified:
            st.success("Merkle proof matches the block header root.")
        else:
            st.error("Computed proof does not match the block Merkle root.")

        rows = [
            {
                "Step": step["level"],
                "Sibling side": step["position"],
                "Left hash": step["left"],
                "Right hash": step["right"],
                "Double SHA-256 result": step["computed_parent"],
                "Duplicated leaf": "yes" if step["duplicated"] else "no",
            }
            for step in proof
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with st.expander("Hash computations"):
            for step in proof:
                st.markdown(
                    f"<div style='border-left:2px solid {GREEN};padding:0.35rem 0.75rem;"
                    "margin:0.45rem 0;color:#D1D5DB;'>"
                    f"<b>Step {step['level']}</b><br>"
                    f"double_sha256(<code>{step['left']}</code> + <code>{step['right']}</code>)"
                    f"<br>= <code>{step['computed_parent']}</code>"
                    "</div>",
                    unsafe_allow_html=True,
                )

        st.caption(f"Last update: {datetime.now(UTC).strftime('%H:%M:%S UTC')}")
    except Exception as exc:
        st.error(f"Error verifying Merkle proof: {exc}")
