"""Keyword-and-pattern rules for category, urgency, and route.

These are explainable and deterministic. They work without a model, which
is also how CI and first-run (no GGUF downloaded) behave. They can miss
nuanced messages; that is why the hybrid path can defer to the local model.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from triage.settings import CATEGORY_TO_ROUTE

# Weighted keyword groups. Longer / more specific phrases score higher.
CATEGORY_KEYWORDS: dict[str, tuple[tuple[str, int], ...]] = {
    "legal": (
        ("lemon law", 6),
        ("demand letter", 6),
        ("retained counsel", 6),
        ("attorney", 7),
        ("lawyer", 7),
        ("lawsuit", 5),
        ("legal action", 5),
        ("served papers", 5),
        ("arbitration", 4),
        ("better business bureau", 4),
        ("bbb complaint", 4),
        ("dmv complaint", 4),
        ("attorney general", 4),
        ("retain counsel", 4),
        ("sue you", 4),
        ("suing", 3),
        ("legal hold", 3),
    ),
    "fi": (
        ("credit application", 6),
        ("credit app", 5),
        ("run credit", 5),
        ("social security", 4),
        ("ssn", 3),
        ("apr", 4),
        ("interest rate", 4),
        ("finance rate", 4),
        ("gap warranty", 4),
        ("gap insurance", 4),
        ("extended warranty", 3),
        ("service contract", 3),
        ("f&i", 5),
        ("finance and insurance", 5),
        ("payoff quote", 5),
        ("loan payoff", 4),
        ("credit score", 3),
        ("lender", 2),
        ("down payment", 2),
        ("finance the", 3),
    ),
    "billing": (
        ("charged twice", 6),
        ("double charged", 6),
        ("overcharged", 5),
        ("billing error", 5),
        ("refund", 4),
        ("invoice", 3),
        ("statement", 3),
        ("wrong amount", 3),
        ("credit on my account", 3),
        ("appearance package", 2),
        ("was charged", 2),
    ),
    "service": (
        ("check engine", 5),
        ("grinding", 4),
        ("brake", 3),
        ("oil change", 4),
        ("repair order", 4),
        (" ro ", 2),
        ("warranty claim", 4),
        ("recall", 3),
        ("technician", 3),
        ("service appointment", 5),
        ("service department", 3),
        ("won't start", 5),
        ("will not start", 5),
        ("no start", 4),
        ("stranded", 4),
        ("tow truck", 4),
        ("towed", 3),
        ("check engine light", 5),
        ("transmission", 2),
        ("airbag", 2),
        ("appointment tomorrow", 2),
        (" diagnost", 3),
        ("leaking", 2),
        ("overheating", 3),
    ),
    "sales": (
        ("test drive", 5),
        ("test drove", 5),
        ("out-the-door", 5),
        ("out the door", 5),
        ("otd price", 5),
        ("buyer's order", 5),
        ("buyers order", 5),
        ("trade-in", 4),
        ("trade in", 4),
        ("on the lot", 4),
        ("in stock", 3),
        ("lease is up", 4),
        ("lease-end", 4),
        ("quoted me", 3),
        ("salesperson", 3),
        ("sales manager", 3),
        ("down payment on the", 2),
        ("want to buy", 4),
        ("please hold the", 4),
        ("put a deposit", 4),
        ("a deposit on", 4),
        ("interested in the", 3),
        ("interested in a", 3),
        ("new honda", 2),
        ("new civic", 2),
        ("new accord", 2),
        ("new cr-v", 2),
        ("new pilot", 2),
        ("available in", 2),
        ("do you have a", 2),
        ("do you have the", 2),
    ),
    "general": (
        ("saturday hours", 4),
        ("what are your hours", 5),
        ("business hours", 3),
        ("how do i get to", 4),
        ("directions", 3),
        ("thank you for the great", 3),
        ("thanks for the great", 3),
        ("where are you located", 4),
        ("address of the store", 3),
    ),
}

CRITICAL_PATTERNS = (
    r"\bstranded\b",
    r"\btow(ed|ing| truck)?\b",
    r"\bw[o']?n'?t start\b",
    r"\bwill not start\b",
    r"\bno start\b",
    r"\bon (the|a) (side of the )?road\b",
    r"\baccident\b",
    r"\blawsuit\b",
    r"\bserved papers\b",
    r"\bdemand letter\b",
    r"\blemon law\b",
    r"\bunsafe to drive\b",
    r"\bfire\b",
    r"\bairbag(s)? deployed\b",
)

HIGH_PATTERNS = (
    r"\btoday\b",
    r"\bthis afternoon\b",
    r"\bthis morning\b",
    r"\btomorrow\b",
    r"\basap\b",
    r"\burgent\b",
    r"\blawyer\b",
    r"\battorney\b",
    r"\bgrinding\b",
    r"\bcheck engine\b",
    r"\bovercharged\b",
    r"\bcharged twice\b",
    r"\bcredit application\b",
    r"\brun credit\b",
    r"\bdeposit\b",
    r"\blease is up\b",
    r"\bby 5\b",
    r"\bneed the car\b",
    r"\bbbb\b",
)

LOW_PATTERNS = (
    r"\bnext month\b",
    r"\bwhenever\b",
    r"\bno rush\b",
    r"\bjust curious\b",
    r"\bhours\b",
    r"\bdirections\b",
    r"\bthank(?:s| you)\b",
    r"\bwhere are you located\b",
)


@dataclass(frozen=True)
class RuleDecision:
    category: str
    urgency: str
    route: str
    reason: str
    scores: dict[str, int]
    confidence: float
    confident: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_for_match(text: str) -> str:
    return f" {text.lower()} "


def _score_categories(blob: str) -> dict[str, int]:
    scores = {key: 0 for key in CATEGORY_KEYWORDS}
    for category, terms in CATEGORY_KEYWORDS.items():
        for phrase, weight in terms:
            if phrase in blob:
                scores[category] += weight
    return scores


def _urgency(blob: str, category: str) -> str:
    if any(re.search(pat, blob) for pat in CRITICAL_PATTERNS):
        return "critical"
    if any(re.search(pat, blob) for pat in HIGH_PATTERNS):
        return "high"
    if category == "general" or any(re.search(pat, blob) for pat in LOW_PATTERNS):
        # A billing/service message can still say "thanks" and not be low.
        if category in {"legal", "fi", "billing", "service", "sales"} and not any(
            re.search(pat, blob) for pat in LOW_PATTERNS if pat not in {r"\bthank(?:s| you)\b"}
        ):
            if category == "general":
                return "low"
            return "normal"
        if category == "general":
            return "low"
        if any(re.search(pat, blob) for pat in LOW_PATTERNS):
            return "low"
    return "normal"


def classify(text: str) -> RuleDecision:
    """Return a deterministic triage decision for ``text``."""
    blob = _normalize_for_match(text)
    scores = _score_categories(blob)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    top_name, top_score = ranked[0]
    second_score = ranked[1][1]
    if top_score <= 0:
        category = "general"
        confidence = 0.35
        confident = False
        reason = "No strong department keywords; treating this as a general BDC message."
    else:
        category = top_name
        # High confidence when the winner clearly outranks the runner-up.
        margin = top_score - second_score
        confidence = min(0.99, 0.45 + 0.08 * top_score + 0.05 * max(margin, 0))
        confident = top_score >= 4 and margin >= 2 and (second_score < 4 or margin >= 6)
        reason = (
            f"Rules scored {category} at {top_score} "
            f"(next was {ranked[1][0]} at {second_score})."
        )
    urgency = _urgency(blob, category)
    route = CATEGORY_TO_ROUTE[category]
    # Web-style inventory questions can stay with the BDC even if sales-tagged.
    if category == "sales" and re.search(
        r"\b(do you have|in stock|hours|directions|just looking|test drive|interested in)\b", blob
    ) and not re.search(
        r"\b(buyer's order|want to buy|lease is up|out-the-door|out the door|deposit)\b", blob
    ):
        route = "bdc"
    return RuleDecision(
        category=category,
        urgency=urgency,
        route=route,
        reason=reason,
        scores=scores,
        confidence=round(confidence, 3),
        confident=confident,
    )
