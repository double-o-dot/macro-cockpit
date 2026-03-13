"""
한국투자증권 Open API 클라이언트
- 토큰 발급/갱신
- 잔고 조회
- 시세 조회
"""
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), 'api.env')
TOKEN_FILE = os.path.join(BASE_DIR, 'kis_token.json')

load_dotenv(ENV_FILE)

# 실전투자 도메인 (모의투자: https://openapivts.koreainvestment.com:29443)
BASE_URL = 'https://openapi.koreainvestment.com:9443'

APP_KEY = os.getenv('KIS_APP_KEY')
APP_SECRET = os.getenv('KIS_APP_SECRET')


def get_token():
    """접근 토큰 발급 (캐시 있으면 재사용)"""
    # 캐시된 토큰 확인
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding='utf-8') as f:
            cached = json.load(f)
        expires = datetime.fromisoformat(cached['expires_at'])
        if datetime.now() < expires - timedelta(hours=1):
            return cached['access_token']

    # 신규 발급
    resp = requests.post(f'{BASE_URL}/oauth2/tokenP', json={
        'grant_type': 'client_credentials',
        'appkey': APP_KEY,
        'appsecret': APP_SECRET,
    })
    resp.raise_for_status()
    data = resp.json()

    # 캐시 저장 (토큰 유효기간: 약 24시간)
    token_info = {
        'access_token': data['access_token'],
        'token_type': data['token_type'],
        'expires_at': (datetime.now() + timedelta(hours=23)).isoformat(),
    }
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(token_info, f, ensure_ascii=False, indent=2)

    return data['access_token']


def _headers(tr_id):
    """공통 헤더 생성"""
    token = get_token()
    return {
        'content-type': 'application/json; charset=utf-8',
        'authorization': f'Bearer {token}',
        'appkey': APP_KEY,
        'appsecret': APP_SECRET,
        'tr_id': tr_id,
    }


def get_balance(account_no, account_cd='01'):
    """주식 잔고 조회
    account_no: 계좌번호 (8자리, 예: '50123456')
    account_cd: 계좌상품코드 (기본 '01')
    """
    headers = _headers('TTTC8434R')
    params = {
        'CANO': account_no,
        'ACNT_PRDT_CD': account_cd,
        'AFHR_FLPR_YN': 'N',
        'OFL_YN': '',
        'INQR_DVSN': '02',
        'UNPR_DVSN': '01',
        'FUND_STTL_ICLD_YN': 'N',
        'FNCG_AMT_AUTO_RDPT_YN': 'N',
        'PRCS_DVSN': '01',
        'CTX_AREA_FK100': '',
        'CTX_AREA_NK100': '',
    }
    resp = requests.get(
        f'{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance',
        headers=headers, params=params
    )
    resp.raise_for_status()
    return resp.json()


def get_overseas_balance(account_no, account_cd='01'):
    """해외주식 잔고 조회"""
    headers = _headers('TTTS3012R')
    params = {
        'CANO': account_no,
        'ACNT_PRDT_CD': account_cd,
        'OVRS_EXCG_CD': 'NASD',
        'TR_CRCY_CD': 'USD',
        'CTX_AREA_FK200': '',
        'CTX_AREA_NK200': '',
    }
    resp = requests.get(
        f'{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance',
        headers=headers, params=params
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == '__main__':
    print('=== 한국투자증권 API 토큰 발급 테스트 ===')
    try:
        token = get_token()
        print(f'토큰 발급 성공: {token[:20]}...')
        print(f'캐시 저장: {TOKEN_FILE}')
    except Exception as e:
        print(f'토큰 발급 실패: {e}')
