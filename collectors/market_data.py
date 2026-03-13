"""
시장 데이터 수집 (yfinance)
"""
import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import WATCHLIST


def _get_full_watchlist():
    """기본 watchlist + 사용자 추가 종목 병합"""
    merged = dict(WATCHLIST)
    user_config_path = os.path.join(os.path.dirname(__file__), "..", "user_config.json")
    if os.path.exists(user_config_path):
        with open(user_config_path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        merged.update(user_cfg.get("extra_watchlist", {}))
    return merged


def fetch_market_snapshot():
    """관심 종목/지수의 현재 스냅샷 수집"""
    watchlist = _get_full_watchlist()
    results = []
    tickers = list(watchlist.keys())
    data = yf.download(tickers, period="5d", group_by="ticker", progress=False)

    for symbol, name in watchlist.items():
        try:
            if len(watchlist) == 1:
                ticker_data = data
            else:
                ticker_data = data[symbol]

            ticker_data = ticker_data.dropna()
            if ticker_data.empty:
                continue

            latest = ticker_data.iloc[-1]
            prev = ticker_data.iloc[-2] if len(ticker_data) > 1 else latest

            close = float(latest["Close"].iloc[0]) if hasattr(latest["Close"], "iloc") else float(latest["Close"])
            prev_close = float(prev["Close"].iloc[0]) if hasattr(prev["Close"], "iloc") else float(prev["Close"])
            change_pct = ((close - prev_close) / prev_close) * 100

            results.append({
                "symbol": symbol,
                "name": name,
                "price": close,
                "change_pct": round(change_pct, 2),
                "direction": "▲" if change_pct > 0 else "▼" if change_pct < 0 else "─",
            })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "name": name,
                "price": None,
                "change_pct": None,
                "direction": "?",
                "error": str(e),
            })

    return results


def format_market_table(snapshot):
    """시장 데이터를 텍스트 테이블로 포맷"""
    lines = []
    lines.append(f"{'종목':<12} {'가격':>14} {'등락률':>8}")
    lines.append("-" * 36)
    for item in snapshot:
        if item["price"] is not None:
            price_str = f"{item['price']:,.2f}"
            change_str = f"{item['direction']} {item['change_pct']:+.2f}%"
            lines.append(f"{item['name']:<12} {price_str:>14} {change_str:>8}")
        else:
            lines.append(f"{item['name']:<12} {'N/A':>14} {'N/A':>8}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("시장 데이터 수집 중...")
    snapshot = fetch_market_snapshot()
    print(format_market_table(snapshot))
