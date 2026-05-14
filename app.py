"""Streamlit entry point for the Blockchain Dashboard project."""

from datetime import UTC, datetime
from typing import Callable, TypeVar

import streamlit as st

from adapters import AssetAdapter, get_adapter, list_adapters
from modules.dashboard_theme import render_kpi


REFRESH_INTERVAL = "10s"
RenderFn = TypeVar("RenderFn", bound=Callable[..., None])


st.set_page_config(
    page_title="Crypto Intelligence",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


def live_fragment(run_every: str) -> Callable[[RenderFn], RenderFn]:
    """Use partial reruns when the installed Streamlit version supports fragments."""
    fragment = getattr(st, "fragment", None)
    if fragment is None:
        def passthrough(func: RenderFn) -> RenderFn:
            return func

        return passthrough
    return fragment(run_every=run_every)


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --bg: #050816;
        --bg-soft: #0b1220;
        --panel: rgba(10, 16, 28, 0.92);
        --panel-strong: rgba(14, 22, 36, 0.98);
        --panel-border: rgba(255, 255, 255, 0.06);
        --accent: #22C55E;
        --accent-soft: #F7931A;
        --accent-border-strong: #22C55E5C;
        --accent-border-soft: #F7931A57;
        --accent-border-soft-light: #F7931A33;
        --accent-glow-strong: #22C55E2E;
        --accent-glow-soft: #F7931A1F;
        --green: #22C55E;
        --green-glow: #00FF88;
        --orange: #F7931A;
        --text: #F3F4F6;
        --muted: #8A94A7;
    }

    html, body, [class*="css"]  {
        font-family: "IBM Plex Sans", sans-serif;
    }

    body, .stApp {
        color: var(--text);
        background:
            radial-gradient(circle at 15% 20%, rgba(247, 147, 26, 0.10), transparent 0 22%),
            radial-gradient(circle at 85% 0%, rgba(0, 255, 136, 0.10), transparent 0 20%),
            radial-gradient(circle at 50% 100%, rgba(34, 197, 94, 0.08), transparent 0 28%),
            linear-gradient(180deg, #04070f 0%, #050816 48%, #09111b 100%);
    }

    .block-container {
        max-width: 1360px;
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
        border-bottom: none;
        box-shadow: none;
    }

    .stApp > header {
        background: transparent;
    }

    section[data-testid="stSidebar"] {
        display: none !important;
    }

    .asset-selector-wrap {
        margin: 0 auto 1.2rem auto;
        max-width: 760px;
    }

    .hero-wrap {
        text-align: center;
        margin-top: 1.8rem;
        margin-bottom: 2.4rem;
    }

    .hero-kicker {
        color: var(--orange);
        text-transform: uppercase;
        letter-spacing: 0.22em;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 0.9rem;
    }

    .hero-title {
        margin: 0;
        text-wrap: balance;
        color: #F9FAFB;
    }

    .hero-title-gradient {
        background: linear-gradient(90deg, #F9FAFB 0%, #D1FAE5 42%, var(--hero-accent, #22C55E) 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        -webkit-text-fill-color: transparent;
        display: inline-block;
    }

    .hero-subtitle {
        margin: 0.95rem auto 0 auto;
        color: #8A94A7;
        font-size: 1rem;
        line-height: 1.4;
        max-width: 620px;
    }

    [class*="st-key-module_shell_"] {
        background:
            linear-gradient(180deg, rgba(24, 36, 56, 0.98), rgba(16, 25, 40, 0.99)) !important;
        border-left: 1px solid var(--accent-border-soft) !important;
        border-right: 1px solid var(--accent-border-soft-light) !important;
        border-bottom: 1px solid var(--accent-border-soft-light) !important;
        border-top: 1px solid var(--accent-border-strong) !important;
        border-radius: 22px !important;
        padding: 1.35rem 1.35rem 1.2rem 1.35rem !important;
        box-shadow:
            0 28px 60px rgba(0, 0, 0, 0.30),
            inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
        min-height: 860px !important;
        max-height: 860px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        margin-top: 0.35rem;
        scrollbar-width: thin;
        scrollbar-color: rgba(34, 197, 94, 0.35) rgba(255, 255, 255, 0.04);
    }

    .panel-label {
        color: var(--accent-soft);
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 0.73rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }

    .status-line {
        color: #D1D5DB;
        font-size: 0.96rem;
        margin: 0.25rem 0 1.2rem 0;
        text-align: center;
    }

    [class*="st-key-module_shell_"]::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 22px;
        pointer-events: none;
        background:
            radial-gradient(circle at top left, var(--accent-glow-soft), transparent 22%),
            radial-gradient(circle at top right, var(--accent-glow-strong), transparent 24%);
    }

    [class*="st-key-module_shell_"] > div {
        position: relative;
        z-index: 1;
        height: 100%;
    }

    [class*="st-key-module_shell_"]::-webkit-scrollbar {
        width: 8px;
    }

    [class*="st-key-module_shell_"]::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 999px;
    }

    [class*="st-key-module_shell_"]::-webkit-scrollbar-thumb {
        background: rgba(34, 197, 94, 0.30);
        border-radius: 999px;
    }

    [data-testid="column"] {
        align-self: stretch;
    }

    .kpi-card {
        background:
            linear-gradient(180deg, rgba(14, 22, 36, 0.95), rgba(10, 16, 28, 0.95));
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 18px;
        padding: 1rem 1rem 0.95rem 1rem;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.03),
            0 18px 35px rgba(0, 0, 0, 0.22);
        position: relative;
        overflow: visible;
        min-height: 112px;
    }

    .kpi-card::before {
        content: "";
        position: absolute;
        inset: 0 auto auto 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, var(--accent-soft), var(--accent));
        opacity: 0.9;
    }

    .kpi-label {
        color: #C7D0DE !important;
        font-size: 0.74rem !important;
        text-transform: none !important;
        letter-spacing: 0.02em !important;
        font-weight: 700 !important;
        line-height: 1.15 !important;
        white-space: normal !important;
        overflow-wrap: break-word !important;
        word-break: normal !important;
        margin-bottom: 0.35rem !important;
        min-height: auto !important;
        display: block !important;
        opacity: 1 !important;
    }

    .kpi-value {
        color: #F9FAFB;
        font-family: "Space Grotesk", sans-serif;
        font-size: 1.55rem;
        letter-spacing: -0.04em;
        line-height: 1.04;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .kpi-card:hover .kpi-value {
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
    }

    .kpi-delta {
        color: var(--accent);
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 0.35rem;
    }

    .stSlider label,
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label,
    .stMarkdown,
    .stCaption {
        color: var(--muted);
    }

    h1, h2, h3 {
        font-family: "Space Grotesk", sans-serif;
        color: var(--text);
        letter-spacing: -0.03em;
    }

    .stAlert {
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stDataFrame, .stPlotlyChart, .stCodeBlock, .st-emotion-cache-1r6slb0 {
        border-radius: 16px;
    }

    code {
        color: #D1FAE5 !important;
        background: rgba(34, 197, 94, 0.10) !important;
        border: 1px solid rgba(34, 197, 94, 0.18) !important;
        border-radius: 10px !important;
        padding: 0.16rem 0.42rem !important;
        text-decoration: none !important;
        box-shadow: none !important;
    }

    a code, p code, li code, span code {
        color: #D1FAE5 !important;
        background: rgba(34, 197, 94, 0.10) !important;
        border: 1px solid rgba(34, 197, 94, 0.18) !important;
        text-decoration: none !important;
    }

    .stCodeBlock,
    div[data-testid="stCodeBlock"],
    pre {
        background: linear-gradient(180deg, rgba(11, 15, 12, 0.92), rgba(15, 23, 20, 0.96)) !important;
        border: 1px solid rgba(34, 197, 94, 0.12) !important;
        border-radius: 16px !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02) !important;
    }

    pre code {
        background: transparent !important;
        border: none !important;
        color: #D1D5DB !important;
        padding: 0 !important;
    }

    .js-plotly-plot .plotly .modebar {
        display: none !important;
    }

    div[data-testid="stDataFrame"] {
        background: transparent !important;
        border: none !important;
    }

    .st-key-asset_button_row {
        margin: 0 auto 1.2rem auto;
        max-width: 760px;
    }

    .st-key-asset_button_row .stButton > button {
        width: 100%;
        border-radius: 999px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background: rgba(15, 22, 36, 0.88) !important;
        color: #C7D0DE !important;
        padding: 0.72rem 1rem !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }

    .st-key-asset_button_row .stButton > button:hover {
        border-color: rgba(34, 197, 94, 0.35) !important;
        background: rgba(20, 30, 48, 0.98) !important;
        color: #F9FAFB !important;
    }

    .st-key-asset_button_row .stButton > button p,
    .st-key-asset_button_row .stButton > button span,
    .st-key-asset_button_row .stButton > button div {
        color: inherit !important;
        -webkit-text-fill-color: inherit !important;
        font-size: inherit !important;
        font-weight: inherit !important;
        opacity: 1 !important;
    }

    .milestone-nav {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.8rem;
        margin: 0.2rem auto 1.25rem auto;
    }

    .milestone-nav-card {
        display: block;
        min-height: 104px;
        padding: 0.95rem 1rem;
        border-radius: 18px;
        border: 1px solid var(--accent-border-soft-light);
        background:
            radial-gradient(circle at top left, var(--accent-glow-soft), transparent 36%),
            linear-gradient(180deg, rgba(17, 25, 40, 0.94), rgba(10, 16, 28, 0.90));
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.04),
            0 18px 34px rgba(0, 0, 0, 0.18);
        color: #C7D0DE !important;
        text-decoration: none !important;
        transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }

    .milestone-nav-card:hover {
        transform: translateY(-2px);
        border-color: var(--accent-border-strong);
        background:
            radial-gradient(circle at top left, var(--accent-glow-strong), transparent 42%),
            linear-gradient(180deg, rgba(22, 34, 52, 0.98), rgba(11, 18, 30, 0.96));
    }

    .milestone-nav-number {
        color: var(--accent-soft);
        font-family: "Space Grotesk", sans-serif;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }

    .milestone-nav-title {
        color: #F9FAFB;
        font-family: "Space Grotesk", sans-serif;
        font-size: 1rem;
        font-weight: 700;
        margin-top: 0.35rem;
        letter-spacing: -0.02em;
    }

    .milestone-nav-caption {
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.35;
        margin-top: 0.3rem;
    }

    .milestone-anchor {
        display: block;
        position: relative;
        top: -1rem;
        visibility: hidden;
    }

    @media (max-width: 900px) {
        .milestone-nav {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 560px) {
        .milestone-nav {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "selected_asset" not in st.session_state:
    st.session_state.selected_asset = "BTC"


def preload_asset_data() -> None:
    """Warm per-asset caches once so switching assets stays snappy."""
    if st.session_state.get("_assets_preloaded", False):
        return

    warmed: set[str] = set()
    for candidate in list_adapters():
        try:
            warm_cache = getattr(candidate, "warm_cache", None)
            if callable(warm_cache):
                warm_cache()
            else:
                candidate.top_metrics()
            warmed.add(candidate.identity.code)
        except Exception:
            continue

    st.session_state["_assets_preloaded"] = True
    st.session_state["_warmed_assets"] = sorted(warmed)


preload_asset_data()

selected_code = st.session_state.selected_asset
adapter: AssetAdapter = get_adapter(selected_code)
identity = adapter.identity
accent = identity.accent
accent_soft = identity.accent_soft

st.markdown(
    f"""
    <style>
    :root {{
        --accent: {accent};
        --accent-soft: {accent_soft};
        --accent-border-strong: {accent}5C;
        --accent-border-soft: {accent_soft}57;
        --accent-border-soft-light: {accent_soft}33;
        --accent-glow-strong: {accent}2E;
        --accent-glow-soft: {accent_soft}1F;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="hero-wrap">
        <div class="hero-kicker" style="color:{accent_soft};">{identity.kicker}</div>
        <h1 class="hero-title" style="font-family: 'Space Grotesk', sans-serif; font-size: clamp(4.2rem, 9vw, 6.2rem); line-height: 0.88; letter-spacing: -0.09em; font-weight: 800; text-shadow: 0 0 26px rgba(0, 0, 0, 0.18), 0 0 18px {accent}33;">
            <span class="hero-title-gradient" style="--hero-accent: {accent};">Crypto Intelligence</span>
        </h1>
        <div class="hero-subtitle">Multi-asset blockchain analytics · viewing <span style="color:{accent};font-weight:600;">{identity.name} ({identity.symbol})</span></div>
        <div class="status-line">Live dashboard | partial checks every 10 seconds | updates only on new blocks</div>
    </div>
    """,
    unsafe_allow_html=True,
)

all_adapters = list_adapters()
with st.container(key="asset_button_row"):
    asset_cols = st.columns(len(all_adapters))
    for index, candidate in enumerate(all_adapters):
        cid = candidate.identity
        active_dot = " ●" if cid.code == selected_code else ""
        label = f"{cid.symbol}{active_dot}" + ("" if cid.available else " · Soon")
        with asset_cols[index]:
            if st.button(label, key=f"asset_{cid.code}", use_container_width=True):
                st.session_state.selected_asset = cid.code
                st.rerun()

if not identity.available:
    st.info(
        f"{identity.name} data feed coming soon — module layout shown with placeholder data."
    )


def render_placeholder_panel(spec, accent_color: str, soft_color: str) -> None:
    """Render a structured 'coming soon' panel for assets without a data feed."""
    st.subheader(spec.title)
    st.caption(spec.caption)
    st.markdown(
        f"""
        <div style="margin-top:0.6rem;padding:1.2rem 1.1rem;border-radius:14px;
                    border:1px dashed {accent_color}55;
                    background:linear-gradient(180deg, {accent_color}10, {soft_color}08);
                    color:#9CA3AF;font-size:0.92rem;line-height:1.45;">
            <div style="color:{accent_color};font-weight:600;letter-spacing:0.08em;
                        text-transform:uppercase;font-size:0.7rem;margin-bottom:0.4rem;">
                Awaiting data feed
            </div>
            Module wiring is in place. Connect the live API for this asset to populate
            <span style="color:{accent_color};">{spec.title}</span>.
        </div>
        """,
        unsafe_allow_html=True,
    )


@live_fragment(REFRESH_INTERVAL)
def render_live_metrics() -> None:
    """Refresh the KPI strip without reloading the full page."""
    metrics = adapter.top_metrics()
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            render_kpi(metric.label, metric.value, metric.delta)
    st.caption(f"Last update: {datetime.now(UTC).strftime('%H:%M:%S UTC')}")


render_live_metrics()


def _render_module(spec, renderer) -> None:
    if renderer is not None:
        renderer()
    else:
        render_placeholder_panel(spec, accent, accent_soft)


@live_fragment(REFRESH_INTERVAL)
def render_live_state() -> None:
    _render_module(adapter.state_module(), adapter.state_renderer)


@live_fragment(REFRESH_INTERVAL)
def render_live_mechanism() -> None:
    _render_module(adapter.mechanism_module(), adapter.mechanism_renderer)


@live_fragment(REFRESH_INTERVAL)
def render_live_evolution() -> None:
    _render_module(adapter.evolution_module(), adapter.evolution_renderer)


@live_fragment(REFRESH_INTERVAL)
def render_live_forecast() -> None:
    _render_module(adapter.forecast_module(), adapter.forecast_renderer)


state_spec = adapter.state_module()
mechanism_spec = adapter.mechanism_module()
evolution_spec = adapter.evolution_module()
forecast_spec = adapter.forecast_module()
optional_specs = adapter.optional_modules() if hasattr(adapter, "optional_modules") else []
optional_renderers = getattr(adapter, "optional_renderers", [])

milestone_nav = [
    ("m1", "M1", state_spec.title, state_spec.caption),
    ("m2", "M2", mechanism_spec.title, mechanism_spec.caption),
    ("m3", "M3", evolution_spec.title, evolution_spec.caption),
    ("m4", "M4", forecast_spec.title, forecast_spec.caption),
]
milestone_nav.extend(
    (
        f"m{index + 5}",
        f"M{index + 5}",
        spec.title,
        spec.caption,
    )
    for index, spec in enumerate(optional_specs)
)

st.markdown(
    '<div class="panel-label">Dashboard Navigation</div><div class="milestone-nav">'
    + "".join(
        f'<a class="milestone-nav-card" href="#{anchor}">'
        f'<div class="milestone-nav-number">{number}</div>'
        f'<div class="milestone-nav-title">{title}</div>'
        f'<div class="milestone-nav-caption">{caption}</div>'
        "</a>"
        for anchor, number, title, caption in milestone_nav
    )
    + "</div>",
    unsafe_allow_html=True,
)

top_left, top_right = st.columns(2)
with top_left:
    st.markdown('<span id="m1" class="milestone-anchor"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="panel-label" style="color:{accent_soft};">M1 | {state_spec.panel_label}</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="module_shell_m1"):
        render_live_state()
with top_right:
    st.markdown('<span id="m2" class="milestone-anchor"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="panel-label" style="color:{accent_soft};">M2 | {mechanism_spec.panel_label}</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="module_shell_m2"):
        render_live_mechanism()

bottom_left, bottom_right = st.columns(2)
with bottom_left:
    st.markdown('<span id="m3" class="milestone-anchor"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="panel-label" style="color:{accent_soft};">M3 | {evolution_spec.panel_label}</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="module_shell_m3"):
        render_live_evolution()
with bottom_right:
    st.markdown('<span id="m4" class="milestone-anchor"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="panel-label" style="color:{accent_soft};">M4 | {forecast_spec.panel_label}</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="module_shell_m4"):
        render_live_forecast()

if optional_specs:
    st.markdown(
        '<div class="panel-label" style="margin-top:1.2rem;">Advanced Modules</div>',
        unsafe_allow_html=True,
    )
    for index in range(0, len(optional_specs), 2):
        optional_cols = st.columns(2)
        for offset, col in enumerate(optional_cols):
            module_index = index + offset
            if module_index >= len(optional_specs):
                continue

            spec = optional_specs[module_index]
            renderer = optional_renderers[module_index] if module_index < len(optional_renderers) else None
            module_number = module_index + 5

            with col:
                st.markdown(
                    f'<span id="m{module_number}" class="milestone-anchor"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="panel-label" style="color:{accent_soft};">'
                    f'M{module_number} | {spec.panel_label}</div>',
                    unsafe_allow_html=True,
                )
                with st.container(key=f"module_shell_m{module_number}"):
                    _render_module(spec, renderer)
