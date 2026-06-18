"""
personalize.py — LLM writes a ZIP-specific email. Constrained, not freeform.

The subject is templated around the real number so the strongest fact leads. The body
follows a fixed frame; the model fills vertical-specific language but never invents a
number — every figure comes from the revenue model.
"""

from anthropic import Anthropic

client = Anthropic()

SUBJECT_TEMPLATE = "RE: {denied} out of 100 patients can't get financing in {zip}"

BODY_SYSTEM = """You write one short cold email to a healthcare practice owner.
RULES:
- Use ONLY the numbers provided. Never invent or round figures.
- Frame: name the loss -> quantify it -> position as a LAYER ON TOP of their existing
  financing (not a replacement) -> one soft CTA.
- Plain, direct, no hype, no exclamation points. 90 words max.
"""


def subject(denied_per_100: int, zip: str) -> str:
    return SUBJECT_TEMPLATE.format(denied=denied_per_100, zip=zip)


def body(company: dict) -> str:
    facts = (
        f"Practice: {company['name']} ({company['vertical']}) in ZIP {company['zip']}.\n"
        f"{company['denied_per_100']} of every 100 patients there can't get financing.\n"
        f"That is about ${company['lost_revenue_mo']:,}/month in lost treatments."
    )
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=300,
        system=BODY_SYSTEM,
        messages=[{"role": "user", "content": facts}],
    )
    return msg.content[0].text


def draft(company: dict) -> dict:
    return {
        "to": company.get("email"),
        "subject": subject(company["denied_per_100"], company["zip"]),
        "body": body(company),
    }
