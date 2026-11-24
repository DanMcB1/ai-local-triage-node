"""Score the labeled sample inbox for accuracy, latency, and PII quality."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Iterable

from triage.engine import triage
from triage.hardware import hardware_report
from triage.model import model_status
from triage.pii import detect
from triage.samples import SampleMessage, all_samples


def _fmt_ms(value: float) -> str:
    if value < 1:
        return f"{value:.2f} ms"
    if value < 10:
        return f"{value:.1f} ms"
    return f"{value:.0f} ms"


def _safe_div(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def _prf(true_pos: int, pred: int, gold: int) -> dict:
    precision = _safe_div(true_pos, pred)
    recall = _safe_div(true_pos, gold)
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": true_pos,
        "predicted": pred,
        "expected": gold,
    }


@dataclass
class SampleScore:
    id: str
    expected_category: str
    predicted_category: str
    category_ok: bool
    expected_urgency: str
    predicted_urgency: str
    urgency_ok: bool
    expected_route: str
    predicted_route: str
    route_ok: bool
    expected_pii: list[str]
    predicted_pii: list[str]
    pii_ok: bool
    ambiguous: bool
    used_backend: str
    latency_ms: float
    tokens_per_second: float | None
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvalReport:
    backend: str
    n: int
    category_accuracy: float
    urgency_accuracy: float
    route_accuracy: float
    exact_triage_accuracy: float
    pii: dict
    latency_ms_p50: float
    latency_ms_p95: float
    throughput_per_min: float
    mean_tokens_per_second: float | None
    used_backends: dict
    hardware: dict
    model: dict
    rows: list[SampleScore] = field(default_factory=list)
    missed: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _pii_sets(sample: SampleMessage, text: str) -> tuple[set[str], set[str], bool]:
    expected = set(sample.pii_types)
    predicted = {item.pii_type for item in detect(text)}
    # A sample is "ok" when every expected type is found and no unexpected
    # type is found. (Values are checked separately in unit tests.)
    ok = expected <= predicted and predicted <= expected
    return expected, predicted, ok


def evaluate(
    samples: Iterable[SampleMessage] | None = None,
    *,
    backend: str = "rules",
    network_off: bool = False,
) -> EvalReport:
    items = list(samples) if samples is not None else all_samples()
    rows: list[SampleScore] = []
    pii_tp = pii_pred = pii_gold = 0
    latencies: list[float] = []
    speeds: list[float] = []
    used = Counter()
    wall0 = time.perf_counter()

    for sample in items:
        text = sample.text()
        result = triage(text, backend=backend, network_off=network_off)
        expected_pii, predicted_pii, pii_ok = _pii_sets(sample, text)
        pii_tp += len(expected_pii & predicted_pii)
        pii_pred += len(predicted_pii)
        pii_gold += len(expected_pii)
        used[result.used_backend] += 1
        latencies.append(result.latency_ms)
        if result.tokens_per_second:
            speeds.append(result.tokens_per_second)
        rows.append(
            SampleScore(
                id=sample.id,
                expected_category=sample.category,
                predicted_category=result.category,
                category_ok=result.category == sample.category,
                expected_urgency=sample.urgency,
                predicted_urgency=result.urgency,
                urgency_ok=result.urgency == sample.urgency,
                expected_route=sample.route,
                predicted_route=result.route,
                route_ok=result.route == sample.route,
                expected_pii=sorted(expected_pii),
                predicted_pii=sorted(predicted_pii),
                pii_ok=pii_ok,
                ambiguous=sample.ambiguous,
                used_backend=result.used_backend,
                latency_ms=result.latency_ms,
                tokens_per_second=result.tokens_per_second,
                reason=result.reason,
            )
        )

    n = len(rows) or 1
    cat_ok = sum(1 for r in rows if r.category_ok)
    urg_ok = sum(1 for r in rows if r.urgency_ok)
    rte_ok = sum(1 for r in rows if r.route_ok)
    exact_ok = sum(1 for r in rows if r.category_ok and r.urgency_ok and r.route_ok)
    missed = [
        {
            "id": r.id,
            "field": field,
            "expected": getattr(r, f"expected_{field}"),
            "predicted": getattr(r, f"predicted_{field}"),
            "ambiguous": r.ambiguous,
        }
        for r in rows
        for field, ok in (
            ("category", r.category_ok),
            ("urgency", r.urgency_ok),
            ("route", r.route_ok),
        )
        if not ok
    ]
    lat_sorted = sorted(latencies) or [0.0]
    p95_index = min(len(lat_sorted) - 1, int(round(0.95 * (len(lat_sorted) - 1))))
    wall_ms = (time.perf_counter() - wall0) * 1000
    throughput = (len(rows) / wall_ms) * 60_000 if rows and wall_ms else 0.0
    return EvalReport(
        backend=backend,
        n=len(rows),
        category_accuracy=round(cat_ok / n, 3),
        urgency_accuracy=round(urg_ok / n, 3),
        route_accuracy=round(rte_ok / n, 3),
        exact_triage_accuracy=round(exact_ok / n, 3),
        pii=_prf(pii_tp, pii_pred, pii_gold),
        latency_ms_p50=float(median(lat_sorted)),
        latency_ms_p95=float(lat_sorted[p95_index]),
        throughput_per_min=round(throughput, 2),
        mean_tokens_per_second=(round(sum(speeds) / len(speeds), 2) if speeds else None),
        used_backends=dict(used),
        hardware=hardware_report(),
        model=model_status(),
        rows=rows,
        missed=missed,
    )


def markdown_report(report: EvalReport) -> str:
    """Render a scorecard a person can read in an interview."""
    pii = report.pii
    hw = report.hardware
    model = report.model
    lines = [
        "# Local Quantized Triage Node — sample scorecard",
        "",
        f"Backend: **{report.backend}**. Labeled messages: **{report.n}**.",
        "This is a portfolio demo set, not a customer evaluation.",
        "",
        "## Accuracy",
        "",
        f"- Category: **{report.category_accuracy:.1%}**",
        f"- Urgency: **{report.urgency_accuracy:.1%}**",
        f"- Route: **{report.route_accuracy:.1%}**",
        f"- Exact (category + urgency + route): **{report.exact_triage_accuracy:.1%}**",
        (
            f"- PII type detection: precision **{pii['precision']:.1%}**, "
            f"recall **{pii['recall']:.1%}**, F1 **{pii['f1']:.3f}** "
            f"({pii['true_positives']}/{pii['expected']} expected types found)."
        ),
        "",
        "## Speed",
        "",
        f"- Latency p50: **{_fmt_ms(report.latency_ms_p50)}**; p95: **{_fmt_ms(report.latency_ms_p95)}**",
        f"- Throughput on this run: **{report.throughput_per_min:.2f} messages/min**",
    ]
    if report.mean_tokens_per_second:
        lines.append(
            f"- Local model generation: **{report.mean_tokens_per_second:.1f} tokens/sec** on CPU"
        )
    lines.extend(
        [
            "",
            "## Hardware",
            "",
            f"- CPU: {hw.get('cpu')} ({hw.get('cpu_cores')} cores)",
            f"- RAM: {hw.get('ram_gib')} GiB",
            f"- GPU: {hw.get('gpu')}",
            f"- Model ready: {model.get('ready')} ({model.get('model_name')})",
            f"- Backends used: {report.used_backends}",
            "",
        ]
    )
    if report.missed:
        lines.append("## Misses (vs. the labels in this demo set)")
        lines.append("")
        for item in report.missed:
            flag = " (ambiguous on purpose)" if item["ambiguous"] else ""
            lines.append(
                f"- `{item['id']}` {item['field']}: expected `{item['expected']}`, "
                f"got `{item['predicted']}`{flag}"
            )
            lines.append("")
    else:
        lines.append("The engine matched every category, urgency, and route label in this set.")
        lines.append("")
    return "\n".join(lines) + "\n"
