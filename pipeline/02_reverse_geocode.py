#!/usr/bin/env python3
"""
Stage 2: Reverse geocode entries missing country/state/city.

Uses Nominatim (free, 1 req/sec). Checkpoints every 50 entries so it can resume.

Input:  stage1_classified.json
Output: stage2_geocoded.json
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(SCRIPT_DIR, "stage1_classified.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "stage2_geocoded.json")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "BuddhistMonasteryDirectory/1.0 (research project)"

CHECKPOINT_INTERVAL = 50

# ─── State abbreviation maps ──────────────────────────────────────

US_STATE_ABBREV = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "puerto rico": "PR",
    "u.s. virgin islands": "VI", "guam": "GU",
    "american samoa": "AS", "northern mariana islands": "MP",
}

CA_PROVINCE_ABBREV = {
    "british columbia": "BC", "alberta": "AB", "ontario": "ON",
    "quebec": "QC", "québec": "QC", "nova scotia": "NS", "manitoba": "MB",
    "saskatchewan": "SK", "new brunswick": "NB",
    "prince edward island": "PE", "newfoundland and labrador": "NL",
    "northwest territories": "NT", "yukon": "YT", "nunavut": "NU",
}

BR_STATE_ABBREV = {
    "acre": "AC", "alagoas": "AL", "amapá": "AP", "amazonas": "AM",
    "bahia": "BA", "ceará": "CE", "distrito federal": "DF",
    "espírito santo": "ES", "espirito santo": "ES", "goiás": "GO", "goias": "GO",
    "maranhão": "MA", "maranhao": "MA", "mato grosso": "MT",
    "mato grosso do sul": "MS", "minas gerais": "MG", "pará": "PA", "para": "PA",
    "paraíba": "PB", "paraiba": "PB", "paraná": "PR", "parana": "PR",
    "pernambuco": "PE", "piauí": "PI", "piaui": "PI",
    "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondônia": "RO", "rondonia": "RO",
    "roraima": "RR", "santa catarina": "SC", "são paulo": "SP",
    "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO",
}

MX_STATE_ABBREV = {
    "ciudad de méxico": "CDMX", "ciudad de mexico": "CDMX",
    "distrito federal": "CDMX", "mexico city": "CDMX",
    "aguascalientes": "Ags", "baja california": "BC",
    "baja california sur": "BCS", "campeche": "Camp",
    "chiapas": "Chis", "chihuahua": "Chih", "coahuila": "Coah",
    "colima": "Col", "durango": "Dgo", "guanajuato": "Gto",
    "guerrero": "Gro", "hidalgo": "Hgo", "jalisco": "Jal",
    "estado de méxico": "Edomex", "estado de mexico": "Edomex",
    "michoacán": "Mich", "michoacan": "Mich", "morelos": "Mor",
    "nayarit": "Nay", "nuevo león": "NL", "nuevo leon": "NL",
    "oaxaca": "Oax", "puebla": "Pue", "querétaro": "Qro",
    "queretaro": "Qro", "quintana roo": "QRoo",
    "san luis potosí": "SLP", "san luis potosi": "SLP",
    "sinaloa": "Sin", "sonora": "Son", "tabasco": "Tab",
    "tamaulipas": "Tamps", "tlaxcala": "Tlax",
    "veracruz": "Ver", "yucatán": "Yuc", "yucatan": "Yuc",
    "zacatecas": "Zac",
}

AR_PROVINCE_ABBREV = {
    "buenos aires": "Buenos Aires", "ciudad autónoma de buenos aires": "CABA",
    "catamarca": "Catamarca", "chaco": "Chaco", "chubut": "Chubut",
    "córdoba": "Córdoba", "cordoba": "Córdoba", "corrientes": "Corrientes",
    "entre ríos": "Entre Ríos", "formosa": "Formosa", "jujuy": "Jujuy",
    "la pampa": "La Pampa", "la rioja": "La Rioja", "mendoza": "Mendoza",
    "misiones": "Misiones", "neuquén": "Neuquén", "río negro": "Río Negro",
    "salta": "Salta", "san juan": "San Juan", "san luis": "San Luis",
    "santa cruz": "Santa Cruz", "santa fe": "Santa Fe",
    "santiago del estero": "Santiago del Estero",
    "tierra del fuego": "Tierra del Fuego", "tucumán": "Tucumán",
}


def abbreviate_state(state_name, country_code):
    """Convert full state name to abbreviation where applicable."""
    if not state_name:
        return ""
    key = state_name.lower().strip()
    if country_code == "US":
        return US_STATE_ABBREV.get(key, state_name)
    elif country_code == "CA":
        return CA_PROVINCE_ABBREV.get(key, state_name)
    elif country_code == "BR":
        return BR_STATE_ABBREV.get(key, state_name)
    elif country_code == "MX":
        return MX_STATE_ABBREV.get(key, state_name)
    elif country_code == "AR":
        return AR_PROVINCE_ABBREV.get(key, state_name)
    return state_name


# ─── Nominatim ─────────────────────────────────────────────────────

def reverse_geocode(lat, lng, retries=3):
    """Reverse geocode a lat/lng via Nominatim. Returns address dict."""
    params = urllib.parse.urlencode({
        "lat": lat,
        "lon": lng,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 18,
        "accept-language": "en",
    })
    url = f"{NOMINATIM_URL}?{params}"

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", USER_AGENT)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            address = data.get("address", {})
            return {
                "country_code": (address.get("country_code", "") or "").upper(),
                "state": address.get("state", "") or "",
                "city": (address.get("city") or address.get("town")
                         or address.get("village") or address.get("hamlet")
                         or address.get("municipality") or ""),
                "road": address.get("road", "") or "",
                "house_number": address.get("house_number", "") or "",
                "postcode": address.get("postcode", "") or "",
                "display_name": data.get("display_name", ""),
            }
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries - 1:
                wait = [5, 15, 30][attempt]
                print(f" RATE LIMITED ({e.code}), waiting {wait}s...", end="", flush=True)
                time.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            raise

    return None


def build_address_from_geo(geo):
    """Build address string from geocode result."""
    parts = []
    if geo.get("house_number") and geo.get("road"):
        parts.append(f"{geo['house_number']} {geo['road']}")
    elif geo.get("road"):
        parts.append(geo["road"])
    if geo.get("city"):
        parts.append(geo["city"])
    state = geo.get("state", "")
    postcode = geo.get("postcode", "")
    if state and postcode:
        parts.append(f"{state} {postcode}")
    elif state:
        parts.append(state)
    return ", ".join(parts)


# ─── Main ──────────────────────────────────────────────────────────

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Run 01_clean_and_filter.py first.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        entries = json.load(f)
    print(f"Loaded {len(entries)} classified entries")

    # Load checkpoint if exists
    processed = []
    done_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            processed = json.load(f)
        done_ids = {e.get("osm_id") for e in processed if e.get("osm_id")}
        print(f"Resuming from checkpoint: {len(processed)} already processed")

    remaining = [e for e in entries if e.get("osm_id") not in done_ids]
    needs_geocode = sum(1 for e in remaining if e.get("_needs_geocode"))
    print(f"Remaining: {len(remaining)} entries ({needs_geocode} need geocoding)")

    if needs_geocode > 0:
        est_minutes = needs_geocode * 1.1 / 60
        print(f"Estimated time: ~{est_minutes:.0f} minutes")

    total = len(entries)
    geocoded_count = 0
    skipped_count = 0
    failed_count = 0

    for entry in remaining:
        idx = len(processed) + 1
        name_short = entry["name"][:45]

        if not entry.get("_needs_geocode"):
            # Already has location data, just abbreviate state
            if entry.get("country") and entry.get("state"):
                entry["state"] = abbreviate_state(entry["state"], entry["country"])
            if "_needs_geocode" in entry:
                del entry["_needs_geocode"]
            processed.append(entry)
            skipped_count += 1
            continue

        print(f"[{idx}/{total}] {name_short}...", end=" ", flush=True)

        try:
            geo = reverse_geocode(entry["lat"], entry["lng"])
            if geo:
                country = geo["country_code"]
                if not entry["country"]:
                    entry["country"] = country
                if not entry["state"]:
                    raw_state = geo["state"]
                    entry["state"] = abbreviate_state(raw_state, country)
                if not entry["city"]:
                    entry["city"] = geo["city"]
                if not entry["address"] or entry["address"].strip(", ") == "":
                    entry["address"] = build_address_from_geo(geo)

                print(f"OK ({entry['country']}, {entry['state']}, {entry['city']})")
                geocoded_count += 1
            else:
                print("FAILED (no result)")
                failed_count += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed_count += 1

        if "_needs_geocode" in entry:
            del entry["_needs_geocode"]
        processed.append(entry)

        # Checkpoint
        if idx % CHECKPOINT_INTERVAL == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(processed, f, indent=2, ensure_ascii=False)
            print(f"  [Checkpoint saved: {idx}/{total}]")

        time.sleep(1.05)

    # Final save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Saved {len(processed)} entries to {OUTPUT_FILE}")
    print(f"  Geocoded: {geocoded_count}")
    print(f"  Skipped (already had data): {skipped_count}")
    print(f"  Failed: {failed_count}")


if __name__ == "__main__":
    main()
