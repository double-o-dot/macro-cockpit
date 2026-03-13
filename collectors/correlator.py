"""
테크 뉴스 <-> 시장 연관성 탐색
GeekNews의 기술 트렌드가 어떤 시장 테마와 연결되는지 분석
"""
from config import TECH_MARKET_KEYWORDS


def find_correlations(geeknews_items, finance_news_items):
    """
    GeekNews 항목과 금융 뉴스 사이의 테마 연관성을 탐색

    Returns:
        list of dict: 매칭된 테마와 관련 뉴스 쌍
    """
    correlations = []

    for theme, keywords in TECH_MARKET_KEYWORDS.items():
        matched_tech = []
        matched_finance = []

        for item in geeknews_items:
            text = f"{item['title']} {item['summary']}".lower()
            for kw in keywords:
                if kw.lower() in text:
                    matched_tech.append(item)
                    break

        for item in finance_news_items:
            text = f"{item['title']} {item['summary']}".lower()
            for kw in keywords:
                if kw.lower() in text:
                    matched_finance.append(item)
                    break

        if matched_tech and matched_finance:
            correlations.append({
                "theme": theme,
                "tech_news": matched_tech,
                "finance_news": matched_finance,
            })
        elif matched_tech:
            correlations.append({
                "theme": theme,
                "tech_news": matched_tech,
                "finance_news": [],
                "note": "테크 트렌드 감지 - 시장 영향 모니터링 필요",
            })

    return correlations


def format_correlations(correlations):
    """연관성 분석 결과를 텍스트로 포맷"""
    if not correlations:
        return "\n## 테크-시장 연관성\n오늘은 뚜렷한 테마 매칭이 없습니다.\n"

    lines = ["\n## 테크-시장 연관성 분석\n"]

    for corr in correlations:
        theme = corr["theme"]
        tech_count = len(corr["tech_news"])
        fin_count = len(corr["finance_news"])

        if corr["finance_news"]:
            signal = "🔗 연결됨"
        else:
            signal = "👀 관찰 중"

        lines.append(f"### [{signal}] {theme} (테크 {tech_count}건 / 금융 {fin_count}건)")

        lines.append("  테크 뉴스:")
        for item in corr["tech_news"][:3]:
            lines.append(f"    - {item['title']}")

        if corr["finance_news"]:
            lines.append("  금융 뉴스:")
            for item in corr["finance_news"][:3]:
                lines.append(f"    - {item['title']}")

        if corr.get("note"):
            lines.append(f"  Note: {corr['note']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    # 테스트용 더미 데이터
    test_tech = [
        {"title": "NVIDIA, 새로운 AI 칩 발표", "summary": "GPU 성능 2배 향상"},
        {"title": "AWS, 클라우드 신규 서비스 출시", "summary": "SaaS 시장 확대"},
    ]
    test_finance = [
        {"title": "반도체 주가 급등, SK하이닉스 신고가", "summary": "HBM 수요 증가"},
        {"title": "삼성전자 실적 발표", "summary": "메모리 반도체 회복"},
    ]
    corrs = find_correlations(test_tech, test_finance)
    print(format_correlations(corrs))
