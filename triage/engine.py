"""Triage pipeline: deterministic PII, then rules, model, or hybrid routing."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field

from triage import model as model_mod
from triage import pii as pii_mod
from triage import rules as rules_mod
from triage.hardware import hardware_report
from triage.network import GUARD
from triage.settings import CATEGORY_TO_ROUTE, DEFAULT_BACKEND, MODEL_NAME

VALID_BACKENDS = {"rules", "model", "hybrid"}


@dataclass
class TriageResult:
    category: str
    urgency: str
    route: str
    reason: str
    backend: str
    used_backend: str
    pii: list[dict] = field(default_factory=list)
    masked_text: str = ""
    original_text: str = ""
    latency_ms: float = 0.0
    pii_ms: float = 0.0
    rules_ms: float = 0.0
    model_ms: float = 0.0
    tokens_per_second: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    model_name: str | None = None
    rules: dict | None = None
    model: dict | None = None
    fallback_reason: str | None = None
    network_guard: bool = False
    hardware: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_backend(name: str | None) -> str:
    value = (name or DEFAULT_BACKEND).strip().lower()
    if value not in VALID_BACKENDS:
        raise ValueError(f"Unknown backend {name!r}. Use rules, model, or hybrid.")
    return value


def triage(
    text: str,
    *,
    backend: str | None = None,
    network_off: bool | None = None,
    mask_pii_for_model: bool = True,
) -> TriageResult:
    """Screen a message for PII and classify category, urgency, and route."""
    backend_name = _normalize_backend(backend or os.environ.get("TRIAGE_BACKEND"))
    if network_off is None:
        network_off = os.environ.get("TRIAGE_NETWORK", "").lower() in {"off", "0", "false", "guard"}
    if network_off and not GUARD.enabled:
        GUARD.enable()

    t_all = time.perf_counter()
    t0 = time.perf_counter()
    findings = pii_mod.detect(text)
    pii_ms = round((time.perf_counter() - t0) * 1000, 2)
    masked = pii_mod.mask(text, findings) if mask_pii_for_model else text

    t1 = time.perf_counter()
    rule_decision = rules_mod.classify(text)
    rules_ms = round((time.perf_counter() - t1) * 1000, 2)

    model_decision = None
    model_error = None
    used = "rules"
    reason = rule_decision.reason
    category = rule_decision.category
    urgency = rule_decision.urgency
    route = rule_decision.route
    model_ms = 0
    tps = None
    prompt_tokens = None
    completion_tokens = None
    model_name = None

    want_model = backend_name == "model" or (
        backend_name == "hybrid" and not rule_decision.confident
    )
    if want_model:
        try:
            model_decision = model_mod.classify(masked)
            used = "model"
            category = model_decision.category
            urgency = model_decision.urgency
            route = model_decision.route
            # Keep route aligned if the model picked a department route that
            # does not match its own category; prefer the stated route.
            if route not in {
                CATEGORY_TO_ROUTE[category],
                "bdc" if category in {"sales", "general"} else CATEGORY_TO_ROUTE[category],
            }:
                # Allow any declared route; do not silently rewrite it.
                pass
            reason = model_decision.reason
            model_ms = model_decision.latency_ms
            tps = model_decision.tokens_per_second
            prompt_tokens = model_decision.prompt_tokens
            completion_tokens = model_decision.completion_tokens
            model_name = model_decision.model_name
        except Exception as exc:  # noqa: BLE001 — fallback is the point
            model_error = str(exc)
            used = "rules"
            if backend_name == "model":
                reason = f"Model unavailable ({model_error}). Fell back to rules. {rule_decision.reason}"
            else:
                reason = f"Hybrid used rules (model fallback: {model_error}). {rule_decision.reason}"

    if backend_name == "hybrid" and used == "rules" and not model_error:
        reason = f"Hybrid used rules (confident). {rule_decision.reason}"

    total_ms = round((time.perf_counter() - t_all) * 1000, 2)
    return TriageResult(
        category=category,
        urgency=urgency,
        route=route,
        reason=reason,
        backend=backend_name,
        used_backend=used,
        pii=[item.to_dict() for item in findings],
        masked_text=masked,
        original_text=text,
        latency_ms=total_ms,
        pii_ms=pii_ms,
        rules_ms=rules_ms,
        model_ms=model_ms,
        tokens_per_second=tps,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model_name=model_name or (MODEL_NAME if used == "model" else None),
        rules=rule_decision.to_dict(),
        model=model_decision.to_dict() if model_decision else None,
        fallback_reason=model_error,
        network_guard=GUARD.enabled,
        hardware=hardware_report(),
    )
