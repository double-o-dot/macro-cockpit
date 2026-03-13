"""
투자 브리핑 시스템 설정
"""

# --- 데이터 소스 ---
SOURCES = {
    "geeknews_rss": "https://news.hada.io/rss/news",
    "naver_economy": "https://news.google.com/rss/search?q=한국+경제&hl=ko&gl=KR&ceid=KR:ko",
    "naver_stock": "https://news.google.com/rss/search?q=주식+시장&hl=ko&gl=KR&ceid=KR:ko",
}

# --- 관심 종목/지수 ---
WATCHLIST = {
    # 한국 지수
    "^KS11": "KOSPI",
    "^KQ11": "KOSDAQ",
    # 미국 지수
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^DJI": "다우존스",
    # 환율/원자재
    "USDKRW=X": "달러/원",
    "GC=F": "금",
    "CL=F": "원유(WTI)",
    "BTC-USD": "비트코인",
}

# --- 테마 키워드 (테크 <-> 시장 연관성 탐색용) ---
TECH_MARKET_KEYWORDS = {
    "AI": ["엔비디아", "NVDA", "반도체", "GPU", "AI", "LLM", "OpenAI", "Anthropic", "딥러닝"],
    "클라우드": ["AWS", "Azure", "GCP", "클라우드", "SaaS", "인프라"],
    "반도체": ["삼성전자", "SK하이닉스", "TSMC", "반도체", "메모리", "HBM", "파운드리"],
    "핀테크": ["결제", "블록체인", "암호화폐", "비트코인", "스테이블코인", "CBDC"],
    "모빌리티": ["자율주행", "전기차", "테슬라", "배터리", "2차전지"],
    "바이오": ["신약", "FDA", "바이오", "제약", "헬스케어"],
}

# --- 출력 설정 ---
OUTPUT_DIR = "reports"
