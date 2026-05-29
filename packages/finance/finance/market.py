from typing import Protocol, Dict, Any, List

class MarketDataProvider(Protocol):
    def quote(self, ticker: str) -> Dict[str, Any]: ...
    def candles(self, ticker: str, period: str = "1y") -> List[Dict[str, Any]]: ...

class StaticProvider:
    def __init__(self, quotes: Dict[str, Dict[str, Any]] | None = None):
        self._q = quotes or {}
    def quote(self, ticker: str) -> Dict[str, Any]:
        return self._q.get(ticker.upper(), {"price": 100.0})
    def candles(self, ticker: str, period: str = "1y") -> List[Dict[str, Any]]:
        out=[]; p=self.quote(ticker).get("price",100.0)
        for i in range(250):
            out.append({"close": p*(1+0.0005*i), "volume": 1000000})
        return out
