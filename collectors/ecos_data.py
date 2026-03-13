"""
한국은행 ECOS API 경제지표 수집
- 기준금리, 소비자물가지수, 통화량 등
- API 키: https://ecos.bok.or.kr/api/#/ 에서 무료 발급
"""
import os
import requests
from datetime import datetime, timedelta


ECOS_API_KEY = os.environ.get("ECOS_API_KEY", "")
ECOS_BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

# 주요 통계 코드
INDICATORS = {
    "기준금리": {
        "stat_code": "722Y001",
        "item_code": "0101000",
        "cycle": "M",  # Monthly
    },
    "소비자물가지수": {
        "stat_code": "901Y009",
        "item_code": "0",
        "cycle": "M",
    },
    "M2(광의통화)": {
        "stat_code": "101Y003",
        "item_code": "BBGA00",
        "cycle": "M",
    },
    "경상수지": {
        "stat_code": "301Y013",
        "item_code": "000000",
        "cycle": "M",
    },
}


def fetch_ecos_indicator(stat_code, item_code, cycle="M", count=6):
    """
    ECOS API에서 특정 지표 조회

    Args:
        stat_code: 통계표 코드
        item_code: 통계항목 코드
        cycle: D(일), M(월), Q(분기), A(년)
        count: 조회 건수
    """
    if not ECOS_API_KEY:
        return None

    end_date = datetime.now().strftime("%Y%m")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m")

    url = (
        f"{ECOS_BASE_URL}/{ECOS_API_KEY}/json/kr/1/{count}"
        f"/{stat_code}/{cycle}/{start_date}/{end_date}/{item_code}"
    )

    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if "StatisticSearch" not in data:
            return None

        rows = data["StatisticSearch"]["row"]
        return [
            {
                "date": row.get("TIME", ""),
                "value": row.get("DATA_VALUE", ""),
                "unit": row.get("UNIT_NAME", ""),
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[WARN] ECOS API 호출 실패: {e}")
        return None


def fetch_all_indicators():
    """모든 주요 지표 수집"""
    results = {}
    for name, params in INDICATORS.items():
        data = fetch_ecos_indicator(
            params["stat_code"],
            params["item_code"],
            params["cycle"],
        )
        if data:
            results[name] = data
    return results


def format_ecos_data(indicators):
    """경제지표를 텍스트로 포맷"""
    if not indicators:
        if not ECOS_API_KEY:
            return (
                "\n## 한국 경제지표 (ECOS)\n"
                "> ECOS_API_KEY가 설정되지 않았습니다.\n"
                "> https://ecos.bok.or.kr/api/#/ 에서 무료 API 키를 발급받으세요.\n"
                "> 발급 후: set ECOS_API_KEY=발급받은키\n"
            )
        return "\n## 한국 경제지표 (ECOS)\n> 데이터 수집 실패\n"

    lines = ["\n## 한국 경제지표 (ECOS)\n"]
    for name, data in indicators.items():
        if data:
            latest = data[-1]
            prev = data[-2] if len(data) > 1 else None
            line = f"- **{name}**: {latest['value']}"
            if latest.get("unit"):
                line += f" ({latest['unit']})"
            if prev:
                line += f" [이전: {prev['value']}]"
            line += f" ({latest['date']})"
            lines.append(line)

    return "\n".join(lines)


if __name__ == "__main__":
    if not ECOS_API_KEY:
        print("ECOS_API_KEY 환경변수를 설정해주세요.")
        print("발급: https://ecos.bok.or.kr/api/#/")
    else:
        indicators = fetch_all_indicators()
        print(format_ecos_data(indicators))
