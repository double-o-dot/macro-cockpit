"""
Claude API를 활용한 AI 분석 모듈
- 수집된 데이터를 자연어로 분석/요약
- Valley 공유용 콘텐츠 생성
"""
import os

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def get_client():
    """Anthropic 클라이언트 생성"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def analyze_briefing(market_text, finance_news_text, geeknews_text, correlation_text):
    """
    수집된 전체 데이터를 Claude에게 분석 요청

    Returns:
        dict: {summary, valley_post, insights} 또는 None (API 미설정시)
    """
    if not HAS_ANTHROPIC:
        return None

    client = get_client()
    if not client:
        return None

    prompt = f"""당신은 한국의 개인 투자자를 위한 금융 분석가입니다.
아래 수집된 데이터를 분석하여 3가지를 작성해주세요.

## 수집 데이터

### 시장 현황
{market_text}

### 금융/경제 뉴스
{finance_news_text}

### GeekNews 기술 트렌드
{geeknews_text}

### 테크-시장 연관성 분석
{correlation_text}

---

## 요청사항

### 1. 오늘의 시황 요약 (3~5문장)
- 시장 흐름의 핵심 포인트
- 주요 변동의 원인 분석

### 2. Valley 커뮤니티 공유용 포스트 (200~400자)
- 테크 트렌드와 시장의 연결점을 중심으로
- 인사이트가 있고, 대화를 유도하는 톤
- 제목도 포함

### 3. 주목할 포인트 3가지
- 오늘 데이터에서 투자자가 관심 가져야 할 시그널
- 각각 한줄 설명 + 관련 근거

JSON 형식으로 응답해주세요:
{{"summary": "...", "valley_post_title": "...", "valley_post_body": "...", "watchpoints": ["...", "...", "..."]}}
"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        response_text = message.content[0].text

        # JSON 블록 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())
    except Exception as e:
        print(f"[WARN] AI 분석 실패: {e}")
        return None


def format_ai_analysis(analysis):
    """AI 분석 결과를 마크다운으로 포맷"""
    if not analysis:
        return "\n## AI 분석\n> ANTHROPIC_API_KEY가 설정되지 않았거나 API 호출에 실패했습니다.\n> 환경변수를 설정하면 AI 분석이 활성화됩니다.\n"

    lines = ["\n## AI 분석 (Claude Haiku)\n"]

    lines.append("### 시황 요약")
    lines.append(analysis.get("summary", "N/A"))
    lines.append("")

    lines.append("### Valley 공유용 포스트")
    lines.append(f"**{analysis.get('valley_post_title', 'N/A')}**")
    lines.append(analysis.get("valley_post_body", "N/A"))
    lines.append("")

    lines.append("### 주목할 포인트")
    for i, point in enumerate(analysis.get("watchpoints", []), 1):
        lines.append(f"{i}. {point}")
    lines.append("")

    return "\n".join(lines)
