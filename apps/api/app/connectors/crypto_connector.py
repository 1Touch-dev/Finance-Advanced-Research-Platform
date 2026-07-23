"""
Crypto Intelligence Connector
──────────────────────────────
Multi-chain wallet intelligence, whale tracking, on-chain analytics.
Free data sources:
  - CoinGecko API (no key needed for basic tier)
  - Blockchain.info (BTC)
  - Etherscan (free key from ETHERSCAN_API_KEY or keyless fallback)
  - CoinCap (no key)
"""
import os
import time
import logging
import requests
from typing import Optional

log = logging.getLogger(__name__)

ETHERSCAN_KEY = os.getenv("ETHERSCAN_API_KEY", "")
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
ETHERSCAN_BASE = "https://api.etherscan.io/api"
BLOCKCHAIN_INFO = "https://blockchain.info"
COINCAP_BASE = "https://api.coincap.io/v2"

HEADERS = {"User-Agent": "Finance-Platform/1.0 abhishekk@kyma.world"}


def _get(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Crypto fetch %s error: %s", url, e)
        return {}


# ─── Price & Market Data ──────────────────────────────────────────────────────

def get_crypto_prices(coins: list = None) -> dict:
    """Current prices and 24h change for popular cryptos."""
    ids = ",".join(coins or ["bitcoin", "ethereum", "solana", "binancecoin",
                              "ripple", "cardano", "avalanche-2", "polkadot",
                              "chainlink", "uniswap", "toncoin", "dogecoin",
                              "shiba-inu", "litecoin", "stellar"])
    data = _get(f"{COINGECKO_BASE}/simple/price", params={
        "ids": ids,
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
    })
    return data


def get_coin_detail(coin_id: str) -> dict:
    """Full detail for a specific coin."""
    data = _get(f"{COINGECKO_BASE}/coins/{coin_id}", params={
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
    })
    if not data:
        return {}
    mkt = data.get("market_data", {})
    return {
        "id": data.get("id"),
        "symbol": data.get("symbol", "").upper(),
        "name": data.get("name"),
        "description": (data.get("description", {}).get("en") or "")[:400],
        "image": data.get("image", {}).get("small"),
        "homepage": (data.get("links", {}).get("homepage") or [""])[0],
        "price_usd": mkt.get("current_price", {}).get("usd"),
        "market_cap": mkt.get("market_cap", {}).get("usd"),
        "volume_24h": mkt.get("total_volume", {}).get("usd"),
        "change_24h": mkt.get("price_change_percentage_24h"),
        "change_7d": mkt.get("price_change_percentage_7d"),
        "change_30d": mkt.get("price_change_percentage_30d"),
        "ath": mkt.get("ath", {}).get("usd"),
        "atl": mkt.get("atl", {}).get("usd"),
        "circulating_supply": mkt.get("circulating_supply"),
        "total_supply": mkt.get("total_supply"),
        "max_supply": mkt.get("max_supply"),
        "rank": data.get("market_cap_rank"),
        "categories": data.get("categories", [])[:5],
        "genesis_date": data.get("genesis_date"),
        "sentiment_votes_up": data.get("sentiment_votes_up_percentage"),
        "sentiment_votes_down": data.get("sentiment_votes_down_percentage"),
    }


def get_trending_cryptos() -> list:
    """Trending coins on CoinGecko (top searched in 24h)."""
    data = _get(f"{COINGECKO_BASE}/search/trending")
    coins = data.get("coins", [])
    return [
        {
            "rank": c.get("item", {}).get("market_cap_rank"),
            "name": c.get("item", {}).get("name"),
            "symbol": c.get("item", {}).get("symbol"),
            "id": c.get("item", {}).get("id"),
            "price_btc": c.get("item", {}).get("price_btc"),
        }
        for c in coins[:10]
    ]


def get_global_market() -> dict:
    """Global crypto market overview."""
    data = _get(f"{COINGECKO_BASE}/global")
    d = data.get("data", {})
    return {
        "total_market_cap_usd": d.get("total_market_cap", {}).get("usd"),
        "total_volume_24h_usd": d.get("total_volume", {}).get("usd"),
        "btc_dominance": d.get("market_cap_percentage", {}).get("btc"),
        "eth_dominance": d.get("market_cap_percentage", {}).get("eth"),
        "active_cryptos": d.get("active_cryptocurrencies"),
        "market_cap_change_24h": d.get("market_cap_change_percentage_24h_usd"),
        "defi_volume_24h": d.get("defi_volume_24h"),
    }


def get_defi_overview() -> dict:
    """DeFi market overview."""
    data = _get(f"{COINGECKO_BASE}/global/decentralized_finance_defi")
    d = data.get("data", {})
    return {
        "defi_market_cap": d.get("defi_market_cap"),
        "eth_market_cap": d.get("eth_market_cap"),
        "defi_to_eth_ratio": d.get("defi_to_eth_ratio"),
        "trading_volume_24h": d.get("trading_volume_24h"),
        "defi_dominance": d.get("defi_dominance"),
        "top_coin_name": d.get("top_coin_name"),
        "top_coin_defi_dominance": d.get("top_coin_defi_dominance"),
    }


# ─── ETH Wallet Intelligence ──────────────────────────────────────────────────

def get_eth_wallet(address: str) -> dict:
    """Ethereum wallet profile via Etherscan or Blockscout fallback."""
    address = address.strip()
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
    }
    if ETHERSCAN_KEY:
        params["apikey"] = ETHERSCAN_KEY

    bal_data = _get(ETHERSCAN_BASE, params=params)
    balance_wei = int(bal_data.get("result", 0) or 0)
    balance_eth = balance_wei / 1e18

    # ERC-20 token holdings
    token_params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 20,
        "sort": "desc",
    }
    if ETHERSCAN_KEY:
        token_params["apikey"] = ETHERSCAN_KEY
    token_data = _get(ETHERSCAN_BASE, params=token_params)
    token_txs = token_data.get("result", []) or []

    # Collect unique token symbols
    tokens_seen = {}
    for tx in token_txs:
        sym = tx.get("tokenSymbol", "")
        if sym and sym not in tokens_seen:
            tokens_seen[sym] = {
                "symbol": sym,
                "name": tx.get("tokenName"),
                "contract": tx.get("contractAddress"),
                "decimals": tx.get("tokenDecimal"),
            }

    # Normal transactions
    tx_params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 10,
        "sort": "desc",
    }
    if ETHERSCAN_KEY:
        tx_params["apikey"] = ETHERSCAN_KEY
    tx_data = _get(ETHERSCAN_BASE, params=tx_params)
    txs = tx_data.get("result", []) or []

    recent_txs = []
    for tx in txs[:10]:
        val = int(tx.get("value", 0) or 0) / 1e18
        recent_txs.append({
            "hash": tx.get("hash", "")[:20] + "...",
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value_eth": round(val, 6),
            "timestamp": tx.get("timeStamp"),
            "is_error": tx.get("isError") == "1",
        })

    return {
        "address": address,
        "chain": "ethereum",
        "balance_eth": round(balance_eth, 6),
        "balance_usd": None,  # enrich with price
        "token_count": len(tokens_seen),
        "tokens": list(tokens_seen.values())[:10],
        "recent_transactions": recent_txs,
        "tx_count": len(txs),
    }


def get_btc_wallet(address: str) -> dict:
    """Bitcoin wallet profile via blockchain.info."""
    address = address.strip()
    data = _get(f"{BLOCKCHAIN_INFO}/rawaddr/{address}", params={"limit": 10})
    if not data:
        return {"address": address, "chain": "bitcoin", "error": "not found"}

    txs = data.get("txs", [])
    recent_txs = []
    for tx in txs[:10]:
        out_total = sum(o.get("value", 0) for o in tx.get("out", [])) / 1e8
        in_total = sum(i.get("prev_out", {}).get("value", 0) for i in tx.get("inputs", [])) / 1e8
        recent_txs.append({
            "hash": tx.get("hash", "")[:20] + "...",
            "time": tx.get("time"),
            "value_in_btc": round(in_total, 8),
            "value_out_btc": round(out_total, 8),
            "fee_btc": round((in_total - out_total) if in_total > out_total else 0, 8),
        })

    return {
        "address": address,
        "chain": "bitcoin",
        "balance_btc": data.get("final_balance", 0) / 1e8,
        "total_received_btc": data.get("total_received", 0) / 1e8,
        "total_sent_btc": data.get("total_sent", 0) / 1e8,
        "n_tx": data.get("n_tx"),
        "recent_transactions": recent_txs,
    }


# ─── Whale Alert (Large Transactions) ────────────────────────────────────────

def get_whale_alerts(min_usd: float = 1_000_000, limit: int = 20) -> list:
    """
    Approximate whale-alert via CoinGecko large-cap exchange flows.
    Real-time whale alerts require Whale Alert API (free tier: 10 req/min).
    Falls back to significant CoinCap market movers.
    """
    # Use CoinGecko top coins and flag those with large volume spikes
    data = _get(f"{COINGECKO_BASE}/coins/markets", params={
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": 50,
        "page": 1,
        "price_change_percentage": "1h,24h",
    })

    whales = []
    for coin in (data if isinstance(data, list) else []):
        vol = coin.get("total_volume", 0) or 0
        cap = coin.get("market_cap", 1) or 1
        vol_to_cap = vol / cap if cap else 0
        change_1h = coin.get("price_change_percentage_1h_in_currency", 0) or 0
        change_24h = coin.get("price_change_percentage_24h", 0) or 0
        if vol > min_usd and (abs(change_1h) > 3 or abs(change_24h) > 8):
            whales.append({
                "coin": coin.get("name"),
                "symbol": (coin.get("symbol") or "").upper(),
                "price_usd": coin.get("current_price"),
                "volume_24h": vol,
                "change_1h_pct": round(change_1h, 2),
                "change_24h_pct": round(change_24h, 2),
                "vol_to_cap_ratio": round(vol_to_cap, 3),
                "alert_reason": (
                    "VOLUME_SPIKE" if vol_to_cap > 0.5
                    else "PRICE_SURGE_1H" if abs(change_1h) > 5
                    else "LARGE_MOVE_24H"
                ),
            })

    return sorted(whales, key=lambda x: abs(x["change_1h_pct"]), reverse=True)[:limit]


# ─── Token / Exchange Flow ────────────────────────────────────────────────────

def get_token_flow(coin_id: str) -> dict:
    """Exchange inflow/outflow signals via market data heuristics."""
    data = _get(f"{COINGECKO_BASE}/coins/{coin_id}", params={
        "localization": "false",
        "tickers": "true",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
    })
    if not data:
        return {"error": "not found"}

    mkt = data.get("market_data", {})
    tickers = data.get("tickers", [])

    # Top exchange volumes
    exchange_vols = {}
    for t in tickers[:20]:
        mkt_name = t.get("market", {}).get("name", "Unknown")
        vol = t.get("converted_volume", {}).get("usd", 0) or 0
        exchange_vols[mkt_name] = exchange_vols.get(mkt_name, 0) + vol

    top_exchanges = sorted(exchange_vols.items(), key=lambda x: x[1], reverse=True)[:5]

    vol_24h = mkt.get("total_volume", {}).get("usd", 0) or 0
    cap = mkt.get("market_cap", {}).get("usd", 1) or 1
    vol_to_cap = vol_24h / cap if cap else 0

    # Signal interpretation
    change_24h = mkt.get("price_change_percentage_24h") or 0
    if vol_to_cap > 0.5 and change_24h > 5:
        flow_signal = "STRONG_INFLOW — high volume + price surge"
    elif vol_to_cap > 0.5 and change_24h < -5:
        flow_signal = "STRONG_OUTFLOW — high volume + price decline"
    elif vol_to_cap > 0.2:
        flow_signal = "ELEVATED_ACTIVITY — above-average volume"
    else:
        flow_signal = "NORMAL — standard volume"

    return {
        "coin_id": coin_id,
        "symbol": (data.get("symbol") or "").upper(),
        "name": data.get("name"),
        "price_usd": mkt.get("current_price", {}).get("usd"),
        "volume_24h_usd": vol_24h,
        "market_cap_usd": cap,
        "vol_to_cap_ratio": round(vol_to_cap, 3),
        "change_24h_pct": round(change_24h, 2),
        "flow_signal": flow_signal,
        "top_exchanges": [{"name": e, "volume_usd": round(v)} for e, v in top_exchanges],
    }


# ─── Crypto News ─────────────────────────────────────────────────────────────

def get_crypto_news(coin: str = "bitcoin", limit: int = 10) -> list:
    """Crypto news via CoinGecko trending + status updates."""
    # Status updates for the coin
    data = _get(f"{COINGECKO_BASE}/coins/{coin}/status_updates", params={"per_page": limit})
    updates = data.get("status_updates", []) or []
    articles = []
    for u in updates:
        articles.append({
            "title": u.get("description", "")[:120],
            "source": u.get("project", {}).get("name", "CoinGecko"),
            "url": u.get("project", {}).get("links", {}).get("homepage", [""])[0],
            "created_at": u.get("created_at"),
            "category": u.get("category"),
        })
    return articles


# ─── Convenience: full crypto dashboard ──────────────────────────────────────

def crypto_dashboard() -> dict:
    """Aggregate dashboard: global market + top 10 prices + trending + whale alerts."""
    try:
        global_market = get_global_market()
    except Exception:
        global_market = {}
    try:
        prices = get_crypto_prices()
    except Exception:
        prices = {}
    try:
        trending = get_trending_cryptos()
    except Exception:
        trending = []
    try:
        whales = get_whale_alerts(min_usd=500_000_000, limit=10)
    except Exception:
        whales = []

    # Format prices list
    price_list = [
        {
            "id": k,
            "price_usd": v.get("usd"),
            "market_cap_usd": v.get("usd_market_cap"),
            "volume_24h_usd": v.get("usd_24h_vol"),
            "change_24h_pct": v.get("usd_24h_change"),
        }
        for k, v in prices.items()
    ]
    price_list.sort(key=lambda x: x.get("market_cap_usd") or 0, reverse=True)

    return {
        "global": global_market,
        "top_coins": price_list,
        "trending": trending,
        "whale_alerts": whales,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
