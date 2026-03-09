"""
Macro Cockpit Web Dashboard
Claude-style modern UI

Usage: python cockpit_web.py
"""
import sys
import os
import json
import asyncio
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Macro Cockpit")

# Stock code -> clean name mapping (pdfplumber garbles Korean)
STOCK_NAMES = {
    # KRW
    "A0008E0": {"ticker": "ACE ETF", "name": "ACE 미국장기국채선물"},
    "A001000": {"ticker": "신라섬유", "name": "신라섬유"},
    "A001260": {"ticker": "남광토건", "name": "남광토건"},
    "A001510": {"ticker": "SK증권", "name": "SK증권"},
    "A017670": {"ticker": "SKT", "name": "SK텔레콤"},
    "A039130": {"ticker": "하나투어", "name": "하나투어"},
    "A062040": {"ticker": "산일전기", "name": "산일전기"},
    "A068270": {"ticker": "셀트리온", "name": "셀트리온"},
    "A102120": {"ticker": "어보브반도체", "name": "어보브반도체"},
    "A282720": {"ticker": "금양그린파워", "name": "금양그린파워"},
    "A322000": {"ticker": "HD에너지", "name": "HD현대에너지솔루션"},
    "A357580": {"ticker": "AACR", "name": "아머코리아"},
    "A389260": {"ticker": "대명에너지", "name": "대명에너지"},
    # USD
    "US25461A3876": {"ticker": "KORU", "name": "Direxion 한국 3배"},
    "US25461A4452": {"ticker": "AGQ", "name": "ProShares 은 2배"},
    "US38747R8271": {"ticker": "GDXJ", "name": "VanEck 주니어금광"},
    "US46138E6288": {"ticker": "KBWB", "name": "인베스코 금융주 ETF"},
    "US46152A7182": {"ticker": "ISHG", "name": "iShares 단기국채"},
    "US4642875151": {"ticker": "IWM", "name": "iShares 러셀2000"},
    "US69608A1088": {"ticker": "PLTR", "name": "팔란티어"},
    "US74347W3530": {"ticker": "PRNT", "name": "3D프린팅 ETF"},
    "US74350P6759": {"ticker": "PSLV", "name": "스프롯 실물 은"},
    "CA85207K1075": {"ticker": "PSLV", "name": "스프롯 실물 은"},
    "US78409V1044": {"ticker": "SPY", "name": "S&P 500 ETF"},
    "US81369Y6059": {"ticker": "XLF", "name": "금융 셀렉트 ETF"},
    "US92189F7915": {"ticker": "VGSH", "name": "뱅가드 초단기금리"},
}


# yfinance ticker symbols for live price fetching
YFINANCE_MAP = {
    "A017670": "017670.KS",    # SK텔레콤
    "US69608A1088": "PLTR",
    "US46138E6288": "KBWB",
    "CA85207K1075": "PSLV",
    "US74350P6759": "PSLV",
    "US92189F7915": "VGSH",
    "US81369Y6059": "XLF",
    # A0008E0 (ACE ETF) - KRX code unknown from PDF, add manually if needed
}


def _clean(code, raw_name=""):
    info = STOCK_NAMES.get(code, {})
    return info.get("ticker", code[:8]), info.get("name", raw_name or code)


@app.get("/", response_class=HTMLResponse)
async def index():
    return (ROOT / "cockpit" / "templates" / "index.html").read_text("utf-8")


@app.get("/api/portfolio")
async def api_portfolio():
    try:
        json_path = ROOT / "Portfolio" / "portfolio_latest.json"
        if not json_path.exists():
            return {"status": "empty"}

        data = json.loads(json_path.read_text("utf-8"))
        holdings = []
        for code, h in data.get("holdings", {}).items():
            ticker, name = _clean(code, h.get("name", ""))
            is_usd = h.get("currency") == "USD"
            avg = h.get("avg_price_usd", 0) if is_usd else h.get("avg_price", 0)
            qty = h.get("quantity", 0)
            holdings.append({
                "code": code, "ticker": ticker, "name": name,
                "quantity": qty, "avg_price": avg,
                "est_value": round(qty * avg, 2),
                "currency": "USD" if is_usd else "KRW",
            })

        return {
            "status": "ok", "holdings": holdings,
            "cash": data.get("cash", {}),
            "meta": data.get("meta", {}),
            "tx_counts": {
                "krw": len(data.get("krw_transactions", [])),
                "usd": len(data.get("usd_transactions", [])),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/review")
async def api_review():
    try:
        json_path = ROOT / "Portfolio" / "portfolio_latest.json"
        if not json_path.exists():
            return {"status": "empty"}

        data = json.loads(json_path.read_text("utf-8"))
        from cockpit.trade_review import analyze_trades
        result = analyze_trades(data)

        for trade in result.get("closed_trades", []):
            t, n = _clean(trade.get("code", ""), trade.get("name", ""))
            trade["ticker"] = t
            trade["clean_name"] = n
        for pos in result.get("open_positions", []):
            t, n = _clean(pos.get("code", ""), pos.get("name", ""))
            pos["ticker"] = t
            pos["clean_name"] = n

        return {"status": "ok", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/signal")
async def api_signal():
    try:
        from cockpit.macro_signal import fetch_macro_data, generate_signals
        loop = asyncio.get_event_loop()
        macro_data = await loop.run_in_executor(None, fetch_macro_data)
        signals = generate_signals(macro_data)
        return {"status": "ok", "macro_data": macro_data, "signals": signals}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/digest")
async def api_digest():
    try:
        index_path = ROOT / "Insights_Archive" / "_digest_index.json"
        if not index_path.exists():
            return {"status": "empty"}
        idx = json.loads(index_path.read_text("utf-8"))
        results = sorted(idx.values(), key=lambda x: x.get("usefulness", 0), reverse=True)
        return {"status": "ok", "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/implications")
async def api_implications():
    try:
        impl_path = ROOT / "Insights_Archive" / "_portfolio_implications.json"
        if not impl_path.exists():
            return {"status": "empty"}
        data = json.loads(impl_path.read_text("utf-8"))
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/prices")
async def api_prices():
    """Fetch live prices for portfolio holdings via yfinance"""
    try:
        import yfinance as yf

        json_path = ROOT / "Portfolio" / "portfolio_latest.json"
        if not json_path.exists():
            return {"status": "empty"}
        data = json.loads(json_path.read_text("utf-8"))

        code_to_yf = {}
        for code in data.get("holdings", {}).keys():
            yf_sym = YFINANCE_MAP.get(code)
            if yf_sym:
                code_to_yf[code] = yf_sym

        if not code_to_yf:
            return {"status": "ok", "prices": {}}

        tickers = list(set(code_to_yf.values()))
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda: yf.download(tickers, period="5d", group_by="ticker", progress=False),
        )

        yf_prices = {}
        for yf_sym in tickers:
            try:
                td = df if len(tickers) == 1 else df[yf_sym]
                closes = td["Close"].dropna()
                if hasattr(closes, "columns"):
                    closes = closes.iloc[:, 0]
                if not closes.empty:
                    yf_prices[yf_sym] = round(float(closes.iloc[-1]), 2)
            except Exception:
                pass

        prices = {}
        for code, yf_sym in code_to_yf.items():
            if yf_sym in yf_prices:
                prices[code] = yf_prices[yf_sym]

        return {"status": "ok", "prices": prices}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import webbrowser
    print()
    print("  Macro Cockpit Web Dashboard")
    print("  http://localhost:8080")
    print()
    webbrowser.open("http://localhost:8080")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")
