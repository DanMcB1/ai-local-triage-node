"""Tests for the deterministic triage rules."""

from __future__ import annotations

import unittest

from triage.rules import classify
from triage.samples import get_sample


class RulesTests(unittest.TestCase):
    def test_stranded_car_is_critical_service(self) -> None:
        decision = classify(get_sample("svc-stranded").text())
        self.assertEqual(decision.category, "service")
        self.assertEqual(decision.urgency, "critical")
        self.assertEqual(decision.route, "service_advisor")
        self.assertTrue(decision.confident)

    def test_credit_application_is_high_fi(self) -> None:
        decision = classify(get_sample("fi-credit-app").text())
        self.assertEqual(decision.category, "fi")
        self.assertEqual(decision.urgency, "high")
        self.assertEqual(decision.route, "fi_manager")

    def test_lemon_law_is_critical_legal(self) -> None:
        decision = classify(get_sample("legal-lemon").text())
        self.assertEqual(decision.category, "legal")
        self.assertEqual(decision.urgency, "critical")
        self.assertEqual(decision.route, "legal_compliance")

    def test_hours_question_is_low_general_bdc(self) -> None:
        decision = classify(get_sample("gen-hours").text())
        self.assertEqual(decision.category, "general")
        self.assertEqual(decision.urgency, "low")
        self.assertEqual(decision.route, "bdc")

    def test_lawyer_request_beats_credit_application_mention(self) -> None:
        decision = classify(get_sample("legal-lawyer").text())
        self.assertEqual(decision.category, "legal")
        self.assertEqual(decision.route, "legal_compliance")

    def test_overcharge_is_billing_even_if_product_is_gap(self) -> None:
        decision = classify(get_sample("bill-gap-cancel").text())
        self.assertEqual(decision.category, "billing")
        self.assertEqual(decision.route, "controller")
        self.assertTrue(decision.confident)

    def test_test_drive_web_lead_goes_to_bdc(self) -> None:
        decision = classify(get_sample("sales-testdrive").text())
        self.assertEqual(decision.category, "sales")
        self.assertEqual(decision.route, "bdc")

    def test_buyers_order_goes_to_sales_manager(self) -> None:
        decision = classify(get_sample("sales-buyers-order").text())
        self.assertEqual(decision.category, "sales")
        self.assertEqual(decision.route, "sales_manager")
        self.assertEqual(decision.urgency, "high")

    def test_trade_in_with_check_engine_is_not_confident(self) -> None:
        decision = classify(get_sample("amb-trade-cel").text())
        self.assertFalse(decision.confident)
        self.assertGreaterEqual(decision.scores["sales"], 4)
        self.assertGreaterEqual(decision.scores["service"], 4)

    def test_empty_message_is_general(self) -> None:
        decision = classify("Hello there.")
        self.assertEqual(decision.category, "general")
        self.assertFalse(decision.confident)


if __name__ == "__main__":
    unittest.main()
