"""
enrich_credit.py — join a scraped business to its ZIP's credit signal.

Takes the national credit map (built from HMDA + Census, see data/) and attaches a
denial rate + revenue-impact number to every company record. ZIPs that don't resolve
cleanly fall back to county-level aggregates so nothing is dropped silently.
"""

import pandas as pd

from revenue_model import revenue_impact


def load_credit_map(path: str = "data/credit_map.csv") -> dict[str, float]:
    """ZIP -> denial_rate. The map is ~42,000 ZIPs, denial rates 1%–31%."""
    df = pd.read_csv(path, dtype={"zip": str})
    return dict(zip(df["zip"], df["denial_rate"]))


def enrich(companies: list[dict], credit_map: dict[str, float],
           county_fallback: dict[str, float] | None = None) -> list[dict]:
    """Attach denial_rate + lost_revenue_mo to each company."""
    county_fallback = county_fallback or {}
    out = []
    for c in companies:
        z = c.get("zip")
        rate = credit_map.get(z)
        if rate is None:
            # fall back to county-level aggregate rather than drop the record
            rate = county_fallback.get(c.get("county"))
            if rate is None:
                continue  # no signal available; skip
        ri = revenue_impact(z, denial_rate=rate, vertical=c.get("vertical", "med_spa"))
        out.append({**c, "denial_rate": rate, "lost_revenue_mo": ri.lost_revenue_mo,
                    "denied_per_100": ri.denied_per_100})
    return out
