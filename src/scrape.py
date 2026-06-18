"""
scrape.py — pull the ICP by ZIP via Apify (Google Maps scraper).

Iterating ZIP by ZIP (rather than by city/state) casts a wider net, yields more
companies, and lines records up for the credit join in enrich_credit.py.
"""

from apify_client import ApifyClient

ICP_QUERIES = {
    "med_spa": "med spa",
    "dental": "dental office",
    "beauty": "beauty clinic",
    "hrt": "hormone therapy clinic",
}


def scrape_zip(client: ApifyClient, zip: str, vertical: str) -> list[dict]:
    """Scrape one ICP vertical in one ZIP. Returns normalized company dicts."""
    run = client.actor("compass/google-maps-scraper").call(run_input={
        "searchStringsArray": [f"{ICP_QUERIES[vertical]} in {zip}"],
        "maxCrawledPlacesPerSearch": 50,
    })
    items = client.dataset(run["defaultDatasetId"]).list_items().items
    return [{
        "name": it.get("title"),
        "vertical": vertical,
        "address": it.get("address"),
        "zip": zip,
        "state": it.get("state"),
        "source": "apify",
    } for it in items]
