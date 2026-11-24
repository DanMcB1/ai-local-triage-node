"""Tests for the triage pipeline, including model fallback."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from triage.engine import triage
from triage.model import ModelDecision
from triage.samples import get_sample


def _fake_model(**overrides) -> ModelDecision:
    data = dict(
        category="sales",
        urgency="high",
        route="sales_manager",
        reason="Mocked local model decision.",
        latency_ms=12,
        prompt_tokens=80,
        completion_tokens=20,
        tokens_per_second=40.0,
        model_name="mock-model",
        raw='{"category":"sales","urgency":"high","route":"sales_manager","reason":"Mocked local model decision."}',
    )
    data.update(overrides)
    return ModelDecision(**data)


class EngineTests(unittest.TestCase):
    def test_rules_backend_never_calls_model(self) -> None:
        with patch("triage.engine.model_mod.classify") as classify:
            result = triage(get_sample("svc-brakes").text(), backend="rules")
        classify.assert_not_called()
        self.assertEqual(result.used_backend, "rules")
        self.assertEqual(result.category, "service")
        self.assertEqual(result.urgency, "high")

    def test_pii_is_masked_before_the_model_sees_it(self) -> None:
        captured: list[str] = []

        def fake(text: str) -> ModelDecision:
            captured.append(text)
            return _fake_model(category="fi", route="fi_manager")

        with patch("triage.engine.model_mod.classify", side_effect=fake):
            result = triage(get_sample("fi-run-credit").text(), backend="model")
        self.assertTrue(captured)
        self.assertNotIn("219-09-9999", captured[0])
        self.assertIn("[SSN]", captured[0])
        self.assertTrue(any(item["pii_type"] == "ssn" for item in result.pii))
        self.assertIn("[SSN]", result.masked_text)

    def test_model_failure_falls_back_to_rules(self) -> None:
        with patch(
            "triage.engine.model_mod.classify",
            side_effect=RuntimeError("weights missing"),
        ):
            result = triage(get_sample("svc-stranded").text(), backend="model")
        self.assertEqual(result.used_backend, "rules")
        self.assertEqual(result.category, "service")
        self.assertIn("weights missing", result.fallback_reason or "")
        self.assertIn("Fell back to rules", result.reason)

    def test_hybrid_uses_rules_when_confident(self) -> None:
        with patch("triage.engine.model_mod.classify") as classify:
            result = triage(get_sample("legal-lemon").text(), backend="hybrid")
        classify.assert_not_called()
        self.assertEqual(result.used_backend, "rules")
        self.assertEqual(result.category, "legal")
        self.assertIn("confident", result.reason.lower())

    def test_hybrid_calls_model_when_rules_are_not_confident(self) -> None:
        with patch(
            "triage.engine.model_mod.classify",
            return_value=_fake_model(category="sales", route="sales_manager", urgency="high"),
        ) as classify:
            result = triage(get_sample("amb-trade-cel").text(), backend="hybrid")
        classify.assert_called_once()
        self.assertEqual(result.used_backend, "model")
        self.assertEqual(result.category, "sales")
        self.assertEqual(result.route, "sales_manager")

    def test_unknown_backend_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            triage("hello", backend="cloud")

    def test_hardware_and_latency_are_present(self) -> None:
        result = triage("What are your Saturday hours?", backend="rules")
        self.assertIn("cpu", result.hardware)
        self.assertIn("GPU", result.hardware["gpu"] or "")
        self.assertGreaterEqual(result.latency_ms, 0)


if __name__ == "__main__":
    unittest.main()
