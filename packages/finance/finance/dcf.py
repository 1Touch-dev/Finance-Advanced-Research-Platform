from typing import Dict, List

def dcf(fcf_years: List[float], wacc: float, terminal_growth: float) -> Dict[str, float]:
    """Simple DCF with terminal growth (Gordon)."""
    disc = 1.0
    pv = 0.0
    r = wacc
    for t, f in enumerate(fcf_years, start=1):
        disc = (1+r)**t
        pv += f / disc
    tv = fcf_years[-1] * (1+terminal_growth) / (r - terminal_growth)
    pv_tv = tv / ((1+r)**len(fcf_years))
    return {"pv_operating": pv, "terminal_value_pv": pv_tv, "enterprise_value": pv + pv_tv}

def reverse_dcf(price_per_share: float, shares_out: float, wacc: float, years: int = 5) -> float:
    """Implied terminal growth that matches current EV given flat FCF trajectory starting at price*shares/years."""
    ev = price_per_share * shares_out
    # naive: assume constant FCF X; solve tv to close gap; return g (bounded scan)
    avg = ev/years*0.08
    for g in [x/1000 for x in range(0,50)]:
        pv = sum(avg/((1+wacc)**t) for t in range(1, years+1))
        tv = avg*(1+g)/(wacc-g)
        pv_tv = tv/((1+wacc)**years)
        if pv+pv_tv >= ev:
            return g
    return 0.0
