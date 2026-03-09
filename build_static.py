"""
정적 사이트 빌드 스크립트
GitHub Pages 배포용 docs/ 폴더에 데이터 JSON 생성

Usage:
    python build_static.py          # 전체 빌드
    python build_static.py --quick  # 매크로 시그널 스킵 (빠른 빌드)
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

DOCS = ROOT / "docs"
DATA = DOCS / "data"
DATA.mkdir(parents=True, exist_ok=True)


def build_portfolio():
    """포트폴리오 데이터 빌드"""
    json_path = ROOT / "Portfolio" / "portfolio_latest.json"
    if not json_path.exists():
        return {"status": "empty"}

    from cockpit_web import _clean
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


def build_review():
    """매매 리뷰 데이터 빌드"""
    json_path = ROOT / "Portfolio" / "portfolio_latest.json"
    if not json_path.exists():
        return {"status": "empty"}

    from cockpit_web import _clean
    from cockpit.trade_review import analyze_trades
    data = json.loads(json_path.read_text("utf-8"))
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


def build_signal():
    """매크로 시그널 데이터 빌드"""
    from cockpit.macro_signal import fetch_macro_data, generate_signals
    macro_data = fetch_macro_data()
    signals = generate_signals(macro_data)
    return {"status": "ok", "macro_data": macro_data, "signals": signals}


def build_digest():
    """PDF 인사이트 데이터 빌드"""
    index_path = ROOT / "Insights_Archive" / "_digest_index.json"
    if not index_path.exists():
        return {"status": "empty"}
    idx = json.loads(index_path.read_text("utf-8"))
    results = sorted(idx.values(), key=lambda x: x.get("usefulness", 0), reverse=True)
    return {"status": "ok", "data": results}


def build_implications():
    """포트폴리오 시사점 데이터 빌드"""
    impl_path = ROOT / "Insights_Archive" / "_portfolio_implications.json"
    if not impl_path.exists():
        return {"status": "empty"}
    data = json.loads(impl_path.read_text("utf-8"))
    return {"status": "ok", "data": data}


def build_prices():
    """실시간 가격 데이터 빌드"""
    import yfinance as yf
    from cockpit_web import YFINANCE_MAP

    json_path = ROOT / "Portfolio" / "portfolio_latest.json"
    if not json_path.exists():
        return {"status": "ok", "prices": {}}
    data = json.loads(json_path.read_text("utf-8"))

    code_to_yf = {}
    for code in data.get("holdings", {}).keys():
        yf_sym = YFINANCE_MAP.get(code)
        if yf_sym:
            code_to_yf[code] = yf_sym

    if not code_to_yf:
        return {"status": "ok", "prices": {}}

    # Add USDKRW exchange rate
    code_to_yf["__FX__"] = "USDKRW=X"

    tickers = list(set(code_to_yf.values()))
    df = yf.download(tickers, period="5d", group_by="ticker", progress=False)

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


def save(name, data):
    path = DATA / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [OK] {path.relative_to(ROOT)}")


def main():
    quick = "--quick" in sys.argv
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n  Static Build {'(QUICK)' if quick else ''} — {now}")
    print("  " + "=" * 40)

    save("portfolio", build_portfolio())
    save("review", build_review())
    save("digest", build_digest())
    save("implications", build_implications())

    if not quick:
        print("  Fetching macro signals...")
        save("signal", build_signal())
        print("  Fetching live prices...")
        save("prices", build_prices())
    else:
        print("  [SKIP] signal, prices (--quick)")

    # 빌드 메타 정보
    meta = {"built_at": now, "quick": quick}
    save("_meta", meta)

    print(f"\n  Build complete → {DOCS.relative_to(ROOT)}/")
    print()


if __name__ == "__main__":
    main()
