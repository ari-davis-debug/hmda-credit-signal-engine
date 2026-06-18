"""
crm_sync.py — push the credit signal back into the client's CRM.

This is the real output of the engine. It isn't just a list of emails to send — it's the
client's *own* CRM, upgraded: every target account gets the HMDA-derived denial rate, the
calculated monthly revenue loss, and the ready-to-use messaging written onto the record.
Their reps open their CRM and the signal + the pitch are already there.

Supports HubSpot / Salesforce-style upserts via a generic field map.
"""

import requests

# Map engine fields -> the client's CRM custom-property names.
FIELD_MAP = {
    "denial_rate":      "hmda_denial_rate",
    "denied_per_100":   "patients_denied_per_100",
    "lost_revenue_mo":  "monthly_revenue_at_risk",
    "credit_tier":      "credit_signal_tier",
    "draft_subject":    "outbound_subject",
    "draft_body":       "outbound_message",
}


def to_crm_properties(account: dict) -> dict:
    """Translate a scored account into the client's CRM property names."""
    return {crm_field: account[k] for k, crm_field in FIELD_MAP.items() if k in account}


def upsert_account(account: dict, *, crm_base: str, token: str) -> None:
    """Upsert one scored account into the client's CRM, keyed by domain.

    The rep ends up with a target account that already carries:
      - how many of their patients can't get financing (denied_per_100)
      - the dollars/month they're losing (monthly_revenue_at_risk)
      - the message that says it, pre-written
    """
    payload = {"properties": to_crm_properties(account)}
    r = requests.patch(
        f"{crm_base}/objects/companies/{account['domain']}?idProperty=domain",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()


def sync(accounts: list[dict], *, crm_base: str, token: str) -> int:
    """Push a batch of scored accounts into the CRM. Returns count synced."""
    n = 0
    for a in accounts:
        if a.get("denial_rate") is None:
            continue  # never push an account without a real signal
        upsert_account(a, crm_base=crm_base, token=token)
        n += 1
    return n
