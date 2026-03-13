"""
Macro Cockpit - 통합 CLI
사용법:
  python cockpit.py portfolio     포트폴리오 스냅샷
  python cockpit.py review        매매 복기
  python cockpit.py signal        매크로 신호등
  python cockpit.py digest        커뮤니티 PDF 분석
  python cockpit.py dashboard     전체 대시보드
  python cockpit.py help          도움말
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")


def cmd_portfolio():
    """포트폴리오 스냅샷"""
    from cockpit.portfolio_parser import parse_toss_pdf, generate_summary, save_parsed

    pdf_dir = os.path.join(os.path.dirname(__file__), "Portfolio")
    pdfs = sorted([f for f in os.listdir(pdf_dir) if f.endswith(".pdf")], reverse=True)

    if not pdfs:
        print("Portfolio/ 폴더에 토스 거래내역서 PDF를 넣어주세요.")
        return

    latest = os.path.join(pdf_dir, pdfs[0])
    print(f"Parsing: {pdfs[0]}")

    data = parse_toss_pdf(latest)
    print(f"KRW 거래: {len(data['krw_transactions'])}건 | USD 거래: {len(data['usd_transactions'])}건")
    print(generate_summary(data["holdings"], data["cash"]))

    out = os.path.join(pdf_dir, "portfolio_latest.json")
    save_parsed(data, out)
    print(f"Saved: {out}")


def cmd_review():
    """매매 복기"""
    import json
    from cockpit.portfolio_parser import parse_toss_pdf
    from cockpit.trade_review import analyze_trades, format_review

    pdf_dir = os.path.join(os.path.dirname(__file__), "Portfolio")
    json_path = os.path.join(pdf_dir, "portfolio_latest.json")

    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        pdfs = sorted([f for f in os.listdir(pdf_dir) if f.endswith(".pdf")], reverse=True)
        if not pdfs:
            print("Portfolio/ 폴더에 PDF가 없습니다.")
            return
        data = parse_toss_pdf(os.path.join(pdf_dir, pdfs[0]))

    result = analyze_trades(data)
    print(format_review(result))


def cmd_signal():
    """매크로 신호등"""
    from cockpit.macro_signal import fetch_macro_data, generate_signals, format_signals

    print("Fetching macro data...")
    macro_data = fetch_macro_data()
    signals = generate_signals(macro_data)
    print(format_signals(macro_data, signals))


def cmd_digest():
    """커뮤니티 PDF 분석"""
    import json
    from cockpit.portfolio_parser import generate_summary
    from cockpit.pdf_brain import digest_all, format_digest

    # 포트폴리오 요약 로드 (있으면)
    holdings_text = ""
    json_path = os.path.join(os.path.dirname(__file__), "Portfolio", "portfolio_latest.json")
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            pdata = json.load(f)
        holdings_text = generate_summary(pdata.get("holdings", {}), pdata.get("cash", {}))

    force = "--force" in sys.argv
    print(f"Analyzing community PDFs...{' (force re-analyze)' if force else ''}")
    results = digest_all(holdings_summary=holdings_text, force=force)
    print(format_digest(results))


def cmd_dashboard():
    """전체 대시보드"""
    from cockpit.dashboard import run_dashboard
    skip_pdf = "--skip-pdf" in sys.argv
    report, filename = run_dashboard(skip_pdf=skip_pdf)
    print(report)


def cmd_help():
    print(__doc__)


COMMANDS = {
    "portfolio": cmd_portfolio,
    "review": cmd_review,
    "signal": cmd_signal,
    "digest": cmd_digest,
    "dashboard": cmd_dashboard,
    "help": cmd_help,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)

    command = sys.argv[1]
    if command in COMMANDS:
        COMMANDS[command]()
    else:
        print(f"Unknown command: {command}")
        cmd_help()
