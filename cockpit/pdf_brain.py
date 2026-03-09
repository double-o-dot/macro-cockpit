"""
커뮤니티 PDF 브레인
- community_report_pdf/ 폴더의 PDF 자동 분석
- Claude API로 인사이트 추출/채점
- Insights_Archive/에 요약 저장
- 포트폴리오와 교차 분석
"""
import os
import re
import json
from datetime import datetime

import base64

import pdfplumber
import fitz  # PyMuPDF

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "community_report_pdf")
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "..", "Insights_Archive")
DIGEST_DB = os.path.join(ARCHIVE_DIR, "_digest_index.json")


def _load_digest_index():
    """분석 이력 로드"""
    if os.path.exists(DIGEST_DB):
        with open(DIGEST_DB, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_digest_index(index):
    """분석 이력 저장"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(DIGEST_DB, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def scan_pdfs():
    """community_report_pdf/ 폴더의 PDF 목록 조회"""
    if not os.path.exists(PDF_DIR):
        return []
    files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    return sorted(files)


def extract_text(pdf_path, max_pages=10):
    """PDF에서 텍스트 추출 (최대 10페이지)"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:max_pages]:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_images(pdf_path, max_pages=5):
    """이미지 PDF를 페이지별 PNG로 변환 (Claude Vision용)"""
    doc = fitz.open(pdf_path)
    images = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        mat = fitz.Matrix(1.5, 1.5)  # ~108 dpi
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
        images.append(b64)
    doc.close()
    return images


def _get_client():
    """Anthropic 클라이언트"""
    # api.env 로드
    env_path = os.path.join(os.path.dirname(__file__), "..", "api.env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not HAS_ANTHROPIC:
        return None
    return anthropic.Anthropic(api_key=api_key)


def analyze_pdf(filename, text, holdings_summary="", images=None):
    """
    Claude API로 PDF 분석 (텍스트 또는 이미지)

    Returns:
        dict: 분석 결과 또는 None
    """
    client = _get_client()
    if not client:
        return _fallback_analyze(filename, text)

    holdings_context = ""
    if holdings_summary:
        holdings_context = f"\n\n## 현재 포트폴리오\n{holdings_summary}"

    analysis_prompt = f"""이것은 투자 커뮤니티에서 수집한 PDF 리포트입니다.
파일명: {filename}
{holdings_context}

아래 항목을 JSON으로 분석해주세요:

1. "source_type": 리포트 유형 (개인분석/증권사리포트/뉴스정리/매매계획 중 택1)
2. "credibility": 출처 신뢰도 (1~10)
3. "summary": 핵심 인사이트 요약 (3~7줄, 한국어)
4. "key_tickers": 언급된 주요 종목/ETF 리스트
5. "themes": 관련 투자 테마 (예: ["귀금속", "AI", "에너지"])
6. "macro_view": 매크로 관점 요약 (1~2줄)
7. "usefulness": 유용성 점수 (1~10)
8. "portfolio_relevance": 현재 포트폴리오와의 관련성 설명 (1~2줄, 포트폴리오 정보가 있을 때만)
9. "action_suggestion": 이 리포트 기반 추천 행동 (1줄)

JSON만 반환:
"""

    try:
        # 이미지 기반 분석 (Vision)
        if images and not text:
            content = []
            # 최대 3페이지 이미지만 전송 (비용 절감)
            for img_b64 in images[:3]:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                })
            content.append({"type": "text", "text": analysis_prompt})
        else:
            # 텍스트 기반 분석
            content = f"## 내용:\n{text[:6000]}\n\n{analysis_prompt}"

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            messages=[{"role": "user", "content": content}],
        )
        response_text = message.content[0].text

        # JSON 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        result["analyzed_by"] = "claude-haiku-vision" if (images and not text) else "claude-haiku"
        return result
    except Exception as e:
        print(f"  [WARN] AI 분석 실패: {e}")
        return _fallback_analyze(filename, text)


def _fallback_analyze(filename, text):
    """API 없을 때 기본 분석 (키워드 기반)"""
    themes = []
    theme_keywords = {
        "귀금속": ["금", "은", "silver", "gold", "금광", "PSLV", "GDXJ", "GLD"],
        "AI/테크": ["AI", "팔란티어", "PLTR", "엔비디아", "NVDA", "반도체", "GPU"],
        "에너지": ["원유", "Murban", "정유", "에너지", "oil", "WTI", "브렌트"],
        "금융": ["은행", "금리", "금융", "KBWB", "XLF", "모기지"],
        "한국시장": ["코스피", "KOSPI", "코스닥", "한국", "삼성", "SK"],
        "매크로": ["금리", "인플레", "연준", "Fed", "환율", "달러"],
    }

    text_lower = text.lower()
    for theme, keywords in theme_keywords.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                themes.append(theme)
                break

    # 종목 추출 (간단한 패턴)
    tickers = re.findall(r'\b[A-Z]{2,5}\b', text)
    known_tickers = {"PLTR", "NVDA", "PSLV", "GDXJ", "KBWB", "XLF", "AAPL", "TSLA",
                     "QQQ", "SPY", "MSFT", "AMZN", "META", "GOOG", "AMD", "IREN",
                     "SOXL", "SQQQ", "TQQQ", "KORU", "AGQ", "GLD", "SLV"}
    found_tickers = [t for t in set(tickers) if t in known_tickers]

    return {
        "source_type": "개인분석",
        "credibility": 5,
        "summary": f"파일명: {filename}\n텍스트 길이: {len(text)}자\n테마: {', '.join(themes) if themes else 'N/A'}",
        "key_tickers": found_tickers,
        "themes": themes,
        "macro_view": "API 키 없음 - 자동 요약 불가",
        "usefulness": 5,
        "action_suggestion": "API 키 설정 후 재분석 권장",
        "analyzed_by": "keyword_fallback",
    }


def digest_all(holdings_summary="", force=False):
    """
    전체 PDF 일괄 분석

    Args:
        holdings_summary: 포트폴리오 요약 텍스트
        force: True면 이미 분석한 것도 재분석

    Returns:
        list of dict: 분석 결과 목록
    """
    pdfs = scan_pdfs()
    if not pdfs:
        print("community_report_pdf/ 폴더에 PDF가 없습니다.")
        return []

    index = _load_digest_index()
    results = []

    for filename in pdfs:
        if not force and filename in index:
            results.append(index[filename])
            continue

        pdf_path = os.path.join(PDF_DIR, filename)
        print(f"  Analyzing: {filename}")

        try:
            text = extract_text(pdf_path)
            images = None

            if not text or len(text) < 50:
                # 이미지 PDF → Vision 분석
                images = extract_images(pdf_path, max_pages=3)
                if not images:
                    print(f"    -> 텍스트/이미지 추출 모두 실패")
                    result = {
                        "filename": filename,
                        "error": "추출 실패",
                        "analyzed_at": datetime.now().isoformat(),
                    }
                    index[filename] = result
                    results.append(result)
                    i_count = len([r for r in results if not r.get("error")])
                    continue
                print(f"    -> 이미지 PDF ({len(images)}p) - Vision 분석")

            result = analyze_pdf(filename, text, holdings_summary, images=images)
            result["filename"] = filename
            result["text_length"] = len(text) if text else 0
            result["image_pages"] = len(images) if images else 0
            result["analyzed_at"] = datetime.now().isoformat()

            # 아카이브 저장 (유용성 6점 이상)
            if result.get("usefulness", 0) >= 6:
                _save_archive(filename, result)
        except Exception as e:
            print(f"    -> 오류: {e}")
            result = {
                "filename": filename,
                "error": str(e),
                "analyzed_at": datetime.now().isoformat(),
            }

        index[filename] = result
        results.append(result)

    _save_digest_index(index)
    return results


def _save_archive(filename, result):
    """유용한 인사이트를 아카이브 파일로 저장"""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    # 날짜 추출 시도
    date_match = re.search(r'(\d{1,2})월(\d{1,2})일', filename)
    if date_match:
        date_str = f"2026-{int(date_match.group(1)):02d}-{int(date_match.group(2)):02d}"
    else:
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            d = date_match.group(1)
            date_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

    safe_name = re.sub(r'[^\w가-힣-]', '_', filename.replace('.pdf', ''))
    archive_file = os.path.join(ARCHIVE_DIR, f"{date_str}_{safe_name}.md")

    content = f"""# {filename}
- 분석일: {result.get('analyzed_at', 'N/A')}
- 유형: {result.get('source_type', 'N/A')}
- 신뢰도: {result.get('credibility', 'N/A')}/10
- 유용성: {result.get('usefulness', 'N/A')}/10
- 테마: {', '.join(result.get('themes', []))}
- 관련종목: {', '.join(result.get('key_tickers', []))}

## 핵심 인사이트
{result.get('summary', 'N/A')}

## 매크로 관점
{result.get('macro_view', 'N/A')}

## 포트폴리오 관련성
{result.get('portfolio_relevance', 'N/A')}

## 추천 행동
{result.get('action_suggestion', 'N/A')}
"""
    with open(archive_file, "w", encoding="utf-8") as f:
        f.write(content)


def inject_analysis(filename, analysis_dict):
    """
    Claude Code 등 외부에서 분석한 결과를 수동으로 주입

    Args:
        filename: PDF 파일명
        analysis_dict: {
            "source_type", "credibility", "summary", "key_tickers",
            "themes", "macro_view", "usefulness", "portfolio_relevance",
            "action_suggestion"
        }

    Returns:
        dict: 저장된 결과
    """
    index = _load_digest_index()

    result = dict(analysis_dict)
    result["filename"] = filename
    result["analyzed_by"] = result.get("analyzed_by", "claude-code-manual")
    result["analyzed_at"] = datetime.now().isoformat()

    # 인덱스에 저장
    index[filename] = result
    _save_digest_index(index)

    # 유용성 6점 이상이면 아카이브도 저장
    if result.get("usefulness", 0) >= 6:
        _save_archive(filename, result)

    return result


def inject_batch(analyses):
    """
    여러 PDF 분석 결과를 일괄 주입

    Args:
        analyses: list of dict, 각각 {"filename": "...", ...분석결과}

    Returns:
        int: 저장된 건수
    """
    index = _load_digest_index()
    count = 0

    for analysis in analyses:
        filename = analysis.get("filename", "")
        if not filename:
            continue

        result = dict(analysis)
        result["analyzed_by"] = result.get("analyzed_by", "claude-code-manual")
        result["analyzed_at"] = datetime.now().isoformat()

        index[filename] = result

        if result.get("usefulness", 0) >= 6:
            _save_archive(filename, result)

        count += 1

    _save_digest_index(index)
    return count


def format_digest(results):
    """분석 결과 포맷"""
    lines = []
    lines.append("=" * 65)
    lines.append("  PDF BRAIN - Community Report Digest")
    lines.append("=" * 65)

    if not results:
        lines.append("\n  분석할 PDF가 없습니다.")
        return "\n".join(lines)

    # 유용성 순 정렬
    scored = [r for r in results if r.get("usefulness")]
    scored.sort(key=lambda x: x.get("usefulness", 0), reverse=True)
    unscored = [r for r in results if not r.get("usefulness")]

    lines.append(f"\n  총 {len(results)}개 PDF 분석 완료")
    lines.append(f"  분석엔진: {scored[0].get('analyzed_by', 'N/A') if scored else 'N/A'}")

    if scored:
        lines.append(f"\n[Top Insights] (유용성 순)")
        lines.append(f"  {'파일명':<35} {'유용':>4} {'신뢰':>4} {'테마':<25}")
        lines.append("  " + "-" * 70)
        for r in scored:
            themes = ", ".join(r.get("themes", [])[:3])
            lines.append(
                f"  {r['filename'][:35]:<35} "
                f"{r.get('usefulness', '?'):>4} "
                f"{r.get('credibility', '?'):>4} "
                f"{themes:<25}"
            )

    # 상위 3개 상세 요약
    top3 = scored[:3]
    if top3:
        lines.append(f"\n[Top 3 Detail]")
        for i, r in enumerate(top3, 1):
            lines.append(f"\n  #{i} {r['filename']}")
            lines.append(f"     유형: {r.get('source_type', 'N/A')} | "
                         f"유용성: {r.get('usefulness', '?')}/10 | "
                         f"신뢰도: {r.get('credibility', '?')}/10")
            summary = r.get("summary", "N/A")
            for line in summary.split("\n")[:5]:
                lines.append(f"     {line.strip()}")
            if r.get("action_suggestion"):
                lines.append(f"     -> {r['action_suggestion']}")

    if unscored:
        lines.append(f"\n[Errors] ({len(unscored)}건)")
        for r in unscored:
            lines.append(f"  {r['filename']}: {r.get('error', 'unknown')}")

    lines.append("\n" + "=" * 65)
    return "\n".join(lines)


# --- CLI ---

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("Scanning community PDFs...")
    results = digest_all()
    print(format_digest(results))
