"""Tests for deterministic PII detectors."""

from __future__ import annotations

import unittest

from triage.pii import aba_routing_ok, detect, luhn_ok, mask, vin_ok


class LuhnTests(unittest.TestCase):
    def test_known_test_cards_pass(self) -> None:
        self.assertTrue(luhn_ok("4111111111111111"))
        self.assertTrue(luhn_ok("4111-1111-1111-1111"))
        self.assertTrue(luhn_ok("5555555555554444"))
        self.assertTrue(luhn_ok("378282246310005"))

    def test_invalid_checksum_fails(self) -> None:
        self.assertFalse(luhn_ok("4111111111111112"))
        self.assertFalse(luhn_ok("1234567890123"))


class VinAndAbaTests(unittest.TestCase):
    def test_demo_vins_pass(self) -> None:
        self.assertTrue(vin_ok("1LKSDM267MCB00001"))
        self.assertTrue(vin_ok("1LKSCRV55MC000101"))
        self.assertTrue(vin_ok("1LKSCVD5XPA000505"))

    def test_invalid_check_digit_fails(self) -> None:
        self.assertFalse(vin_ok("1HGCV2F36KA123456"))
        self.assertFalse(vin_ok("1LKSDM26XMCB00001"))

    def test_letters_ioq_rejected(self) -> None:
        self.assertFalse(vin_ok("1LKSDM26IMCB00001"))

    def test_all_numeric_run_is_not_a_vin(self) -> None:
        # All nines passes the ISO 3779 check digit but is not a real VIN.
        self.assertFalse(vin_ok("99999999999999999"))
        self.assertTrue(vin_ok("1HGCM82633A004352"))

    def test_aba_known_samples(self) -> None:
        self.assertTrue(aba_routing_ok("267084005"))
        self.assertTrue(aba_routing_ok("021000021"))
        self.assertFalse(aba_routing_ok("267084006"))
        self.assertFalse(aba_routing_ok("12345"))


class DetectTests(unittest.TestCase):
    def test_formatted_ssn_and_labeled_bare_ssn(self) -> None:
        text = "SSN: 219-09-9999 and also SSN: 219099999"
        types = [f.pii_type for f in detect(text)]
        self.assertEqual(types.count("ssn"), 2)

    def test_bare_nine_digits_are_not_ssns(self) -> None:
        text = "Please look up stock number 123456789 on the Civic."
        self.assertEqual(detect(text), [])

    def test_luhn_failure_is_not_a_card(self) -> None:
        text = "The typo card was 4111-1111-1111-1112."
        self.assertFalse(any(f.pii_type == "credit_card" for f in detect(text)))

    def test_labeled_failed_luhn_is_still_a_card(self) -> None:
        # Same rule as the PII unmasking proxy: a label makes the typo a card,
        # so it is masked instead of leaking.
        text = "card: 4111 1111 1111 1112"
        findings = detect(text)
        self.assertEqual([f.pii_type for f in findings], ["credit_card"])
        self.assertEqual(findings[0].value, "4111 1111 1111 1112")
        self.assertEqual(findings[0].check, "labeled")
        self.assertEqual(mask(text), "card: [CREDIT_CARD]")
        self.assertNotIn("4111", mask(text))

    def test_valid_card_is_found(self) -> None:
        text = "Deposit on Visa 4111-1111-1111-1111."
        findings = detect(text)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].pii_type, "credit_card")
        self.assertEqual(findings[0].check, "luhn")

    def test_phone_email_name(self) -> None:
        text = "Customer: Maya Elena Alvarez\nPhone: (207) 555-0148\nEmail: maya.alvarez@example.com"
        types = {f.pii_type for f in detect(text)}
        self.assertEqual(types, {"name", "phone", "email"})

    def test_vin_routing_account_dl_dob(self) -> None:
        text = (
            "VIN: 1LKSCRV55MC000101\n"
            "Routing number: 267084005\n"
            "Account number: 1002003344\n"
            "Driver's license: PA2671843\n"
            "Date of birth: 03/14/1988\n"
        )
        types = {f.pii_type for f in detect(text)}
        self.assertEqual(
            types,
            {"vin", "routing_number", "bank_account", "drivers_license", "dob"},
        )

    def test_invalid_vin_not_flagged(self) -> None:
        text = "Is VIN 1HGCV2F36KA123456 on the lot?"
        self.assertFalse(any(f.pii_type == "vin" for f in detect(text)))

    def test_numeric_17_digit_run_is_not_a_vin(self) -> None:
        nines = "99999999999999999"
        unlabeled = f"The reference number is {nines} today"
        types = {f.pii_type for f in detect(unlabeled)}
        self.assertNotIn("vin", types)
        self.assertNotIn("phone", types)
        self.assertNotIn("bank_account", types)
        self.assertNotIn("credit_card", types)

        real = "VIN 1HGCM82633A004352 is on the lot"
        vins = [f.value for f in detect(real) if f.pii_type == "vin"]
        self.assertEqual(vins, ["1HGCM82633A004352"])

        # Luhn-valid 17-digit numeric runs are cards, not VINs.
        luhn_ok_17 = "99999999999999996"
        findings = detect(f"Charge {luhn_ok_17} today")
        self.assertEqual([f.pii_type for f in findings], ["credit_card"])

        # After a card label, a 17-digit run that fails Luhn is still a card.
        labeled = f"Card number {nines} for a deposit"
        findings = detect(labeled)
        self.assertEqual([f.pii_type for f in findings], ["credit_card"])
        self.assertEqual(mask(labeled), "Card number [CREDIT_CARD] for a deposit")

        # After an account label, the same failed-Luhn run stays untagged.
        account = f"Account number: {nines}"
        self.assertEqual(detect(account), [])

    def test_invalid_routing_not_flagged(self) -> None:
        text = "Routing number: 267084006"
        self.assertFalse(any(f.pii_type == "routing_number" for f in detect(text)))

    def test_overlap_prefers_card_over_random_digits(self) -> None:
        text = "Visa 4111-1111-1111-1111"
        findings = detect(text)
        self.assertEqual([f.pii_type for f in findings], ["credit_card"])

    def test_mask_replaces_with_type_tokens(self) -> None:
        text = "Call (207) 555-0148 or maya.alvarez@example.com"
        masked = mask(text)
        self.assertNotIn("555-0148", masked)
        self.assertNotIn("maya.alvarez@example.com", masked)
        self.assertIn("[PHONE]", masked)
        self.assertIn("[EMAIL]", masked)

    def test_unlabeled_account_like_digits_not_flagged(self) -> None:
        text = "Repair order 7781 was opened against invoice 44012 today."
        types = {f.pii_type for f in detect(text)}
        self.assertTrue(types <= set(), msg=types)


if __name__ == "__main__":
    unittest.main()
