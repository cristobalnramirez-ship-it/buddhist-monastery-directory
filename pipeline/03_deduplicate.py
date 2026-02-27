#!/usr/bin/env python3
"""
Stage 3: Deduplicate OSM entries against existing monasteries.json.

Input:  stage2_geocoded.json + ../monasteries.json
Output: stage3_new_only.json   (entries not in existing dataset)
        enrichments.json       (suggested updates to existing entries)
        duplicates_log.json    (matched pairs for review)
"""

import json
import os
import re
import sys
from math import radians, cos, sin, asin, sqrt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

INPUT_FILE = os.path.join(SCRIPT_DIR, "stage2_geocoded.json")
EXISTING_FILE = os.path.join(PROJECT_DIR, "monasteries.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "stage3_new_only.json")
ENRICHMENTS_FILE = os.path.join(SCRIPT_DIR, "enrichments.json")
DUPLICATES_FILE = os.path.join(SCRIPT_DIR, "duplicates_log.json")

STOP_WORDS = {
    "the", "of", "and", "in", "at", "a", "an", "for",
    "de", "do", "da", "das", "dos", "e", "la", "el", "del", "los", "las",
    "buddhist", "monastery", "temple", "center", "centre", "meditation",
    "society", "association", "foundation", "inc", "international",
}

# ─── Distance ──────────────────────────────────────────────────────

def haversine_m(lat1, lng1, lat2, lng2):
    """Distance in meters between two lat/lng points."""
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return 2 * R * asin(sqrt(a))


# ─── Name similarity ──────────────────────────────────────────────

def tokenize(name):
    """Lowercase, remove parens, split on non-alpha, remove stop words."""
    s = re.sub(r'\([^)]*\)', '', name.lower())
    tokens = set(re.findall(r'[a-z]+', s))
    return tokens - STOP_WORDS


def name_similarity(name1, name2):
    """Token-level Jaccard similarity, 0 to 1."""
    tokens1 = tokenize(name1)
    tokens2 = tokenize(name2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


# ─── Main ──────────────────────────────────────────────────────────

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Run 02_reverse_geocode.py first.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        osm_entries = json.load(f)
    print(f"Loaded {len(osm_entries)} geocoded OSM entries")

    with open(EXISTING_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"Loaded {len(existing)} existing monasteries")

    new_only = []
    duplicates = []
    enrichments = []

    for osm in osm_entries:
        best_match = None
        best_distance = float("inf")
        best_sim = 0

        for ex in existing:
            dist = haversine_m(osm["lat"], osm["lng"], ex["lat"], ex["lng"])

            if dist < 200:  # within 200m — candidate
                sim = name_similarity(osm["name"], ex["name"])

                if dist < 50 or sim > 0.3:
                    if dist < best_distance:
                        best_match = ex
                        best_distance = dist
                        best_sim = sim

        if best_match:
            # It's a duplicate
            dup_record = {
                "osm_name": osm["name"],
                "existing_name": best_match["name"],
                "distance_m": round(best_distance, 1),
                "name_similarity": round(best_sim, 3),
                "osm_id": osm.get("osm_id"),
            }
            duplicates.append(dup_record)

            # Check if OSM can enrich the existing entry
            enrich = {}
            if not best_match.get("website") and osm.get("website"):
                enrich["website"] = osm["website"]
            if not best_match.get("phone") and osm.get("phone"):
                enrich["phone"] = osm["phone"]

            if enrich:
                enrich["existing_name"] = best_match["name"]
                enrich["osm_name"] = osm["name"]
                enrich["osm_id"] = osm.get("osm_id")
                enrichments.append(enrich)
        else:
            new_only.append(osm)

    print(f"\nResults:")
    print(f"  Duplicates found: {len(duplicates)}")
    print(f"  New entries: {len(new_only)}")
    print(f"  Enrichment suggestions: {len(enrichments)}")

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(new_only, f, indent=2, ensure_ascii=False)
    print(f"\nSaved new-only entries to {OUTPUT_FILE}")

    with open(DUPLICATES_FILE, "w", encoding="utf-8") as f:
        json.dump(duplicates, f, indent=2, ensure_ascii=False)
    print(f"Saved duplicates log to {DUPLICATES_FILE}")

    with open(ENRICHMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(enrichments, f, indent=2, ensure_ascii=False)
    print(f"Saved enrichment suggestions to {ENRICHMENTS_FILE}")

    # Print some duplicate examples
    if duplicates:
        print(f"\nSample duplicates:")
        for d in duplicates[:10]:
            print(f"  OSM: {d['osm_name']}")
            print(f"  Existing: {d['existing_name']}")
            print(f"  Distance: {d['distance_m']}m, Similarity: {d['name_similarity']}")
            print()


if __name__ == "__main__":
    main()
