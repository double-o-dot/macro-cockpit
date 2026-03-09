"""
통합 대시보드
- 포트폴리오 + 매크로 + PDF 인사이트를 하나로
"""
import os
import json
from datetime import datetime

from cockpit.portfolio_parser import parse_toss_pdf, generate_summary
from cockpit.trade_review import analyze_trades, format_review
from cockpit.macro_signal import fetch_macro_data, generate_signals, format_signals
from cockpit.pdf_brain import digest_all, format_digest, _load_digest_index


def run_dashboard(skip_pdf=False):
    """전체 대시보드 실행"""
    sections = []
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections.append(f"\n{'#' * 65}")
    sections.append(f"  MACRO COCKPIT DASHBOARD - {today}")
    sections.append(f"{'#' * 65}")

    # 1. 포트폴리오
    print("[1/4] Portfolio...")
    portfolio_data = _load_portfolio()
    if portfolio_data:
        holdings = portfolio_data.get("holdings", {})
        cash = portfolio_data.get("cash", {})
        sections.append(generate_summary(holdings, cash))

        # 매매 복기 요약
        review = analyze_trades(portfolio_data)
        stats = review["stats"]
        if stats["total_closed"] > 0:
            sections.append(
                f"\n  [Trade Stats] "
                f"{stats['total_closed']}건 매매 | "
                f"승률 {stats['win_rate']}% | "
                f"KRW {stats.get('total_pnl_krw', 0):+,}원 | "
                f"USD ${stats.get('total_pnl_usd', 0):+,.2f}"
            )

        # 오픈 포지션 요약
        dca_positions = [p for p in review["open_positions"] if p["pattern"] == "dca"]
        if dca_positions:
            sections.append("\n  [DCA Positions]")
            for p in dca_positions:
                sections.append(
                    f"    {p['name']}: {p['quantity']}주 @ "
                    f"${p['avg_price']:.2f} ({p['first_buy']}~{p['last_buy']})"
                )
    else:
        sections.append("\n  [Portfolio] PDF not found. Run: python cockpit.py portfolio")

    # 2. 매크로 신호등
    print("[2/4] Macro signals...")
    try:
        macro_data = fetch_macro_data()
        signals = generate_signals(macro_data)
        sections.append(format_signals(macro_data, signals))
    except Exception as e:
        sections.append(f"\n  [Macro] Error: {e}")

    # 3. PDF 인사이트 요약 (캐시 사용)
    print("[3/4] PDF insights...")
    if not skip_pdf:
        holdings_text = ""
        if portfolio_data:
            holdings_text = generate_summary(
                portfolio_data.get("holdings", {}),
                portfolio_data.get("cash", {}),
            )
        try:
            pdf_results = digest_all(holdings_summary=holdings_text)
            sections.append(format_digest(pdf_results))
        except Exception as e:
            sections.append(f"\n  [PDF Brain] Error: {e}")
    else:
        index = _load_digest_index()
        sections.append(f"\n  [PDF Brain] {len(index)}개 PDF 분석 완료 (캐시)")

    # 4. 종합 체크리스트
    print("[4/4] Generating checklist...")
    sections.append(_generate_checklist(portfolio_data, signals if 'signals' in dir() else []))

    report = "\n".join(sections)

    # 저장
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    filename = os.path.join(
        reports_dir,
        f"dashboard_{datetime.now().strftime('%Y-%m-%d_%H%M')}.txt"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nDashboard saved: {filename}")
    return report, filename


def _load_portfolio():
    """포트폴리오 JSON 로드 (없으면 PDF 파싱)"""
    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "Portfolio")
    json_path = os.path.join(pdf_dir, "portfolio_latest.json")

    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)

    pdfs = sorted(
        [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")],
        reverse=True,
    ) if os.path.exists(pdf_dir) else []

    if pdfs:
        return parse_toss_pdf(os.path.join(pdf_dir, pdfs[0]))
    return None


def _generate_checklist(portfolio_data, signals):
    """종합 체크리스트"""
    lines = []
    lines.append("\n" + "=" * 65)
    lines.append("  TODAY'S CHECKLIST")
    lines.append("=" * 65)

    # 시그널 기반 체크리스트
    if signals:
        danger = [s for s in signals if s.get("level") in ("danger", "caution")]
        if danger:
            lines.append("\n  [Warning]")
            for s in danger:
                lines.append(f"    - {s['indicator']}: {s['message'][:60]}")

        bullish = [s for s in signals if s.get("level") == "bullish"]
        if bullish:
            lines.append("\n  [Positive]")
            for s in bullish:
                lines.append(f"    - {s['indicator']}: {s['message'][:60]}")

    # DCA 리마인더
    if portfolio_data:
        lines.append("\n  [Daily DCA]")
        lines.append("    [ ] PLTR 1주 매수")
        lines.append("    [ ] KBWB 1주 매수")

    lines.append("\n" + "=" * 65)
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    report, filename = run_dashboard()
    print(report)
