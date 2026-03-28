#!/usr/bin/env python3
"""
サウジナビ コンテンツ自動収集スクリプト
大使館・外務省・英語/アラビア語メディアから情報を収集し、content.jsonを更新する
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

AST = timezone(timedelta(hours=3))
CONTENT_PATH = Path(__file__).parent.parent / "public" / "data" / "content.json"

EMBASSY_URL = "https://www.ksa.emb-japan.go.jp/itprtop_ja/index.html"
EMBASSY_BASE = "https://www.ksa.emb-japan.go.jp"
MOFA_URL = "https://www.anzen.mofa.go.jp/info/pcinfectionspothazardinfo_050.html"
MOFA_BASE = "https://www.anzen.mofa.go.jp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# 英語・アラビア語メディアソース（RSS）
MEDIA_SOURCES = [
    {
        "name": "Arab News",
        "name_ja": "アラブニュース",
        "rss_url": "https://www.arabnews.com/rss",
        "base_url": "https://www.arabnews.com",
    },
    {
        "name": "Saudi Gazette",
        "name_ja": "サウジガゼット",
        "rss_url": "https://saudigazette.com.sa/rss",
        "base_url": "https://saudigazette.com.sa",
    },
    {
        "name": "Al Arabiya",
        "name_ja": "アルアラビーヤ",
        "rss_url": "https://english.alarabiya.net/tools/mrss",
        "base_url": "https://english.alarabiya.net",
    },
]


def fetch_url(url):
    """URLからHTMLを取得（curlを使用、Akamai対策ヘッダー付き）"""
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-L", "--compressed",
                "--max-time", "30",
                "--http2",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "-H", "Accept-Language: ja,en-US;q=0.9,en;q=0.8",
                "-H", "Accept-Encoding: gzip, deflate, br",
                "-H", "Connection: keep-alive",
                "-H", "Upgrade-Insecure-Requests: 1",
                "-H", "Sec-Fetch-Dest: document",
                "-H", "Sec-Fetch-Mode: navigate",
                "-H", "Sec-Fetch-Site: none",
                "-H", "Sec-Fetch-User: ?1",
                "-H", "Cache-Control: max-age=0",
                url,
            ],
            capture_output=True,
            timeout=45,
        )
        if result.returncode != 0:
            print(f"[WARN] curl failed for {url}: exit code {result.returncode}", file=sys.stderr)
            return None
        html = result.stdout.decode("utf-8", errors="replace")
        if not html.strip():
            print(f"[WARN] Empty response from {url}", file=sys.stderr)
            return None
        # Access Denied チェック
        if "Access Denied" in html and len(html) < 1000:
            print(f"[WARN] Access Denied from {url} ({len(html)} bytes)", file=sys.stderr)
            print(f"[DEBUG] Response: {html[:300]}", file=sys.stderr)
            return None
        print(f"[DEBUG] Fetched {url}: {len(html)} bytes")
        return html
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


class SimpleHTMLTextExtractor(HTMLParser):
    """HTMLからテキストとリンクを抽出する簡易パーサー"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.links = []
        self._current_link = None
        self._current_link_text = []
        self._skip_tags = {"script", "style", "noscript"}
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip_depth += 1
        if tag == "a":
            href = dict(attrs).get("href", "")
            self._current_link = href
            self._current_link_text = []

    def handle_endtag(self, tag):
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "a" and self._current_link is not None:
            text = "".join(self._current_link_text).strip()
            if text and self._current_link:
                self.links.append({"text": text, "href": self._current_link})
            self._current_link = None
            self._current_link_text = []

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        self.text_parts.append(data)
        if self._current_link is not None:
            self._current_link_text.append(data)

    def get_text(self):
        return "".join(self.text_parts)


def parse_html(html):
    """HTMLをパースしてテキストとリンクを返す"""
    parser = SimpleHTMLTextExtractor()
    parser.feed(html)
    return parser.get_text(), parser.links


def reiwa_to_western(year_str):
    """令和年を西暦に変換"""
    try:
        reiwa_year = int(year_str)
        return 2018 + reiwa_year  # 令和1年 = 2019年
    except ValueError:
        return None


def parse_japanese_date(text_around):
    """令和・西暦の日付を YYYY-MM-DD に変換"""
    # 令和X年M月D日
    m = re.search(r"令和(\d{1,2})年(\d{1,2})月(\d{1,2})日", text_around)
    if m:
        western = reiwa_to_western(m.group(1))
        if western:
            return f"{western}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 西暦 2026年3月16日 or 2026/3/16
    m = re.search(r"(\d{4})[/年.](\d{1,2})[/月.](\d{1,2})", text_around)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    return None


def collect_embassy():
    """大使館サイトから情報を収集"""
    print("[INFO] Fetching embassy page...")
    html = fetch_url(EMBASSY_URL)
    if not html:
        return None, []

    text, links = parse_html(html)
    print(f"[DEBUG] Found {len(links)} total links on embassy page")

    # 「新着情報」「領事情報」セクション以降のリンクだけを抽出
    # テキスト内のセクション開始位置を特定
    news_section_start = text.find("新着情報")
    ryoji_section_start = text.find("領事情報")

    if news_section_start < 0 and ryoji_section_start < 0:
        print("[WARN] Could not find 新着情報 or 領事情報 section in embassy page")
        # フォールバック: タイトルパターンでフィルタ
        section_start = 0
    else:
        section_start = min(
            pos for pos in [news_section_start, ryoji_section_start] if pos >= 0
        )

    print(f"[DEBUG] News section starts at position {section_start}")

    # お知らせリンクを抽出
    news_items = []
    seen_titles = set()

    # ナビゲーションリンクの除外パターン
    nav_keywords = {
        "一覧へ", "トップページ", "サイトマップ", "English", "大使館案内",
        "領事・治安・医療", "経済・技術協力", "パスポート", "戸籍国籍届",
        "海外子女教育", "日本へのビザ", "外務省", "サイトポリシー",
        "リンク集", "個人情報保護方針", "アクセシビリティ",
    }

    for link in links:
        title = link["text"].strip()
        href = link["href"]

        # 改行・空白をクリーンアップ
        title = re.sub(r"\s+", " ", title).strip()

        # [56KB] などのファイルサイズ表記を除去
        title_clean = re.sub(r"\s*\[\d+KB\]\s*", "", title).strip()

        # 短すぎるタイトルを除外
        if not title_clean or len(title_clean) < 8:
            continue
        if title_clean in seen_titles:
            continue

        # ナビゲーションリンクを除外
        if title_clean in nav_keywords:
            continue

        # テキスト内でこのリンクタイトルがニュースセクション以降にあるか確認
        title_pos = text.find(title_clean[:15])
        if title_pos < 0 or (section_start > 0 and title_pos < section_start):
            continue

        # URLを正規化
        if not href.startswith("http"):
            if href.startswith("/"):
                href = EMBASSY_BASE + href
            else:
                href = EMBASSY_BASE + "/" + href

        seen_titles.add(title_clean)
        news_items.append({
            "title": title_clean,
            "url": href,
            "source": "在サウジ日本大使館"
        })

    # 各ニュースに日付を付与
    for item in news_items:
        title_pos = text.find(item["title"][:15])
        if title_pos >= 0:
            search_range = text[max(0, title_pos - 150):title_pos + 10]
            date_str = parse_japanese_date(search_range)
            if date_str:
                item["date"] = date_str
            else:
                item["date"] = datetime.now(AST).strftime("%Y-%m-%d")
        else:
            item["date"] = datetime.now(AST).strftime("%Y-%m-%d")

        item["summary"] = item["title"]

    print(f"[DEBUG] Extracted {len(news_items)} embassy news items")
    for item in news_items[:5]:
        print(f"[DEBUG]   - {item['date']}: {item['title'][:60]}")

    # 最新の最大10件
    embassy_title = news_items[0]["title"] if news_items else "情報を取得できませんでした"
    embassy_body = f"最新{min(len(news_items), 10)}件のお知らせを取得しました。" if news_items else "大使館サイトからの情報取得に失敗しました。"

    embassy_data = {
        "title": embassy_title,
        "body": embassy_body,
        "url": EMBASSY_URL
    }

    return embassy_data, news_items[:10]


def collect_mofa():
    """外務省海外安全HPから情報を収集"""
    print("[INFO] Fetching MOFA page...")
    html = fetch_url(MOFA_URL)
    if not html:
        return None

    text, links = parse_html(html)

    # 危険レベルを抽出
    level_match = re.search(r"レベル\s*(\d)\s*[：:]\s*(.+?)(?:\n|。|$)", text)
    if level_match:
        level_num = level_match.group(1)
        level_desc = level_match.group(2).strip()
        title = f"危険情報：レベル{level_num} {level_desc}"
    else:
        # レベル表記がない場合のフォールバック
        if "十分注意" in text:
            title = "危険情報：レベル1 十分注意してください"
        elif "不要不急" in text:
            title = "危険情報：レベル2 不要不急の渡航は止めてください"
        elif "渡航中止" in text:
            title = "危険情報：レベル3 渡航は止めてください"
        elif "退避" in text:
            title = "危険情報：レベル4 退避してください"
        else:
            title = "サウジアラビアの安全情報"

    # 概要テキストを抽出（最初の有意な段落）
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 20]
    body_candidates = [p for p in paragraphs if "サウジ" in p or "危険" in p or "注意" in p or "テロ" in p or "渡航" in p]
    body = body_candidates[0] if body_candidates else "詳細は外務省海外安全HPをご確認ください。"

    # 300文字以内に切り詰め
    if len(body) > 300:
        body = body[:297] + "..."

    return {
        "title": title,
        "body": body,
        "url": MOFA_URL
    }


def parse_rss_xml(xml_text):
    """RSS/Atom XMLをパースしてアイテムリストを返す（xml.etree使用）"""
    items = []
    try:
        # 名前空間を無視するためにプレフィックスを除去
        xml_clean = re.sub(r'xmlns\s*=\s*"[^"]*"', '', xml_text)
        xml_clean = re.sub(r'xmlns:\w+\s*=\s*"[^"]*"', '', xml_clean)
        root = ET.fromstring(xml_clean)
    except ET.ParseError as e:
        print(f"[WARN] XML parse error: {e}", file=sys.stderr)
        return items

    # RSS 2.0: <channel><item>
    for item_el in root.iter("item"):
        item = {}
        title_el = item_el.find("title")
        link_el = item_el.find("link")
        desc_el = item_el.find("description")
        date_el = item_el.find("pubDate")
        if title_el is not None and title_el.text:
            item["title"] = title_el.text.strip()
        if link_el is not None and link_el.text:
            item["link"] = link_el.text.strip()
        if desc_el is not None and desc_el.text:
            item["description"] = desc_el.text.strip()
        if date_el is not None and date_el.text:
            item["pubdate"] = date_el.text.strip()
        if item.get("title"):
            items.append(item)

    # Atom: <entry>
    if not items:
        for entry_el in root.iter("entry"):
            item = {}
            title_el = entry_el.find("title")
            link_el = entry_el.find("link")
            desc_el = entry_el.find("summary") or entry_el.find("content")
            date_el = entry_el.find("published") or entry_el.find("updated")
            if title_el is not None and title_el.text:
                item["title"] = title_el.text.strip()
            if link_el is not None:
                item["link"] = link_el.get("href", "") or (link_el.text or "").strip()
            if desc_el is not None and desc_el.text:
                item["description"] = desc_el.text.strip()
            if date_el is not None and date_el.text:
                item["pubdate"] = date_el.text.strip()
            if item.get("title"):
                items.append(item)

    return items


def parse_rss_date(date_str):
    """RSS日付文字列をYYYY-MM-DD形式に変換"""
    if not date_str:
        return None
    # RFC 2822: "Sat, 28 Mar 2026 10:30:00 +0300"
    m = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})", date_str)
    if m:
        months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                  "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        day = int(m.group(1))
        month = months.get(m.group(2), 1)
        year = int(m.group(3))
        return f"{year}-{month:02d}-{day:02d}"
    # ISO 8601: "2026-03-28T10:30:00+03:00"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def strip_html_tags(text):
    """HTMLタグを除去してプレーンテキストを返す"""
    return re.sub(r"<[^>]+>", "", text).strip()


def collect_media():
    """英語メディアのRSSフィードからサウジ関連ニュースを収集"""
    media_items = []

    for source in MEDIA_SOURCES:
        print(f"[INFO] Fetching {source['name']} RSS...")
        xml = fetch_url(source["rss_url"])
        if not xml:
            print(f"[WARN] Failed to fetch {source['name']} RSS")
            continue

        rss_items = parse_rss_xml(xml)
        if not rss_items:
            print(f"[WARN] No items parsed from {source['name']} RSS")
            continue

        print(f"[DEBUG] {source['name']}: found {len(rss_items)} RSS items")

        # サウジ関連記事をフィルタ（Al Arabiyaは中東全体なのでフィルタ必要）
        saudi_keywords = {
            "saudi", "riyadh", "jeddah", "mecca", "medina", "neom",
            "vision 2030", "aramco", "mbs", "kingdom",
            "サウジ", "リヤド", "ジェッダ",
        }

        count = 0
        for item in rss_items:
            if count >= 5:  # 各ソースから最大5件
                break

            title = item.get("title", "")
            link = item.get("link", "")
            description = strip_html_tags(item.get("description", ""))

            if not title or not link:
                continue

            # Al Arabiyaはサウジ関連のみフィルタ
            if source["name"] == "Al Arabiya":
                combined = (title + " " + description).lower()
                if not any(kw in combined for kw in saudi_keywords):
                    continue

            # 日付パース
            date_str = parse_rss_date(item.get("pubdate", ""))
            if not date_str:
                date_str = datetime.now(AST).strftime("%Y-%m-%d")

            # 要約を作成（descriptionの先頭100文字）
            summary = description[:100] + "..." if len(description) > 100 else description
            if not summary:
                summary = title

            media_items.append({
                "title": title,
                "url": link,
                "date": date_str,
                "source": source["name_ja"],
                "summary": summary,
            })
            count += 1

        print(f"[DEBUG] {source['name']}: collected {count} items")

    # 日付で降順ソート
    media_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    print(f"[INFO] Total media items collected: {len(media_items)}")
    return media_items


def main():
    now = datetime.now(AST)
    now_iso = now.isoformat()

    # 既存のcontent.jsonを読み込む
    existing = {}
    if CONTENT_PATH.exists():
        try:
            existing = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("[WARN] Existing content.json is invalid, starting fresh", file=sys.stderr)

    # 大使館情報を収集
    embassy_data, embassy_news = collect_embassy()

    # 外務省情報を収集
    mofa_data = collect_mofa()

    # メディアニュースを収集
    media_news = collect_media()

    # 既存のニュースアイテムを保持
    existing_news = existing.get("news", {}).get("items", [])

    # 新しいニュースアイテムをマージ（重複排除）
    all_news = []
    seen_urls = set()

    # 大使館のニュースを追加
    for item in embassy_news:
        if item.get("url") and item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            all_news.append(item)

    # メディアニュースを追加
    for item in media_news:
        if item.get("url") and item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            all_news.append(item)

    # 既存のニュースで重複しないものを追加
    for item in existing_news:
        if item.get("url") and item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            all_news.append(item)

    # 最新20件に制限（大使館10+メディア10程度）
    all_news = all_news[:20]

    # content.jsonを組み立て
    content = {
        "lastCollected": now_iso,
        "security": {
            "lastUpdated": now_iso,
            "mofa": mofa_data if mofa_data else existing.get("security", {}).get("mofa"),
            "embassy": embassy_data if embassy_data else existing.get("security", {}).get("embassy"),
        },
        "news": {
            "lastUpdated": now_iso if (embassy_news or media_news) else existing.get("news", {}).get("lastUpdated"),
            "items": all_news
        }
    }

    # 書き出し
    CONTENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTENT_PATH.write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(f"[OK] content.json updated at {now_iso}")
    print(f"     Embassy: {'OK' if embassy_data else 'FAILED'}")
    print(f"     MOFA: {'OK' if mofa_data else 'FAILED'}")
    print(f"     Media: {len(media_news)} items")
    print(f"     Total news: {len(all_news)}")


if __name__ == "__main__":
    main()
