# Local Quantized Triage Node — sample scorecard

Measured on 24 November 2026, America/New_York, on an 8-core Intel Xeon with **no GPU**. The labeled set is 40 fictional Lakeside Auto Group messages. This is a portfolio demo set, not a customer evaluation.

PII screening is always the deterministic detectors (regex plus Luhn, ABA, and ISO 3779). It scored **precision 100%, recall 100%, F1 1.000** (40/40 expected types) on every backend below. That number will not hold on messy real mail; it means the detectors match the labels we planted.

The optional model is **Qwen2.5-1.5B-Instruct Q4_K_M** (`qwen2.5-1.5b-instruct-q4_k_m.gguf`, 1,117,320,736 bytes), loaded with `llama-cpp-python` and `n_gpu_layers=0`. Generation on this CPU was about **14.4–14.5 tokens/sec**. Load time on a warm start was about 1.1 seconds. In production this node would typically use one GPU.

## Comparison

| Backend | Category | Urgency | Route | Exact match | Latency p50 | Latency p95 | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Rules only | 97.5% | 100% | 97.5% | 97.5% | 0.18 ms | 0.48 ms | Instant. The only miss is the deliberate close call `amb-trade-cel`. |
| Hybrid | 100% | 95.0% | 97.5% | 92.5% | 0.21 ms | 3.6 s | Used rules on 36 messages and the local model on 4 close calls. |
| Local GGUF on every message | 72.5% | 35.0% | 72.5% | 12.5% | 3.2 s | 26 s | About 14.4 tok/s and 7.9 messages/min on this CPU. |

The recommended path is **hybrid**. The 1.5B model is useful on a close call — it correctly tagged a trade-in with the check engine light on as **sales**, which the rules had called **service**. It is not good enough to be the only classifier, especially for urgency. That is an intentional, measured result, not a surprise.

## How to reproduce

```bash
.venv/bin/python -m triage eval --backend rules --out examples/eval-report-rules.md
.venv/bin/python -m triage eval --backend hybrid --out examples/eval-report-hybrid.md
.venv/bin/python -m triage eval --backend model --out examples/eval-report-model.md
```

The last command takes several minutes on CPU. Raw reports from this run are in the same folder.

## Hardware (this run)

- CPU: Intel(R) Xeon(R) Processor (8 cores)
- RAM: 15.6 GiB
- GPU: None detected. This demo runs on CPU. In production this node would typically use one GPU.
- Platform: Linux x86_64
