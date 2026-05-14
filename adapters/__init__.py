"""Per-asset adapters that decouple data fetching from rendering."""
from adapters.base import AssetAdapter, AssetIdentity, ModuleSpec, TopMetric
from adapters.btc import BtcAdapter
from adapters.eth import EthAdapter
from adapters.sol import SolAdapter


_ADAPTERS: dict[str, AssetAdapter] = {
    "BTC": BtcAdapter(),
    "ETH": EthAdapter(),
    "SOL": SolAdapter(),
}


def get_adapter(code: str) -> AssetAdapter:
    return _ADAPTERS[code]


def list_adapters() -> list[AssetAdapter]:
    return list(_ADAPTERS.values())


__all__ = [
    "AssetAdapter",
    "AssetIdentity",
    "ModuleSpec",
    "TopMetric",
    "get_adapter",
    "list_adapters",
]
