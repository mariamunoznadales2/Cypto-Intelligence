"""Common contract for per-asset data adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class AssetIdentity:
    """Visual + lexical identity of a crypto asset."""

    code: str
    name: str
    symbol: str
    kicker: str
    accent: str
    accent_soft: str
    available: bool


@dataclass(frozen=True)
class ModuleSpec:
    """Label set for a module slot, customised per asset."""

    panel_label: str
    title: str
    caption: str


@dataclass(frozen=True)
class TopMetric:
    label: str
    value: str
    delta: str | None = None


class AssetAdapter(Protocol):
    """Each adapter exposes data + labels in an asset-agnostic shape."""

    identity: AssetIdentity

    def top_metrics(self) -> list[TopMetric]: ...
    def state_module(self) -> ModuleSpec: ...
    def mechanism_module(self) -> ModuleSpec: ...
    def evolution_module(self) -> ModuleSpec: ...
    def forecast_module(self) -> ModuleSpec: ...

    # Renderers — adapters that have real data plug their existing module renderers.
    # Placeholder adapters return None and the host renders a coming-soon panel.
    state_renderer: Callable[[], None] | None
    mechanism_renderer: Callable[[], None] | None
    evolution_renderer: Callable[[], None] | None
    forecast_renderer: Callable[[], None] | None
