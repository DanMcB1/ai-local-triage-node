"""Local Quantized Triage Node — Streamlit UI.

Run with ./run.sh
Works fully offline in rules-only mode. The optional GGUF is local and is
never required for the first run, tests, or CI.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from triage.engine import triage
from triage.eval import evaluate, markdown_report
from triage.hardware import hardware_report
from triage.model import get_llm, model_status
from triage.network import GUARD
from triage.pii import highlight_html
from triage.samples import all_samples, get_sample
from triage.settings import (
    CATEGORY_LABELS,
    COMPANY,
    MODEL_NAME,
    ROUTE_LABELS,
    URGENCY_LABELS,
)

st.set_page_config(
    page_title="Local Quantized Triage Node",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
  .block-container { padding-top: 1.2rem; max-width: 1360px; }
  .demo-banner {
    background: #fff6e5;
    border: 1px solid #e6d2a8;
    color: #5a4500;
    padding: 0.7rem 1rem;
    border-radius: 8px;
    font-size: 0.95rem;
    margin-bottom: 0.8rem;
  }
  .status-pill {
    display: inline-block;
    border-radius: 999px;
    padding: 0.15rem 0.65rem;
    font-size: 0.8rem;
    font-weight: 600;
    margin-right: 0.4rem;
  }
  .ok { background: #e8f6f2; color: #145a50; border: 1px solid #9ad0c4; }
  .warn { background: #fff6e5; color: #5a4500; border: 1px solid #e6d2a8; }
  .bad { background: #fdeeee; color: #7a1f1f; border: 1px solid #e3b3b3; }
  .result-card {
    background: #fff;
    border: 1px solid #d5dbe3;
    border-radius: 10px;
    padding: 0.9rem 1rem 0.8rem;
    margin: 0 0 0.75rem;
  }
  .result-label {
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #4a5a70;
    font-weight: 700;
    margin: 0 0 0.3rem;
  }
  .message-box {
    background: #fff;
    border: 1px solid #d5dbe3;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    line-height: 1.45;
  }
  mark.pii {
    background: #fdeeee;
    color: #7a1f1f;
    border-radius: 3px;
    padding: 0 0.15rem;
  }
  .pii-tag {
    font-size: 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 700;
    margin-left: 0.3rem;
    color: #9b2c2c;
  }
  h1 { letter-spacing: -0.02em; }
  div[data-testid="stMetric"] {
    background: #f3f5f8;
    border: 1px solid #d5dbe3;
    border-radius: 10px;
    padding: 8px 12px;
  }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _fmt_ms(value: float) -> str:
    if value < 1:
        return f"{value:.2f} ms"
    if value < 10:
        return f"{value:.1f} ms"
    return f"{value:.0f} ms"


def _load_model():
    status = model_status()
    if status["ready"] or (status["file_present"] and status["llama_cpp"]):
        return get_llm()
    return None


@st.cache_resource(show_spinner="Loading the local 1.5B Q4 model on CPU…")
def _cached_model():
    return _load_model()


def _ensure_model_if_needed(backend: str) -> None:
    if backend in {"hybrid", "model"} and model_status()["file_present"] and model_status()["llama_cpp"]:
        _cached_model()


SAMPLES = all_samples()
SAMPLE_LABELS = {
    s.id: f"{s.id}  ·  {CATEGORY_LABELS[s.category]}  ·  {URGENCY_LABELS[s.urgency]}"
    for s in SAMPLES
}


with st.sidebar:
    st.markdown(f"**{COMPANY}**")
    st.caption("Fictional dealer group used across this portfolio.")
    backend = st.radio(
        "Triage backend",
        options=["hybrid", "rules", "model"],
        index=0,
        format_func=lambda v: {
            "hybrid": "Hybrid (rules first, model on close calls)",
            "rules": "Rules only (no model)",
            "model": "Local GGUF for every message",
        }[v],
        help="Hybrid is the recommended path. PII screening is always the deterministic detectors, never the model alone.",
    )
    network_off = st.checkbox(
        "Network guard on (block outbound sockets)",
        value=True,
        help="Localhost still works so this UI can run. Anything else is refused.",
    )
    if network_off and not GUARD.enabled:
        GUARD.enable()
    if not network_off and GUARD.enabled:
        GUARD.disable()

    status = model_status()
    hw = hardware_report()
    st.markdown("#### Node status")
    if status["file_present"] and status["llama_cpp"]:
        st.markdown(
            f'<span class="status-pill ok">Model on disk</span> {MODEL_NAME}',
            unsafe_allow_html=True,
        )
    elif status["file_present"]:
        st.markdown(
            '<span class="status-pill warn">GGUF present, llama-cpp-python not installed</span>',
            unsafe_allow_html=True,
        )
        st.caption("Run `./download_model.sh` or `pip install -r requirements-llm.txt`.")
    else:
        st.markdown(
            '<span class="status-pill warn">Rules-only — GGUF not downloaded</span>',
            unsafe_allow_html=True,
        )
        st.caption("Optional: `./download_model.sh` (~1.04 GB, checksum-verified, not committed).")
    st.markdown(
        f'<span class="status-pill {"ok" if network_off else "warn"}">'
        f'Network guard {"on" if network_off else "off"}</span>',
        unsafe_allow_html=True,
    )
    st.caption(f"CPU: {hw['cpu']} · {hw['cpu_cores']} cores")
    if hw.get("ram_gib"):
        st.caption(f"RAM: {hw['ram_gib']} GiB")
    st.caption(hw["gpu"])


st.title("Local Quantized Triage Node")
st.caption(
    "An offline first-look at incoming dealership messages: screen them for personal data, "
    "then route them to sales, service, F&I, legal, billing, or the BDC."
)
st.markdown(
    f'<div class="demo-banner">'
    f"<strong>Portfolio demo, not production.</strong> Sample company: {COMPANY}. "
    "This is not a certified DLP product and not a hosted model. "
    "Personal data in the sample inbox is fictional (555 numbers, example.com, test cards). "
    "PII screening uses regex plus checksums (Luhn, ABA, VIN). "
    "The optional 1.5B Q4 model runs on this machine's CPU — in production this node would typically use one GPU. "
    "No message is sent to a cloud API."
    "</div>",
    unsafe_allow_html=True,
)

inbox_tab, score_tab, proof_tab = st.tabs(["Inbox", "Scorecard", "Offline proof"])


def _show_result(result) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Category", CATEGORY_LABELS.get(result.category, result.category))
    c2.metric("Urgency", URGENCY_LABELS.get(result.urgency, result.urgency))
    c3.metric("Route to", ROUTE_LABELS.get(result.route, result.route))
    c4.metric("Latency", _fmt_ms(result.latency_ms))

    st.markdown(
        f'<div class="result-card"><div class="result-label">Why</div>'
        f"{result.reason}<br><br>"
        f"<span class='status-pill ok'>Used {result.used_backend}</span>"
        f"<span class='status-pill {'ok' if result.network_guard else 'warn'}'>"
        f"Guard {'on' if result.network_guard else 'off'}</span>"
        + (
            f"<span class='status-pill ok'>{result.tokens_per_second} tok/s</span>"
            if result.tokens_per_second
            else ""
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns((1.15, 0.85))
    with left:
        st.markdown("**Message, with PII marked**")
        html = highlight_html(result.original_text)
        st.markdown(f'<div class="message-box">{html}</div>', unsafe_allow_html=True)
        if result.masked_text != result.original_text:
            with st.expander("What the local model was allowed to see"):
                st.code(result.masked_text, language="text")
    with right:
        st.markdown("**PII findings**")
        if result.pii:
            df = pd.DataFrame(
                [
                    {
                        "Type": item["pii_type"],
                        "Value": item["value"],
                        "Check": item["check"],
                    }
                    for item in result.pii
                ]
            )
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("No PII findings in this message.")
        if result.rules:
            st.markdown("**Rules scores**")
            scores = result.rules.get("scores") or {}
            score_df = pd.DataFrame(
                [{"Department": CATEGORY_LABELS.get(k, k), "Score": v} for k, v in scores.items()]
            ).sort_values("Score", ascending=False)
            st.dataframe(score_df, hide_index=True, use_container_width=True)


with inbox_tab:
    st.subheader("Incoming messages")
    st.caption(
        "Pick a sample from the Lakeside inbox, or paste your own text. "
        "Nothing leaves this machine."
    )
    choice = st.selectbox(
        "Sample message",
        options=[s.id for s in SAMPLES],
        format_func=lambda sid: SAMPLE_LABELS[sid],
        index=[s.id for s in SAMPLES].index("fi-credit-app"),
    )
    sample = get_sample(choice)
    text = st.text_area(
        "Message text",
        value=sample.text(),
        height=260,
        help="You can edit the sample or replace it with another message.",
    )
    run = st.button("Triage this message", type="primary")
    if run:
        _ensure_model_if_needed(backend)
        with st.spinner("Screening for PII and classifying the message…"):
            result = triage(text, backend=backend, network_off=network_off)
        st.session_state["last_result"] = result.to_dict()
        st.session_state["last_result_obj"] = result

    if "last_result_obj" not in st.session_state and st.query_params.get("shot") == "1":
        auto = triage(get_sample("fi-credit-app").text(), backend="rules", network_off=True)
        st.session_state["last_result_obj"] = auto

    if "last_result_obj" in st.session_state:
        _show_result(st.session_state["last_result_obj"])
    else:
        st.caption("Press **Triage this message** to run the local pipeline.")


with score_tab:
    st.subheader("Accuracy and speed on the labeled sample set")
    st.caption(
        f"{len(SAMPLES)} fictional Lakeside messages with human labels. "
        "This is a demo set, not a customer evaluation. "
        "Rules finish instantly. Hybrid only calls the local model on close calls. "
        "Scoring every message with the GGUF takes a few minutes on CPU."
    )
    score_backend = st.radio(
        "Scorecard backend",
        options=["rules", "hybrid", "model"],
        index=0,
        horizontal=True,
        format_func=lambda v: {
            "rules": "Rules only (seconds)",
            "hybrid": "Hybrid (model on close calls)",
            "model": "Local GGUF on every message (slow on CPU)",
        }[v],
        key="score_backend",
    )
    if st.button("Run the scorecard", type="primary"):
        _ensure_model_if_needed(score_backend)
        spinner = (
            "Scoring with the local GGUF on CPU. This can take several minutes…"
            if score_backend == "model"
            else "Scoring the labeled inbox…"
        )
        with st.spinner(spinner):
            report = evaluate(backend=score_backend, network_off=network_off)
        st.session_state["scorecard"] = report

    report = st.session_state.get("scorecard")
    if report is not None:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Category", f"{report.category_accuracy:.1%}")
        m2.metric("Urgency", f"{report.urgency_accuracy:.1%}")
        m3.metric("Route", f"{report.route_accuracy:.1%}")
        m4.metric("PII F1", f"{report.pii['f1']:.3f}")
        m5.metric("Latency p50", _fmt_ms(report.latency_ms_p50))
        st.caption(
            f"Exact triage match {report.exact_triage_accuracy:.1%} · "
            f"p95 {_fmt_ms(report.latency_ms_p95)} · "
            f"{report.throughput_per_min:.1f} messages/min · "
            f"backends used: {report.used_backends}"
            + (
                f" · {report.mean_tokens_per_second:.1f} tok/s"
                if report.mean_tokens_per_second
                else ""
            )
        )
        rows = pd.DataFrame(
            [
                {
                    "id": r.id,
                    "category": r.predicted_category,
                    "category ok": r.category_ok,
                    "urgency": r.predicted_urgency,
                    "urgency ok": r.urgency_ok,
                    "route": r.predicted_route,
                    "route ok": r.route_ok,
                    "PII ok": r.pii_ok,
                    "backend": r.used_backend,
                    "ms": r.latency_ms,
                    "ambiguous": r.ambiguous,
                }
                for r in report.rows
            ]
        )
        st.dataframe(rows, hide_index=True, use_container_width=True)
        if report.missed:
            st.markdown("**Misses versus the demo labels**")
            st.dataframe(pd.DataFrame(report.missed), hide_index=True, use_container_width=True)
        with st.expander("Markdown report"):
            st.markdown(markdown_report(report))
    else:
        st.caption("Press **Run the scorecard** to measure this machine.")


with proof_tab:
    st.subheader("Prove the message stayed on this machine")
    st.caption(
        "The network guard refuses outbound TCP connections (Hugging Face, public DNS, and so on). "
        "Loopback is still allowed, which is how you are looking at this page. "
        "This is a user-space socket patch, not a kernel firewall — I would not call it a certified air gap."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Try an outbound connection to huggingface.co", type="primary"):
            if not GUARD.enabled:
                GUARD.enable()
            probe = GUARD.probe_outbound("huggingface.co", 443, timeout=2)
            st.session_state["probe"] = probe
        probe = st.session_state.get("probe")
        if probe:
            if probe["blocked_by_guard"]:
                st.success(
                    f"Blocked. The node refused huggingface.co:{probe['port']}. "
                    "The file on disk is the only model this process can use."
                )
            elif probe["opened"]:
                st.error("The connection opened. Turn the network guard on in the sidebar and try again.")
            else:
                st.warning(f"Did not open, but not because of the guard: {probe.get('error')}")
            st.json(probe)
    with col_b:
        if st.button("Triage a stranded-car message while the guard is on"):
            if not GUARD.enabled:
                GUARD.enable()
            result = triage(
                "This is Dana Okonkwo. My Civic won't start on the side of Route 30. "
                "I need a tow to Lakeside Honda. I'm stranded.",
                backend="rules",
                network_off=True,
            )
            st.session_state["proof_triage"] = result
        result = st.session_state.get("proof_triage")
        if result:
            st.success(
                f"Local triage still ran: {CATEGORY_LABELS[result.category]} / "
                f"{URGENCY_LABELS[result.urgency]} / {ROUTE_LABELS[result.route]} "
                f"in {_fmt_ms(result.latency_ms)}."
            )
            st.caption(result.reason)
