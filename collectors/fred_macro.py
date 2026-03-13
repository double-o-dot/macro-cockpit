"""
FRED 매크로 경제 데이터 수집기
──────────────────────────────
fredapi 패키지를 사용하여 30+ 거시경제 지표를 수집하고,
카테고리별 종합 점수와 함께 docs/data/macro.json으로 출력한다.

사용법:
    python collectors/fred_macro.py
"""

import os
import sys
import json
import math
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

# ─── 프로젝트 루트 ───
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ─── 환경변수 로드 ───
load_dotenv(os.path.join(PROJECT_ROOT, "api.env"))
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

if not FRED_API_KEY or FRED_API_KEY.startswith("YOUR_"):
    print("ERROR: FRED_API_KEY가 설정되지 않았습니다.")
    print("  1. https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료 키 발급")
    print("  2. api.env 파일에 FRED_API_KEY=발급받은키 형태로 입력")
    sys.exit(1)

from fredapi import Fred  # noqa: E402

fred = Fred(api_key=FRED_API_KEY)

# ─── 경로 ───
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "docs", "data", "macro.json")
SIGNAL_PATH = os.path.join(PROJECT_ROOT, "docs", "data", "signal.json")

# ─── 데이터 수집 기간 ───
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=730)  # 2년

# ═══════════════════════════════════════════════════════════════
# 지표 정의 (6 카테고리, 33개 시리즈)
# ═══════════════════════════════════════════════════════════════

INDICATOR_DEFS = {
    "liquidity": {
        "name": "유동성 (Liquidity)",
        "description": "통화량, Fed 밸런스시트, 역레포 등 시중 유동성 수준",
        "korea_summary": "유동성 확장 시 외국인 자금 한국 유입 가능성 증가",
        "weight": 0.20,
        "indicators": [
            {
                "fred_id": "M2SL",
                "name": "M2 통화량",
                "description": "미국 광의통화. 현금+예금+MMF 총합",
                "how_to_read": "MoM 증가 -> 유동성 풍부, 자산가격 상승 압력. 감소 -> 긴축 신호",
                "korea_impact": "글로벌 유동성 증가 시 외국인 한국 유입 가능성 상승",
                "unit": "십억 USD",
                "frequency": "monthly",
                "positive_when": "rising",  # 이 지표가 '좋은' 상태 방향
            },
            {
                "fred_id": "WALCL",
                "name": "Fed 총자산 (밸런스시트)",
                "description": "연준 보유 자산 총액. QE/QT 규모 판단 핵심",
                "how_to_read": "증가 -> 양적완화(QE), 자산가격 지지. 감소 -> 양적긴축(QT)",
                "korea_impact": "Fed 자산 축소 시 글로벌 달러 유동성 감소, 신흥국 자금유출 압력",
                "unit": "백만 USD",
                "frequency": "weekly",
                "positive_when": "rising",
            },
            {
                "fred_id": "RRPONTSYD",
                "name": "역레포 잔고 (ON RRP)",
                "description": "연준 역레포 잔고. 금융기관 잉여 현금의 안전 보관소",
                "how_to_read": "감소 -> 자금이 시장으로 이동, 유동성 공급. 증가 -> 자금이 연준으로 회수",
                "korea_impact": "역레포 감소는 글로벌 리스크온 신호, 한국 자산 수혜 가능",
                "unit": "십억 USD",
                "frequency": "daily",
                "positive_when": "falling",  # 역레포 감소가 긍정적
            },
            {
                "fred_id": "BOGMBASE",
                "name": "본원통화 (Monetary Base)",
                "description": "중앙은행이 직접 공급한 화폐. 은행 지준 + 유통화폐",
                "how_to_read": "증가 -> 중앙은행 자금 공급 확대. 감소 -> 통화 긴축",
                "korea_impact": "본원통화 확대는 글로벌 달러 풍부, 원화 강세 요인",
                "unit": "십억 USD",
                "frequency": "monthly",
                "positive_when": "rising",
            },
            {
                "fred_id": "WRESBAL",
                "name": "은행 지급준비금",
                "description": "은행이 연준에 예치한 준비금. 은행간 유동성 지표",
                "how_to_read": "증가 -> 은행 유동성 풍부, 대출 여력 확대. 감소 -> 은행 긴축",
                "korea_impact": "미국 은행 유동성 악화 시 글로벌 달러 조달 비용 상승",
                "unit": "십억 USD",
                "frequency": "weekly",
                "positive_when": "rising",
            },
        ],
    },
    "inflation": {
        "name": "인플레이션 (Inflation)",
        "description": "소비자물가, 생산자물가, 기대인플레이션 등",
        "korea_summary": "인플레이션 재상승 시 Fed 긴축 장기화, 원화 약세 및 금리 부담 확대",
        "weight": 0.20,
        "indicators": [
            {
                "fred_id": "CPIAUCSL",
                "name": "CPI (소비자물가지수)",
                "description": "도시 소비자 전체 항목 물가지수",
                "how_to_read": "YoY 2% 부근이 Fed 목표. 상승 -> 긴축 장기화. 하락 -> 완화 기대",
                "korea_impact": "CPI 급등 -> Fed 긴축 지속 -> 원화 약세 + 수출주 타격",
                "unit": "지수",
                "frequency": "monthly",
                "positive_when": "falling",  # 인플레 하락이 긍정적(시장관점)
            },
            {
                "fred_id": "CPILFESL",
                "name": "Core CPI (식품/에너지 제외)",
                "description": "변동성 큰 식품/에너지 제외 근원물가",
                "how_to_read": "Fed가 가장 주시하는 물가 지표. 끈적한 인플레 판단 핵심",
                "korea_impact": "Core CPI 고착화 시 금리인하 지연, 한국 금리도 동반 고착",
                "unit": "지수",
                "frequency": "monthly",
                "positive_when": "falling",
            },
            {
                "fred_id": "PPIACO",
                "name": "PPI (생산자물가 - 전체 상품)",
                "description": "생산단계 물가. CPI의 선행지표 역할",
                "how_to_read": "PPI 상승 -> 향후 CPI 상승 압력. 하락 -> 디스인플레이션 신호",
                "korea_impact": "PPI 상승은 미국 제조업 원가 부담, 한국 수출품 경쟁력 변동",
                "unit": "지수",
                "frequency": "monthly",
                "positive_when": "falling",
            },
            {
                "fred_id": "PCEPILFE",
                "name": "Core PCE",
                "description": "개인소비지출 물가(근원). Fed의 공식 인플레 목표 지표",
                "how_to_read": "Fed 목표 2%. 이 지표가 가장 중요한 인플레 판단 기준",
                "korea_impact": "Core PCE 하락 -> 금리인하 기대 -> 원화 강세, KOSPI 수혜",
                "unit": "지수",
                "frequency": "monthly",
                "positive_when": "falling",
            },
            {
                "fred_id": "T10YIE",
                "name": "10년 기대인플레이션 (BEI)",
                "description": "10년 국채 - TIPS 스프레드. 시장의 인플레 기대치",
                "how_to_read": "2.0~2.5%가 정상. 급등 -> 인플레 우려 재부상. 급락 -> 디플레 우려",
                "korea_impact": "기대인플레 급등 시 실질금리 변동으로 외국인 채권투자 영향",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "stable",
            },
            {
                "fred_id": "T5YIE",
                "name": "5년 기대인플레이션 (BEI)",
                "description": "5년 국채 - TIPS 스프레드. 중기 인플레 기대",
                "how_to_read": "10Y BEI보다 민감. 단기 인플레 기대 변화를 빠르게 반영",
                "korea_impact": "5Y BEI 급등은 단기 긴축 강화 신호, 신흥국 자본유출 위험",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "stable",
            },
        ],
    },
    "rates": {
        "name": "금리 & 수익률곡선 (Rates & Yield Curve)",
        "description": "연방기금금리, 국채 수익률, 장단기 스프레드",
        "korea_summary": "미국 금리 인하 시 한미 금리차 축소로 원화 강세, 외국인 유입 기대",
        "weight": 0.20,
        "indicators": [
            {
                "fred_id": "FEDFUNDS",
                "name": "연방기금금리 (Fed Funds Rate)",
                "description": "연준 기준금리. 모든 금리의 기준점",
                "how_to_read": "인하 -> 경기부양/자산가격 상승. 인상 -> 긴축/자산가격 하락 압력",
                "korea_impact": "FFR 인하 시 한미 금리차 축소, 외국인 자금 유입 기대",
                "unit": "%",
                "frequency": "monthly",
                "positive_when": "falling",
            },
            {
                "fred_id": "DGS2",
                "name": "2년 국채 수익률",
                "description": "단기 금리. Fed 정책 기대를 가장 잘 반영",
                "how_to_read": "하락 -> 금리인하 기대 증가. 상승 -> 추가 긴축 가능성",
                "korea_impact": "2Y 급락은 금리인하 시그널, 한국 성장주 수혜",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "falling",
            },
            {
                "fred_id": "DGS5",
                "name": "5년 국채 수익률",
                "description": "중기 금리. 경기 전망을 반영",
                "how_to_read": "장기물 대비 움직임으로 경기 전망 판단",
                "korea_impact": "5Y 하락세는 중기 경기둔화 전망, 방어주 선호 구간",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "falling",
            },
            {
                "fred_id": "DGS10",
                "name": "10년 국채 수익률",
                "description": "장기 금리. 경제 성장률+인플레 기대 반영",
                "how_to_read": "하락 -> 경기둔화/디스인플레 기대. 상승 -> 성장+인플레 기대",
                "korea_impact": "10Y 상승은 글로벌 채권 금리 동반 상승, 부동산/성장주 부담",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "falling",
            },
            {
                "fred_id": "DGS30",
                "name": "30년 국채 수익률",
                "description": "초장기 금리. 장기 성장/인플레 기대",
                "how_to_read": "10Y 대비 스프레드로 텀프리미엄 판단",
                "korea_impact": "30Y 급등은 재정 우려 신호, 글로벌 안전자산 선호 변화",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "falling",
            },
            {
                "fred_id": "T10Y2Y",
                "name": "10Y-2Y 스프레드",
                "description": "장단기 금리차. 경기침체 선행지표",
                "how_to_read": "역전(마이너스) -> 경기침체 경고. 정상화(양전환) -> 침체 임박 또는 회복 시작",
                "korea_impact": "10Y-2Y 역전 -> 경기침체 신호, KOSPI 하방 압력",
                "unit": "%p",
                "frequency": "daily",
                "positive_when": "rising",  # 정상화 방향이 긍정적
            },
            {
                "fred_id": "T10Y3M",
                "name": "10Y-3M 스프레드",
                "description": "10년-3개월 금리차. 가장 정확한 침체 예측 지표",
                "how_to_read": "역전 -> 12~18개월 내 경기침체 확률 상승. 양전환 -> 회복 신호",
                "korea_impact": "3M 스프레드 역전은 가장 강력한 침체 경고, 한국 수출 타격 예고",
                "unit": "%p",
                "frequency": "daily",
                "positive_when": "rising",
            },
        ],
    },
    "credit": {
        "name": "신용 & 금융환경 (Credit & Financial Conditions)",
        "description": "하이일드 스프레드, 투자등급 스프레드, 금융환경지수, 금융스트레스",
        "korea_summary": "신용 스프레드 확대 시 글로벌 리스크오프, 한국 외국인 매도 압력 증가",
        "weight": 0.15,
        "indicators": [
            {
                "fred_id": "BAMLH0A0HYM2",
                "name": "하이일드 스프레드 (HY OAS)",
                "description": "하이일드 채권 - 국채 스프레드. 신용 리스크 체온계",
                "how_to_read": "축소 -> 리스크온, 신용 양호. 확대 -> 리스크오프, 신용 경색 우려",
                "korea_impact": "HY 스프레드 확대는 글로벌 위험회피, 한국 주식 외국인 매도 촉발",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "falling",  # 스프레드 축소가 긍정적
            },
            {
                "fred_id": "BAMLC0A0CM",
                "name": "투자등급 스프레드 (IG OAS)",
                "description": "투자등급 채권 - 국채 스프레드",
                "how_to_read": "확대 -> 우량기업도 자금조달 비용 증가. 축소 -> 신용환경 양호",
                "korea_impact": "IG 스프레드 확대는 기업 투자 위축, 글로벌 경기둔화 신호",
                "unit": "%",
                "frequency": "daily",
                "positive_when": "falling",
            },
            {
                "fred_id": "NFCI",
                "name": "시카고 Fed 금융환경지수 (NFCI)",
                "description": "시카고 Fed 발표 금융환경지수. 금리/스프레드/레버리지 종합",
                "how_to_read": "양수 -> 금융환경 긴축. 음수 -> 금융환경 완화. 0이 평균",
                "korea_impact": "NFCI 양수 전환 시 글로벌 유동성 경색, 신흥국 타격",
                "unit": "지수",
                "frequency": "weekly",
                "positive_when": "falling",  # 음수 방향이 완화적
            },
            {
                "fred_id": "STLFSI2",
                "name": "세인트루이스 Fed 금융스트레스지수",
                "description": "금융시장 스트레스 측정. 금리/변동성/스프레드 종합",
                "how_to_read": "0 이상 -> 스트레스 평균 이상. 0 이하 -> 안정적",
                "korea_impact": "스트레스지수 급등은 글로벌 안전자산 선호, 원화 약세 촉발",
                "unit": "지수",
                "frequency": "weekly",
                "positive_when": "falling",
            },
            {
                "fred_id": "DRTSCILM",
                "name": "은행 대출기준 강화 비율",
                "description": "대출 기준을 강화한 은행 비율(%). SLOOS 서베이",
                "how_to_read": "상승 -> 은행 대출 까다로워짐, 신용 경색. 하락 -> 대출 완화",
                "korea_impact": "미국 은행 대출 경색은 글로벌 신용 축소, 한국 기업 달러조달 비용 증가",
                "unit": "%",
                "frequency": "quarterly",
                "positive_when": "falling",
            },
        ],
    },
    "labor": {
        "name": "고용 (Labor Market)",
        "description": "실업률, 비농업고용, 실업수당 청구, 구인건수",
        "korea_summary": "미국 고용 둔화 시 경기침체 우려로 한국 수출 감소 가능성",
        "weight": 0.10,
        "indicators": [
            {
                "fred_id": "UNRATE",
                "name": "실업률",
                "description": "미국 실업률. 경기 후행지표이나 Fed 이중책무의 핵심",
                "how_to_read": "상승 -> 경기둔화, Fed 완화 기대. 하락 -> 경기 견조, 긴축 유지",
                "korea_impact": "실업률 급등 시 미국 소비 위축, 한국 대미 수출 타격",
                "unit": "%",
                "frequency": "monthly",
                "positive_when": "falling",
            },
            {
                "fred_id": "PAYEMS",
                "name": "비농업 고용 (NFP)",
                "description": "비농업 부문 총 고용자수. 매월 첫째 금요일 발표",
                "how_to_read": "증가 -> 고용 견조, 경기 확장. 감소 -> 경기 수축 신호",
                "korea_impact": "NFP 부진은 미국 경기둔화 신호, 위험자산 매도 촉발",
                "unit": "천 명",
                "frequency": "monthly",
                "positive_when": "rising",
            },
            {
                "fred_id": "ICSA",
                "name": "신규 실업수당 청구 (Initial Claims)",
                "description": "주간 신규 실업수당 청구건수. 고용시장의 실시간 온도계",
                "how_to_read": "감소 -> 고용시장 견조. 30만 이상 지속 -> 경기침체 경고",
                "korea_impact": "실업수당 급증은 미국 소비 위축의 선행지표, 한국 수출주 주의",
                "unit": "건",
                "frequency": "weekly",
                "positive_when": "falling",
            },
            {
                "fred_id": "JTSJOL",
                "name": "구인건수 (JOLTS Job Openings)",
                "description": "미국 전체 구인건수. 노동 수요의 직접 지표",
                "how_to_read": "감소 -> 기업 채용 위축, 경기 하강. 증가 -> 노동 수요 견조",
                "korea_impact": "구인건수 급감은 미국 경기 정점 신호, 글로벌 주식시장 조정 가능",
                "unit": "천 건",
                "frequency": "monthly",
                "positive_when": "rising",
            },
        ],
    },
    "growth": {
        "name": "성장 & 심리 (Growth & Sentiment)",
        "description": "GDP, 소비자심리, 경기선행지수, 산업생산, 소매판매",
        "korea_summary": "미국 경기 확장은 한국 수출에 긍정적, 심리 위축은 선제적 경고",
        "weight": 0.15,
        "indicators": [
            {
                "fred_id": "GDP",
                "name": "GDP (명목)",
                "description": "미국 국내총생산. 경제 규모의 최종 지표",
                "how_to_read": "분기별 발표. QoQ 연율 2%+ -> 정상 성장. 마이너스 2분기 -> 기술적 침체",
                "korea_impact": "미국 GDP 둔화는 한국 수출 감소로 직결 (한국 수출의 15% 대미)",
                "unit": "십억 USD",
                "frequency": "quarterly",
                "positive_when": "rising",
            },
            {
                "fred_id": "UMCSENT",
                "name": "미시간대 소비자심리지수",
                "description": "소비자 체감경기. 소비 지출의 선행지표",
                "how_to_read": "상승 -> 소비 확대 기대. 급락 -> 소비 위축 경고",
                "korea_impact": "소비심리 악화는 미국 소비 감소, 한국 소비재 수출 타격",
                "unit": "지수",
                "frequency": "monthly",
                "positive_when": "rising",
            },
            {
                "fred_id": "USSLIND",
                "name": "경기선행지수 (LEI)",
                "description": "Conference Board 경기선행지수. 향후 6~12개월 경기 방향",
                "how_to_read": "연속 하락 -> 경기침체 예고. 반등 -> 경기 회복 신호",
                "korea_impact": "LEI 연속 하락은 미국 침체 선행 경고, KOSPI 선제적 하락 가능",
                "unit": "지수",
                "frequency": "monthly",
                "positive_when": "rising",
            },
            {
                "fred_id": "INDPRO",
                "name": "산업생산지수",
                "description": "미국 제조업/광업/유틸리티 생산량",
                "how_to_read": "증가 -> 제조업 확장. MoM 마이너스 지속 -> 제조업 침체",
                "korea_impact": "미국 산업생산 증가는 반도체/소재 수입 증가, 한국 수출 수혜",
                "unit": "지수",
                "frequency": "monthly",
                "positive_when": "rising",
            },
            {
                "fred_id": "RSAFS",
                "name": "소매판매 (Retail Sales)",
                "description": "미국 소매 판매액. 소비 경제의 직접 지표",
                "how_to_read": "MoM 증가 -> 소비 견조. 감소 -> 소비 위축 신호",
                "korea_impact": "소매판매 부진은 미국 내수 위축, 한국 소비재/IT 수출 영향",
                "unit": "백만 USD",
                "frequency": "monthly",
                "positive_when": "rising",
            },
        ],
    },
}


# ═══════════════════════════════════════════════════════════════
# 데이터 수집
# ═══════════════════════════════════════════════════════════════

def fetch_series(fred_id: str) -> pd.Series | None:
    """FRED에서 단일 시리즈 가져오기 (최근 2년)"""
    try:
        s = fred.get_series(fred_id, observation_start=START_DATE, observation_end=END_DATE)
        if s is None or s.empty:
            return None
        s = s.dropna()
        return s
    except Exception as e:
        print(f"  [WARN] {fred_id} 수집 실패: {e}")
        return None


def safe_float(val) -> float | None:
    """NaN-safe float 변환"""
    if val is None:
        return None
    f = float(val)
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, 4)


def compute_changes(series: pd.Series) -> dict:
    """
    시리즈에서 MoM, 3개월, YoY 변화율 계산.
    레벨 데이터(지수, 금액)는 %변화율, 이미 %인 데이터는 차분(pp)으로 계산.
    """
    if series is None or len(series) < 2:
        return {
            "value": safe_float(series.iloc[-1]) if series is not None and len(series) > 0 else None,
            "change_mom": None,
            "change_3m": None,
            "change_yoy": None,
        }

    latest = float(series.iloc[-1])

    def pct_change(old, new):
        if old is None or old == 0:
            return None
        return round(((new - old) / abs(old)) * 100, 2)

    # 1개월 전 (약 21영업일 or 1개 데이터포인트 전)
    mom_idx = max(0, len(series) - 2)
    for i in range(len(series) - 2, -1, -1):
        if (series.index[-1] - series.index[i]).days >= 25:
            mom_idx = i
            break
    prev_1m = float(series.iloc[mom_idx]) if mom_idx < len(series) - 1 else None

    # 3개월 전
    prev_3m = None
    for i in range(len(series) - 1, -1, -1):
        if (series.index[-1] - series.index[i]).days >= 80:
            prev_3m = float(series.iloc[i])
            break

    # 1년 전
    prev_1y = None
    for i in range(len(series) - 1, -1, -1):
        if (series.index[-1] - series.index[i]).days >= 350:
            prev_1y = float(series.iloc[i])
            break

    return {
        "value": safe_float(latest),
        "change_mom": pct_change(prev_1m, latest) if prev_1m else None,
        "change_3m": pct_change(prev_3m, latest) if prev_3m else None,
        "change_yoy": pct_change(prev_1y, latest) if prev_1y else None,
    }


def determine_trend(series: pd.Series) -> str:
    """
    추세 판단: rising / falling / stable / accelerating / decelerating
    최근 3개 데이터 포인트의 변화 방향과 가속도로 결정
    """
    if series is None or len(series) < 3:
        return "unknown"

    # 최근 6개 데이터 포인트 (또는 가능한 만큼)
    recent = series.tail(min(6, len(series)))
    if len(recent) < 3:
        return "unknown"

    # 1차 변화: 최근 구간 vs 이전 구간
    mid = len(recent) // 2
    first_half_mean = float(recent.iloc[:mid].mean())
    second_half_mean = float(recent.iloc[mid:].mean())

    if first_half_mean == 0:
        return "stable"

    change_rate = (second_half_mean - first_half_mean) / abs(first_half_mean) * 100

    # 2차 변화(가속도): 변화의 변화
    if len(recent) >= 4:
        q1 = float(recent.iloc[:len(recent)//3].mean())
        q2 = float(recent.iloc[len(recent)//3:2*len(recent)//3].mean())
        q3 = float(recent.iloc[2*len(recent)//3:].mean())

        if q1 != 0 and q2 != 0:
            delta1 = (q2 - q1) / abs(q1)
            delta2 = (q3 - q2) / abs(q2)

            if delta2 > delta1 and change_rate > 0.5:
                return "accelerating"
            elif delta2 < delta1 and change_rate > 0.5:
                return "decelerating"

    if change_rate > 1.0:
        return "rising"
    elif change_rate < -1.0:
        return "falling"
    else:
        return "stable"


def determine_signal(trend: str, change_mom: float | None, change_3m: float | None) -> str:
    """
    시그널 배지 결정:
    Strong Uptrend / Moderate Uptrend / Sideways /
    Moderate Downtrend / Strong Downtrend / Reversal
    """
    if change_mom is None:
        return "Sideways"

    # 3개월 변화 방향과 MoM 변화 방향이 다르면 반전 신호
    if change_3m is not None:
        if (change_3m > 2 and change_mom < -1) or (change_3m < -2 and change_mom > 1):
            return "Reversal"

    if trend == "accelerating":
        return "Strong Uptrend"
    elif trend == "rising":
        if change_mom is not None and abs(change_mom) > 2:
            return "Strong Uptrend"
        return "Moderate Uptrend"
    elif trend == "falling":
        if change_mom is not None and abs(change_mom) > 2:
            return "Strong Downtrend"
        return "Moderate Downtrend"
    elif trend == "decelerating":
        return "Moderate Downtrend"
    else:
        return "Sideways"


def get_history_points(series: pd.Series, n: int = 12) -> list[float]:
    """시계열의 최근 n개 포인트 (차트용)"""
    if series is None or series.empty:
        return []
    tail = series.tail(n)
    return [safe_float(v) for v in tail.values if safe_float(v) is not None]


# ═══════════════════════════════════════════════════════════════
# 카테고리별 점수 계산
# ═══════════════════════════════════════════════════════════════

def score_indicator(ind_def: dict, changes: dict, trend: str) -> float:
    """
    개별 지표 점수: 0~100
    positive_when 방향과 실제 추세/변화를 비교하여 산출
    """
    positive = ind_def.get("positive_when", "rising")
    mom = changes.get("change_mom")
    yoy = changes.get("change_yoy")

    if mom is None:
        return 50.0  # 데이터 부족 시 중립

    score = 50.0  # 기본 중립

    if positive == "rising":
        # 상승이 좋은 지표
        if mom > 0:
            score += min(mom * 5, 25)
        else:
            score += max(mom * 5, -25)

        if trend == "accelerating":
            score += 10
        elif trend == "rising":
            score += 5
        elif trend == "falling":
            score -= 10
        elif trend == "decelerating":
            score -= 5

    elif positive == "falling":
        # 하락이 좋은 지표 (인플레, 금리, 스프레드 등)
        if mom < 0:
            score += min(abs(mom) * 5, 25)
        else:
            score -= min(mom * 5, 25)

        if trend == "falling":
            score += 10
        elif trend == "decelerating":
            score += 5
        elif trend == "rising":
            score -= 10
        elif trend == "accelerating":
            score -= 15

    elif positive == "stable":
        # 안정이 좋은 지표 (기대인플레 등)
        if abs(mom) < 1:
            score += 15
        elif abs(mom) < 3:
            score += 5
        else:
            score -= min(abs(mom) * 3, 25)

    # YoY 보정
    if yoy is not None:
        if positive == "rising" and yoy > 0:
            score += min(yoy * 1.5, 10)
        elif positive == "rising" and yoy < 0:
            score -= min(abs(yoy) * 1.5, 10)
        elif positive == "falling" and yoy < 0:
            score += min(abs(yoy) * 1.5, 10)
        elif positive == "falling" and yoy > 0:
            score -= min(yoy * 1.5, 10)

    return max(0, min(100, score))


def score_category(indicator_scores: list[float]) -> float:
    """카테고리 점수: 개별 점수들의 평균"""
    if not indicator_scores:
        return 50.0
    return round(sum(indicator_scores) / len(indicator_scores), 1)


def score_to_label(score: float) -> tuple[str, str]:
    """
    점수 -> (레이블, 색상)
    """
    if score >= 75:
        return ("확장", "#22c55e")       # green
    elif score >= 60:
        return ("양호", "#84cc16")       # lime
    elif score >= 45:
        return ("중립", "#eab308")       # yellow
    elif score >= 30:
        return ("주의", "#f97316")       # orange
    else:
        return ("위험", "#ef4444")       # red


def composite_to_label(score: float) -> str:
    """종합 점수에 대한 한국어 설명"""
    if score >= 75:
        return "확장 국면"
    elif score >= 60:
        return "양호 국면"
    elif score >= 45:
        return "중립/관망 국면"
    elif score >= 30:
        return "주의 국면"
    else:
        return "위험 국면"


# ═══════════════════════════════════════════════════════════════
# 종합 요약 생성
# ═══════════════════════════════════════════════════════════════

def generate_composite_summary(categories_output: list[dict]) -> str:
    """카테고리별 점수를 바탕으로 종합 요약문 생성"""
    parts = []
    cat_lookup = {c["key"]: c for c in categories_output}

    liq = cat_lookup.get("liquidity", {})
    inf = cat_lookup.get("inflation", {})
    rat = cat_lookup.get("rates", {})
    cre = cat_lookup.get("credit", {})
    lab = cat_lookup.get("labor", {})
    gro = cat_lookup.get("growth", {})

    # 유동성
    if liq.get("score", 50) >= 60:
        parts.append("유동성은 확장 중")
    elif liq.get("score", 50) >= 45:
        parts.append("유동성은 보통 수준")
    else:
        parts.append("유동성이 축소되고 있어 주의 필요")

    # 인플레이션
    if inf.get("score", 50) >= 60:
        parts.append("인플레이션은 안정세")
    elif inf.get("score", 50) >= 45:
        parts.append("인플레이션 불확실성 존재")
    else:
        parts.append("인플레이션 재상승 우려가 부담")

    # 금리
    if rat.get("score", 50) >= 60:
        parts.append("금리는 하향 안정 추세")
    elif rat.get("score", 50) >= 45:
        parts.append("금리는 고수준 유지 중")
    else:
        parts.append("고금리가 시장에 부담")

    # 신용
    if cre.get("score", 50) >= 60:
        parts.append("신용환경 양호")
    elif cre.get("score", 50) < 40:
        parts.append("신용 스프레드 확대에 주의")

    # 성장/고용 종합
    avg_growth_labor = (gro.get("score", 50) + lab.get("score", 50)) / 2
    if avg_growth_labor >= 60:
        parts.append("경기와 고용은 견조")
    elif avg_growth_labor < 40:
        parts.append("경기둔화 및 고용 악화 신호 감지")

    summary = ". ".join(parts) + "."

    # 한국 영향
    korea_parts = []
    if liq.get("score", 50) >= 60:
        korea_parts.append("외국인 자금 유입 기대")
    if inf.get("score", 50) < 45:
        korea_parts.append("Fed 긴축 장기화로 원화 약세 압력")
    if rat.get("score", 50) < 45:
        korea_parts.append("고금리 지속으로 성장주 부담")
    if cre.get("score", 50) < 40:
        korea_parts.append("글로벌 리스크오프 시 KOSPI 하방 압력")

    if korea_parts:
        summary += " 한국 시장: " + ", ".join(korea_parts) + "."

    return summary


# ═══════════════════════════════════════════════════════════════
# 기존 signal.json 로드
# ═══════════════════════════════════════════════════════════════

def load_existing_signals() -> dict:
    """기존 signal.json에서 시장 데이터 로드"""
    if not os.path.exists(SIGNAL_PATH):
        return {}
    try:
        with open(SIGNAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════

def collect_all() -> dict:
    """전체 FRED 매크로 데이터 수집 및 점수 산출"""
    print("=" * 60)
    print("  FRED Macro Collector - 거시경제 데이터 수집 시작")
    print("=" * 60)

    categories_output = []
    all_scores = []

    for cat_key, cat_def in INDICATOR_DEFS.items():
        print(f"\n[{cat_def['name']}]")
        cat_indicators = []
        cat_scores = []

        for ind_def in cat_def["indicators"]:
            fred_id = ind_def["fred_id"]
            print(f"  Fetching {fred_id} ({ind_def['name']})...", end=" ")

            series = fetch_series(fred_id)
            if series is None or series.empty:
                print("SKIP (no data)")
                cat_indicators.append({
                    "fred_id": fred_id,
                    "name": ind_def["name"],
                    "description": ind_def["description"],
                    "how_to_read": ind_def["how_to_read"],
                    "korea_impact": ind_def["korea_impact"],
                    "value": None,
                    "unit": ind_def["unit"],
                    "change_mom": None,
                    "change_3m": None,
                    "change_yoy": None,
                    "trend": "unknown",
                    "signal": "No Data",
                    "history": [],
                })
                continue

            changes = compute_changes(series)
            trend = determine_trend(series)
            signal = determine_signal(trend, changes["change_mom"], changes["change_3m"])
            history = get_history_points(series)
            ind_score = score_indicator(ind_def, changes, trend)
            cat_scores.append(ind_score)

            print(f"OK  val={changes['value']}  MoM={changes['change_mom']}%  trend={trend}  score={ind_score:.0f}")

            cat_indicators.append({
                "fred_id": fred_id,
                "name": ind_def["name"],
                "description": ind_def["description"],
                "how_to_read": ind_def["how_to_read"],
                "korea_impact": ind_def["korea_impact"],
                "value": changes["value"],
                "unit": ind_def["unit"],
                "change_mom": changes["change_mom"],
                "change_3m": changes["change_3m"],
                "change_yoy": changes["change_yoy"],
                "trend": trend,
                "signal": signal,
                "history": history,
            })

        cat_score = score_category(cat_scores)
        label, color = score_to_label(cat_score)
        all_scores.append((cat_score, cat_def["weight"]))

        print(f"  >> {cat_def['name']} 점수: {cat_score} ({label})")

        categories_output.append({
            "key": cat_key,
            "name": cat_def["name"],
            "score": cat_score,
            "label": label,
            "color": color,
            "description": cat_def["description"],
            "korea_summary": cat_def["korea_summary"],
            "indicators": cat_indicators,
        })

    # 종합 점수 (가중 평균)
    if all_scores:
        total_weight = sum(w for _, w in all_scores)
        composite = sum(s * w for s, w in all_scores) / total_weight if total_weight > 0 else 50
        composite = round(composite, 1)
    else:
        composite = 50.0

    composite_label = composite_to_label(composite)
    composite_summary = generate_composite_summary(categories_output)

    print(f"\n{'=' * 60}")
    print(f"  종합 매크로 점수: {composite} / 100  ({composite_label})")
    print(f"  {composite_summary}")
    print(f"{'=' * 60}")

    # 기존 signal.json 통합
    existing_signals = load_existing_signals()

    output = {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "composite_score": composite,
        "composite_label": composite_label,
        "composite_summary": composite_summary,
        "categories": categories_output,
        "market_signals": existing_signals,
    }

    return output


def save_output(data: dict):
    """macro.json으로 저장"""
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data = collect_all()
    save_output(data)
    print("\nDone.")
