#!/usr/bin/env python3
"""
Stage 1: Clean, filter noise, and classify OSM Buddhist sites by tradition.

Input:  osm_buddhist_americas.json (raw OSM data)
Output: stage1_classified.json     (entries with confirmed tradition)
        stage1_needs_review.json   (entries we couldn't classify)
"""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

INPUT_FILE = os.path.join(SCRIPT_DIR, "osm_buddhist_americas.json")
CLASSIFIED_FILE = os.path.join(SCRIPT_DIR, "stage1_classified.json")
REVIEW_FILE = os.path.join(SCRIPT_DIR, "stage1_needs_review.json")

# Also check /tmp if not found in pipeline dir
INPUT_FALLBACK = "/tmp/osm_buddhist_americas.json"

# ─── Noise filtering ───────────────────────────────────────────────

NOISE_KEYWORDS = [
    # Non-Buddhist religions wrongly tagged
    "jehovah", "witness", "pentecostal", "evangelical", "adventist",
    "mormon", "latter-day", "lds", "falun gong", "falun dafa",
    "church of christ", "baptist", "methodist", "catholic", "lutheran",
    "presbyterian", "assemblies of god", "kingdom hall", "mosque",
    "synagogue", "hindu temple",
    # Businesses / non-religious
    "restaurant", "thai food", "chinese food", "buffet", "grocery",
    "spa ", "massage parlor", "martial art", "kung fu school",
    "karate", "yoga studio", "acupuncture",
]

NOISE_DENOMINATIONS = [
    "jehovahs_witness", "pentecostal", "reformed", "tenrikyo",
    "honbushin", "falun_gong",
]


def is_noise(entry):
    """Return True if entry is probably not a Buddhist site."""
    name_lower = entry.get("name", "").lower()
    denom_lower = (entry.get("denomination", "") or "").lower()

    if denom_lower in NOISE_DENOMINATIONS:
        return True

    for kw in NOISE_KEYWORDS:
        if kw in name_lower:
            return True

    return False


# ─── Denomination → Tradition mapping ──────────────────────────────

DENOMINATION_MAP = {
    # Theravada
    "theravada":          ("Theravada", ""),
    "theravāda":          ("Theravada", ""),
    "thai_theravada":     ("Theravada", "Thai Forest"),
    "thai":               ("Theravada", "Thai"),
    "thai_mahanikaya":    ("Theravada", "Thai Maha Nikaya"),
    "burmese_theravada":  ("Theravada", "Burmese"),
    "sri_lankan":         ("Theravada", "Sri Lankan"),
    "khmer":              ("Theravada", "Cambodian"),
    "lao":                ("Theravada", "Lao"),
    "bhutanese_vajrayana":("Tibetan", "Bhutanese Vajrayana"),

    # Insight/Vipassana
    "vipassana":          ("Insight/Vipassana", ""),
    "vipassna":           ("Insight/Vipassana", ""),

    # Zen
    "zen":                ("Zen", ""),
    "soto":               ("Zen", "Soto"),
    "rinzai":             ("Zen", "Rinzai"),
    "rinkai":             ("Zen", "Rinzai"),
    "seon":               ("Zen", "Korean Zen"),
    "korean_zen":         ("Zen", "Korean Zen"),
    "jogye":              ("Zen", "Korean Zen (Jogye)"),
    "thien":              ("Zen", "Vietnamese Zen"),
    "plum_village":       ("Zen", "Plum Village"),
    "plum_village_tradition": ("Zen", "Plum Village"),

    # Tibetan
    "tibetan":            ("Tibetan", ""),
    "vajrayana":          ("Tibetan", ""),
    "gelug":              ("Tibetan", "Gelug"),
    "kagyu":              ("Tibetan", "Kagyu"),
    "nyingma":            ("Tibetan", "Nyingma"),
    "sakya":              ("Tibetan", "Sakya"),
    "kadampa":            ("Tibetan", "New Kadampa Tradition"),
    "new_kadampa":        ("Tibetan", "New Kadampa Tradition"),
    "new_kadampa_tradition": ("Tibetan", "New Kadampa Tradition"),
    "shambhala":          ("Tibetan", "Shambhala"),
    "bon":                ("Tibetan", "Bon"),
    "bön":                ("Tibetan", "Bon"),
    "black_sect_tantric": ("Tibetan", ""),

    # Pure Land
    "pure_land":          ("Pure Land", ""),
    "jodo_shinshu":       ("Pure Land", "Jodo Shinshu"),
    "jodo_shu":           ("Pure Land", "Jodo Shu"),
    "fo_guang_shan":      ("Pure Land", "Fo Guang Shan"),

    # Chan
    "chan":                ("Chan", ""),
    "chinese_mahayana":   ("Chan", ""),

    # Mahayana (general — try to be more specific via name later)
    "mahayana":           ("_mahayana", ""),

    # Nichiren / SGI
    "nichiren":           ("SGI/Nichiren", "Nichiren"),
    "nichiren_shoshu":    ("SGI/Nichiren", "Nichiren Shoshu"),
    "sgi":                ("SGI/Nichiren", "Soka Gakkai"),
    "soka_gakkai":        ("SGI/Nichiren", "Soka Gakkai"),

    # Other specific
    "shingon":            ("Shingon", ""),
    "shingon_shu":        ("Shingon", ""),
    "won":                ("Won", ""),
    "triratna":           ("Other", "Triratna"),
    "secular":            ("Other", "Secular"),
    "nondenominational":  ("Other", "Non-denominational"),
    "shaolin":            ("Chan", "Shaolin"),
    "dhammakaya":         ("Theravada", "Dhammakaya"),
    "mongolian":          ("Tibetan", "Mongolian"),
    "sakyamuni":          ("_mahayana", ""),

    # Generic — not useful
    "buddhist":           (None, ""),
    "bou":                (None, ""),
}

# ─── Name-based heuristics ─────────────────────────────────────────

# Each tuple: (list_of_keywords, tradition, subTradition)
# Checked in order; first match wins
NAME_TRADITION_HINTS = [
    # Theravada — Southeast Asian temple names
    (["wat ", "wat_", "watt ", "vihara", "vihar", "theravada",
      "bhavana ", "forest monastery", "forest hermitage",
      "dhammaram", "dhammarama", "buddhadham",
      "ratanaram", "rattanaram", "vanaram",
      "jetavana", "bodhivana",
      "cambodian buddhist", "khmer buddhist", "lao buddhist",
      "sri lankan buddhist", "burmese buddhist", "myanmar buddhist",
      "thai buddhist", "ceylon buddhist",
      "pagoda"], "Theravada", ""),

    # Insight/Vipassana
    (["vipassana", "insight meditation", "spirit rock",
      "insight center"], "Insight/Vipassana", ""),

    # Zen
    (["zen ", "zen_", " zen", "zendo", "zen center", "zen mountain",
      "zen monastery", "sesshin", "rinzai", "soto ",
      "sanbo ", "empty cloud", "fire lotus",
      "thich nhat hanh", "plum village",
      "order of interbeing",
      "korean zen", "kwan um"], "Zen", ""),

    # Tibetan
    (["tibetan", "vajra", "kagyu", "gelug", "nyingma", "sakya",
      "kadampa", "shambhala", "rigpa", "dzogchen",
      " ling", "gompa", "choling", "chöling",
      "kunzang", "palchen", "thubten", "tashi",
      "namgyal", "drepung", "sera ", "ganden",
      "karma triyana", "karmapa",
      "dorje", "chenrezig", "tara ",
      "dharma center", "dharma centre",
      "buddhist center", "meditation center kadampa",
      "kpc ", "ktc ", "kdk "], "Tibetan", ""),

    # Pure Land
    (["jodo", "shin buddhist", "hongwanji", "fo guang",
      "hsi lai", "pure land", "amitabha",
      "nishi hongwanji", "higashi hongwanji",
      "buddhist churches of america",
      "bca "], "Pure Land", ""),

    # Chan / Chinese
    (["chan ", "chan_", "dharma drum", "cttb",
      "ten thousand buddhas", "city of ten thousand",
      "chuang yen", "zhuang yan",
      "tzu chi", "fo guang shan",
      "hsi fang", "xi fang",
      "chinese buddhist", "china buddhist",
      "hua zang", "chung tai",
      "buddha's light"], "Chan", ""),

    # SGI / Nichiren
    (["sgi", "soka gakkai", "nichiren",
      "sorka gakkai", "sgi-usa", "sgi usa",
      "nam myoho", "daimoku",
      "rissho kosei"], "SGI/Nichiren", ""),

    # Shingon
    (["shingon", "koyasan"], "Shingon", ""),

    # Won
    (["won buddhism", "won dharma", "won buddhist"], "Won", ""),

    # Vietnamese (often Mahayana/Pure Land/Zen mix)
    (["chua ", "chùa ", "chùa", "chua_",
      "vietnamese buddhist", "tu vien"], "Zen", "Vietnamese"),
]


def classify_by_denomination(denomination):
    """Map OSM denomination to (tradition, subTradition). Returns (None, '') if unknown."""
    if not denomination:
        return (None, "")
    key = denomination.lower().strip()
    if key in DENOMINATION_MAP:
        return DENOMINATION_MAP[key]
    return (None, "")


def classify_by_name(name):
    """Try to guess tradition from the site name. Returns (tradition, subTradition) or (None, '')."""
    name_lower = name.lower()
    for keywords, tradition, sub in NAME_TRADITION_HINTS:
        for kw in keywords:
            if kw in name_lower:
                return (tradition, sub)
    return (None, "")


def resolve_mahayana(name):
    """For entries tagged 'mahayana', try to be more specific via name."""
    tradition, sub = classify_by_name(name)
    if tradition and tradition != "_mahayana":
        return (tradition, sub)
    # Generic Mahayana — could be Chan, Pure Land, or mixed
    # Check for Chinese/Vietnamese indicators
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["temple", "tien", "guan", "si "]):
        return ("Chan", "")
    return ("Pure Land", "")  # default for unspecific Mahayana


def classify(entry):
    """Classify an entry. Returns (tradition, subTradition) or (None, '') if unknown."""
    denom = entry.get("denomination", "") or ""

    # Try denomination first
    tradition, sub = classify_by_denomination(denom)
    if tradition == "_mahayana":
        return resolve_mahayana(entry["name"])
    if tradition:
        return (tradition, sub)

    # Try name heuristics
    tradition, sub = classify_by_name(entry["name"])
    if tradition and tradition != "_mahayana":
        return (tradition, sub)
    if tradition == "_mahayana":
        return resolve_mahayana(entry["name"])

    return (None, "")


# ─── Address building ──────────────────────────────────────────────

def build_address(entry):
    """Build a partial address string from available addr_* fields."""
    parts = []
    street = entry.get("addr_street", "").strip()
    city = entry.get("addr_city", "").strip()
    state = entry.get("addr_state", "").strip()
    postcode = entry.get("addr_postcode", "").strip()

    if street:
        parts.append(street)
    if city:
        parts.append(city)
    if state and postcode:
        parts.append(f"{state} {postcode}")
    elif state:
        parts.append(state)
    elif postcode:
        parts.append(postcode)

    return ", ".join(parts)


def normalize_url(url):
    """Ensure URL starts with http:// or https://."""
    if not url:
        return ""
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# ─── Main ──────────────────────────────────────────────────────────

def main():
    # Find input file
    input_path = INPUT_FILE
    if not os.path.exists(input_path):
        input_path = INPUT_FALLBACK
    if not os.path.exists(input_path):
        print(f"ERROR: Cannot find input file at {INPUT_FILE} or {INPUT_FALLBACK}")
        print("Copy osm_buddhist_americas.json into the pipeline/ directory first.")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    print(f"Loaded {len(raw)} raw OSM entries from {input_path}")

    # Filter noise
    filtered = []
    noise_count = 0
    for entry in raw:
        if is_noise(entry):
            noise_count += 1
            continue
        if not entry.get("name", "").strip():
            noise_count += 1
            continue
        filtered.append(entry)
    print(f"Filtered {noise_count} noise entries, {len(filtered)} remain")

    # Classify
    classified = []
    needs_review = []

    for entry in filtered:
        tradition, sub_tradition = classify(entry)

        result = {
            "name": entry["name"].strip(),
            "tradition": tradition or "Other",
            "subTradition": sub_tradition,
            "country": (entry.get("addr_country", "") or "").upper(),
            "city": entry.get("addr_city", "") or "",
            "state": entry.get("addr_state", "") or "",
            "lat": entry["lat"],
            "lng": entry["lng"],
            "address": build_address(entry),
            "website": normalize_url(entry.get("website", "") or ""),
            "phone": (entry.get("phone", "") or "").strip(),
            "osm_id": entry.get("osm_id"),
            "osm_type": entry.get("osm_type", ""),
            "amenity": entry.get("amenity", ""),
            "denomination_raw": entry.get("denomination", ""),
            "_needs_geocode": not all([
                entry.get("addr_country"),
                entry.get("addr_state"),
                entry.get("addr_city"),
            ]),
        }

        if tradition is None:
            needs_review.append(result)
        else:
            classified.append(result)

    print(f"\nClassified: {len(classified)} entries (will proceed to geocoding)")
    print(f"Needs review: {len(needs_review)} entries (saved for manual classification)")

    # Tradition breakdown
    from collections import Counter
    traditions = Counter(e["tradition"] for e in classified)
    print("\n  Tradition breakdown (classified):")
    for t, n in sorted(traditions.items(), key=lambda x: -x[1]):
        print(f"    {t}: {n}")

    # Save
    with open(CLASSIFIED_FILE, "w", encoding="utf-8") as f:
        json.dump(classified, f, indent=2, ensure_ascii=False)
    print(f"\nSaved classified entries to {CLASSIFIED_FILE}")

    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(needs_review, f, indent=2, ensure_ascii=False)
    print(f"Saved needs-review entries to {REVIEW_FILE}")


if __name__ == "__main__":
    main()
