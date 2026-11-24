"""Tests for the labeled-set scorecard and the sample inbox itself."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from triage.eval import evaluate, markdown_report
from triage.pii import detect
from triage.samples import all_samples
from triage.settings import CATEGORIES, ROUTES, URGENCIES


class SampleInboxTests(unittest.TestCase):
    def test_unique_ids_and_allowed_labels(self) -> None:
        samples = all_samples()
        ids = [s.id for s in samples]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(samples), 30)
        cats = {s.category for s in samples}
        self.assertEqual(cats, set(CATEGORIES))
        for sample in samples:
            self.assertIn(sample.urgency, URGENCIES)
            self.assertIn(sample.route, ROUTES)

    def test_expected_pii_types_are_present_in_the_text(self) -> None:
        for sample in all_samples():
            found = {item.pii_type for item in detect(sample.text())}
            missing = set(sample.pii_types) - found
            self.assertFalse(
                missing,
                msg=f"{sample.id} expected {sample.pii_types} but detector found {found}",
            )

    def test_negative_cases_do_not_claim_invalid_pii(self) -> None:
        for sample_id, banned in (
            ("neg-bad-card", "credit_card"),
            ("neg-bad-vin", "vin"),
            ("neg-bare-nine", "ssn"),
            ("sales-stock", "ssn"),
        ):
            sample = next(s for s in all_samples() if s.id == sample_id)
            found = {item.pii_type for item in detect(sample.text())}
            self.assertNotIn(banned, found, msg=sample_id)
            self.assertNotIn(banned, sample.pii_types)


class EvalTests(unittest.TestCase):
    def test_rules_scorecard_is_strong_on_this_demo_set(self) -> None:
        report = evaluate(backend="rules")
        self.assertEqual(report.n, len(all_samples()))
        self.assertGreaterEqual(report.category_accuracy, 0.9)
        self.assertGreaterEqual(report.urgency_accuracy, 0.9)
        self.assertGreaterEqual(report.route_accuracy, 0.9)
        self.assertEqual(report.pii["precision"], 1.0)
        self.assertEqual(report.pii["recall"], 1.0)
        self.assertEqual(report.used_backends, {"rules": report.n})
        md = markdown_report(report)
        self.assertIn("sample scorecard", md)
        self.assertIn("not a customer evaluation", md)

    def test_eval_with_model_backend_uses_the_fallback_when_mocked(self) -> None:
        with patch(
            "triage.engine.model_mod.classify",
            side_effect=RuntimeError("no weights in CI"),
        ):
            report = evaluate(backend="model")
        self.assertEqual(report.used_backends, {"rules": report.n})
        self.assertGreaterEqual(report.category_accuracy, 0.9)


class CliSmokeTests(unittest.TestCase):
    def test_once_and_prove_offline_cli(self) -> None:
        from io import StringIO
        from unittest.mock import patch as _patch

        from triage.__main__ import main
        from triage.network import GUARD

        self.addCleanup(lambda: (GUARD.disable(), GUARD.restore()))
        buf = StringIO()
        with _patch("sys.stdout", buf):
            self.assertEqual(main(["once", "--id", "svc-brakes", "--backend", "rules"]), 0)
            self.assertEqual(main(["list"]), 0)
            self.assertEqual(main(["hardware"]), 0)
            self.assertEqual(main(["prove-offline"]), 0)

    def test_once_json_contains_findings(self) -> None:
        from io import StringIO
        from unittest.mock import patch as _patch

        from triage.__main__ import main

        buf = StringIO()
        with _patch("sys.stdout", buf):
            rc = main(["once", "--id", "fi-run-credit", "--backend", "rules", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["category"], "fi")
        self.assertTrue(any(item["pii_type"] == "ssn" for item in payload["pii"]))


if __name__ == "__main__":
    unittest.main()
