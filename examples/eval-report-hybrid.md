# Local Quantized Triage Node — sample scorecard

Backend: **hybrid**. Labeled messages: **40**.
This is a portfolio demo set, not a customer evaluation.

## Accuracy

- Category: **100.0%**
- Urgency: **95.0%**
- Route: **97.5%**
- Exact (category + urgency + route): **92.5%**
- PII type detection: precision **100.0%**, recall **100.0%**, F1 **1.000** (40/40 expected types found).

## Speed

- Latency p50: **0.21 ms**; p95: **3552 ms**
- Throughput on this run: **122.98 messages/min**
- Local model generation: **14.5 tokens/sec** on CPU

## Hardware

- CPU: Intel(R) Xeon(R) Processor (8 cores)
- RAM: 15.6 GiB
- GPU: None detected. This demo runs on CPU. In production this node would typically use one GPU.
- Model ready: True (Qwen2.5-1.5B-Instruct Q4_K_M)
- Backends used: {'rules': 36, 'model': 4}

## Misses (vs. the labels in this demo set)

- `amb-trade-cel` urgency: expected `high`, got `normal` (ambiguous on purpose)

- `neg-bare-nine` route: expected `bdc`, got `sales_manager`

- `svc-vin-only` urgency: expected `low`, got `normal`

