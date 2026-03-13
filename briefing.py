"""
일일 투자 브리핑 생성기
- 시장 데이터 + GeekNews + 금융 뉴스를 수집
- 테마별 연관성 분석
- Valley 공유용 콘텐츠 생성
"""
import os
import sys
from datetime import datetime

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# api.env 로드
_env_path = os.path.join(PROJECT_ROOT, "api.env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())

from config import OUTPUT_DIR
from collectors.market_data import fetch_market_snapshot, format_market_table
from collectors.news_feed import fetch_geeknews, fetch_finance_news, format_news_list
from collectors.correlator import find_correlations, format_correlations
from collectors.ai_analyst import analyze_briefing, format_ai_analysis
from collectors.ecos_data import fetch_all_indicators, format_ecos_data


def generate_briefing():
    """전체 브리핑 리포트 생성"""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] 일일 브리핑 생성 시작...\n")

    # 1. 시장 데이터 수집
    print("1/5 시장 데이터 수집 중...")
    market = fetch_market_snapshot()
    market_text = format_market_table(market)

    # 2. 한국 경제지표 수집
    print("2/5 경제지표 수집 중...")
    ecos_indicators = fetch_all_indicators()
    ecos_text = format_ecos_data(ecos_indicators)

    # 3. 뉴스 수집
    print("3/5 뉴스 수집 중...")
    geeknews = fetch_geeknews(15)
    finance_news = fetch_finance_news(15)

    gn_text = format_news_list(geeknews, "GeekNews 기술 트렌드")
    fn_text = format_news_list(finance_news, "금융/경제 뉴스")

    # 4. 연관성 분석
    print("4/5 테크-시장 연관성 분석 중...")
    correlations = find_correlations(geeknews, finance_news)
    corr_text = format_correlations(correlations)

    # 5. AI 분석 (API 키 있을 때만)
    print("5/5 AI 분석 중...")
    ai_result = analyze_briefing(market_text, fn_text, gn_text, corr_text)
    ai_text = format_ai_analysis(ai_result)

    # 5. Valley 공유용 인사이트 생성 (AI 없을 때 폴백)
    valley_text = generate_valley_content(correlations, market, geeknews)

    # 6. 리포트 조합
    report = f"""# 일일 투자 브리핑 - {today}

## 시장 현황
```
{market_text}
```
{ecos_text}
{fn_text}
{gn_text}
{corr_text}
{ai_text}
{valley_text}

---
Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    # 6. 파일 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = os.path.join(OUTPUT_DIR, f"briefing_{today}.md")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n브리핑 저장 완료: {filename}")
    return report, filename


def generate_valley_content(correlations, market, geeknews):
    """Valley 커뮤니티 공유용 콘텐츠 초안 생성"""
    lines = ["\n## Valley 공유용 콘텐츠 초안\n"]

    # 시장 요약 한줄
    movers = [m for m in market if m.get("change_pct") is not None]
    top_up = sorted([m for m in movers if m["change_pct"] > 0], key=lambda x: x["change_pct"], reverse=True)
    top_down = sorted([m for m in movers if m["change_pct"] < 0], key=lambda x: x["change_pct"])

    lines.append("### 오늘의 시장 한줄 요약")
    summary_parts = []
    if top_up:
        summary_parts.append(f"{top_up[0]['name']} {top_up[0]['direction']}{top_up[0]['change_pct']:+.2f}%")
    if top_down:
        summary_parts.append(f"{top_down[0]['name']} {top_down[0]['direction']}{top_down[0]['change_pct']:+.2f}%")
    if summary_parts:
        lines.append(f"  {' | '.join(summary_parts)}")
    lines.append("")

    # 연관성 기반 인사이트
    if correlations:
        active = [c for c in correlations if c["finance_news"]]
        watching = [c for c in correlations if not c["finance_news"]]

        if active:
            lines.append("### 테크-시장 연결 포인트")
            for corr in active[:2]:
                tech_title = corr["tech_news"][0]["title"]
                fin_title = corr["finance_news"][0]["title"]
                lines.append(f"  [{corr['theme']}] {tech_title}")
                lines.append(f"  -> 시장 반응: {fin_title}")
                lines.append("")

        if watching:
            lines.append("### 아직 시장 미반영 - 선행 시그널?")
            for corr in watching[:2]:
                lines.append(f"  [{corr['theme']}] {corr['tech_news'][0]['title']}")
            lines.append("")

    # GeekNews 관심 뉴스 top 3
    if geeknews:
        lines.append("### GeekNews에서 주목할 뉴스")
        for item in geeknews[:3]:
            lines.append(f"  - {item['title']}")
            if item.get("link"):
                lines.append(f"    {item['link']}")
        lines.append("")

    lines.append("> 이 콘텐츠는 자동 수집 데이터 기반 초안입니다. Valley 공유 전 검토/편집하세요.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    report, filename = generate_briefing()
    print("\n" + "=" * 50)
    print(report)
