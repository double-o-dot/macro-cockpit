"""
Macro Cockpit - 분석 블로거 에이전트
====================================
PDF 인사이트 데이터를 기반으로 블로그 스타일 HTML 아티클을 자동 생성하고
GitHub Pages에 배포하는 에이전트.

사용법:
    python article_agent.py                     # usefulness >= 9인 미발행 PDF 자동 처리
    python article_agent.py --min-score 8       # 최소 점수 지정
    python article_agent.py --file "xxx.pdf"    # 특정 PDF만 처리
    python article_agent.py --list              # 발행 가능 목록 확인
    python article_agent.py --deploy            # 생성 후 git push까지
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ──
BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
REPORTS_DIR = DOCS_DIR / "reports"
DATA_DIR = DOCS_DIR / "data"
DIGEST_FILE = DATA_DIR / "digest.json"
REPORTS_JSON = DATA_DIR / "reports.json"
ARCHIVE_DIR = BASE_DIR / "Insights_Archive"

# ── 테마 프리셋 ──
THEME_PRESETS = {
    "AI": {
        "gradient": "linear-gradient(135deg, #1a1a1a 0%, #2d3a2d 50%, #76B900 200%)",
        "accent": "#76B900",
        "header_bg": "#1a1a1a",
        "tag_bg": "#76B900",
    },
    "에너지": {
        "gradient": "linear-gradient(135deg, #2A1515 0%, #4A2020 100%)",
        "accent": "#C0392B",
        "header_bg": "#2A1515",
        "tag_bg": "#C0392B",
    },
    "통신": {
        "gradient": "linear-gradient(135deg, #1B2A4A 0%, #2C4A7C 100%)",
        "accent": "#3B7DD8",
        "header_bg": "#1B2A4A",
        "tag_bg": "#3B7DD8",
    },
    "금융": {
        "gradient": "linear-gradient(135deg, #1A2A1A 0%, #2A4A2A 100%)",
        "accent": "#27AE60",
        "header_bg": "#1A2A1A",
        "tag_bg": "#27AE60",
    },
    "지정학": {
        "gradient": "linear-gradient(135deg, #1A1A2E 0%, #16213E 100%)",
        "accent": "#D97757",
        "header_bg": "#1A1A2E",
        "tag_bg": "#D97757",
    },
    "귀금속": {
        "gradient": "linear-gradient(135deg, #2A2510 0%, #4A3F20 100%)",
        "accent": "#D4A017",
        "header_bg": "#2A2510",
        "tag_bg": "#D4A017",
    },
    "default": {
        "gradient": "linear-gradient(135deg, #2A2520 0%, #4A3F35 100%)",
        "accent": "#D97757",
        "header_bg": "#2A2520",
        "tag_bg": "#D97757",
    },
}


def detect_theme(themes: list) -> dict:
    """테마 키워드로 적절한 컬러 프리셋 선택"""
    theme_str = " ".join(themes).lower()
    if any(k in theme_str for k in ["ai", "반도체", "gpu", "데이터센터"]):
        return THEME_PRESETS["AI"]
    if any(k in theme_str for k in ["원유", "에너지", "호르무즈", "oil"]):
        return THEME_PRESETS["에너지"]
    if any(k in theme_str for k in ["통신", "telecom", "skt"]):
        return THEME_PRESETS["통신"]
    if any(k in theme_str for k in ["금융", "은행", "모기지", "banking"]):
        return THEME_PRESETS["금융"]
    if any(k in theme_str for k in ["지정학", "전쟁", "중동", "쿠르드"]):
        return THEME_PRESETS["지정학"]
    if any(k in theme_str for k in ["귀금속", "은", "금", "silver", "gold"]):
        return THEME_PRESETS["귀금속"]
    return THEME_PRESETS["default"]


def load_digest() -> list:
    """digest.json 로드"""
    with open(DIGEST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("data", [])


def load_reports() -> dict:
    """reports.json 로드"""
    with open(REPORTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def save_reports(data: dict):
    """reports.json 저장"""
    with open(REPORTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_published_files(reports_data: dict) -> set:
    """이미 발행된 파일명 목록"""
    published = set()
    for r in reports_data.get("data", []):
        desc = r.get("description", "")
        title = r.get("title", "")
        published.add(r.get("file", ""))
    return published


def extract_date_from_filename(filename: str) -> str:
    """파일명에서 날짜 추출"""
    m = re.search(r"(\d{8})", filename)
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    m = re.search(r"(\d+)월(\d+)일", filename)
    if m:
        return f"2026-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return datetime.now().strftime("%Y-%m-%d")


def generate_article_html(pdf: dict, theme: dict) -> str:
    """PDF 인사이트 데이터로 HTML 아티클 생성"""
    accent = theme["accent"]
    gradient = theme["gradient"]
    tag_bg = theme["tag_bg"]

    title = pdf.get("summary", "")[:60] + "..."
    if len(pdf.get("summary", "")) <= 60:
        title = pdf["summary"]

    # 짧은 제목 생성
    themes_str = " / ".join(pdf.get("themes", [])[:2]).upper()
    tickers = pdf.get("key_tickers", [])
    tickers_html = "".join(
        f'<span style="display:inline-block;background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:16px;font-size:11px;margin:2px;">{t}</span>'
        for t in tickers[:5]
    )

    # Bullet list from action suggestion
    action = pdf.get("action_suggestion", "")
    macro_view = pdf.get("macro_view", "")
    relevance = pdf.get("portfolio_relevance", "")

    date_str = extract_date_from_filename(pdf["filename"])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{pdf['filename'].replace('.pdf','')} - Macro Cockpit</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Noto Sans KR', sans-serif; background: #F5F0EB; color: #2D2D2D; padding: 20px; }}
  .container {{ max-width: 720px; margin: 0 auto; }}
  .header {{
    background: {gradient};
    color: white; padding: 40px 30px; border-radius: 16px; margin-bottom: 16px;
    position: relative; overflow: hidden;
  }}
  .header::after {{
    content: ''; position: absolute; top: -40px; right: -40px;
    width: 140px; height: 140px; background: rgba(255,255,255,0.1); border-radius: 50%;
  }}
  .header .tag {{
    display: inline-block; background: {tag_bg}; color: white;
    font-size: 11px; font-weight: 700; padding: 4px 12px; border-radius: 20px;
    margin-bottom: 12px; letter-spacing: 1px;
  }}
  .header h1 {{ font-size: 24px; font-weight: 900; line-height: 1.4; margin-bottom: 8px; }}
  .header .subtitle {{ font-size: 13px; opacity: 0.7; font-weight: 300; }}
  .card {{
    background: white; border-radius: 16px; padding: 28px;
    margin-bottom: 16px; border: 1px solid #E5DED5;
  }}
  .card h2 {{
    font-size: 16px; font-weight: 700; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }}
  .card h2 .num {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; background: #1a1a1a; color: white;
    border-radius: 50%; font-size: 13px; font-weight: 700; flex-shrink: 0;
  }}
  .body-text {{ font-size: 14px; line-height: 1.7; color: #444; margin-bottom: 14px; }}
  .bullet-list {{ list-style: none; padding: 0; }}
  .bullet-list li {{
    position: relative; padding-left: 18px; margin-bottom: 10px;
    font-size: 14px; line-height: 1.6;
  }}
  .bullet-list li::before {{
    content: ''; position: absolute; left: 0; top: 8px;
    width: 8px; height: 8px; background: {accent}; border-radius: 50%;
  }}
  .quote-block {{
    background: #faf7f3; border-left: 4px solid {accent};
    padding: 18px 20px; margin: 14px 0; border-radius: 0 12px 12px 0;
  }}
  .quote-block p {{ font-size: 14px; font-weight: 500; line-height: 1.6; font-style: italic; }}
  .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 14px 0; }}
  @media (max-width: 480px) {{ .stat-grid {{ grid-template-columns: 1fr; }} }}
  .stat-box {{
    padding: 16px; border-radius: 12px; background: #f7f4f0;
  }}
  .stat-box .s-label {{ font-size: 11px; font-weight: 500; color: #888; margin-bottom: 4px; }}
  .stat-box .s-value {{ font-size: 20px; font-weight: 900; color: #1a1a1a; }}
  .stat-box .s-desc {{ font-size: 11px; color: #999; margin-top: 2px; }}
  .action-box {{
    background: {gradient}; color: white;
    border-radius: 16px; padding: 24px; margin-bottom: 16px;
  }}
  .action-box h2 {{ font-size: 16px; font-weight: 700; margin-bottom: 12px; color: white; }}
  .action-box p {{ font-size: 14px; line-height: 1.7; opacity: 0.9; }}
  .ticker-tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }}
  .ticker-tag {{
    display: inline-block; background: rgba(0,0,0,0.06); padding: 4px 12px;
    border-radius: 16px; font-size: 12px; font-weight: 600; color: {accent};
  }}
  .footer {{
    text-align: center; padding: 20px; font-size: 11px; color: #999;
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <span class="tag">{themes_str}</span>
    <h1>{pdf['filename'].replace('.pdf', '').replace('_', ' ')}</h1>
    <div class="subtitle">{date_str}</div>
    <div style="margin-top: 12px;">{tickers_html}</div>
  </div>

  <div class="card">
    <h2><span class="num">1</span> 핵심 요약</h2>
    <p class="body-text">{pdf.get('summary', '')}</p>
    <div class="ticker-tags">
      {''.join(f'<span class="ticker-tag">{t}</span>' for t in tickers)}
    </div>
  </div>

  <div class="card">
    <h2><span class="num">2</span> 매크로 시각</h2>
    <div class="quote-block">
      <p>{macro_view}</p>
    </div>
  </div>

  <div class="stat-grid">
    <div class="stat-box">
      <div class="s-label">신뢰도</div>
      <div class="s-value">{pdf.get('credibility', '-')}/10</div>
      <div class="s-desc">{pdf.get('source_type', '')}</div>
    </div>
    <div class="stat-box">
      <div class="s-label">유용성</div>
      <div class="s-value">{pdf.get('usefulness', '-')}/10</div>
      <div class="s-desc">포트폴리오 관련도</div>
    </div>
  </div>

  <div class="card">
    <h2><span class="num">3</span> 포트폴리오 연관성</h2>
    <p class="body-text">{relevance}</p>
  </div>

  <div class="action-box">
    <h2>Action Plan</h2>
    <p>{action}</p>
  </div>

  <div class="footer">
    본 아티클은 투자 참고 자료이며, 투자 권유를 목적으로 하지 않습니다.<br>
    투자 판단은 본인의 책임하에 이루어져야 합니다.<br><br>
    Macro Cockpit | {date_str} 작성
  </div>

</div>
</body>
</html>"""
    return html


def generate_article_id(pdf: dict) -> str:
    """파일명에서 아티클 ID 생성"""
    name = pdf["filename"].replace(".pdf", "")
    name = re.sub(r"[^a-zA-Z0-9가-힣_]", "_", name)
    return name


def generate_html_filename(pdf: dict) -> str:
    """HTML 파일명 생성"""
    date = extract_date_from_filename(pdf["filename"]).replace("-", "")
    name = pdf["filename"].replace(".pdf", "")
    name = re.sub(r"[^a-zA-Z0-9가-힣_]", "_", name)
    # 날짜가 이미 포함되어 있으면 그대로, 아니면 날짜 추가
    if re.match(r"\d{8}", name):
        return f"{name}.html"
    return f"{date}_{name}.html"


def list_candidates(min_score: int = 9):
    """발행 가능한 PDF 목록 출력"""
    digests = load_digest()
    reports = load_reports()
    published_files = get_published_files(reports)

    candidates = [d for d in digests if d.get("usefulness", 0) >= min_score]

    print(f"\n{'='*60}")
    print(f"  발행 가능 인사이트 (usefulness >= {min_score})")
    print(f"{'='*60}")

    for i, pdf in enumerate(candidates, 1):
        html_file = generate_html_filename(pdf)
        is_published = html_file in published_files
        status = "✓ 발행됨" if is_published else "  미발행"
        themes = ", ".join(pdf.get("themes", [])[:3])
        print(f"\n  {i}. [{status}] {pdf['filename']}")
        print(f"     신뢰도: {pdf.get('credibility', '-')}/10 | 유용성: {pdf.get('usefulness', '-')}/10")
        print(f"     테마: {themes}")
        print(f"     요약: {pdf.get('summary', '')[:80]}...")

    unpublished = [d for d in candidates
                   if generate_html_filename(d) not in published_files]
    print(f"\n  총 {len(candidates)}개 중 미발행: {len(unpublished)}개")
    print(f"{'='*60}\n")

    return unpublished


def process_pdf(pdf: dict, dry_run: bool = False) -> dict | None:
    """단일 PDF → HTML 아티클 생성"""
    theme = detect_theme(pdf.get("themes", []))
    html = generate_article_html(pdf, theme)
    html_filename = generate_html_filename(pdf)
    html_path = REPORTS_DIR / html_filename

    if dry_run:
        print(f"  [DRY-RUN] Would create: {html_path}")
        return None

    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    date_str = extract_date_from_filename(pdf["filename"])
    themes_tags = pdf.get("themes", [])[:4]

    report_entry = {
        "id": generate_article_id(pdf),
        "title": pdf.get("summary", "")[:60],
        "date": date_str,
        "source": "",
        "description": pdf.get("summary", ""),
        "file": html_filename,
        "tags": themes_tags,
    }

    print(f"  [OK] {html_filename} ({len(html):,} bytes)")
    return report_entry


def run(min_score: int = 9, target_file: str = None, deploy: bool = False, dry_run: bool = False):
    """메인 실행"""
    digests = load_digest()
    reports = load_reports()
    published_files = get_published_files(reports)

    if target_file:
        candidates = [d for d in digests if d["filename"] == target_file]
        if not candidates:
            print(f"  [ERROR] '{target_file}' not found in digest.json")
            return
    else:
        candidates = [
            d for d in digests
            if d.get("usefulness", 0) >= min_score
            and generate_html_filename(d) not in published_files
        ]

    if not candidates:
        print("  발행할 새 아티클이 없습니다.")
        return

    print(f"\n  {len(candidates)}개 아티클 생성 시작...\n")

    new_entries = []
    for pdf in candidates:
        entry = process_pdf(pdf, dry_run=dry_run)
        if entry:
            new_entries.append(entry)

    if new_entries and not dry_run:
        reports["data"] = new_entries + reports.get("data", [])
        save_reports(reports)
        print(f"\n  reports.json 업데이트 완료 ({len(new_entries)}개 추가)")

    if deploy and not dry_run:
        print("\n  Git 배포 시작...")
        os.system(f'cd "{BASE_DIR}" && git add docs/reports/ docs/data/reports.json')
        os.system(
            f'cd "{BASE_DIR}" && git commit -m "Add {len(new_entries)} new insight article(s) via article_agent"'
        )
        os.system(f'cd "{BASE_DIR}" && git push origin main')
        print("  배포 완료!")

    print(f"\n  완료: {len(new_entries)}개 아티클 생성됨")


def main():
    parser = argparse.ArgumentParser(description="Macro Cockpit 분석 블로거 에이전트")
    parser.add_argument("--min-score", type=int, default=9, help="최소 usefulness 점수 (기본: 9)")
    parser.add_argument("--file", type=str, help="특정 PDF만 처리")
    parser.add_argument("--list", action="store_true", help="발행 가능 목록 확인")
    parser.add_argument("--deploy", action="store_true", help="생성 후 git push까지")
    parser.add_argument("--dry-run", action="store_true", help="실제 파일 생성 없이 미리보기")
    args = parser.parse_args()

    if args.list:
        list_candidates(args.min_score)
    else:
        run(
            min_score=args.min_score,
            target_file=args.file,
            deploy=args.deploy,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
