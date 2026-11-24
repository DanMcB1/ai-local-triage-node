"""Optional local GGUF backend via llama-cpp-python.

The model is never required: if the weights or the binding are missing,
callers get a clear status and should fall back to rules. Downloads are
handled by ./download_model.sh — this module only loads a local file.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from triage.settings import (
    CATEGORIES,
    MODEL_FILENAME,
    MODEL_NAME,
    MODEL_PATH,
    MODEL_QUANT,
    MODEL_REPO,
    ROUTES,
    URGENCIES,
)

try:
    from llama_cpp import Llama, LlamaGrammar
except ImportError:  # pragma: no cover - optional on CI
    Llama = None  # type: ignore[assignment]
    LlamaGrammar = None  # type: ignore[assignment]


# Short JSON only, so CPU generation stays in a few seconds.
_GRAMMAR = r"""
root ::= "{" ws "\"category\"" ws ":" ws category "," ws "\"urgency\"" ws ":" ws urgency "," ws "\"route\"" ws ":" ws route "," ws "\"reason\"" ws ":" ws reason "}"
category ::= "\"sales\"" | "\"service\"" | "\"fi\"" | "\"legal\"" | "\"billing\"" | "\"general\""
urgency ::= "\"critical\"" | "\"high\"" | "\"normal\"" | "\"low\""
route ::= "\"sales_manager\"" | "\"service_advisor\"" | "\"fi_manager\"" | "\"legal_compliance\"" | "\"controller\"" | "\"bdc\""
reason ::= "\"" word (" " word){0,15} "\""
word ::= [A-Za-z0-9] [A-Za-z0-9,.'\-]{0,18}
ws ::= [ \t\n]*
"""

_SYSTEM = """You triage incoming dealership messages for Lakeside Auto Group.
Return JSON only with keys category, urgency, route, reason.
category must be one of: sales, service, fi, legal, billing, general.
urgency must be one of: critical, high, normal, low.
route must be one of: sales_manager, service_advisor, fi_manager, legal_compliance, controller, bdc.
fi means Finance & Insurance. legal is attorney, lawsuit, lemon law, or a regulator complaint.
critical is stranded, tow, a lawsuit just served, or a lemon-law demand.
high is same-day need, a lawyer request, a credit application, or a safety issue that still drives.
Use bdc for simple inventory or hours questions; use sales_manager when someone is ready to buy or needs an out-the-door price.
Personal values may already be replaced by tokens like [SSN] or [CREDIT_CARD].
Keep reason under 16 words."""

_LLM: object | None = None
_LOAD_ERROR: str | None = None
_LOAD_SECONDS: float | None = None


@dataclass(frozen=True)
class ModelDecision:
    category: str
    urgency: str
    route: str
    reason: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    tokens_per_second: float
    model_name: str
    raw: str

    def to_dict(self) -> dict:
        return asdict(self)


def model_path() -> Path:
    override = os.environ.get("TRIAGE_MODEL_PATH")
    return Path(override) if override else MODEL_PATH


def llama_cpp_available() -> bool:
    return Llama is not None


def model_file_present() -> bool:
    path = model_path()
    return path.is_file() and path.stat().st_size > 1_000_000


def model_status() -> dict:
    path = model_path()
    return {
        "model_name": MODEL_NAME,
        "repo": MODEL_REPO,
        "filename": MODEL_FILENAME,
        "quant": MODEL_QUANT,
        "path": str(path),
        "file_present": model_file_present(),
        "llama_cpp": llama_cpp_available(),
        "ready": model_file_present() and llama_cpp_available() and _LOAD_ERROR is None,
        "load_error": _LOAD_ERROR,
        "load_seconds": _LOAD_SECONDS,
        "n_threads": int(os.environ.get("TRIAGE_THREADS") or os.cpu_count() or 4),
    }


def _build_llm():
    global _LOAD_ERROR, _LOAD_SECONDS, _LLM
    if not llama_cpp_available():
        _LOAD_ERROR = "llama-cpp-python is not installed. Run ./download_model.sh or pip install -r requirements-llm.txt."
        return None
    if not model_file_present():
        _LOAD_ERROR = f"Model file not found at {model_path()}. Run ./download_model.sh."
        return None
    threads = int(os.environ.get("TRIAGE_THREADS") or os.cpu_count() or 4)
    t0 = time.perf_counter()
    llm = Llama(
        model_path=str(model_path()),
        n_ctx=int(os.environ.get("TRIAGE_N_CTX", "2048")),
        n_threads=threads,
        n_batch=int(os.environ.get("TRIAGE_N_BATCH", "256")),
        n_gpu_layers=0,
        verbose=False,
    )
    _LOAD_SECONDS = round(time.perf_counter() - t0, 2)
    _LOAD_ERROR = None
    _LLM = llm
    return llm


def get_llm():
    """Load the GGUF once per process. Returns None if unavailable."""
    global _LLM
    if _LLM is not None:
        return _LLM
    return _build_llm()


def _parse_json(text: str) -> dict | None:
    blob = text.strip()
    if not blob:
        return None
    try:
        data = json.loads(blob)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", blob, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _valid(data: dict) -> dict | None:
    category = str(data.get("category", "")).strip().lower()
    urgency = str(data.get("urgency", "")).strip().lower()
    route = str(data.get("route", "")).strip().lower()
    reason = str(data.get("reason", "")).strip()
    if category not in CATEGORIES or urgency not in URGENCIES or route not in ROUTES:
        return None
    if not reason:
        reason = "Local model classification."
    return {
        "category": category,
        "urgency": urgency,
        "route": route,
        "reason": reason[:240],
    }


def classify(text: str) -> ModelDecision:
    """Run the local model on already-prepared (usually masked) text.

    Raises RuntimeError if the model cannot be loaded or the output cannot
    be parsed. Callers should catch that and fall back to rules.
    """
    llm = get_llm()
    if llm is None:
        raise RuntimeError(_LOAD_ERROR or "Local model is not available.")
    grammar = LlamaGrammar.from_string(_GRAMMAR)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": text.strip()[:3000]},
    ]
    t0 = time.perf_counter()
    out = llm.create_chat_completion(
        messages=messages,
        temperature=0.0,
        max_tokens=80,
        grammar=grammar,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw = (out.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    usage = out.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    tps = 0.0
    if completion_tokens and elapsed_ms:
        tps = round(completion_tokens / (elapsed_ms / 1000.0), 2)
    parsed = _parse_json(raw)
    valid = _valid(parsed) if parsed else None
    if not valid:
        raise RuntimeError(f"Local model returned unusable output: {raw[:200]!r}")
    return ModelDecision(
        category=valid["category"],
        urgency=valid["urgency"],
        route=valid["route"],
        reason=valid["reason"],
        latency_ms=elapsed_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        tokens_per_second=tps,
        model_name=MODEL_NAME,
        raw=raw,
    )


def reset_for_tests() -> None:
    """Drop the cached loader state. Used by unit tests."""
    global _LLM, _LOAD_ERROR, _LOAD_SECONDS
    _LLM = None
    _LOAD_ERROR = None
    _LOAD_SECONDS = None
