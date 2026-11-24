# Local Quantized Triage Node — sample scorecard

Backend: **rules**. Labeled messages: **40**.
This is a portfolio demo set, not a customer evaluation.

## Accuracy

- Category: **97.5%**
- Urgency: **100.0%**
- Route: **97.5%**
- Exact (category + urgency + route): **97.5%**
- PII type detection: precision **100.0%**, recall **100.0%**, F1 **1.000** (40/40 expected types found).

## Speed

- Latency p50: **0.18 ms**; p95: **0.48 ms**
- Throughput on this run: **128969.62 messages/min**

## Hardware

- CPU: Intel(R) Xeon(R) Processor (8 cores)
- RAM: 15.6 GiB
- GPU: None detected. This demo runs on CPU. In production this node would typically use one GPU.
- Model ready: True (Qwen2.5-1.5B-Instruct Q4_K_M)
- Backends used: {'rules': 40}

## Misses (vs. the labels in this demo set)

- `amb-trade-cel` category: expected `sales`, got `service` (ambiguous on purpose)

- `amb-trade-cel` route: expected `sales_manager`, got `service_advisor` (ambiguous on purpose)

