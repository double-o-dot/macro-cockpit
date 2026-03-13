"""
투자 브리핑 시스템 관리 도구
- 관심 종목 추가/제거/조회
- 테마 키워드 관리
- 브리핑 즉시 실행
- API 키 상태 확인
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")


CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.py")
USER_CONFIG = os.path.join(os.path.dirname(__file__), "user_config.json")


def load_user_config():
    """사용자 설정 로드 (JSON)"""
    if os.path.exists(USER_CONFIG):
        with open(USER_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"extra_watchlist": {}, "extra_keywords": {}}


def save_user_config(config):
    """사용자 설정 저장"""
    with open(USER_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("설정 저장 완료.")


def cmd_status():
    """현재 설정 상태 확인"""
    from config import WATCHLIST, TECH_MARKET_KEYWORDS

    print("\n=== 투자 브리핑 시스템 상태 ===\n")

    # API 키 상태
    anthropic_key = "설정됨" if os.environ.get("ANTHROPIC_API_KEY") else "미설정"
    ecos_key = "설정됨" if os.environ.get("ECOS_API_KEY") else "미설정"
    print(f"ANTHROPIC_API_KEY: {anthropic_key}")
    print(f"ECOS_API_KEY:      {ecos_key}")

    # 관심 종목
    user_cfg = load_user_config()
    all_watchlist = {**WATCHLIST, **user_cfg.get("extra_watchlist", {})}
    print(f"\n관심 종목 ({len(all_watchlist)}개):")
    for symbol, name in all_watchlist.items():
        marker = " [사용자]" if symbol in user_cfg.get("extra_watchlist", {}) else ""
        print(f"  {symbol:<15} {name}{marker}")

    # 테마 키워드
    print(f"\n테마 ({len(TECH_MARKET_KEYWORDS)}개): {', '.join(TECH_MARKET_KEYWORDS.keys())}")

    # 리포트 목록
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    if os.path.exists(reports_dir):
        reports = sorted(os.listdir(reports_dir), reverse=True)[:5]
        print(f"\n최근 리포트:")
        for r in reports:
            print(f"  {r}")


def cmd_add(symbol, name):
    """관심 종목 추가"""
    config = load_user_config()
    config["extra_watchlist"][symbol] = name
    save_user_config(config)
    print(f"추가됨: {symbol} -> {name}")


def cmd_remove(symbol):
    """관심 종목 제거"""
    config = load_user_config()
    if symbol in config["extra_watchlist"]:
        del config["extra_watchlist"][symbol]
        save_user_config(config)
        print(f"제거됨: {symbol}")
    else:
        print(f"사용자 목록에 {symbol}이 없습니다. (기본 종목은 config.py에서 직접 수정)")


def cmd_run():
    """브리핑 즉시 실행"""
    from briefing import generate_briefing
    report, filename = generate_briefing()
    print(f"\n리포트: {filename}")


def cmd_help():
    print("""
투자 브리핑 시스템 관리 도구

사용법:
  python manage.py status              현재 설정 상태 확인
  python manage.py run                 브리핑 즉시 실행
  python manage.py add <심볼> <이름>   관심 종목 추가
  python manage.py remove <심볼>       관심 종목 제거

예시:
  python manage.py add 005930.KS 삼성전자
  python manage.py add AAPL 애플
  python manage.py add 000660.KS SK하이닉스
  python manage.py remove AAPL

환경변수 설정:
  set ANTHROPIC_API_KEY=sk-ant-...     Claude AI 분석 활성화
  set ECOS_API_KEY=...                 한국은행 경제지표 활성화
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == "status":
        cmd_status()
    elif command == "run":
        cmd_run()
    elif command == "add" and len(sys.argv) >= 4:
        cmd_add(sys.argv[2], sys.argv[3])
    elif command == "remove" and len(sys.argv) >= 3:
        cmd_remove(sys.argv[2])
    elif command == "help":
        cmd_help()
    else:
        cmd_help()
