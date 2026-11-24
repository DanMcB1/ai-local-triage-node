# Local Quantized Triage Node

A small, local demo of an **offline triage node**: a first look at incoming dealership messages and documents *before* they go anywhere else. It screens each message for personal data, then classifies category, urgency, and the desk that should see it — sales, service, F&I, legal, billing, or the BDC.

This is a **portfolio demo**, not production software and not a certified DLP or air-gap product. Detection is regex plus checksums, not a commercial DLP engine. The optional language model is a **1.5B parameter Q4 GGUF** that runs on this machine's **CPU**. In production this node would typically use **one GPU**. Sample messages belong to the fictional **Lakeside Auto Group (sample)**. Tests and CI run without the model.

Built for **Daniel McBrearty** as part of a Forward Deployed Engineer / solutions engineer portfolio.

## Why this matters for FDE work

A dealer group will often say: *we like the assistant, but those messages cannot leave the store.* Credit applications, a photocopy of a driver's license, a customer texting a card number to hold a car — that is the same instinct as not leaving a deal jacket on the desk overnight.

One pattern that comes up in those conversations is a **local triage node**. A small quantized model (and, next to it, boring deterministic checks) lives on a box at the dealership. It does the night-shift BDC work: is there an SSN or a card number in this message? Is this a sales lead, a tow, or something legal needs to see first? Only then, if the policy allows it, would a larger or hosted model ever get involved.

An FDE is often the person who has to make that promise testable. This demo is built so you can:

- show PII screening that does not depend on "the model thought so" (Luhn for cards, ABA weights for routing numbers, ISO 3779 for VINs)
- mask those values before the local model sees the text, so the same habit still applies if a cloud model is added later
- measure accuracy and latency on a labeled sample inbox
- flip a **network guard** and prove an outbound socket to Hugging Face is refused while triage still runs

## Quick start

You need Python 3.10+ (3.13 is fine). No account, no cloud key. The first run does **not** require the GGUF; it starts in rules-only mode.

```bash
git clone https://github.com/DanMcB1/ai-local-triage-node.git && cd ai-local-triage-node
./run.sh
```

Then open [http://127.0.0.1:8518](http://127.0.0.1:8518).

To enable the local 1.5B Q4 model (free, one-time, ~1.04 GB, checksum-verified, **not** committed to git):

```bash
./download_model.sh
./run.sh
```

`download_model.sh` fetches [`qwen2.5-1.5b-instruct-q4_k_m.gguf`](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) and checks a pinned SHA-256. It also installs `llama-cpp-python` from the project's CPU wheel index, so you do not need a C++ compiler.

Useful one-liners, once the virtualenv exists:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m triage once --id svc-brakes --backend hybrid
.venv/bin/python -m triage once --id fi-credit-app --backend rules
.venv/bin/python -m triage eval --backend rules --out examples/eval-report.md
.venv/bin/python -m triage prove-offline
```

## What's on the screen

- An honest banner that this is a demo, not certified DLP, and that the model (when present) runs on CPU
- **Inbox** — the labeled Lakeside sample messages, or a message you paste. PII is highlighted. You see category, urgency, route, latency, and the rules scores
- **Scorecard** — accuracy, PII precision/recall, latency p50/p95, and throughput against the labeled set
- **Offline proof** — one button tries `huggingface.co` and should be refused; another button still triages a stranded-car message locally
- A sidebar for hybrid / rules / model, the network guard, and hardware (CPU cores, no GPU)

## How it works

1. **Detect PII.** `triage/pii.py` is regex plus checksums. Formatted SSNs are flagged; a bare 9-digit stock number is not, unless it is labeled `SSN:`. Cards must pass Luhn. Routing numbers must pass the ABA weights. VINs must pass the ISO 3779 check digit. Names, driver's licenses, dates of birth, and bank accounts are labeled heuristics. This will miss some values. That limitation is documented on purpose.
2. **Mask.** Findings are replaced with tokens such as `[SSN]` and `[CREDIT_CARD]` before the local model sees the text.
3. **Classify.** Rules in `triage/rules.py` score department keywords and urgency patterns. They are deterministic and are what CI runs.
4. **Hybrid.** If the rules are confident, they stand. If two departments both score strongly, or the winner is weak, the local GGUF is asked for a JSON decision (constrained by a grammar). If the model is missing or fails, the engine falls back to rules.
5. **Network guard.** `triage/network.py` patches outbound `socket` connections and refuses anything that is not loopback. Streamlit on `127.0.0.1` still works.

The default UI port is **8518** (`TRIAGE_UI_PORT` overrides it).

## The model

| | |
| --- | --- |
| Weights | [Qwen2.5-1.5B-Instruct Q4_K_M GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) |
| Size | 1,117,320,736 bytes (~1.04 GB) |
| Runtime | `llama-cpp-python`, `n_gpu_layers=0` |
| Hardware in this demo | CPU only |

The weights are downloaded by a script and **gitignored**. Please do not commit them.

On the 8-core Intel Xeon (no GPU) that produced [`examples/eval-report.md`](examples/eval-report.md):

| Backend | Category | Urgency | Route | Exact | Latency p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rules only | 97.5% | 100% | 97.5% | 97.5% | 0.18 ms |
| Hybrid (36 rules + 4 model) | 100% | 95.0% | 97.5% | 92.5% | 0.21 ms (p95 3.6 s) |
| Local GGUF on every message | 72.5% | 35.0% | 72.5% | 12.5% | 3.2 s (p95 26 s) |

PII type detection was **F1 1.000** on this planted set (that will not hold on messy real mail). The local model generated at about **14.4 tokens/sec** on CPU, or roughly 8 messages/min if you force it on every message. Hybrid is the recommended path: rules handle the obvious cases instantly, and the model is reserved for close calls — it correctly tagged a trade-in with the check engine light on as sales, which the rules had called service. The 1.5B model is **not** accurate enough to be the only classifier, especially for urgency. A production node with one GPU would be much faster; I would still keep the checksums and the hybrid split.

## What's intentionally not here

- No paid API, no cloud inference, no telemetry
- No claim of GLBA, PCI, or HIPAA compliance
- No kernel-level air gap (the guard is a user-space socket patch)
- No fine-tuning and no 7B/70B model
- No production identity, audit SIEM, or case-management system

## Tests

```bash
python -m unittest discover -s tests
```

The suite covers Luhn / ABA / VIN checks, the "bare 9-digit number is not an SSN" rule, rules classifications, hybrid fallback when the model is missing, the labeled-set scorecard, and the network guard (including "triage still works while outbound sockets are refused"). CI installs only `requirements.txt` and does not download the GGUF.

## License

MIT. Copyright (c) 2026 Daniel McBrearty.
