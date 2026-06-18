"""
contacts.py — resolve the decision-maker via Clay's 12-provider waterfall.

Finds the actual person (practice manager / owner), verifies the email, and gets the
title. Never settles for info@. Clay runs the provider waterfall; this module shapes the
request and normalizes the response into the contacts table.
"""

import requests

CLAY_WEBHOOK = "https://api.clay.com/v1/..."  # per-table webhook, configured in Clay


def enrich_contact(company: dict, clay_token: str) -> dict | None:
    """Send a company to the Clay waterfall, return a verified decision-maker or None."""
    payload = {
        "company": company["name"],
        "domain": company.get("domain"),
        "roles": ["owner", "practice manager", "office manager"],
    }
    r = requests.post(CLAY_WEBHOOK, json=payload,
                      headers={"Authorization": f"Bearer {clay_token}"}, timeout=60)
    r.raise_for_status()
    d = r.json()
    if not d.get("email") or not d.get("email_verified"):
        return None
    return {
        "company_id": company["id"],
        "full_name": d.get("full_name"),
        "title": d.get("title"),
        "email": d["email"],
        "email_verified": True,
        "enriched_by": d.get("provider"),
    }
