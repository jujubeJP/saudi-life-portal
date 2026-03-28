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

import os
import urllib.request
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

AST = timezone(timedelta(hours=3))
CONTENT_PATH = Path(__file__).parent.parent / "public" / "data" / "content.json"

EMBASSY_URL = "https://www.ksa.emb-japan.go.jp/itpr_ja/index.html"
EMBASSY_BASE = "https://www.ksa.emb-japan.go.jp"
MOFA_URL = "https://www.anzen.mofa.go.jp/info/pcinfectionspothazardinfo_050.html"
MOFA_BASE = "https://www.anzen.mofa.go.jp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# メディアソース（Google News RSSを使用 - bot保護なし、複数ソースを集約）
MEDIA_SOURCES = [
    {
        "name": "Google News (EN)",
        "name_ja": "英語ニュース",
        "rss_url": "https://news.google.com/rss/search?q=Saudi+Arabia&hl=en&gl=SA&ceid=SA:en",
        "filter_saudi": False,  # 検索クエリ自体がサウジ関連
    },
    {
        "name": "Google News (AR)",
        "name_ja": "アラビア語ニュース",
        "rss_url": "https://news.google.com/rss/search?q=%D8%A7%D9%84%D8%B3%D8%B9%D9%88%D8%AF%D9%8A%D8%A9&hl=ar&gl=SA&ceid=SA:ar",
        "filter_saudi": False,
    },
    {
        "name": "Google News (JP)",
        "name_ja": "日本語ニュース",
        "rss_url": "https://news.google.com/rss/search?q=%E3%82%B5%E3%82%A6%E3%82%B8%E3%82%A2%E3%83%A9%E3%83%93%E3%82%A2&hl=ja&gl=JP&ceid=JP:ja",
        "filter_saudi": False,
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
    """大使館サイト（在外公館トピックス）から情報を収集"""
    print("[INFO] Fetching embassy topics page...")
    html = fetch_url(EMBASSY_URL)
    if not html:
        return None, []

    text, links = parse_html(html)
    print(f"[DEBUG] Found {len(links)} total links on embassy page")

    # 「在外公館トピックス」セクションを特定
    topics_start = text.find("在外公館トピックス")
    if topics_start < 0:
        print("[WARN] Could not find 在外公館トピックス section")
        topics_start = 0
    topics_text = text[topics_start:]
    print(f"[DEBUG] Topics section starts at position {topics_start}")

    # お知らせリンクを抽出
    news_items = []
    seen_titles = set()

    # ナビゲーションリンクの除外パターン
    nav_keywords = [
        "一覧へ", "トップページ", "サイトマップ", "English", "大使館案内",
        "領事・治安・医療", "経済・技術協力", "パスポート", "戸籍国籍届",
        "海外子女教育", "日本へのビザ", "外務省", "サイトポリシー",
        "リンク集", "個人情報保護方針", "アクセシビリティ", "トップへ戻る",
        "ページの先頭", "前のページ", "次のページ",
    ]

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

        # ナビゲーションリンクを除外（部分一致）
        if any(kw in title_clean for kw in nav_keywords):
            continue

        # URLを正規化
        if not href.startswith("http"):
            if href.startswith("/"):
                href = EMBASSY_BASE + href
            else:
                href = EMBASSY_BASE + "/" + href

        # 在外公館トピックスのリンクのみ（外務省mofa.go.jpのリンクは除外）
        if "mofa.go.jp" in href:
            continue

        # 在外公館トピックスセクション内にこのタイトルが存在するか確認
        check_len = min(len(title_clean), 30)
        if title_clean[:check_len] not in topics_text:
            continue

        seen_titles.add(title_clean)

        # 日付を検索（タイトルの直前にある令和日付）
        # タイトル開始位置の手前だけを検索（タイトル内の日付を拾わないように）
        title_pos = topics_text.find(title_clean[:check_len])
        date_str = None
        if title_pos >= 0:
            search_range = topics_text[max(0, title_pos - 80):title_pos]
            date_str = parse_japanese_date(search_range)
            print(f"[DEBUG] Date for '{title_clean[:30]}': search='{search_range[-40:]}' → {date_str}")

        news_items.append({
            "title": title_clean,
            "url": href,
            "date": date_str or datetime.now(AST).strftime("%Y-%m-%d"),
            "source": "在サウジ日本大使館"
        })

    # 日付で降順ソート（新しい順）
    news_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    print(f"[DEBUG] Extracted {len(news_items)} embassy news items (sorted)")
    for item in news_items[:12]:
        print(f"[DEBUG]   - {item['date']}: {item['title'][:60]}")

    # 最新10件に制限
    news_items = news_items[:10]
    embassy_title = news_items[0]["title"] if news_items else "情報を取得できませんでした"
    embassy_body = f"直近{len(news_items)}件のお知らせを取得しました。" if news_items else "大使館サイトからの情報取得に失敗しました。"

    embassy_data = {
        "title": embassy_title,
        "body": embassy_body,
        "url": EMBASSY_URL
    }

    return embassy_data, news_items


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


def clean_xml_for_parsing(xml_text):
    """XMLパース前にHTMLエンティティや不正タグを修正"""
    # HTMLエンティティをXML互換に変換（&amp; &lt; &gt; &quot; &apos; 以外）
    html_entities = {
        "&nbsp;": " ", "&ndash;": "-", "&mdash;": "--", "&lsquo;": "'",
        "&rsquo;": "'", "&ldquo;": '"', "&rdquo;": '"', "&bull;": "*",
        "&hellip;": "...", "&copy;": "(c)", "&reg;": "(R)", "&trade;": "(TM)",
        "&eacute;": "e", "&egrave;": "e", "&ouml;": "o", "&uuml;": "u",
    }
    for entity, replacement in html_entities.items():
        xml_text = xml_text.replace(entity, replacement)

    # 未知のHTMLエンティティを除去 (&amp; &lt; &gt; &quot; &apos; は保持)
    xml_text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)\w+;', '', xml_text)

    # CDATA内のコンテンツはそのまま保持されるのでOK
    # 名前空間を除去
    xml_text = re.sub(r'xmlns\s*=\s*"[^"]*"', '', xml_text)
    xml_text = re.sub(r'xmlns:\w+\s*=\s*"[^"]*"', '', xml_text)

    return xml_text


def parse_rss_xml(xml_text):
    """RSS/Atom XMLをパースしてアイテムリストを返す（xml.etree使用、フォールバックあり）"""
    items = []

    # まずxml.etreeで試行
    xml_clean = clean_xml_for_parsing(xml_text)
    try:
        root = ET.fromstring(xml_clean)

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

        if items:
            return items

    except ET.ParseError as e:
        print(f"[DEBUG] XML parse failed, trying regex fallback: {e}", file=sys.stderr)

    # フォールバック: 正規表現でRSSアイテムを抽出
    items = parse_rss_regex(xml_text)
    return items


def parse_rss_regex(xml_text):
    """正規表現でRSS/Atomフィードからアイテムを抽出（XMLパース失敗時のフォールバック）"""
    items = []

    # <item>...</item> ブロックを抽出
    item_blocks = re.findall(r'<item\b[^>]*>(.*?)</item>', xml_text, re.DOTALL | re.IGNORECASE)

    # Atom <entry>...</entry> も試行
    if not item_blocks:
        item_blocks = re.findall(r'<entry\b[^>]*>(.*?)</entry>', xml_text, re.DOTALL | re.IGNORECASE)

    for block in item_blocks:
        item = {}

        # タイトル（CDATA対応）
        m = re.search(r'<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', block, re.DOTALL)
        if m:
            item["title"] = strip_html_tags(m.group(1)).strip()

        # リンク
        m = re.search(r'<link[^>]*>(?:<!\[CDATA\[)?(https?://[^<\]]+?)(?:\]\]>)?</link>', block, re.DOTALL)
        if not m:
            m = re.search(r'<link[^>]*href="([^"]+)"', block)
        if m:
            item["link"] = m.group(1).strip()

        # 説明
        m = re.search(r'<description[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', block, re.DOTALL)
        if not m:
            m = re.search(r'<summary[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</summary>', block, re.DOTALL)
        if m:
            item["description"] = strip_html_tags(m.group(1)).strip()

        # 日付
        m = re.search(r'<pubDate[^>]*>(.*?)</pubDate>', block, re.DOTALL)
        if not m:
            m = re.search(r'<published[^>]*>(.*?)</published>', block, re.DOTALL)
        if not m:
            m = re.search(r'<updated[^>]*>(.*?)</updated>', block, re.DOTALL)
        if m:
            item["pubdate"] = m.group(1).strip()

        if item.get("title"):
            items.append(item)

    print(f"[DEBUG] Regex fallback extracted {len(items)} items")
    return items


def parse_rss_date(date_str):
    """RSS日付文字列をYYYY-MM-DDTHH:MM形式に変換（時刻付き）"""
    if not date_str:
        return None
    # RFC 2822: "Sat, 28 Mar 2026 10:30:00 +0300"
    m = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\s+(\d{2}):(\d{2})", date_str)
    if m:
        months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                  "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        day = int(m.group(1))
        month = months.get(m.group(2), 1)
        year = int(m.group(3))
        hour = m.group(4)
        minute = m.group(5)
        return f"{year}-{month:02d}-{day:02d}T{hour}:{minute}"
    # RFC 2822 日付のみ（時刻なし）
    m2 = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})", date_str)
    if m2:
        months = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                  "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        day = int(m2.group(1))
        month = months.get(m2.group(2), 1)
        year = int(m2.group(3))
        return f"{year}-{month:02d}-{day:02d}"
    # ISO 8601: "2026-03-28T10:30:00+03:00"
    m3 = re.search(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", date_str)
    if m3:
        return f"{m3.group(1)}-{m3.group(2)}-{m3.group(3)}T{m3.group(4)}:{m3.group(5)}"
    # ISO 8601 日付のみ
    m4 = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m4:
        return f"{m4.group(1)}-{m4.group(2)}-{m4.group(3)}"
    return None


def strip_html_tags(text):
    """HTMLタグを除去してプレーンテキストを返す"""
    return re.sub(r"<[^>]+>", "", text).strip()


def translate_to_japanese(text):
    """テキストを日本語に翻訳（Claude API使用）"""
    if not ANTHROPIC_API_KEY or not text or not text.strip():
        return text
    try:
        # 既に日本語ならスキップ
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text):
            return text

        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": f"以下のニュース見出しを自然な日本語に翻訳してください。翻訳のみを出力し、説明は不要です。\n\n{text[:300]}"}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            translated = result.get("content", [{}])[0].get("text", "").strip()
            return translated if translated else text
    except Exception as e:
        print(f"[WARN] Translation failed: {e}", file=sys.stderr)
        return text


def collect_media():
    """英語/アラビア語/日本語メディアのRSSフィードからサウジ関連ニュースを言語別に収集"""
    # 言語キー: EN, AR, JP
    lang_keys = ["en", "ar", "jp"]
    results = {k: [] for k in lang_keys}

    for i, source in enumerate(MEDIA_SOURCES):
        lang = lang_keys[i] if i < len(lang_keys) else "en"
        print(f"[INFO] Fetching {source['name']} RSS...")
        xml = fetch_url(source["rss_url"])
        if not xml:
            print(f"[WARN] Failed to fetch {source['name']} RSS")
            continue

        rss_items = parse_rss_xml(xml)
        if not rss_items:
            print(f"[DEBUG] {source['name']} preview: {xml[:200]}", file=sys.stderr)
            print(f"[WARN] No items parsed from {source['name']} RSS")
            continue

        print(f"[DEBUG] {source['name']}: found {len(rss_items)} RSS items")

        count = 0
        for item in rss_items:
            if count >= 10:  # 各言語から最大10件
                break

            title = item.get("title", "")
            link = item.get("link", "")

            if not title or not link:
                continue

            # Google Newsのタイトルからソース名を抽出（"見出し - ソース名" 形式）
            source_name = source["name_ja"]
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                source_name = parts[1].strip()

            # 日付パース（時刻付き）
            date_str = parse_rss_date(item.get("pubdate", ""))
            if not date_str:
                date_str = datetime.now(AST).strftime("%Y-%m-%dT%H:%M")

            # タイトルを日本語に翻訳
            title_ja = translate_to_japanese(title)

            results[lang].append({
                "title": title_ja,
                "url": link,
                "date": date_str,
                "source": source_name,
            })
            count += 1

        print(f"[DEBUG] {source['name']}: collected {count} items")

    # 各言語を日付で降順ソート
    for lang in lang_keys:
        results[lang].sort(key=lambda x: x.get("date", ""), reverse=True)
        print(f"[INFO] {lang.upper()} media items: {len(results[lang])}")

    return results


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

    # メディアニュースを言語別に収集
    media_by_lang = collect_media()

    # 大使館ニュースは毎回新規収集分のみ使用（既存データをマージしない）
    embassy_all = embassy_news if embassy_news else existing.get("news", {}).get("items", [])

    # 各言語メディアニュースのマージ（既存と新規、重複排除、各10件）
    def merge_media(new_items, existing_items):
        merged = []
        seen = set()
        for item in new_items:
            if item.get("url") and item["url"] not in seen:
                seen.add(item["url"])
                merged.append(item)
        for item in existing_items:
            if item.get("url") and item["url"] not in seen:
                seen.add(item["url"])
                merged.append(item)
        merged.sort(key=lambda x: x.get("date", ""), reverse=True)
        return merged[:10]

    news_en = merge_media(media_by_lang.get("en", []), existing.get("news_en", {}).get("items", []))
    news_ar = merge_media(media_by_lang.get("ar", []), existing.get("news_ar", {}).get("items", []))
    news_jp = merge_media(media_by_lang.get("jp", []), existing.get("news_jp", {}).get("items", []))

    has_new_media = any(media_by_lang.get(k) for k in ["en", "ar", "jp"])

    # content.jsonを組み立て
    content = {
        "lastCollected": now_iso,
        "security": {
            "lastUpdated": now_iso,
            "mofa": mofa_data if mofa_data else existing.get("security", {}).get("mofa"),
            "embassy": embassy_data if embassy_data else existing.get("security", {}).get("embassy"),
        },
        "news": {
            "lastUpdated": now_iso if embassy_news else existing.get("news", {}).get("lastUpdated"),
            "items": embassy_all
        },
        "news_en": {
            "lastUpdated": now_iso if media_by_lang.get("en") else existing.get("news_en", {}).get("lastUpdated"),
            "items": news_en
        },
        "news_ar": {
            "lastUpdated": now_iso if media_by_lang.get("ar") else existing.get("news_ar", {}).get("lastUpdated"),
            "items": news_ar
        },
        "news_jp": {
            "lastUpdated": now_iso if media_by_lang.get("jp") else existing.get("news_jp", {}).get("lastUpdated"),
            "items": news_jp
        },
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
    print(f"     Media EN: {len(news_en)} items")
    print(f"     Media AR: {len(news_ar)} items")
    print(f"     Media JP: {len(news_jp)} items")
    print(f"     Embassy news: {len(embassy_all)} items")


if __name__ == "__main__":
    main()
