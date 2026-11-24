"""CLI for the Local Quantized Triage Node.

Examples:

    python -m triage once --id svc-brakes
    python -m triage once --text "My Civic won't start..."
    python -m triage eval --backend rules
    python -m triage download
    python -m triage prove-offline
    python -m triage hardware
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from triage.engine import triage
from triage.eval import evaluate, markdown_report
from triage.hardware import hardware_report
from triage.model import model_status
from triage.network import GUARD
from triage.samples import all_samples, get_sample
from triage.settings import MODEL_PATH, MODEL_SHA256, MODEL_SIZE_BYTES, MODEL_URL, ROOT


def _cmd_once(args: argparse.Namespace) -> int:
    if args.id:
        text = get_sample(args.id).text()
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()
    result = triage(text, backend=args.backend, network_off=args.network_off)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Category: {result.category}")
        print(f"Urgency:  {result.urgency}")
        print(f"Route:    {result.route}")
        print(f"Backend:  {result.used_backend} (requested {result.backend})")
        print(f"Latency:  {result.latency_ms} ms")
        if result.tokens_per_second:
            print(f"Speed:    {result.tokens_per_second} tok/s")
        print(f"PII:      {len(result.pii)} finding(s)")
        for item in result.pii:
            print(f"  - {item['pii_type']}: {item['value']} ({item['check']})")
        print(f"Reason:   {result.reason}")
        if result.fallback_reason:
            print(f"Fallback: {result.fallback_reason}")
        print(f"Guard:    {'on' if result.network_guard else 'off'}")
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    report = evaluate(backend=args.backend, network_off=args.network_off)
    text = markdown_report(report)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
    print(text)
    if args.json:
        payload = report.to_dict()
        # The per-row dump is large; keep it unless asked not to.
        print(json.dumps(payload, indent=2))
    return 0


def _cmd_download(_args: argparse.Namespace) -> int:
    script = ROOT / "download_model.sh"
    if not script.is_file():
        print("download_model.sh is missing.", file=sys.stderr)
        return 1
    print("Launching download_model.sh (checksum-verified GGUF from Hugging Face)…")
    print(f"  url:  {MODEL_URL}")
    print(f"  dest: {MODEL_PATH}")
    print(f"  sha256: {MODEL_SHA256}")
    print(f"  size: {MODEL_SIZE_BYTES} bytes")
    os_exec = __import__("os")
    os_exec.execv("/bin/bash", ["bash", str(script)])
    return 0


def _cmd_prove(args: argparse.Namespace) -> int:
    GUARD.blocked_attempts.clear()
    GUARD.enable()
    probe = GUARD.probe_outbound(host=args.host, port=args.port)
    # Triage must still work with the guard on.
    result = triage(
        "My Civic won't start on Route 30. I need a tow to Lakeside Honda.",
        backend="rules",
        network_off=True,
    )
    payload = {
        "probe": probe,
        "triage": {
            "category": result.category,
            "urgency": result.urgency,
            "route": result.route,
            "network_guard": result.network_guard,
            "latency_ms": result.latency_ms,
        },
    }
    print(json.dumps(payload, indent=2))
    if not probe["blocked_by_guard"]:
        print("Expected the guard to block the outbound probe.", file=sys.stderr)
        return 1
    if result.category != "service":
        print("Local rules triage did not classify the stranded-car message as service.", file=sys.stderr)
        return 1
    print("OK: outbound probe was blocked; local triage still ran.")
    return 0


def _cmd_hardware(_args: argparse.Namespace) -> int:
    print(json.dumps({"hardware": hardware_report(), "model": model_status()}, indent=2))
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    for sample in all_samples():
        pii = ",".join(sample.pii_types) or "-"
        print(f"{sample.id:20} {sample.category:8} {sample.urgency:8} {sample.route:18} pii={pii}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m triage", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    once = sub.add_parser("once", help="Triage one message")
    once.add_argument("--id", help="Sample id from the labeled inbox")
    once.add_argument("--file", help="Path to a text file")
    once.add_argument("--text", help="Raw message text")
    once.add_argument("--backend", default="hybrid", choices=["hybrid", "model", "rules"])
    once.add_argument("--network-off", action="store_true")
    once.add_argument("--json", action="store_true")
    once.set_defaults(func=_cmd_once)

    ev = sub.add_parser("eval", help="Score the labeled sample inbox")
    ev.add_argument("--backend", default="rules", choices=["hybrid", "model", "rules"])
    ev.add_argument("--network-off", action="store_true")
    ev.add_argument("--out", help="Write a markdown report to this path")
    ev.add_argument("--json", action="store_true")
    ev.set_defaults(func=_cmd_eval)

    dl = sub.add_parser("download", help="Download the pinned GGUF (wraps download_model.sh)")
    dl.set_defaults(func=_cmd_download)

    prove = sub.add_parser("prove-offline", help="Block an outbound probe, then triage locally")
    prove.add_argument("--host", default="huggingface.co")
    prove.add_argument("--port", type=int, default=443)
    prove.set_defaults(func=_cmd_prove)

    hw = sub.add_parser("hardware", help="Print CPU / RAM / model status")
    hw.set_defaults(func=_cmd_hardware)

    lst = sub.add_parser("list", help="List sample message ids")
    lst.set_defaults(func=_cmd_list)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
