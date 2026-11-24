# Local Quantized Triage Node — sample scorecard

Backend: **model**. Labeled messages: **40**.
This is a portfolio demo set, not a customer evaluation.

## Accuracy

- Category: **72.5%**
- Urgency: **35.0%**
- Route: **72.5%**
- Exact (category + urgency + route): **12.5%**
- PII type detection: precision **100.0%**, recall **100.0%**, F1 **1.000** (40/40 expected types found).

## Speed

- Latency p50: **3232 ms**; p95: **25925 ms**
- Throughput on this run: **7.88 messages/min**
- Local model generation: **14.4 tokens/sec** on CPU

## Hardware

- CPU: Intel(R) Xeon(R) Processor (8 cores)
- RAM: 15.6 GiB
- GPU: None detected. This demo runs on CPU. In production this node would typically use one GPU.
- Model ready: True (Qwen2.5-1.5B-Instruct Q4_K_M)
- Backends used: {'model': 40}

## Misses (vs. the labels in this demo set)

- `svc-brakes` urgency: expected `high`, got `critical`

- `svc-stranded` route: expected `service_advisor`, got `sales_manager`

- `svc-oil` urgency: expected `low`, got `normal`

- `svc-recall` urgency: expected `normal`, got `critical`

- `svc-ro` category: expected `service`, got `sales`

- `svc-ro` urgency: expected `high`, got `critical`

- `svc-warranty` category: expected `service`, got `fi`

- `svc-warranty` urgency: expected `normal`, got `critical`

- `svc-warranty` route: expected `service_advisor`, got `fi_manager`

- `svc-cel` urgency: expected `high`, got `normal`

- `svc-overheat` category: expected `service`, got `fi`

- `sales-testdrive` route: expected `bdc`, got `sales_manager`

- `sales-lease` urgency: expected `high`, got `critical`

- `sales-trade` urgency: expected `low`, got `normal`

- `sales-stock` route: expected `bdc`, got `sales_manager`

- `sales-buyers-order` urgency: expected `high`, got `normal`

- `sales-hold-card` urgency: expected `high`, got `critical`

- `fi-credit-app` urgency: expected `high`, got `critical`

- `fi-credit-app` route: expected `fi_manager`, got `controller`

- `fi-gap` category: expected `fi`, got `sales` (ambiguous on purpose)

- `fi-gap` route: expected `fi_manager`, got `sales_manager` (ambiguous on purpose)

- `fi-run-credit` category: expected `fi`, got `billing`

- `fi-run-credit` urgency: expected `high`, got `normal`

- `fi-run-credit` route: expected `fi_manager`, got `controller`

- `fi-ssn-labeled-bare` category: expected `fi`, got `billing`

- `fi-ssn-labeled-bare` urgency: expected `high`, got `normal`

- `fi-ssn-labeled-bare` route: expected `fi_manager`, got `bdc`

- `legal-lemon` category: expected `legal`, got `fi`

- `legal-lawyer` urgency: expected `high`, got `critical` (ambiguous on purpose)

- `legal-bbb` category: expected `legal`, got `fi` (ambiguous on purpose)

- `legal-bbb` urgency: expected `high`, got `critical` (ambiguous on purpose)

- `legal-lawsuit` category: expected `legal`, got `fi`

- `legal-accident` category: expected `legal`, got `fi` (ambiguous on purpose)

- `legal-accident` urgency: expected `high`, got `critical` (ambiguous on purpose)

- `bill-double` urgency: expected `high`, got `critical`

- `bill-appearance` urgency: expected `normal`, got `critical`

- `bill-refund` urgency: expected `normal`, got `critical`

- `bill-gap-cancel` urgency: expected `high`, got `critical` (ambiguous on purpose)

- `gen-hours` urgency: expected `low`, got `normal`

- `gen-directions` urgency: expected `low`, got `normal`

- `amb-trade-cel` urgency: expected `high`, got `normal` (ambiguous on purpose)

- `neg-bad-card` category: expected `sales`, got `billing` (ambiguous on purpose)

- `neg-bad-card` urgency: expected `high`, got `normal` (ambiguous on purpose)

- `neg-bad-card` route: expected `sales_manager`, got `bdc` (ambiguous on purpose)

- `neg-bad-vin` route: expected `bdc`, got `sales_manager`

- `neg-bare-nine` route: expected `bdc`, got `sales_manager`

- `svc-vin-only` urgency: expected `low`, got `normal`

- `sales-mc-deposit` urgency: expected `high`, got `normal`

