"""
매매 복기 자동화
- 토스 PDF 파싱 결과에서 종목별 매매 분석
- 실현 손익, 승률, 보유기간 등 계산
- 적립식 vs 스윙 패턴 분류
"""
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

from cockpit.portfolio_parser import parse_toss_pdf, _is_buy


def analyze_trades(data):
    """
    파싱된 포트폴리오 데이터에서 매매 분석

    Returns:
        dict: {
            "closed_trades": [...],   # 완결된 매매 (매수->매도)
            "open_positions": [...],  # 현재 보유 중
            "stats": {...},           # 전체 통계
        }
    """
    closed = []
    open_pos = []

    # 실제 보유종목 (파서의 holdings 기준)
    actual_holdings = set(data.get("holdings", {}).keys())

    # KRW 종목 분석
    krw_by_code = _group_by_code(data["krw_transactions"])
    for code, txns in krw_by_code.items():
        result = _analyze_stock(txns, "KRW")
        closed.extend(result["closed"])
        # 실제 holdings에 있는 종목만 open position으로
        if result["open"] and code in actual_holdings:
            open_pos.append(result["open"])

    # USD 종목 분석
    usd_by_code = _group_by_code(data["usd_transactions"])
    for code, txns in usd_by_code.items():
        result = _analyze_stock(txns, "USD")
        closed.extend(result["closed"])
        if result["open"] and code in actual_holdings:
            open_pos.append(result["open"])

    # 전체 통계
    stats = _calc_stats(closed, open_pos)

    return {
        "closed_trades": closed,
        "open_positions": open_pos,
        "stats": stats,
    }


def _group_by_code(txns):
    """종목코드별 거래 그룹화"""
    groups = defaultdict(list)
    for txn in txns:
        code = txn.get("code", "")
        if code:
            groups[code].append(txn)
    return groups


def _analyze_stock(txns, currency):
    """
    단일 종목의 매수/매도 매칭 분석

    Returns:
        dict: {"closed": [...], "open": {...} or None}
    """
    closed_rounds = []
    buy_queue = []  # (date, qty, price)

    for i, txn in enumerate(txns):
        qty = txn["quantity"]
        if currency == "USD":
            price = txn.get("price_usd") or txn.get("price_krw", 0)
        else:
            price = txn.get("price", 0)

        # 잔고 변화로 매수/매도 판단
        prev_bal = 0
        for j in range(i - 1, -1, -1):
            prev_bal = txns[j]["balance_qty"]
            break
        is_buy = txn["balance_qty"] > prev_bal

        if is_buy:
            buy_queue.append({
                "date": txn["date"],
                "qty": qty,
                "price": price,
            })
        else:
            # 매도: FIFO로 매수와 매칭
            sell_qty = qty
            sell_price = price
            sell_date = txn["date"]
            matched_buys = []

            while sell_qty > 0 and buy_queue:
                buy = buy_queue[0]
                match_qty = min(sell_qty, buy["qty"])

                matched_buys.append({
                    "date": buy["date"],
                    "qty": match_qty,
                    "price": buy["price"],
                })

                buy["qty"] -= match_qty
                sell_qty -= match_qty

                if buy["qty"] <= 0:
                    buy_queue.pop(0)

            if matched_buys:
                total_buy_cost = sum(b["price"] * b["qty"] for b in matched_buys)
                total_qty = sum(b["qty"] for b in matched_buys)
                avg_buy = total_buy_cost / total_qty if total_qty else 0
                first_buy_date = matched_buys[0]["date"]

                pnl = (sell_price - avg_buy) * total_qty
                pnl_pct = ((sell_price - avg_buy) / avg_buy * 100) if avg_buy else 0
                hold_days = _days_between(first_buy_date, sell_date)

                closed_rounds.append({
                    "name": txn["name"],
                    "code": txn.get("code", ""),
                    "currency": currency,
                    "buy_date": first_buy_date,
                    "sell_date": sell_date,
                    "quantity": total_qty,
                    "avg_buy_price": round(avg_buy, 4),
                    "sell_price": sell_price,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "hold_days": hold_days,
                    "pattern": _classify_pattern(hold_days, total_qty),
                })

    # 남은 미체결 매수 = 현재 보유
    open_position = None
    if buy_queue:
        total_qty = sum(b["qty"] for b in buy_queue)
        total_cost = sum(b["price"] * b["qty"] for b in buy_queue)
        avg_price = total_cost / total_qty if total_qty else 0
        first_date = buy_queue[0]["date"]
        last_date = buy_queue[-1]["date"]

        open_position = {
            "name": txns[-1]["name"],
            "code": txns[-1].get("code", ""),
            "currency": currency,
            "quantity": total_qty,
            "avg_price": round(avg_price, 4),
            "first_buy": first_date,
            "last_buy": last_date,
            "buy_count": len(buy_queue),
            "pattern": _classify_open_pattern(buy_queue),
        }

    return {"closed": closed_rounds, "open": open_position}


def _days_between(d1, d2):
    """두 날짜 문자열 간 일수 차이"""
    fmt = "%Y.%m.%d"
    try:
        dt1 = datetime.strptime(d1, fmt)
        dt2 = datetime.strptime(d2, fmt)
        return (dt2 - dt1).days
    except ValueError:
        return 0


def _classify_pattern(hold_days, qty):
    """매매 패턴 분류"""
    if hold_days == 0:
        return "day_trade"
    elif hold_days <= 3:
        return "swing_short"
    elif hold_days <= 14:
        return "swing"
    else:
        return "position"


def _classify_open_pattern(buy_queue):
    """보유중인 포지션 패턴 분류"""
    if len(buy_queue) <= 1:
        return "single_entry"
    dates = [b["date"] for b in buy_queue]
    unique_dates = len(set(dates))
    if unique_dates >= 3:
        return "dca"  # Dollar Cost Averaging (적립식)
    return "multi_entry"


def _calc_stats(closed, open_pos):
    """전체 매매 통계"""
    if not closed:
        return {
            "total_closed": 0,
            "win_rate": 0,
            "total_pnl_krw": 0,
            "total_pnl_usd": 0,
        }

    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] < 0]
    even = [t for t in closed if t["pnl"] == 0]

    krw_pnl = sum(t["pnl"] for t in closed if t["currency"] == "KRW")
    usd_pnl = sum(t["pnl"] for t in closed if t["currency"] == "USD")

    patterns = defaultdict(int)
    for t in closed:
        patterns[t["pattern"]] += 1

    return {
        "total_closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "even": len(even),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "total_pnl_krw": round(krw_pnl),
        "total_pnl_usd": round(usd_pnl, 2),
        "avg_hold_days": round(
            sum(t["hold_days"] for t in closed) / len(closed), 1
        ),
        "patterns": dict(patterns),
    }


# --- 리포트 생성 ---

def format_review(result):
    """매매 복기 리포트 텍스트 생성"""
    lines = []
    lines.append("=" * 60)
    lines.append("  TRADE REVIEW")
    lines.append("=" * 60)

    stats = result["stats"]
    lines.append(f"\n[Summary]")
    lines.append(f"  총 매매: {stats['total_closed']}건")
    lines.append(
        f"  승/패/무: {stats.get('wins',0)}/{stats.get('losses',0)}/{stats.get('even',0)}"
        f"  (승률 {stats['win_rate']}%)"
    )
    if stats.get("total_pnl_krw"):
        lines.append(f"  실현손익(KRW): {stats['total_pnl_krw']:+,}원")
    if stats.get("total_pnl_usd"):
        lines.append(f"  실현손익(USD): ${stats['total_pnl_usd']:+,.2f}")
    if stats.get("avg_hold_days") is not None:
        lines.append(f"  평균 보유기간: {stats['avg_hold_days']}일")
    if stats.get("patterns"):
        pat_str = ", ".join(f"{k}:{v}" for k, v in stats["patterns"].items())
        lines.append(f"  매매패턴: {pat_str}")

    # 실현 매매 상세 (최근 10건)
    closed = result["closed_trades"]
    if closed:
        lines.append(f"\n[Closed Trades] (최근 {min(10, len(closed))}건)")
        lines.append(
            f"  {'종목':<20} {'기간':<25} {'수량':>5} {'손익':>12} {'수익률':>8} {'패턴':<12}"
        )
        lines.append("  " + "-" * 85)
        for t in closed[-10:]:
            sym = f"{t['currency']}"
            pnl_str = (
                f"{t['pnl']:+,.0f}" if t["currency"] == "KRW"
                else f"${t['pnl']:+,.2f}"
            )
            period = f"{t['buy_date']}~{t['sell_date']}({t['hold_days']}d)"
            lines.append(
                f"  {t['name'][:20]:<20} {period:<25} {t['quantity']:>5} "
                f"{pnl_str:>12} {t['pnl_pct']:>+7.1f}% {t['pattern']:<12}"
            )

    # 현재 보유 포지션
    open_pos = result["open_positions"]
    if open_pos:
        lines.append(f"\n[Open Positions]")
        lines.append(
            f"  {'종목':<25} {'수량':>5} {'평단가':>12} {'매수기간':<25} {'패턴':<10}"
        )
        lines.append("  " + "-" * 80)
        for p in open_pos:
            price_str = (
                f"{p['avg_price']:,.0f}" if p["currency"] == "KRW"
                else f"${p['avg_price']:,.2f}"
            )
            period = f"{p['first_buy']}~{p['last_buy']}"
            lines.append(
                f"  {p['name'][:25]:<25} {p['quantity']:>5} {price_str:>12} "
                f"{period:<25} {p['pattern']:<10}"
            )

    lines.append("=" * 60)
    return "\n".join(lines)


# --- CLI ---

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "Portfolio")

    # 캐시된 JSON이 있으면 사용, 없으면 PDF 파싱
    json_path = os.path.join(pdf_dir, "portfolio_latest.json")
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded: portfolio_latest.json")
    else:
        pdfs = sorted([f for f in os.listdir(pdf_dir) if f.endswith(".pdf")], reverse=True)
        if not pdfs:
            print("Portfolio/ 폴더에 PDF가 없습니다.")
            sys.exit(1)
        data = parse_toss_pdf(os.path.join(pdf_dir, pdfs[0]))

    result = analyze_trades(data)
    print(format_review(result))
