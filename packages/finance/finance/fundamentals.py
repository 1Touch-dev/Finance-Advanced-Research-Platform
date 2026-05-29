from typing import Dict, Any

def statements_from_inputs(rev: float, op_margin: float, tax_rate: float, capex: float, wc_delta: float) -> Dict[str, Any]:
    ebit = rev*op_margin
    nopat = ebit*(1-tax_rate)
    fcf = nopat + 0 - capex - wc_delta
    return {"revenue": rev, "ebit": ebit, "nopat": nopat, "capex": capex, "wc_delta": wc_delta, "fcf": fcf}
