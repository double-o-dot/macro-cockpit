"""
실시간 가격 업데이트 스크립트
- 포트폴리오 보유 종목 + config.py watchlist 가격을 일괄 수집
- 미국 주식: yfinance
- 한국 주식: 한국투자증권 KIS API (kis_client.py)
- 결과를 docs/data/prices.json으로 저장
"""
import os
import sys
import json
from datetime import datetime

import yfinance as yf

# 프로젝트 루트를 PYTHONPATH에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import WATCHLIST

# KIS API (한국 주식용)
try:
    from api.kis_client import get_token, _headers, BASE_URL, APP_KEY
    import requests as _requests
    KIS_AVAILABLE = True
except Exception:
    KIS_AVAILABLE = False

# 경로 설정
PORTFOLIO_PATH = os.path.join(PROJECT_ROOT, "docs", "data", "portfolio.json")
PRICES_PATH = os.path.join(PROJECT_ROOT, "docs", "data", "prices.json")


# ---------------------------------------------------------------------------
# 데이터 로딩
# ---------------------------------------------------------------------------

def load_portfolio_tickers():
    """portfolio.json에서 보유 종목 티커 + 이름 추출, 통화 구분 포함"""
    if not os.path.exists(PORTFOLIO_PATH):
        print("[WARN] portfolio.json 없음 - 보유 종목 건너뜀")
        return []

    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    holdings = []
    for h in data.get("holdings", []):
        ticker = h.get("ticker", "")
        name = h.get("name", "")
        currency = h.get("currency", "USD")
        code = h.get("code", "")
        holdings.append({
            "ticker": ticker,
            "name": name,
            "currency": currency,
            "code": code,
        })
    return holdings


def load_watchlist_tickers():
    """config.py WATCHLIST에서 관심 종목 추출"""
    items = []
    for symbol, name in WATCHLIST.items():
        # 통화 판별: .KS/.KQ 접미사 = KRW, 그 외 USD
        if symbol.endswith(".KS") or symbol.endswith(".KQ"):
            currency = "KRW"
        else:
            currency = "USD"
        items.append({
            "ticker": symbol,
            "name": name,
            "currency": currency,
            "code": "",
        })
    return items


# ---------------------------------------------------------------------------
# 미국 주식 가격 (yfinance)
# ---------------------------------------------------------------------------

def fetch_us_prices(tickers_info):
    """yfinance를 사용하여 미국 주식/ETF 가격 일괄 조회

    Args:
        tickers_info: list of dict, 각각 ticker/name/currency/code 키 포함

    Returns:
        list of dict: 가격 정보 리스트
    """
    if not tickers_info:
        return []

    symbols = [t["ticker"] for t in tickers_info]
    name_map = {t["ticker"]: t["name"] for t in tickers_info}
    currency_map = {t["ticker"]: t["currency"] for t in tickers_info}

    results = []

    # yfinance 일괄 다운로드 (최근 5일 + 52주 범위용 1년)
    try:
        # 52주 고/저 계산을 위해 1년치 데이터
        data_1y = yf.download(symbols, period="1y", group_by="ticker", progress=False)
        # 최근 5일 (전일 종가 비교용)
        data_5d = yf.download(symbols, period="5d", group_by="ticker", progress=False)
    except Exception as e:
        print(f"[ERROR] yfinance 다운로드 실패: {e}")
        return results

    for info in tickers_info:
        symbol = info["ticker"]
        try:
            # 데이터 추출 (단일 종목 vs 복수 종목 처리)
            if len(symbols) == 1:
                td_1y = data_1y
                td_5d = data_5d
            else:
                td_1y = data_1y[symbol]
                td_5d = data_5d[symbol]

            td_1y = td_1y.dropna()
            td_5d = td_5d.dropna()

            if td_5d.empty:
                print(f"  [SKIP] {symbol} - 데이터 없음")
                continue

            # 현재가 (가장 최근 종가)
            close_series = td_5d["Close"]
            if hasattr(close_series, "columns"):
                close_series = close_series.iloc[:, 0]

            current_price = float(close_series.iloc[-1])
            prev_close = float(close_series.iloc[-2]) if len(close_series) > 1 else current_price
            change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

            # 52주 고/저
            high_series = td_1y["High"]
            low_series = td_1y["Low"]
            if hasattr(high_series, "columns"):
                high_series = high_series.iloc[:, 0]
            if hasattr(low_series, "columns"):
                low_series = low_series.iloc[:, 0]

            high_52w = float(high_series.max())
            low_52w = float(low_series.min())

            # 거래량
            vol_series = td_5d["Volume"]
            if hasattr(vol_series, "columns"):
                vol_series = vol_series.iloc[:, 0]
            volume = int(vol_series.iloc[-1])

            results.append({
                "ticker": symbol,
                "name": name_map.get(symbol, symbol),
                "currency": currency_map.get(symbol, "USD"),
                "current_price": round(current_price, 2),
                "prev_close": round(prev_close, 2),
                "change_pct": change_pct,
                "high_52w": round(high_52w, 2),
                "low_52w": round(low_52w, 2),
                "volume": volume,
            })
            print(f"  [OK] {symbol}: {current_price:.2f}")

        except Exception as e:
            print(f"  [SKIP] {symbol} - {e}")

    return results


# ---------------------------------------------------------------------------
# 한국 주식 가격 (KIS API)
# ---------------------------------------------------------------------------

def fetch_kr_price_kis(stock_code):
    """KIS API로 한국 주식 현재가 조회

    Args:
        stock_code: 종목코드 (6자리, 예: '461300')

    Returns:
        dict or None
    """
    if not KIS_AVAILABLE:
        return None

    try:
        headers = _headers("FHKST01010100")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }
        resp = _requests.get(
            f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

        output = data.get("output", {})
        if not output:
            return None

        current_price = int(output.get("stck_prpr", 0))
        prev_close = int(output.get("stck_sdpr", 0))
        high_52w = int(output.get("stck_dryy_hgpr", 0))
        low_52w = int(output.get("stck_dryy_lwpr", 0))
        volume = int(output.get("acml_vol", 0))

        change_pct = 0.0
        if prev_close > 0:
            change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

        return {
            "current_price": current_price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "volume": volume,
        }
    except Exception as e:
        print(f"  [KIS ERROR] {stock_code}: {e}")
        return None


def fetch_kr_prices(tickers_info):
    """한국 주식 가격 일괄 조회

    Args:
        tickers_info: list of dict (ticker, name, currency, code)

    Returns:
        list of dict
    """
    results = []

    for info in tickers_info:
        # 종목코드 추출: code가 'A461300' 형태면 앞 'A' 제거
        code = info.get("code", "")
        if code.startswith("A"):
            code = code[1:]
        elif not code:
            # ticker에서 추출 시도 (숫자 6자리)
            ticker = info.get("ticker", "")
            digits = "".join(c for c in ticker if c.isdigit())
            if len(digits) == 6:
                code = digits

        if not code:
            print(f"  [SKIP] {info['ticker']} - 한국 종목코드 없음")
            continue

        price_data = fetch_kr_price_kis(code)
        if price_data:
            results.append({
                "ticker": info["ticker"],
                "name": info["name"],
                "currency": "KRW",
                "current_price": price_data["current_price"],
                "prev_close": price_data["prev_close"],
                "change_pct": price_data["change_pct"],
                "high_52w": price_data["high_52w"],
                "low_52w": price_data["low_52w"],
                "volume": price_data["volume"],
            })
            print(f"  [OK] {info['ticker']} ({code}): {price_data['current_price']:,}")
        else:
            print(f"  [SKIP] {info['ticker']} ({code}) - KIS API 응답 없음")

    return results


# ---------------------------------------------------------------------------
# 환율 조회
# ---------------------------------------------------------------------------

def fetch_fx_rate():
    """USD/KRW 환율 조회 (yfinance)"""
    try:
        data = yf.download("USDKRW=X", period="5d", progress=False)
        data = data.dropna()
        if data.empty:
            return None
        close = data["Close"]
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        rate = float(close.iloc[-1])
        print(f"  [OK] USD/KRW: {rate:.2f}")
        return round(rate, 2)
    except Exception as e:
        print(f"  [WARN] 환율 조회 실패: {e}")
        return None


# ---------------------------------------------------------------------------
# 메인 실행
# ---------------------------------------------------------------------------

def main():
    print("=" * 50)
    print("  주식 가격 업데이트")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1) 보유 종목 + 관심 종목 수집
    portfolio_items = load_portfolio_tickers()
    watchlist_items = load_watchlist_tickers()

    # 2) 통화별 분류
    us_holdings = [t for t in portfolio_items if t["currency"] == "USD"]
    kr_holdings = [t for t in portfolio_items if t["currency"] == "KRW"]
    # watchlist 종목 중 holdings에 이미 있는 것은 제외
    holding_tickers = {t["ticker"] for t in portfolio_items}
    us_watchlist = [t for t in watchlist_items if t["ticker"] not in holding_tickers]

    print(f"\n보유 종목: US={len(us_holdings)}, KR={len(kr_holdings)}")
    print(f"관심 종목: {len(us_watchlist)}")

    # 3) 미국 주식 가격 조회
    print("\n[미국 주식 - yfinance]")
    us_holding_prices = fetch_us_prices(us_holdings)

    print("\n[관심 종목/지수 - yfinance]")
    watchlist_prices = fetch_us_prices(us_watchlist)

    # 4) 한국 주식 가격 조회
    print("\n[한국 주식 - KIS API]")
    if KIS_AVAILABLE:
        kr_holding_prices = fetch_kr_prices(kr_holdings)
    else:
        print("  [WARN] KIS API 사용 불가 - yfinance fallback 시도")
        # 한국 종목을 yfinance로 시도 (제한적)
        kr_yf_items = []
        for item in kr_holdings:
            code = item.get("code", "")
            if code.startswith("A"):
                code = code[1:]
            if code:
                kr_yf_items.append({
                    "ticker": f"{code}.KS",
                    "name": item["name"],
                    "currency": "KRW",
                    "code": item.get("code", ""),
                })
        kr_holding_prices = fetch_us_prices(kr_yf_items) if kr_yf_items else []

    # 5) 환율 조회
    print("\n[환율]")
    fx_rate = fetch_fx_rate()

    # 6) 결과 조합
    all_holdings = us_holding_prices + kr_holding_prices
    all_watchlist = watchlist_prices

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "fx_usdkrw": fx_rate,
        "holdings": all_holdings,
        "watchlist": all_watchlist,
    }

    # 7) 저장
    os.makedirs(os.path.dirname(PRICES_PATH), exist_ok=True)
    with open(PRICES_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 50}")
    print(f"  저장 완료: {PRICES_PATH}")
    print(f"  보유 종목: {len(all_holdings)}개")
    print(f"  관심 종목: {len(all_watchlist)}개")
    print(f"  환율: {fx_rate}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
