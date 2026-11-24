"""Labeled sample inbox for Lakeside Auto Group (sample).

Every personal value is fictional and obviously so: example.com emails,
555 phone numbers, well-known test card numbers, reserved-style SSNs,
and demo VINs with a valid ISO 3779 check digit. The labels exist so the
scorecard can report accuracy; they are not a production evaluation set.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from triage.settings import STORE_DEFAULT


@dataclass(frozen=True)
class SampleMessage:
    id: str
    source: str
    subject: str
    body: str
    store: str
    category: str
    urgency: str
    route: str
    pii_types: tuple[str, ...] = ()
    ambiguous: bool = False
    notes: str = ""

    def text(self) -> str:
        subject = self.subject.strip()
        body = self.body.strip()
        if subject:
            return f"Subject: {subject}\n\n{body}\n"
        return body + "\n"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["text"] = self.text()
        return data


def _msg(
    mid: str,
    source: str,
    subject: str,
    body: str,
    category: str,
    urgency: str,
    route: str,
    pii_types: tuple[str, ...] = (),
    ambiguous: bool = False,
    notes: str = "",
    store: str = STORE_DEFAULT,
) -> SampleMessage:
    return SampleMessage(
        id=mid,
        source=source,
        subject=subject,
        body=body.strip() + "\n",
        store=store,
        category=category,
        urgency=urgency,
        route=route,
        pii_types=pii_types,
        ambiguous=ambiguous,
        notes=notes,
    )


SAMPLES: tuple[SampleMessage, ...] = (
    _msg(
        "svc-brakes",
        "email",
        "Grinding noise when I brake",
        """Hi Lakeside Honda service,

My 2022 Honda Accord is making a grinding noise when I brake. Can I get a
service appointment tomorrow morning? I'm a little worried about driving it.

Thanks,
Chris Nguyen
""",
        "service",
        "high",
        "service_advisor",
    ),
    _msg(
        "svc-stranded",
        "sms",
        "",
        """This is Dana Okonkwo. My Civic won't start on the side of Route 30
near Devon. I need a tow to Lakeside Honda. I'm stranded with the kids
in the car.""",
        "service",
        "critical",
        "service_advisor",
    ),
    _msg(
        "svc-oil",
        "web",
        "Oil change next month",
        """I'd like to book an oil change for my 2021 Pilot sometime next month.
No rush — whenever you have an opening on a Tuesday afternoon is fine.

Sam Whitaker
""",
        "service",
        "low",
        "service_advisor",
    ),
    _msg(
        "svc-recall",
        "email",
        "Airbag recall appointment",
        """I got a letter about the Honda airbag recall. Can the service
department schedule the repair for my CR-V? VIN 1LKSCRV55MC000101.

Elena Vasquez
elena.vasquez@example.com
""",
        "service",
        "normal",
        "service_advisor",
        pii_types=("vin", "email"),
    ),
    _msg(
        "svc-ro",
        "email",
        "RO 7781 still isn't ready",
        """Repair order 7781 was supposed to be done at noon and it's 3:30.
I need the car for a trip at 5. Can someone in the service department call me?

Luis Ortega
Phone: (610) 555-0172
""",
        "service",
        "high",
        "service_advisor",
        pii_types=("phone",),
    ),
    _msg(
        "svc-warranty",
        "email",
        "Warranty claim on the transmission",
        """Hi, I'm following up on a warranty claim for a transmission cooler
line on my 2019 Accord. The advisor said parts were ordered last week.

Anita Rosales
""",
        "service",
        "normal",
        "service_advisor",
    ),
    _msg(
        "svc-cel",
        "web",
        "Check engine light came on",
        """The check engine light came on this morning on the way to work.
The car still drives. Can I get a diagnostic at the service department today?

Jordan Hale
""",
        "service",
        "high",
        "service_advisor",
    ),
    _msg(
        "svc-overheat",
        "sms",
        "",
        """My Pilot is overheating on I-76. I'm pulled over and I think I need
a tow truck to Lakeside Honda service. — Nate Brooks""",
        "service",
        "critical",
        "service_advisor",
    ),
    _msg(
        "sales-testdrive",
        "web",
        "Test drive Saturday",
        """I'm interested in the 2024 Honda CR-V EX on your site. Can I schedule
a test drive Saturday morning at Lakeside Honda?

Priya Shah
priya.shah@example.com
Phone: (215) 555-0133
""",
        "sales",
        "normal",
        "bdc",
        pii_types=("email", "phone"),
    ),
    _msg(
        "sales-otd",
        "email",
        "Out-the-door price on the white Pilot",
        """What's your out-the-door price on the white Pilot on the lot?
I don't want a payment quote, I want the OTD number including fees.

Marcus Lee
""",
        "sales",
        "normal",
        "sales_manager",
    ),
    _msg(
        "sales-lease",
        "web",
        "Lease is up tomorrow",
        """My lease is up tomorrow and I want to buy a new Civic today if you
have one in silver. Please have a salesperson call me this afternoon.

From: Taylor Quinn
Phone: (484) 555-0190
""",
        "sales",
        "high",
        "sales_manager",
        pii_types=("name", "phone"),
    ),
    _msg(
        "sales-trade",
        "email",
        "Trade-in value",
        """Can someone give me a trade-in range on my 2018 Accord?
VIN 1LKSDM267MCB00001. I am just looking, no rush.

Customer: Riley Chen
""",
        "sales",
        "low",
        "bdc",
        pii_types=("vin", "name"),
    ),
    _msg(
        "sales-stock",
        "web",
        "Do you have a Civic in stock?",
        """Do you have a Civic Sport in stock in black or gray? Stock number
on a forum post I saw was 123456789 but I don't know if that's yours.

Thanks,
Avery Patel
""",
        "sales",
        "normal",
        "bdc",
        notes="The bare 9-digit stock number must not be flagged as an SSN.",
    ),
    _msg(
        "sales-buyers-order",
        "email",
        "Ready to write a buyer's order",
        """I want to buy the Accord I test drove yesterday. Can you send a
buyer's order this afternoon so I can come in today?

Samira Haddad
""",
        "sales",
        "high",
        "sales_manager",
    ),
    _msg(
        "sales-hold-card",
        "sms",
        "",
        """Please hold the silver CR-V for me until Saturday. You can use my
Visa 4111-1111-1111-1111 for a deposit. I'm Avery Patel at (267) 555-0144.
""",
        "sales",
        "high",
        "sales_manager",
        pii_types=("credit_card", "phone"),
        notes="Well-known test Visa; Luhn-valid.",
    ),
    _msg(
        "fi-credit-app",
        "document",
        "F&I credit application review",
        """Lakeside Auto Group — F&I credit application review
Store: Lakeside Honda    Desk: afternoon shift

Applicant name: Maya Elena Alvarez
SSN: 219-09-9999
Date of birth: 03/14/1988
Driver's license: PA2671843
Phone: (207) 555-0148
Email: maya.alvarez@example.com

Vehicle: 2023 Honda CR-V EX    VIN: 1LKSCRV55MC000101
Requested term: 72 months    Target APR: 6.49%

Bank for ACH down-payment residual:
Routing number: 267084005
Account number: 1002003344

A deposit was authorized on the customer's Visa 4111-1111-1111-1111.

These values are fictional sample data for a portfolio demo.
""",
        "fi",
        "high",
        "fi_manager",
        pii_types=(
            "name",
            "ssn",
            "dob",
            "drivers_license",
            "phone",
            "email",
            "vin",
            "routing_number",
            "bank_account",
            "credit_card",
        ),
    ),
    _msg(
        "fi-apr",
        "email",
        "APR on a 72-month loan",
        """What APR can F&I offer on a 72-month loan for a well-qualified
buyer this week? This is a process question, not a specific customer.

Jordan Lee, F&I desk
""",
        "fi",
        "normal",
        "fi_manager",
    ),
    _msg(
        "fi-gap",
        "web",
        "GAP and a service contract",
        """If I finance the CR-V, can F&I also price GAP insurance and a
service contract? I'd like the numbers before I come back Saturday.

Chris Nguyen
""",
        "fi",
        "normal",
        "fi_manager",
        ambiguous=True,
    ),
    _msg(
        "fi-run-credit",
        "email",
        "OK to run credit",
        """Please run credit when you get a chance. Social Security number:
219-09-9999. Applicant name: Maya Elena Alvarez.

Thanks,
Maya
""",
        "fi",
        "high",
        "fi_manager",
        pii_types=("ssn", "name"),
    ),
    _msg(
        "fi-payoff",
        "email",
        "Need a payoff quote",
        """Can F&I get a loan payoff quote on my current Accord? Account
number 1002003344, routing number 267084005 if you need the bank too.

Customer: Luis Ortega
""",
        "fi",
        "normal",
        "fi_manager",
        pii_types=("bank_account", "routing_number", "name"),
    ),
    _msg(
        "fi-ssn-labeled-bare",
        "sms",
        "",
        """Hi, this is Riley Chen. SSN: 219099999 for the credit application
you started yesterday. Please have F&I call me.
""",
        "fi",
        "high",
        "fi_manager",
        pii_types=("ssn",),
        notes="Bare 9-digit SSN is only in-scope because it is labeled.",
    ),
    _msg(
        "legal-lemon",
        "email",
        "Lemon law demand letter",
        """Attached is a formal demand letter under the Pennsylvania lemon law
regarding my 2023 Pilot, VIN 1LKSPLT39MC000303. I have retained counsel and
expect a written response.

Attorney: Morgan Blake
Morgan Blake LLP
morgan.blake@example.com
""",
        "legal",
        "critical",
        "legal_compliance",
        pii_types=("vin", "email"),
    ),
    _msg(
        "legal-lawyer",
        "email",
        "My lawyer wants the deal jacket",
        """My lawyer asked for a copy of the deal jacket and the credit
application from when I bought the Civic. Please have someone in legal
or compliance call me this week.

From: Anita Rosales
Phone: (610) 555-0188
""",
        "legal",
        "high",
        "legal_compliance",
        pii_types=("name", "phone"),
        ambiguous=True,
        notes="Mentions a credit application, but the ask is a lawyer request.",
    ),
    _msg(
        "legal-bbb",
        "web",
        "I will file a BBB complaint",
        """If I do not hear from a manager by tomorrow I will file a BBB
complaint and talk to my attorney about the scratch on my car after the
service department had it.

Dana Okonkwo
""",
        "legal",
        "high",
        "legal_compliance",
        ambiguous=True,
    ),
    _msg(
        "legal-lawsuit",
        "email",
        "We have been served papers",
        """The store was served papers this morning on a lawsuit involving a
recent used-car sale. Please route this to legal / compliance immediately.

Priya Nair, IT
""",
        "legal",
        "critical",
        "legal_compliance",
        store="Lakeside Auto Group (sample)",
    ),
    _msg(
        "legal-accident",
        "email",
        "Other party's insurance request",
        """There was a collision last week in our loaner. The other party's
lawyer is requesting repair records. Please have legal review this before
anyone sends documents.

Service manager, Lakeside Honda
""",
        "legal",
        "high",
        "legal_compliance",
        ambiguous=True,
    ),
    _msg(
        "bill-double",
        "email",
        "Charged twice for an oil change",
        """I was charged twice for the oil change on invoice 44012. Please
refund the second $79.95. I can show the statement if you need it.

Customer: Sam Whitaker
Email: sam.whitaker@example.com
""",
        "billing",
        "high",
        "controller",
        pii_types=("email", "name"),
    ),
    _msg(
        "bill-appearance",
        "web",
        "Unexpected appearance package",
        """Why is there a $299 appearance package on my statement? I did not
agree to that at delivery. Please have billing look at the invoice.

Taylor Quinn
""",
        "billing",
        "normal",
        "controller",
    ),
    _msg(
        "bill-refund",
        "email",
        "Refund for a cancelled accessory",
        """I cancelled the all-weather mats the same day and never received a
refund. Can the controller look at invoice 44088?

Elena Vasquez
""",
        "billing",
        "normal",
        "controller",
    ),
    _msg(
        "bill-gap-cancel",
        "email",
        "Overcharged for cancelled GAP",
        """I was overcharged for the GAP warranty I cancelled within the
free-look period. Please refund it and send a corrected statement.

Buyer: Chris Nguyen
""",
        "billing",
        "high",
        "controller",
        pii_types=("name",),
        ambiguous=True,
        notes="GAP is an F&I product, but the ask is a refund / overcharge.",
    ),
    _msg(
        "gen-hours",
        "web",
        "Saturday hours",
        """What are your Saturday hours at Lakeside Honda? I may stop by
just to look at the service waiting area, no appointment needed.
""",
        "general",
        "low",
        "bdc",
    ),
    _msg(
        "gen-directions",
        "sms",
        "",
        """How do I get to Lakeside Honda from I-76? I need directions to
the service entrance, not the sales lot.
""",
        "general",
        "low",
        "bdc",
    ),
    _msg(
        "gen-thanks",
        "email",
        "Thank you for the great visit",
        """Thank you for the great service yesterday. Everyone at the desk
was kind. No follow-up needed.

Kind regards,
Riley Chen
""",
        "general",
        "low",
        "bdc",
    ),
    _msg(
        "gen-location",
        "web",
        "Where are you located?",
        """Where are you located and what are your business hours on Sunday?
Just curious — no rush.
""",
        "general",
        "low",
        "bdc",
    ),
    _msg(
        "amb-trade-cel",
        "email",
        "Trade-in with the check engine light on",
        """I want to trade in my Accord, but the check engine light is on.
Should I still come in for an appraisal, or does service need to look at
it first?

From: Jordan Hale
""",
        "sales",
        "high",
        "sales_manager",
        pii_types=("name",),
        ambiguous=True,
        notes="Both sales and service keywords; primary intent is a trade-in.",
    ),
    _msg(
        "neg-bad-card",
        "sms",
        "",
        """I test drove the Civic this morning. Can you try my card again for the
deposit? I think I typed it wrong last time: 4111-1111-1111-1112.
Please do not run it if it is invalid. This is Avery Patel.
""",
        "sales",
        "high",
        "sales_manager",
        notes="Invalid Luhn; must not be flagged as a credit card.",
        ambiguous=True,
    ),
    _msg(
        "neg-bad-vin",
        "email",
        "Is this VIN on your lot?",
        """Do you have a Civic with VIN 1HGCV2F36KA123456 in stock? I copied
it from an old email and I am not sure it is right.

Thanks,
Samira Haddad
""",
        "sales",
        "normal",
        "bdc",
        notes="This 17-character VIN fails the ISO 3779 check digit and must not be flagged.",
    ),
    _msg(
        "neg-bare-nine",
        "email",
        "Stock number follow-up",
        """I called about stock number 123456789 yesterday. Do you still have
that Civic in stock, or should I look at something else?

Avery Patel
""",
        "sales",
        "normal",
        "bdc",
        notes="Bare 9-digit stock number, no SSN label.",
    ),
    _msg(
        "svc-vin-only",
        "email",
        "Parts question on a VIN",
        """Can the service department check parts availability for a cabin
filter on VIN 1LKSDM269MCB00002? No rush — next month is fine.

Nate Brooks
""",
        "service",
        "low",
        "service_advisor",
        pii_types=("vin",),
    ),
    _msg(
        "sales-mc-deposit",
        "email",
        "Deposit on a Pilot",
        """I'd like to put a deposit on the Pilot I test drove. MasterCard
5555-5555-5555-4444. I'll bring the card in person to finish the hold.

Customer: Elena Vasquez
Phone: (215) 555-0160
Email: elena.vasquez@example.com
""",
        "sales",
        "high",
        "sales_manager",
        pii_types=("credit_card", "name", "phone", "email"),
    ),
)


def all_samples() -> list[SampleMessage]:
    return list(SAMPLES)


def get_sample(sample_id: str) -> SampleMessage:
    for item in SAMPLES:
        if item.id == sample_id:
            return item
    raise KeyError(f"Unknown sample id: {sample_id}")


def as_inbox() -> list[dict]:
    return [item.to_dict() for item in SAMPLES]
