import os
import re
import certifi
import pycountry
import requests
from dotenv import load_dotenv

load_dotenv()

# Fixes SSL certificate path problems on Windows & Docker
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
DEFAULT_ORIGIN = os.getenv("DEFAULT_ORIGIN", "DAC")
BASE_URL = "http://api.aviationstack.com/v1/flights"  # Aviationstack free plan uses HTTP

# Main airport per country (IATA codes)
MAIN_AIRPORT = {
    "BD": "DAC",  # Bangladesh - Dhaka
    "IN": "DEL",  # India - New Delhi
    "NP": "KTM",  # Nepal - Kathmandu
    "TH": "BKK",  # Thailand - Bangkok
    "AE": "DXB",  # UAE - Dubai
    "JP": "HND",  # Japan - Tokyo Haneda
    "US": "JFK",  # USA - New York JFK
    "GB": "LHR",  # UK - London Heathrow
    "SG": "SIN",  # Singapore
    "MY": "KUL",  # Malaysia - Kuala Lumpur
    "LK": "CMB",  # Sri Lanka - Colombo
    "MV": "MLE",  # Maldives - Male
    "KR": "ICN",  # South Korea - Incheon
    "FR": "CDG",  # France - Paris Charles de Gaulle
    "TR": "IST",  # Turkey - Istanbul
    "ID": "DPS",  # Indonesia - Bali / Jakarta
    "VN": "HAN",  # Vietnam - Hanoi
    "IT": "FCO",  # Italy - Rome
    "ES": "MAD",  # Spain - Madrid
    "DE": "FRA",  # Germany - Frankfurt
    "CH": "ZRH",  # Switzerland - Zurich
    "AU": "SYD",  # Australia - Sydney
    "CA": "YYZ",  # Canada - Toronto
}

# Common alias lookup to improve country recognition
COUNTRY_ALIASES = {
    "usa": "US",
    "united states": "US",
    "america": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "britain": "GB",
    "england": "GB",
    "uae": "AE",
    "dubai": "AE",
    "nepal": "NP",
    "india": "IN",
    "bangladesh": "BD",
    "thailand": "TH",
    "japan": "JP",
    "singapore": "SG",
    "malaysia": "MY",
    "sri lanka": "LK",
    "maldives": "MV",
    "korea": "KR",
    "south korea": "KR",
}


def find_countries(text: str):
    """
    Finds country codes in the order they appear in the text.
    Uses both alias dictionary and pycountry standard names.
    """
    found = []
    lowered = text.lower()

    # Check aliases first
    for alias, code in COUNTRY_ALIASES.items():
        pos = lowered.find(alias)
        if pos != -1:
            found.append((pos, code))

    # Check pycountry
    for c in pycountry.countries:
        names = {c.name.lower(), getattr(c, "common_name", c.name).lower()}
        for n in names:
            pos = lowered.find(n)
            if pos != -1:
                found.append((pos, c.alpha_2))
                break

    # Sort by appearance in the text
    found.sort(key=lambda x: x[0])
    # Deduplicate while preserving order
    seen = set()
    result = []
    for _, code in found:
        if code not in seen:
            seen.add(code)
            result.append(code)
    return result


def search_flights(query: str, limit: int = 5):
    """
    Searches for flights based on the user query.
    1. Extracts origin (after 'from') or defaults to DEFAULT_ORIGIN.
    2. Identifies destination country and maps to primary IATA airport.
    3. Queries Aviationstack API or provides structured fallback.
    """
    api_key = os.getenv("AVIATIONSTACK_API_KEY")
    origin_code = os.getenv("DEFAULT_ORIGIN", DEFAULT_ORIGIN)

    # 1. Detect origin after the keyword 'from'
    origin_country = None
    m = re.search(r"\bfrom\s+([A-Za-z\s]+)", query, re.IGNORECASE)
    if m:
        extracted = m.group(1).strip()
        codes = find_countries(extracted)
        if codes:
            origin_country = codes[0]
            origin_code = MAIN_AIRPORT.get(origin_country, origin_code)

    # 2. Detect destination (the country in query that isn't the origin)
    all_codes = find_countries(query)
    dest_country = None
    for code in all_codes:
        if code != origin_country:
            dest_country = code
            break

    # If no destination could be determined but we have countries, pick first
    if not dest_country and all_codes:
        dest_country = all_codes[0]

    dest_code = MAIN_AIRPORT.get(dest_country)
    if not dest_code:
        # Fallback default destination if not detected
        dest_code = "KTM" if "nepal" in query.lower() else "DEL"

    # If no Aviationstack API key is supplied, return clean mock flight data for smooth testing
    if not api_key or api_key.strip() in ("", "your_aviationstack_key"):
        return [
            {
                "airline": "Biman Bangladesh / Nepal Airlines",
                "flight": "BG-071",
                "status": "scheduled",
                "from": f"Origin Airport ({origin_code})",
                "departure": "09:30 AM",
                "to": f"Destination Airport ({dest_code})",
                "arrival": "11:15 AM",
                "approx_price_usd": "$150 - $220",
                "note": "Aviationstack API key not configured or free-tier route simulated.",
            },
            {
                "airline": "Himalaya Airlines",
                "flight": "H9-678",
                "status": "scheduled",
                "from": f"Origin Airport ({origin_code})",
                "departure": "02:45 PM",
                "to": f"Destination Airport ({dest_code})",
                "arrival": "04:30 PM",
                "approx_price_usd": "$160 - $240",
                "note": "Aviationstack API key not configured or free-tier route simulated.",
            },
        ]

    params = {
        "access_key": api_key,
        "dep_iata": origin_code,
        "arr_iata": dest_code,
        "limit": limit,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=20)
        data = response.json()
        if "error" in data:
            return [{"error": f"Aviationstack error: {data['error'].get('message', data['error'])}"}]

        flights = []
        for f in data.get("data", []):
            flights.append({
                "airline": (f.get("airline") or {}).get("name"),
                "flight": (f.get("flight") or {}).get("iata"),
                "status": f.get("flight_status"),
                "from": (f.get("departure") or {}).get("airport") or origin_code,
                "departure": (f.get("departure") or {}).get("scheduled"),
                "to": (f.get("arrival") or {}).get("airport") or dest_code,
                "arrival": (f.get("arrival") or {}).get("scheduled"),
            })

        return flights if flights else [
            {
                "info": f"No active scheduled flights found from {origin_code} to {dest_code} on Aviationstack free index today. Recommend checking direct airline booking portals."
            }
        ]
    except Exception as e:
        return [{"error": f"Flight lookup exception: {str(e)}"}]
