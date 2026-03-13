"""
migrate_to_supabase.py
======================
기존 JSON 데이터를 Supabase DB로 이관하는 마이그레이션 스크립트.

사용법:
    pip install supabase python-dotenv
    python scripts/migrate_to_supabase.py

데이터 소스:
    - docs/data/portfolio.json  -> holdings 테이블
    - docs/data/signal.json     -> signals 테이블
    - Insights_Archive/_digest_index.json -> digest_insights 테이블
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / "api.env"

# JSON 소스 파일 경로
PORTFOLIO_JSON = PROJECT_ROOT / "docs" / "data" / "portfolio.json"
SIGNAL_JSON = PROJECT_ROOT / "docs" / "data" / "signal.json"
DIGEST_INDEX_JSON = PROJECT_ROOT / "Insights_Archive" / "_digest_index.json"


def get_supabase_client() -> Client:
    """api.env에서 환경변수를 로드하고 Supabase 클라이언트를 생성한다."""
    load_dotenv(ENV_PATH)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # RLS bypass를 위해 service_role key 사용

    if not url or not key:
        print("[ERROR] SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 api.env에 없습니다.")
        sys.exit(1)

    return create_client(url, key)


# ---------------------------------------------------------------------------
# 1. portfolio.json -> holdings 테이블
# ---------------------------------------------------------------------------
def migrate_holdings(supabase: Client, user_id: str | None = None) -> int:
    """
    portfolio.json의 holdings 배열을 Supabase holdings 테이블로 이관.

    user_id가 None이면 holdings에 user_id 없이 삽입을 시도하는데,
    service_role key는 RLS를 우회하므로 직접 지정해야 합니다.
    첫 번째 auth.users 사용자를 자동으로 찾거나, 환경변수에서 가져옵니다.
    """
    if not PORTFOLIO_JSON.exists():
        print(f"[SKIP] {PORTFOLIO_JSON} 파일이 존재하지 않습니다.")
        return 0

    with open(PORTFOLIO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    holdings = data.get("holdings", [])
    if not holdings:
        print("[SKIP] portfolio.json에 holdings 데이터가 없습니다.")
        return 0

    # user_id 결정: 환경변수 > 자동 검색
    if not user_id:
        user_id = os.getenv("SUPABASE_DEFAULT_USER_ID")

    if not user_id:
        # auth.users에서 첫 번째 사용자 조회
        try:
            users_resp = supabase.auth.admin.list_users()
            if users_resp and len(users_resp) > 0:
                user_id = str(users_resp[0].id)
                print(f"[INFO] 자동 감지된 user_id: {user_id}")
        except Exception as e:
            print(f"[WARN] 사용자 자동 감지 실패: {e}")

    if not user_id:
        print("[ERROR] user_id를 결정할 수 없습니다.")
        print("        api.env에 SUPABASE_DEFAULT_USER_ID=<uuid> 를 추가하거나,")
        print("        Supabase Auth에 사용자를 먼저 등록하세요.")
        return 0

    # 섹터 매핑 (ticker -> sector)
    sector_map = {
        "NVDA": "Technology",
        "PLTR": "Technology",
        "KORU": "Leveraged ETF",
        "PSLV": "Commodities",
        "KBWB": "Financials",
        "XLF": "Financials",
        "ACE FT": "Financials",  # ACE 미국핀테크
    }

    rows = []
    for h in holdings:
        rows.append({
            "user_id": user_id,
            "ticker": h["ticker"],
            "name": h["name"],
            "quantity": h["quantity"],
            "avg_price": h["avg_price"],
            "currency": h.get("currency", "USD"),
            "sector": sector_map.get(h["ticker"], "Other"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    # upsert: 같은 user_id + ticker 조합이면 업데이트
    resp = supabase.table("holdings").upsert(
        rows,
        on_conflict="user_id,ticker"
    ).execute()

    count = len(resp.data) if resp.data else 0
    print(f"[OK] holdings: {count}건 upsert 완료")
    return count


# ---------------------------------------------------------------------------
# 2. signal.json -> signals 테이블
# ---------------------------------------------------------------------------
def migrate_signals(supabase: Client) -> int:
    """
    signal.json의 signals 배열을 Supabase signals 테이블로 이관.
    macro_data에서 변동률 데이터도 함께 매핑한다.
    """
    if not SIGNAL_JSON.exists():
        print(f"[SKIP] {SIGNAL_JSON} 파일이 존재하지 않습니다.")
        return 0

    with open(SIGNAL_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    signals = data.get("signals", [])
    macro_data = data.get("macro_data", [])

    if not signals:
        print("[SKIP] signal.json에 signals 데이터가 없습니다.")
        return 0

    # macro_data를 symbol 기준으로 인덱싱 (변동률 매핑용)
    macro_by_name = {}
    for m in macro_data:
        # indicator 이름과 매칭하기 위해 name과 symbol 모두 등록
        macro_by_name[m.get("symbol", "")] = m
        macro_by_name[m.get("name", "")] = m

    # indicator -> macro_data 키 매핑
    indicator_to_macro = {
        "VIX": "^VIX",
        "USD/KRW": "USDKRW=X",
        "NVDA": None,  # 개별 종목 - macro_data에 없음
        "Silver": "SI=F",
        "Oil (Murban proxy)": "BZ=F",
        "Financials": None,  # 복합 지표
        "KOSPI": "^KS11",
        "NASDAQ": "^IXIC",
    }

    now = datetime.now(timezone.utc).isoformat()
    rows = []

    for s in signals:
        indicator = s["indicator"]
        macro_key = indicator_to_macro.get(indicator)
        macro = macro_by_name.get(macro_key, {}) if macro_key else {}

        rows.append({
            "indicator": indicator,
            "value": s.get("value"),
            "change_1d": macro.get("chg_1d"),
            "change_1w": macro.get("chg_1w"),
            "change_1m": macro.get("chg_1m"),
            "level": s.get("level", "calm"),
            "message": s.get("message"),
            "captured_at": now,
        })

    resp = supabase.table("signals").insert(rows).execute()

    count = len(resp.data) if resp.data else 0
    print(f"[OK] signals: {count}건 insert 완료")
    return count


# ---------------------------------------------------------------------------
# 3. _digest_index.json -> digest_insights 테이블
# ---------------------------------------------------------------------------
def migrate_digest_insights(supabase: Client) -> int:
    """
    _digest_index.json의 각 PDF 분석 결과를 digest_insights 테이블로 이관.
    filename 기준 upsert로 중복 방지.
    """
    if not DIGEST_INDEX_JSON.exists():
        print(f"[SKIP] {DIGEST_INDEX_JSON} 파일이 존재하지 않습니다.")
        return 0

    with open(DIGEST_INDEX_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("[SKIP] _digest_index.json에 데이터가 없습니다.")
        return 0

    rows = []
    for filename, insight in data.items():
        rows.append({
            "filename": insight.get("filename", filename),
            "summary": insight.get("summary"),
            "usefulness": insight.get("usefulness"),
            "themes": insight.get("themes", []),
            "key_tickers": insight.get("key_tickers", []),
            "action_suggestion": insight.get("action_suggestion"),
            "source_type": insight.get("source_type"),
            "credibility": insight.get("credibility"),
            "macro_view": insight.get("macro_view"),
            "portfolio_relevance": insight.get("portfolio_relevance"),
            "created_at": insight.get("analyzed_at", datetime.now(timezone.utc).isoformat()),
        })

    # upsert on filename (UNIQUE constraint)
    resp = supabase.table("digest_insights").upsert(
        rows,
        on_conflict="filename"
    ).execute()

    count = len(resp.data) if resp.data else 0
    print(f"[OK] digest_insights: {count}건 upsert 완료")
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Supabase 마이그레이션 시작")
    print(f"ENV: {ENV_PATH}")
    print("=" * 60)

    supabase = get_supabase_client()

    total = 0
    total += migrate_holdings(supabase)
    total += migrate_signals(supabase)
    total += migrate_digest_insights(supabase)

    print("=" * 60)
    print(f"마이그레이션 완료. 총 {total}건 처리.")
    print("=" * 60)


if __name__ == "__main__":
    main()
