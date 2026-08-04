"""Quick test: resolve PayPal Mafia person names to SEC CIKs."""
import requests, json, time
SEC_HEADERS = {"User-Agent": "FinanceResearchPlatform research@onetouch.dev", "Accept": "application/json"}

def find_person_cik(name):
    """Resolve a person name to their SEC CIK using EFTS."""
    url = "https://efts.sec.gov/LATEST/search-index"
    params = {"q": f'"{name}"', "forms": "3,4", "dateRange": "custom", "startdt": "2000-01-01"}
    time.sleep(0.15)
    resp = requests.get(url, params=params, headers=SEC_HEADERS, timeout=20)
    if not resp.ok:
        return None, None

    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])

    last_name = name.split()[-1].upper()
    first_name = name.split()[0].upper()

    for hit in hits[:10]:
        source = hit.get("_source", {})
        display_names = source.get("display_names", [])
        ciks = source.get("ciks", [])

        for dn in display_names:
            dn_upper = dn.upper()
            if last_name in dn_upper and first_name in dn_upper:
                # Found the person in display_names. Now find their CIK.
                # Check each CIK in the filing to find the person entity
                for cik in ciks:
                    time.sleep(0.15)
                    sub_resp = requests.get(
                        f"https://data.sec.gov/submissions/CIK{cik}.json",
                        headers=SEC_HEADERS, timeout=10
                    )
                    if sub_resp.ok:
                        sub = sub_resp.json()
                        entity_name = sub.get("name", "").upper()
                        if last_name in entity_name and first_name in entity_name:
                            return cik, sub.get("name", "")
                return None, None  # Found display name but couldn't match CIK
    return None, None

if __name__ == "__main__":
    people = ["Peter Thiel", "Elon Musk", "Reid Hoffman", "Max Levchin", "David Sacks",
              "Keith Rabois", "Jeremy Stoppelman", "Joe Lonsdale"]
    for person in people:
        cik, sec_name = find_person_cik(person)
        print(f"{person}: CIK={cik}, SEC_NAME={sec_name}")
        time.sleep(0.3)
