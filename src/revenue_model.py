"""
revenue_model.py — the math that makes the email land.

Computes the monthly revenue a practice loses to financing denials, using its ZIP's
mortgage-denial rate (HMDA) as a proxy for healthcare-financing denial. Deliberately
simple and transparent: the practice owner can check it on a napkin.

    lost_revenue_per_month = denial_rate × monthly_new_patients × avg_treatment_value
"""

from dataclasses import dataclass

# Per-vertical defaults. A med spa's ticket is not a dental office's. Overridable per account.
VERTICAL_DEFAULTS = {
    "med_spa": {"monthly_patients": 100, "avg_ticket": 1000},
    "dental":  {"monthly_patients": 120, "avg_ticket": 1200},
    "beauty":  {"monthly_patients": 150, "avg_ticket": 600},
    "hrt":     {"monthly_patients": 80,  "avg_ticket": 900},
}


@dataclass
class RevenueImpact:
    zip: str
    denial_rate: float          # 0.27
    monthly_patients: int       # 100
    avg_ticket: int             # 1000
    lost_treatments: int        # 27
    lost_revenue_mo: int        # 27000

    @property
    def denied_per_100(self) -> int:
        """The number that headlines the subject line."""
        return round(self.denial_rate * 100)


def revenue_impact(zip: str, denial_rate: float, vertical: str,
                   monthly_patients: int | None = None,
                   avg_ticket: int | None = None) -> RevenueImpact:
    """Compute per-practice lost revenue. Conservative by design — under-claiming the
    loss is more credible than over-claiming it."""
    d = VERTICAL_DEFAULTS.get(vertical, VERTICAL_DEFAULTS["med_spa"])
    patients = monthly_patients or d["monthly_patients"]
    ticket = avg_ticket or d["avg_ticket"]

    lost_treatments = round(patients * denial_rate)
    lost_revenue = lost_treatments * ticket

    return RevenueImpact(
        zip=zip,
        denial_rate=denial_rate,
        monthly_patients=patients,
        avg_ticket=ticket,
        lost_treatments=lost_treatments,
        lost_revenue_mo=lost_revenue,
    )


if __name__ == "__main__":
    r = revenue_impact("78701", denial_rate=0.27, vertical="med_spa")
    print(f"{r.denied_per_100} of 100 patients can't get financing in {r.zip} "
          f"-> ${r.lost_revenue_mo:,}/month walking out the door")
    # 27 of 100 patients can't get financing in 78701 -> $27,000/month walking out the door
