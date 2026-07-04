from __future__ import annotations

import asyncio
import time
import urllib.parse
import urllib.request
from typing import Any

COINS = {
    "bitcoin": {"symbol": "BTC", "name": "Bitcoin"},
    "ethereum": {"symbol": "ETH", "name": "Ethereum"},
    "monero": {"symbol": "XMR", "name": "Monero"},
}
API_BASE = "https://api.coingecko.com/api/v3"
CACHE_TTL_SECONDS = 5 * 60
_CACHE: dict[tuple[int], tuple[float, dict[str, Any]]] = {}


async def get_crypto_prices(hours: int = 24) -> dict[str, Any]:
    normalized_hours = max(1, min(int(hours), 24 * 30))
    cache_key = (normalized_hours,)
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    payload = await asyncio.to_thread(fetch_crypto_payload, normalized_hours)
    _CACHE[cache_key] = (now, payload)
    return payload


def fetch_crypto_payload(hours: int = 24) -> dict[str, Any]:
    try:
        current = _fetch_current_prices()
        btc_series = _fetch_bitcoin_series(hours)
    except Exception as exc:
        return {
            "available": False,
            "source": "coingecko",
            "error": str(exc),
            "prices": {},
            "series": {"bitcoin": []},
        }

    prices = {}
    for coin_id, meta in COINS.items():
        coin = current.get(coin_id, {})
        prices[coin_id] = {
            "symbol": meta["symbol"],
            "name": meta["name"],
            "usd": coin.get("usd"),
            "usd_24h_change": coin.get("usd_24h_change"),
            "last_updated_at": coin.get("last_updated_at"),
        }

    return {
        "available": True,
        "source": "coingecko",
        "window_hours": hours,
        "prices": prices,
        "series": {"bitcoin": btc_series},
    }


def _fetch_current_prices() -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "ids": ",".join(COINS),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        }
    )
    return _fetch_json(f"{API_BASE}/simple/price?{query}")


def _fetch_bitcoin_series(hours: int) -> list[dict[str, float | int]]:
    now = int(time.time())
    start = now - hours * 3600
    query = urllib.parse.urlencode({"vs_currency": "usd", "from": start, "to": now})
    data = _fetch_json(f"{API_BASE}/coins/bitcoin/market_chart/range?{query}")
    points = data.get("prices", [])
    return [{"x": int(timestamp), "y": float(price)} for timestamp, price in points]


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "owlet-dashboard/0.1"})
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status >= 400:
            raise RuntimeError(f"CoinGecko returned HTTP {response.status}")
        import json

        return json.loads(response.read().decode("utf-8"))
