"""
토스증권 거래내역서 PDF 파서
- PDF 텍스트에서 거래내역 추출
- 현재 보유종목 계산
- 매매 이력 구조화
"""
import re
import os
import json
from datetime import datetime
from collections import defaultdict

import pdfplumber


# --- 유틸리티 ---

def _clean_num(s):
    """숫자 문자열 정리"""
    if not s:
        return 0
    s = str(s).strip().replace(",", "").replace(" ", "")
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return 0


def _extract_usd(s):
    """'($ 2,497.47)' 에서 달러 금액 추출"""
    match = re.search(r'\$\s*([\d,.]+)', str(s))
    if match:
        return float(match.group(1).replace(",", ""))
    return None


# --- KRW 거래 파싱 ---

# KRW 패턴: 날짜 구분 종목명(코드) [숫자들...]
KRW_PATTERN = re.compile(
    r'(\d{4}\.\d{2}\.\d{2})\s+'       # 거래일자
    r'(\S+)\s+'                         # 거래구분 (구매/판매)
    r'(.+?)\((A[A-Z0-9]+)\)\s+'        # 종목명(종목코드)
    r'(\d[\d,]*)\s+'                    # 거래수량
    r'(\d[\d,]*)\s+'                    # 거래대금
    r'(\d[\d,]*)\s+'                    # 단가
    r'(\d[\d,]*)\s+'                    # 수수료
    r'(\d[\d,]*)\s+'                    # 거래세
    r'(\d[\d,]*)\s+'                    # 제세금
    r'(\d[\d,]*)\s+'                    # 변제/연체합
    r'(-?\d[\d,]*)\s+'                  # 잔고
    r'(\d[\d,]*)'                       # 잔액
)


def _parse_krw_lines(text):
    """원화 거래내역 텍스트에서 거래 추출"""
    txns = []
    for m in KRW_PATTERN.finditer(text):
        action = m.group(2)
        # 인코딩 깨진 한글 매핑
        if action in ("\xc6\xc7\xb8\xc5", "\ud310\ub9e4"):
            action = "판매"
        elif action in ("\xb1\xb8\xb8\xc5", "\uad6c\ub9e4"):
            action = "구매"

        txns.append({
            "date": m.group(1),
            "action": action,
            "name": m.group(3).strip(),
            "code": m.group(4),
            "quantity": _clean_num(m.group(5)),
            "amount": _clean_num(m.group(6)),
            "price": _clean_num(m.group(7)),
            "fee": _clean_num(m.group(8)),
            "trade_tax": _clean_num(m.group(9)),
            "tax": _clean_num(m.group(10)),
            "balance_qty": int(str(m.group(12)).replace(",", "")),
            "balance_krw": _clean_num(m.group(13)),
            "currency": "KRW",
        })
    return txns


# --- USD 거래 파싱 ---

# USD 2줄 구조:
# 포맷A (긴 이름): Line1에 이름만, Line2에 (ISIN) ($금액들)
# 포맷B (짧은 이름): Line1에 이름(ISIN), Line2에 ($금액들)
USD_LINE1 = re.compile(
    r'(\d{4}\.\d{2}\.\d{2})\s+'        # 거래일자
    r'(\S+)\s+'                         # 거래구분
    r'(.+?)\s+'                         # 종목명 (ISIN 포함 가능)
    r'(\d[,\d]*\.\d{2})\s+'            # 환율 (소수점 포함)
    r'(\d+)\s+'                         # 거래수량
    r'(\d[\d,]*)\s+'                    # 거래대금(원)
    r'(\d[\d,]*)\s+'                    # 단가(원)
    r'(\d[\d,]*)\s+'                    # 수수료(원)
    r'(\d[\d,]*)\s+'                    # 제세금(원)
    r'(\d[\d,]*)\s+'                    # 변제/연체합(원)
    r'(\d+)\s+'                         # 잔고
    r'(\d[\d,]*)'                       # 잔액(원)
)

# 포맷A: (ISIN) + 달러 금액들
USD_LINE2_WITH_ISIN = re.compile(
    r'\(((?:US|CA)[A-Z0-9]+)\)\s+'     # ISIN 코드
    r'\(\$\s*([\d,.]+)\)\s+'            # 거래대금($)
    r'\(\$\s*([\d,.]+)\)\s+'            # 단가($)
    r'\(\$\s*([\d,.]+)\)\s+'            # 수수료($)
    r'\(\$\s*([\d,.]+)\)\s+'            # 제세금($)
    r'\(\$\s*([\d,.]+)\)\s+'            # 변제($)
    r'\(\$\s*([\d,.]+)\)'               # 잔액($)
)

# 포맷B: 달러 금액만 (ISIN은 Line1에 이미 있음)
USD_LINE2_NO_ISIN = re.compile(
    r'^\s*\(\$\s*([\d,.]+)\)\s+'        # 거래대금($) - 줄 시작
    r'\(\$\s*([\d,.]+)\)\s+'            # 단가($)
    r'\(\$\s*([\d,.]+)\)\s+'            # 수수료($)
    r'\(\$\s*([\d,.]+)\)\s+'            # 제세금($)
    r'\(\$\s*([\d,.]+)\)\s+'            # 변제($)
    r'\(\$\s*([\d,.]+)\)'               # 잔액($)
)

# Line1 종목명에서 ISIN 추출
ISIN_IN_NAME = re.compile(r'\(((?:US|CA)[A-Z0-9]+)\)')


def _parse_usd_lines(text):
    """달러 거래내역 텍스트에서 거래 추출"""
    txns = []
    lines = text.split("\n")

    i = 0
    while i < len(lines):
        m1 = USD_LINE1.search(lines[i])
        if m1:
            action = m1.group(2)
            name_raw = m1.group(3).strip()

            # Line1에서 ISIN 추출 시도 (포맷B)
            isin_in_name = ISIN_IN_NAME.search(name_raw)
            isin = isin_in_name.group(1) if isin_in_name else None
            name_clean = ISIN_IN_NAME.sub("", name_raw).strip() if isin else name_raw

            usd_amount = None
            usd_price = None
            usd_fee = None
            usd_balance = None

            if i + 1 < len(lines):
                # 포맷A: (ISIN) ($...) ($...) ...
                m2a = USD_LINE2_WITH_ISIN.search(lines[i + 1])
                # 포맷B: ($...) ($...) ... (ISIN 없음)
                m2b = USD_LINE2_NO_ISIN.search(lines[i + 1])

                if m2a:
                    if not isin:
                        isin = m2a.group(1)
                    usd_amount = float(m2a.group(2).replace(",", ""))
                    usd_price = float(m2a.group(3).replace(",", ""))
                    usd_fee = float(m2a.group(4).replace(",", ""))
                    usd_balance = float(m2a.group(7).replace(",", ""))
                    i += 1
                elif m2b:
                    usd_amount = float(m2b.group(1).replace(",", ""))
                    usd_price = float(m2b.group(2).replace(",", ""))
                    usd_fee = float(m2b.group(3).replace(",", ""))
                    usd_balance = float(m2b.group(6).replace(",", ""))
                    i += 1

            txns.append({
                "date": m1.group(1),
                "action": action,
                "name": name_clean,
                "code": isin or "",
                "exchange_rate": float(m1.group(4).replace(",", "")),
                "quantity": int(m1.group(5)),
                "amount_krw": _clean_num(m1.group(6)),
                "amount_usd": usd_amount,
                "price_krw": _clean_num(m1.group(7)),
                "price_usd": usd_price,
                "fee_usd": usd_fee,
                "balance_qty": int(m1.group(11)),
                "balance_krw": _clean_num(m1.group(12)),
                "balance_usd": usd_balance,
                "currency": "USD",
            })
        i += 1
    return txns


# --- 보유종목 계산 ---

def _calculate_holdings(krw_txns, usd_txns):
    """거래내역에서 최종 보유종목 계산 (마지막 잔고 기준)"""
    holdings = {}

    # KRW: 각 종목의 마지막 거래에서 잔고 확인
    krw_last = {}
    for txn in krw_txns:
        krw_last[txn["code"]] = txn

    for code, txn in krw_last.items():
        if txn["balance_qty"] != 0:
            holdings[code] = {
                "name": txn["name"],
                "code": code,
                "quantity": txn["balance_qty"],
                "avg_price": _estimate_avg_price(krw_txns, code),
                "currency": "KRW",
            }

    # USD: 각 종목의 마지막 거래에서 잔고 확인
    usd_last = {}
    for txn in usd_txns:
        if txn["code"]:
            usd_last[txn["code"]] = txn

    for code, txn in usd_last.items():
        if txn["balance_qty"] != 0:
            holdings[code] = {
                "name": txn["name"],
                "code": code,
                "quantity": txn["balance_qty"],
                "avg_price_usd": _estimate_avg_price_usd(usd_txns, code),
                "currency": "USD",
            }

    return holdings


def _is_buy(txn_list, idx):
    """잔고(balance_qty) 변화로 매수/매도 판단 (한글 깨짐 대응)"""
    txn = txn_list[idx]
    # 같은 종목의 이전 거래 잔고와 비교
    code = txn.get("code", "")
    prev_bal = 0
    for j in range(idx - 1, -1, -1):
        if txn_list[j].get("code") == code:
            prev_bal = txn_list[j]["balance_qty"]
            break
    return txn["balance_qty"] > prev_bal


def _estimate_avg_price(txns, code):
    """KRW 종목 평균 매수가 추정 (잔고 변화 기반)"""
    code_txns = [(i, t) for i, t in enumerate(txns) if t["code"] == code]
    total_qty = 0
    total_cost = 0
    for idx, txn in code_txns:
        if _is_buy(txns, idx):
            total_qty += txn["quantity"]
            total_cost += txn["amount"]
        else:
            total_qty -= txn["quantity"]
            if total_qty <= 0:
                total_qty = 0
                total_cost = 0
    if total_qty > 0:
        return round(total_cost / total_qty)
    return 0


def _estimate_avg_price_usd(txns, code):
    """USD 종목 평균 매수가 추정 (잔고 변화 기반)"""
    code_txns = [(i, t) for i, t in enumerate(txns) if t.get("code") == code]
    total_qty = 0
    total_cost = 0.0
    for idx, txn in code_txns:
        if _is_buy(txns, idx):
            price = txn.get("price_usd") or 0
            total_qty += txn["quantity"]
            total_cost += price * txn["quantity"]
        else:
            total_qty -= txn["quantity"]
            if total_qty <= 0:
                total_qty = 0
                total_cost = 0.0
    if total_qty > 0:
        return round(total_cost / total_qty, 2)
    return 0.0


# --- 현금 잔액 ---

def _get_final_cash(krw_txns, usd_txns):
    """마지막 거래의 잔액에서 현금 추출"""
    cash = {"krw": 0, "usd": 0.0}
    if krw_txns:
        cash["krw"] = krw_txns[-1]["balance_krw"]
    if usd_txns:
        last_usd = usd_txns[-1]
        cash["usd"] = last_usd.get("balance_usd", 0.0) or 0.0
        cash["krw_equiv"] = last_usd.get("balance_krw", 0)
    return cash


# --- 메타데이터 ---

def _parse_metadata(text):
    """PDF 텍스트에서 계좌 정보 추출"""
    meta = {}
    # 계좌번호
    m = re.search(r'(\d{3}-\d{2}-\d{6})', text)
    if m:
        meta["account"] = m.group(1)
    # 조회기간
    m = re.search(r'(\d{4})\S+\s*(\d+)\S+\s*(\d+)\S+\s*~\s*(\d{4})\S+\s*(\d+)\S+\s*(\d+)', text)
    if m:
        meta["period_start"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        meta["period_end"] = f"{m.group(4)}-{int(m.group(5)):02d}-{int(m.group(6)):02d}"
    return meta


# --- 요약 생성 ---

def generate_summary(holdings, cash):
    """보유종목 + 현금 요약 텍스트"""
    lines = ["=" * 60]
    lines.append("  PORTFOLIO SNAPSHOT")
    lines.append("=" * 60)

    krw_holdings = {k: v for k, v in holdings.items() if v["currency"] == "KRW"}
    usd_holdings = {k: v for k, v in holdings.items() if v["currency"] == "USD"}

    if krw_holdings:
        lines.append("\n[KRW Holdings]")
        lines.append(f"  {'종목':<25} {'수량':>6} {'평단가':>12}")
        lines.append("  " + "-" * 45)
        for code, h in krw_holdings.items():
            lines.append(f"  {h['name']:<25} {h['quantity']:>6} {h['avg_price']:>12,}")

    if usd_holdings:
        lines.append("\n[USD Holdings]")
        lines.append(f"  {'종목':<35} {'수량':>6} {'평단가($)':>12}")
        lines.append("  " + "-" * 55)
        for code, h in usd_holdings.items():
            lines.append(f"  {h['name']:<35} {h['quantity']:>6} {h['avg_price_usd']:>12.2f}")

    lines.append(f"\n[Cash]")
    lines.append(f"  KRW: {cash.get('krw', 0):>15,}")
    if cash.get("usd"):
        lines.append(f"  USD: ${cash['usd']:>14,.2f}")

    lines.append("=" * 60)
    return "\n".join(lines)


# --- 메인 파서 ---

def parse_toss_pdf(pdf_path):
    """
    토스증권 거래내역서 PDF 파싱

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        dict: 구조화된 포트폴리오 데이터
    """
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"

    # 원화/달러 섹션 분리
    # 달러 섹션 시작점 찾기: 환율 컬럼이 있는 첫 번째 USD 거래
    # KRW 섹션에는 환율이 비어있고, USD에는 1,4xx.xx 형태
    krw_txns = _parse_krw_lines(full_text)
    usd_txns = _parse_usd_lines(full_text)

    holdings = _calculate_holdings(krw_txns, usd_txns)
    cash = _get_final_cash(krw_txns, usd_txns)
    meta = _parse_metadata(full_text)

    return {
        "meta": meta,
        "krw_transactions": krw_txns,
        "usd_transactions": usd_txns,
        "holdings": holdings,
        "cash": cash,
        "parsed_at": datetime.now().isoformat(),
    }


def save_parsed(data, output_path):
    """파싱 결과를 JSON으로 저장"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# --- CLI ---

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "Portfolio")
    pdfs = sorted(
        [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")],
        reverse=True,
    )

    if not pdfs:
        print("Portfolio/ 폴더에 토스 거래내역서 PDF가 없습니다.")
        sys.exit(1)

    latest = os.path.join(pdf_dir, pdfs[0])
    print(f"Parsing: {pdfs[0]}")

    data = parse_toss_pdf(latest)

    print(f"\nKRW 거래: {len(data['krw_transactions'])}건")
    print(f"USD 거래: {len(data['usd_transactions'])}건")
    print(f"보유종목: {len(data['holdings'])}개")
    print(generate_summary(data["holdings"], data["cash"]))

    # Save
    out = os.path.join(pdf_dir, "portfolio_latest.json")
    save_parsed(data, out)
    print(f"\nSaved: {out}")
