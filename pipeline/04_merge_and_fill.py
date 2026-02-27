#!/usr/bin/env python3
"""
Stage 4: Merge new entries with existing dataset, fill defaults, output final JSON.

Input:  stage3_new_only.json + ../monasteries.json
Output: ../monasteries_merged.json
"""

import json
import os
import sys
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

INPUT_NEW = os.path.join(SCRIPT_DIR, "stage3_new_only.json")
EXISTING_FILE = os.path.join(PROJECT_DIR, "monasteries.json")
OUTPUT_FILE = os.path.join(PROJECT_DIR, "monasteries_merged.json")

# Country names for summary (mirrors app.js COUNTRY_NAMES)
COUNTRY_NAMES = {
    'US': 'United States', 'CA': 'Canada', 'MX': 'Mexico', 'BR': 'Brazil',
    'AR': 'Argentina', 'CO': 'Colombia', 'CL': 'Chile', 'CR': 'Costa Rica',
    'PE': 'Peru', 'CU': 'Cuba', 'UY': 'Uruguay', 'VE': 'Venezuela',
    'EC': 'Ecuador', 'GT': 'Guatemala', 'PA': 'Panama', 'BO': 'Bolivia',
    'PY': 'Paraguay', 'HN': 'Honduras', 'NI': 'Nicaragua', 'SV': 'El Salvador',
    'JM': 'Jamaica', 'TT': 'Trinidad & Tobago', 'PR': 'Puerto Rico',
    'DO': 'Dominican Republic', 'HT': 'Haiti', 'BZ': 'Belize',
    'GY': 'Guyana', 'SR': 'Suriname', 'GF': 'French Guiana',
    'BB': 'Barbados', 'BS': 'Bahamas', 'AW': 'Aruba', 'CW': 'Curacao',
}


def guess_language(country_code):
    """Guess primary language based on country."""
    if country_code in ("US", "CA", "JM", "TT", "BB", "BS", "GY", "BZ"):
        return "English-primary"
    if country_code in ("BR",):
        return "Non-English primary"
    if country_code in ("MX", "AR", "CO", "CL", "CR", "PE", "UY", "EC",
                        "GT", "PA", "BO", "PY", "HN", "NI", "SV", "VE",
                        "CU", "DO", "PR"):
        return "Non-English primary"
    if country_code in ("HT", "GF", "SR"):
        return "Non-English primary"
    return ""


def finalize_entry(entry, source):
    """Produce a clean entry with all required fields."""
    result = {
        "name": entry.get("name", "").strip(),
        "tradition": entry.get("tradition", "Other"),
        "subTradition": entry.get("subTradition", ""),
        "country": entry.get("country", ""),
        "city": entry.get("city", ""),
        "state": entry.get("state", ""),
        "lat": entry["lat"],
        "lng": entry["lng"],
        "address": entry.get("address", ""),
        "website": entry.get("website", ""),
        "phone": entry.get("phone", ""),
        "description": entry.get("description", ""),
        "visitorFriendly": entry.get("visitorFriendly"),  # None for unknown
        "retreats": entry.get("retreats") if entry.get("retreats") is not None else [],
        "ordination": entry.get("ordination"),  # None for unknown
        "residentTeacher": entry.get("residentTeacher"),  # None for unknown
        "language": entry.get("language", ""),
        "setting": entry.get("setting", ""),
        "source": source,
    }

    # For new OSM entries, guess language if not set
    if source == "osm" and not result["language"] and result["country"]:
        result["language"] = guess_language(result["country"])

    # Add osm_id for provenance on OSM-sourced entries
    if entry.get("osm_id"):
        result["osm_id"] = entry["osm_id"]

    return result


def main():
    if not os.path.exists(INPUT_NEW):
        print(f"ERROR: Input file not found: {INPUT_NEW}")
        print("Run 03_deduplicate.py first.")
        sys.exit(1)

    with open(INPUT_NEW, "r", encoding="utf-8") as f:
        new_entries = json.load(f)
    print(f"Loaded {len(new_entries)} new entries")

    with open(EXISTING_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"Loaded {len(existing)} existing entries")

    # Finalize existing entries
    merged = []
    for entry in existing:
        merged.append(finalize_entry(entry, "curated"))

    # Finalize new entries
    skipped_no_country = 0
    for entry in new_entries:
        if not entry.get("country"):
            skipped_no_country += 1
            continue
        merged.append(finalize_entry(entry, "osm"))

    if skipped_no_country:
        print(f"Skipped {skipped_no_country} entries with no country")

    # Sort: country, state, name
    merged.sort(key=lambda m: (m["country"], m["state"], m["name"]))

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(merged)} total entries to {OUTPUT_FILE}")
    print(f"  Curated: {sum(1 for m in merged if m['source'] == 'curated')}")
    print(f"  OSM: {sum(1 for m in merged if m['source'] == 'osm')}")

    # Country breakdown
    countries = Counter(m["country"] for m in merged)
    print(f"\n  Countries ({len(countries)}):")
    for code, count in sorted(countries.items(), key=lambda x: -x[1]):
        name = COUNTRY_NAMES.get(code, code)
        print(f"    {code} ({name}): {count}")

    # Tradition breakdown
    traditions = Counter(m["tradition"] for m in merged)
    print(f"\n  Traditions:")
    for t, n in sorted(traditions.items(), key=lambda x: -x[1]):
        print(f"    {t}: {n}")

    # Flag new countries that might need frontend updates
    existing_countries = set(e.get("country") for e in existing)
    new_countries = set(m["country"] for m in merged) - existing_countries
    if new_countries:
        print(f"\n  NEW countries not in original dataset: {sorted(new_countries)}")
        print("  These may need to be added to the frontend filters.")


if __name__ == "__main__":
    main()
