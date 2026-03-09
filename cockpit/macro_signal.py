"""
매크로 신호등 시스템
- 주요 매크로 지표 수집 (yfinance)
- 포트폴리오 연관 시그널 생성
- VIX, 환율, 금리, 원자재 모니터링
"""
import os
import json
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd


# 매크로 지표 정의
MACRO_INDICATORS = {
    # 변동성
    "^VIX": {"name": "VIX (변동성)", "category": "volatility"},
    # 미국 금리
    "^TNX": {"name": "미국 10Y 국채금리", "category": "rate"},
    "^FVX": {"name": "미국 5Y 국채금리", "category": "rate"},
    # 달러
    "DX-Y.NYB": {"name": "달러 인덱스(DXY)", "category": "currency"},
    "USDKRW=X": {"name": "USD/KRW 환율", "category": "currency"},
    # 원자재
    "GC=F": {"name": "금(Gold)", "category": "commodity"},
    "SI=F": {"name": "은(Silver)", "category": "commodity"},
    "CL=F": {"name": "WTI 원유", "category": "commodity"},
    "BZ=F": {"name": "브렌트 원유", "category": "commodity"},
    # 지수
    "^GSPC": {"name": "S&P 500", "category": "index"},
    "^IXIC": {"name": "NASDAQ", "category": "index"},
    "^KS11": {"name": "KOSPI", "category": "index"},
}


def fetch_macro_data():
    """매크로 지표 일괄 수집"""
    tickers = list(MACRO_INDICATORS.keys())
    results = []

    data = yf.download(tickers, period="1mo", group_by="ticker", progress=False)

    for symbol, info in MACRO_INDICATORS.items():
        try:
            if len(MACRO_INDICATORS) == 1:
                ticker_data = data
            else:
                ticker_data = data[symbol]

            ticker_data = ticker_data.dropna()
            if ticker_data.empty:
                continue

            closes = ticker_data["Close"]
            if hasattr(closes, "columns"):
                closes = closes.iloc[:, 0]

            latest = float(closes.iloc[-1])
            prev_1d = float(closes.iloc[-2]) if len(closes) > 1 else latest
            prev_1w = float(closes.iloc[-5]) if len(closes) > 5 else prev_1d
            prev_1m = float(closes.iloc[0])

            chg_1d = ((latest - prev_1d) / prev_1d) * 100
            chg_1w = ((latest - prev_1w) / prev_1w) * 100
            chg_1m = ((latest - prev_1m) / prev_1m) * 100

            # 20일 이동평균
            sma20 = float(closes.tail(20).mean()) if len(closes) >= 20 else float(closes.mean())
            above_sma20 = latest > sma20

            results.append({
                "symbol": symbol,
                "name": info["name"],
                "category": info["category"],
                "price": round(latest, 2),
                "chg_1d": round(chg_1d, 2),
                "chg_1w": round(chg_1w, 2),
                "chg_1m": round(chg_1m, 2),
                "sma20": round(sma20, 2),
                "above_sma20": above_sma20,
            })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "name": info["name"],
                "category": info["category"],
                "price": None,
                "error": str(e),
            })

    return results


def generate_signals(macro_data, holdings=None):
    """
    매크로 데이터 + 포트폴리오 기반 시그널 생성

    Returns:
        list of dict: 시그널 목록
    """
    signals = []
    lookup = {d["symbol"]: d for d in macro_data if d.get("price")}

    # --- VIX 시그널 ---
    vix = lookup.get("^VIX")
    if vix:
        level = vix["price"]
        if level > 30:
            signals.append({
                "indicator": "VIX",
                "level": "danger",
                "value": level,
                "message": f"VIX {level:.1f} - 극심한 공포. 신규 매수 자제, 현금 확보 우선",
            })
        elif level > 20:
            signals.append({
                "indicator": "VIX",
                "level": "caution",
                "value": level,
                "message": f"VIX {level:.1f} - 불안정. 분할매수 가능, 큰 포지션 주의",
            })
        else:
            signals.append({
                "indicator": "VIX",
                "level": "calm",
                "value": level,
                "message": f"VIX {level:.1f} - 안정적. 정상 매매 환경",
            })

    # --- 환율 시그널 (USDKRW) ---
    usdkrw = lookup.get("USDKRW=X")
    if usdkrw:
        rate = usdkrw["price"]
        chg = usdkrw["chg_1w"]
        if rate > 1450:
            signals.append({
                "indicator": "USD/KRW",
                "level": "caution",
                "value": rate,
                "message": f"환율 {rate:.0f}원 (주간 {chg:+.1f}%) - 고환율 구간. 해외주식 추가 매수 환율 부담",
            })
        elif rate < 1350:
            signals.append({
                "indicator": "USD/KRW",
                "level": "favorable",
                "value": rate,
                "message": f"환율 {rate:.0f}원 (주간 {chg:+.1f}%) - 저환율. 해외주식 매수 유리",
            })
        else:
            signals.append({
                "indicator": "USD/KRW",
                "level": "neutral",
                "value": rate,
                "message": f"환율 {rate:.0f}원 (주간 {chg:+.1f}%) - 중립 구간",
            })

    # --- 은(Silver) 시그널 - PSLV 관련 ---
    silver = lookup.get("SI=F")
    if silver:
        signals.append({
            "indicator": "Silver",
            "level": "bullish" if silver["above_sma20"] else "bearish",
            "value": silver["price"],
            "message": (
                f"은 ${silver['price']:.2f} (월간 {silver['chg_1m']:+.1f}%) "
                f"{'SMA20 위 - 상승 추세' if silver['above_sma20'] else 'SMA20 아래 - 조정 구간'}"
                f" [PSLV 35주 보유 중]"
            ),
        })

    # --- 금(Gold) 시그널 - GDXJ 관련 ---
    gold = lookup.get("GC=F")
    if gold:
        signals.append({
            "indicator": "Gold",
            "level": "bullish" if gold["above_sma20"] else "bearish",
            "value": gold["price"],
            "message": (
                f"금 ${gold['price']:.2f} (월간 {gold['chg_1m']:+.1f}%) "
                f"{'SMA20 위' if gold['above_sma20'] else 'SMA20 아래'}"
                f" [GDXJ 2주 보유 중]"
            ),
        })

    # --- 원유 시그널 (Murban 프록시: 브렌트) ---
    brent = lookup.get("BZ=F")
    wti = lookup.get("CL=F")
    if brent and wti:
        spread = brent["price"] - wti["price"]
        signals.append({
            "indicator": "Oil (Murban proxy)",
            "level": "info",
            "value": brent["price"],
            "message": (
                f"브렌트 ${brent['price']:.2f} / WTI ${wti['price']:.2f} "
                f"(스프레드 ${spread:.2f}, 월간 {brent['chg_1m']:+.1f}%)"
            ),
        })

    # --- 금리 시그널 ---
    tnx = lookup.get("^TNX")
    if tnx:
        rate = tnx["price"]
        chg = tnx["chg_1m"]
        direction = "상승" if chg > 0 else "하락"
        signals.append({
            "indicator": "US 10Y",
            "level": "caution" if rate > 4.5 else "neutral",
            "value": rate,
            "message": (
                f"미국 10년물 {rate:.2f}% (월간 {chg:+.2f}%p {direction}) "
                f"[금융주(KBWB/XLF) {'유리' if chg > 0 else '주의'}]"
            ),
        })

    # --- KOSPI 시그널 ---
    kospi = lookup.get("^KS11")
    if kospi:
        signals.append({
            "indicator": "KOSPI",
            "level": "bullish" if kospi["above_sma20"] else "bearish",
            "value": kospi["price"],
            "message": (
                f"KOSPI {kospi['price']:.0f} (월간 {kospi['chg_1m']:+.1f}%) "
                f"{'SMA20 위 - 상승 추세' if kospi['above_sma20'] else 'SMA20 아래 - 약세'}"
                f" [ACE ETF 150주 보유 중]"
            ),
        })

    # --- NASDAQ 시그널 - 팔란티어 관련 ---
    nasdaq = lookup.get("^IXIC")
    if nasdaq:
        signals.append({
            "indicator": "NASDAQ",
            "level": "bullish" if nasdaq["above_sma20"] else "bearish",
            "value": nasdaq["price"],
            "message": (
                f"나스닥 {nasdaq['price']:,.0f} (월간 {nasdaq['chg_1m']:+.1f}%) "
                f"{'SMA20 위' if nasdaq['above_sma20'] else 'SMA20 아래'}"
                f" [PLTR 14주 보유 중]"
            ),
        })

    return signals


# --- 포맷팅 ---

LEVEL_ICONS = {
    "danger": "[!!!]",
    "caution": "[! ]",
    "calm": "[ o ]",
    "favorable": "[ + ]",
    "neutral": "[ - ]",
    "bullish": "[ ^ ]",
    "bearish": "[ v ]",
    "info": "[ i ]",
}


def format_signals(macro_data, signals):
    """매크로 대시보드 + 시그널 텍스트 생성"""
    lines = []
    lines.append("=" * 65)
    lines.append("  MACRO COCKPIT")
    lines.append("=" * 65)

    # 카테고리별 지표 테이블
    categories = {
        "index": "Market Index",
        "volatility": "Volatility",
        "rate": "Interest Rate",
        "currency": "Currency",
        "commodity": "Commodity",
    }

    for cat_key, cat_name in categories.items():
        items = [d for d in macro_data if d.get("category") == cat_key and d.get("price")]
        if not items:
            continue
        lines.append(f"\n[{cat_name}]")
        lines.append(f"  {'지표':<22} {'현재가':>12} {'1D':>8} {'1W':>8} {'1M':>8} {'SMA20':>6}")
        lines.append("  " + "-" * 66)
        for d in items:
            sma_mark = "^" if d.get("above_sma20") else "v"
            lines.append(
                f"  {d['name']:<22} {d['price']:>12,.2f} "
                f"{d['chg_1d']:>+7.1f}% {d['chg_1w']:>+7.1f}% {d['chg_1m']:>+7.1f}% "
                f"   {sma_mark}"
            )

    # 시그널
    if signals:
        lines.append(f"\n{'=' * 65}")
        lines.append("  SIGNALS")
        lines.append("=" * 65)
        for sig in signals:
            icon = LEVEL_ICONS.get(sig["level"], "[ ? ]")
            lines.append(f"  {icon} {sig['message']}")

    lines.append("\n" + "=" * 65)
    lines.append(f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 65)
    return "\n".join(lines)


# --- CLI ---

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching macro data...")
    macro_data = fetch_macro_data()
    signals = generate_signals(macro_data)
    print(format_signals(macro_data, signals))
