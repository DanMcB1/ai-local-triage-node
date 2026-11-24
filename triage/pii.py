"""Deterministic PII detectors for dealership messages.

Regex plus checksums (Luhn for cards, ABA weights for routing numbers,
ISO 3779 for VINs). This is not a certified DLP product and will miss
some values. Bare 9-digit numbers are not treated as SSNs unless a label
is next to them. Names and bank accounts are labeled heuristics.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

PRIORITY = {
    "credit_card": 100,
    "ssn": 90,
    "routing_number": 80,
    "vin": 80,
    "bank_account": 70,
    "email": 70,
    "phone": 60,
    "drivers_license": 55,
    "dob": 50,
    "name": 40,
}

PII_LABELS = {
    "ssn": "SSN",
    "credit_card": "CREDIT_CARD",
    "phone": "PHONE",
    "email": "EMAIL",
    "dob": "DOB",
    "drivers_license": "DL",
    "vin": "VIN",
    "routing_number": "ROUTING",
    "bank_account": "ACCOUNT",
    "name": "NAME",
}


@dataclass(frozen=True)
class Finding:
    pii_type: str
    value: str
    start: int
    end: int
    normalized: str
    check: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def luhn_ok(number: str) -> bool:
    """Return True if the digit string passes the Luhn checksum."""
    digits = re.sub(r"\D", "", number)
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def aba_routing_ok(number: str) -> bool:
    """Return True if a 9-digit ABA routing number has a valid checksum."""
    digits = re.sub(r"\D", "", number)
    if len(digits) != 9 or not digits.isdigit():
        return False
    weights = (3, 7, 1, 3, 7, 1, 3, 7, 1)
    total = sum(int(d) * w for d, w in zip(digits, weights))
    return total % 10 == 0


_VIN_MAP = {
    **{str(i): i for i in range(10)},
    **dict(
        zip(
            "ABCDEFGHJKLMNPRSTUVWXYZ",
            [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5, 6, 7, 8, 9],
        )
    ),
}
_VIN_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)


def vin_ok(vin: str) -> bool:
    """Return True if a 17-character VIN has a valid ISO 3779 check digit."""
    vin = re.sub(r"[\s-]+", "", vin).upper()
    if len(vin) != 17:
        return False
    if any(ch in "IOQ" for ch in vin):
        return False
    if any(ch not in _VIN_MAP for ch in vin):
        return False
    total = 0
    for i, ch in enumerate(vin):
        if i == 8:
            continue
        total += _VIN_MAP[ch] * _VIN_WEIGHTS[i]
    remainder = total % 11
    expected = "X" if remainder == 10 else str(remainder)
    return vin[8] == expected


def _normalize(pii_type: str, value: str) -> str:
    if pii_type in {"ssn", "credit_card", "phone", "routing_number", "bank_account"}:
        return re.sub(r"\D", "", value)
    if pii_type == "email":
        return value.strip().lower()
    if pii_type in {"vin", "drivers_license"}:
        return re.sub(r"[\s-]+", "", value).upper()
    if pii_type == "dob":
        return re.sub(r"\s+", "", value)
    if pii_type == "name":
        return re.sub(r"\s+", " ", value).strip()
    return value.strip()


def _finding(pii_type: str, match: re.Match, group: int = 1, check: str = "") -> Finding:
    raw = match.group(group)
    return Finding(
        pii_type=pii_type,
        value=raw,
        start=match.start(group),
        end=match.end(group),
        normalized=_normalize(pii_type, raw),
        check=check,
    )


def _ssns(text: str) -> list[Finding]:
    out: list[Finding] = []
    for match in re.finditer(r"\b(\d{3}-\d{2}-\d{4})\b", text):
        out.append(_finding("ssn", match, check="format"))
    for match in re.finditer(
        r"(?i)\b(?:ssn|social\s*security(?:\s*number)?|ss#)\s*[:#]?\s*(\d{9})\b",
        text,
    ):
        out.append(_finding("ssn", match, check="labeled"))
    return out


def _cards(text: str) -> list[Finding]:
    out: list[Finding] = []
    # 13–19 digits, optional spaces or dashes in groups.
    pattern = re.compile(
        r"(?<!\d)(\d(?:[ -]?\d){12,18})(?!\d)"
    )
    for match in pattern.finditer(text):
        raw = match.group(1)
        digits = re.sub(r"\D", "", raw)
        # Skip things that look like a formatted SSN or a 9-digit id.
        if len(digits) < 13:
            continue
        if not luhn_ok(digits):
            continue
        out.append(
            Finding(
                pii_type="credit_card",
                value=raw,
                start=match.start(1),
                end=match.end(1),
                normalized=digits,
                check="luhn",
            )
        )
    return out


def _phones(text: str) -> list[Finding]:
    out: list[Finding] = []
    pattern = re.compile(
        r"(?<!\d)(?:\+?1[\s.-]*)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]*\d{4}(?!\d)"
    )
    for match in pattern.finditer(text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if digits.startswith("1") and len(digits) == 11:
            national = digits[1:]
        else:
            national = digits
        if len(national) != 10:
            continue
        # Avoid treating long numeric ids as phones; require a separator
        # or parentheses so a bare 10-digit stock number is not flagged.
        if not re.search(r"[()\s.-]", raw):
            continue
        out.append(
            Finding(
                pii_type="phone",
                value=raw.strip(),
                start=match.start(),
                end=match.end(),
                normalized=national,
                check="format",
            )
        )
    return out


def _emails(text: str) -> list[Finding]:
    out: list[Finding] = []
    pattern = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
    for match in pattern.finditer(text):
        out.append(
            Finding(
                pii_type="email",
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                normalized=match.group(0).lower(),
                check="format",
            )
        )
    return out


def _dobs(text: str) -> list[Finding]:
    out: list[Finding] = []
    labeled = re.compile(
        r"(?i)\b(?:dob|date\s*of\s*birth|birth(?:day)?\s*date|born)\s*[:#]?\s*"
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    )
    for match in labeled.finditer(text):
        out.append(_finding("dob", match, check="labeled"))
    return out


def _licenses(text: str) -> list[Finding]:
    out: list[Finding] = []
    pattern = re.compile(
        r"(?i)\b(?:driver'?s?\s*license|dl(?:\s*(?:number|#|no))?|license\s*(?:#|no|number))\s*[:#]?\s*"
        r"([A-Z0-9][A-Z0-9-]{4,14})\b"
    )
    for match in pattern.finditer(text):
        out.append(_finding("drivers_license", match, check="labeled"))
    return out


def _vins(text: str) -> list[Finding]:
    out: list[Finding] = []
    pattern = re.compile(r"\b([A-HJ-NPR-Z0-9]{17})\b", re.I)
    for match in pattern.finditer(text):
        raw = match.group(1)
        if not vin_ok(raw):
            continue
        out.append(_finding("vin", match, check="iso3779"))
    return out


def _routing(text: str) -> list[Finding]:
    out: list[Finding] = []
    pattern = re.compile(
        r"(?i)\b(?:routing(?:\s*number)?|aba(?:\s*routing)?|rtn)\s*[:#]?\s*(\d{9})\b"
    )
    for match in pattern.finditer(text):
        raw = match.group(1)
        if not aba_routing_ok(raw):
            continue
        out.append(_finding("routing_number", match, check="aba"))
    return out


def _accounts(text: str) -> list[Finding]:
    out: list[Finding] = []
    pattern = re.compile(
        r"(?i)\b(?:account(?:\s*number)?|acct(?:\s*(?:#|no|number))?|bank\s*account)\s*[:#]?\s*"
        r"(\d{6,17})\b"
    )
    for match in pattern.finditer(text):
        out.append(_finding("bank_account", match, check="labeled"))
    return out


def _names(text: str) -> list[Finding]:
    out: list[Finding] = []
    pattern = re.compile(
        r"(?i)\b(?:applicant(?:\s*name)?|customer(?:\s*name)?|buyer(?:\s*name)?|"
        r"borrower(?:\s*name)?|from)\s*[:#]\s*"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
    )
    for match in pattern.finditer(text):
        out.append(_finding("name", match, check="labeled"))
    return out


def _overlaps(a: Finding, b: Finding) -> bool:
    return a.start < b.end and b.start < a.end


def _resolve(findings: list[Finding]) -> list[Finding]:
    """Drop overlapping spans, keeping the higher-priority (or longer) match."""
    ordered = sorted(
        findings,
        key=lambda f: (-PRIORITY.get(f.pii_type, 0), -(f.end - f.start), f.start),
    )
    kept: list[Finding] = []
    for item in ordered:
        if any(_overlaps(item, existing) for existing in kept):
            continue
        kept.append(item)
    kept.sort(key=lambda f: (f.start, f.end))
    return kept


def detect(text: str) -> list[Finding]:
    """Return non-overlapping PII findings for ``text``."""
    if not text:
        return []
    findings: list[Finding] = []
    findings.extend(_cards(text))
    findings.extend(_ssns(text))
    findings.extend(_routing(text))
    findings.extend(_vins(text))
    findings.extend(_accounts(text))
    findings.extend(_emails(text))
    findings.extend(_phones(text))
    findings.extend(_licenses(text))
    findings.extend(_dobs(text))
    findings.extend(_names(text))
    return _resolve(findings)


def mask(text: str, findings: list[Finding] | None = None) -> str:
    """Replace each finding with a type token such as [SSN] or [CREDIT_CARD]."""
    if findings is None:
        findings = detect(text)
    if not findings:
        return text
    parts: list[str] = []
    cursor = 0
    for item in sorted(findings, key=lambda f: f.start):
        parts.append(text[cursor : item.start])
        parts.append(f"[{PII_LABELS.get(item.pii_type, item.pii_type.upper())}]")
        cursor = item.end
    parts.append(text[cursor:])
    return "".join(parts)


def highlight_html(text: str, findings: list[Finding] | None = None) -> str:
    """Return escaped HTML with findings wrapped in marked spans."""
    if findings is None:
        findings = detect(text)

    def esc(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    if not findings:
        return esc(text).replace("\n", "<br>")
    parts: list[str] = []
    cursor = 0
    for item in sorted(findings, key=lambda f: f.start):
        parts.append(esc(text[cursor : item.start]))
        label = PII_LABELS.get(item.pii_type, item.pii_type.upper())
        parts.append(
            f'<mark class="pii pii-{item.pii_type}" title="{label}">'
            f"{esc(item.value)}<span class='pii-tag'>{label}</span></mark>"
        )
        cursor = item.end
    parts.append(esc(text[cursor:]))
    return "".join(parts).replace("\n", "<br>")
