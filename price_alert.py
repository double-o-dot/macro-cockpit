"""
종목 가격 알림 스크립트
설정된 조건에 도달하면 Gmail로 알림을 발송합니다.

사용법:
    python price_alert.py           # 알림 체크 실행
    python price_alert.py --dry-run # 체크만 하고 이메일 미발송
    python price_alert.py --status  # 현재 워치리스트 상태 출력
"""
import os
import sys
import json
import base64
import logging
from datetime import datetime
from email.mime.text import MIMEText

import yfinance as yf
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALERT_CONFIG = os.path.join(BASE_DIR, 'price_alerts.json')
ALERT_LOG = os.path.join(BASE_DIR, 'logs', 'price_alerts.log')
TOKEN_FILE = os.path.join(os.path.dirname(BASE_DIR), 'token.json')
MY_EMAIL = 'woong.seo@kurlycorp.com'
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
]

# --- Logging ---
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(ALERT_LOG, encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# --- Default watchlist ---
DEFAULT_ALERTS = [
    {
        "ticker": "RKLB",
        "name": "Rocket Lab",
        "condition": "below",
        "target_price": 65.0,
        "reason": "DCF 가중평균 $81.50 대비 20% 안전마진. GP마진 35%+ 압도적 경쟁우위",
        "enabled": True,
        "last_alerted": None,
        "cooldown_hours": 24,
    },
]


def load_config():
    """알림 설정 로드 (없으면 기본값 생성)"""
    if os.path.exists(ALERT_CONFIG):
        with open(ALERT_CONFIG, encoding='utf-8') as f:
            return json.load(f)
    save_config(DEFAULT_ALERTS)
    return DEFAULT_ALERTS


def save_config(alerts):
    """알림 설정 저장"""
    with open(ALERT_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)


def get_gmail_service():
    """Gmail API 서비스"""
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def fetch_price(ticker):
    """yfinance로 현재가 조회"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='1d')
        if hist.empty:
            return None
        return round(float(hist['Close'].iloc[-1]), 2)
    except Exception as e:
        logger.error(f'가격 조회 실패 [{ticker}]: {e}')
        return None


def check_condition(price, condition, target):
    """조건 충족 여부 확인"""
    if condition == 'below':
        return price <= target
    elif condition == 'above':
        return price >= target
    return False


def should_alert(alert):
    """쿨다운 체크 (같은 알림 반복 방지)"""
    if not alert.get('last_alerted'):
        return True
    try:
        last = datetime.fromisoformat(alert['last_alerted'])
        hours = (datetime.now() - last).total_seconds() / 3600
        return hours >= alert.get('cooldown_hours', 24)
    except (ValueError, TypeError):
        return True


def send_alert_email(service, alert, current_price):
    """알림 이메일 발송"""
    direction = '이하 하락' if alert['condition'] == 'below' else '이상 상승'
    diff_pct = ((current_price - alert['target_price']) / alert['target_price']) * 100

    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif; max-width:600px; margin:0 auto; padding:20px; color:#333;">

<div style="background:#D97757; color:white; padding:15px 20px; border-radius:12px 12px 0 0;">
  <h2 style="margin:0; font-size:18px;">Price Alert Triggered</h2>
</div>

<div style="background:#fff; border:1px solid #E5DED5; border-top:none; padding:20px; border-radius:0 0 12px 12px;">
  <div style="text-align:center; padding:20px 0;">
    <div style="font-size:14px; color:#666; margin-bottom:5px;">{alert["ticker"]} ({alert["name"]})</div>
    <div style="font-size:36px; font-weight:bold; color:{"#d93025" if alert["condition"]=="below" else "#0d652d"};">${current_price:.2f}</div>
    <div style="font-size:13px; color:#666; margin-top:5px;">목표가 ${alert["target_price"]:.2f} {direction} ({diff_pct:+.1f}%)</div>
  </div>

  <div style="background:#f8f9fa; padding:15px; border-radius:8px; margin:15px 0;">
    <div style="font-size:12px; color:#666; margin-bottom:5px;">매수 근거</div>
    <div style="font-size:14px;">{alert["reason"]}</div>
  </div>

  <div style="text-align:center; padding-top:15px;">
    <div style="font-size:12px; color:#999;">Macro Cockpit Price Alert | {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
  </div>
</div>

</body></html>'''

    subject = f'[Price Alert] {alert["ticker"]} ${current_price:.2f} — 목표가 ${alert["target_price"]:.2f} {direction}'
    msg = MIMEText(html, 'html', 'utf-8')
    msg['to'] = MY_EMAIL
    msg['subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return result['id']


def main():
    dry_run = '--dry-run' in sys.argv
    status_only = '--status' in sys.argv

    alerts = load_config()
    active = [a for a in alerts if a.get('enabled', True)]

    if status_only:
        print(f'\n  Price Alert Watchlist ({len(active)}/{len(alerts)} active)')
        print('  ' + '=' * 50)
        for a in alerts:
            status = 'ON' if a.get('enabled') else 'OFF'
            direction = '<=' if a['condition'] == 'below' else '>='
            price = fetch_price(a['ticker'])
            price_str = f'${price:.2f}' if price else 'N/A'
            triggered = check_condition(price, a['condition'], a['target_price']) if price else False
            marker = ' *** TRIGGERED ***' if triggered else ''
            print(f'  [{status}] {a["ticker"]:6} {price_str:>10} {direction} ${a["target_price"]:.2f}{marker}')
            if a.get('last_alerted'):
                print(f'         Last alert: {a["last_alerted"]}')
        print()
        return

    logger.info('=' * 50)
    logger.info(f'Price Alert Check {"(DRY RUN)" if dry_run else ""} — {len(active)} alerts')
    logger.info('=' * 50)

    service = None
    triggered_count = 0

    for alert in active:
        ticker = alert['ticker']
        price = fetch_price(ticker)
        if price is None:
            logger.warning(f'[{ticker}] 가격 조회 실패 — 건너뜀')
            continue

        logger.info(f'[{ticker}] 현재가 ${price:.2f} / 목표 ${alert["target_price"]:.2f} ({alert["condition"]})')

        if check_condition(price, alert['condition'], alert['target_price']):
            if not should_alert(alert):
                logger.info(f'[{ticker}] 조건 충족이나 쿨다운 중 — 건너뜀')
                continue

            logger.info(f'[{ticker}] *** ALERT TRIGGERED *** ${price:.2f}')
            triggered_count += 1

            if dry_run:
                logger.info(f'[{ticker}] [DRY RUN] 이메일 미발송')
            else:
                try:
                    if service is None:
                        service = get_gmail_service()
                    msg_id = send_alert_email(service, alert, price)
                    logger.info(f'[{ticker}] 알림 발송 완료 (ID: {msg_id})')
                    alert['last_alerted'] = datetime.now().isoformat()
                except Exception as e:
                    logger.error(f'[{ticker}] 알림 발송 실패: {e}')

    save_config(alerts)
    logger.info(f'완료: {triggered_count}건 트리거')


if __name__ == '__main__':
    main()
