from typing import List

def sma(values: List[float], n: int) -> List[float]:
    out=[]
    for i in range(len(values)):
        if i+1 < n: out.append(None)
        else: out.append(sum(values[i+1-n:i+1])/n)
    return out

def rsi(values: List[float], n: int = 14) -> List[float]:
    gains=[]; losses=[]
    for i in range(1, len(values)):
        d = values[i]-values[i-1]
        gains.append(max(d,0)); losses.append(max(-d,0))
    out=[None]
    for i in range(1, len(values)):
        if i < n: out.append(None)
        else:
            avg_gain = sum(gains[i-n:i])/n
            avg_loss = sum(losses[i-n:i])/n
            if avg_loss==0: out.append(100.0)
            else:
                r = avg_gain/avg_loss
                out.append(100 - (100/(1+r)))
    return out
