from typing import List, Dict

def multiples(peer: List[Dict[str, float]]) -> Dict[str, float]:
    ev_ebitda = [p["ev"]/p["ebitda"] for p in peer if p.get("ebitda")]
    pe = [p["price"]/p["eps"] for p in peer if p.get("eps")]
    return {"ev_ebitda_avg": sum(ev_ebitda)/len(ev_ebitda) if ev_ebitda else 0.0,
            "pe_avg": sum(pe)/len(pe) if pe else 0.0}
