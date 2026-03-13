"""
뉴스/RSS 피드 수집 (GeekNews + 금융 뉴스)
"""
import feedparser
from datetime import datetime
from config import SOURCES


def fetch_rss(url, limit=20):
    """RSS 피드에서 최신 항목 수집"""
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")

        items.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "summary": entry.get("summary", "")[:300],
            "published": published,
            "source": feed.feed.get("title", "Unknown"),
        })
    return items


def fetch_geeknews(limit=20):
    """GeekNews RSS 수집"""
    return fetch_rss(SOURCES["geeknews_rss"], limit)


def fetch_finance_news(limit=15):
    """금융 뉴스 RSS 수집 (여러 소스 병합)"""
    all_news = []
    for key, url in SOURCES.items():
        if key == "geeknews_rss":
            continue
        try:
            items = fetch_rss(url, limit=limit)
            all_news.extend(items)
        except Exception as e:
            print(f"[WARN] {key} 수집 실패: {e}")
    # 시간순 정렬
    all_news.sort(key=lambda x: x["published"], reverse=True)
    return all_news[:limit]


def format_news_list(items, title="뉴스"):
    """뉴스 목록을 텍스트로 포맷"""
    lines = [f"\n## {title} (최신 {len(items)}건)\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. [{item['published']}] {item['title']}")
        if item["summary"]:
            # HTML 태그 간단 제거
            summary = item["summary"].replace("<p>", "").replace("</p>", "")
            summary = summary.replace("<br>", " ").replace("<br/>", " ")
            if len(summary) > 100:
                summary = summary[:100] + "..."
            lines.append(f"   > {summary}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("GeekNews 수집 중...")
    gn = fetch_geeknews(10)
    print(format_news_list(gn, "GeekNews"))

    print("\n금융 뉴스 수집 중...")
    fn = fetch_finance_news(10)
    print(format_news_list(fn, "금융 뉴스"))
