#!/usr/bin/env python3
"""
サウジナビ コンテンツ自動収集スクリプト
大使館・外務省のWebサイトから情報をスクレイピングし、content.jsonを更新する
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

AST = timezone(timedelta(hours=3))
CONTENT_PATH = Path(__file__).parent.parent / "public" / "data" / "content.json"

EMBASSY_URL = "https://www.ksa.emb-japan.go.jp/itprtop_ja/index.html"
EMBASSY_BASE = "https://www.ksa.emb-japan.go.jp"
MOFA_URL = "https://www.anzen.mofa.go.jp/info/pcinfectionspothazardinfo_050.html"
MOFA_BASE = "https://www.anzen.mofa.go.jp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SaudiNaviBot/1.0; +https://saudi-navi.netlify.app)"
}


def fetch_url(url):
    """URLからHTMLを取得"""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except (URLError, HTTPError) as e:
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

    # デバッグ: リンク数を表示
    print(f"[DEBUG] Found {len(links)} links on embassy page")

    # 大使館のお知らせリンクを抽出
    news_items = []
    seen_titles = set()

    for link in links:
        title = link["text"].strip()
        href = link["href"]

        # タイトルのクリーンアップ: [56KB] などのファイルサイズ表記を除去
        title_clean = re.sub(r"\s*\[\d+KB\]\s*", "", title).strip()

        # ニュース・お知らせらしいリンクをフィルタ
        if not title_clean or len(title_clean) < 5:
            continue
        if title_clean in seen_titles:
            continue

        # ナビゲーションリンクを除外
        if title_clean in ("一覧へ", "トップページ", "サイトマップ"):
            continue

        # 大使館の記事リンクパターン（HTML, PDFどちらも含む）
        is_embassy_link = (
            "/itpr_ja/" in href or
            "/itprtop_ja/" in href or
            href.endswith(".pdf") or
            href.endswith(".html")
        )

        if is_embassy_link:
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
        # タイトルの前後100文字から日付を探す
        title_pos = text.find(item["title"][:20])  # 部分一致で探す
        if title_pos >= 0:
            search_range = text[max(0, title_pos - 100):title_pos + len(item["title"]) + 50]
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
        print(f"[DEBUG]   - {item['date']}: {item['title'][:50]}")

    # 最新の最大10件
    embassy_title = news_items[0]["title"] if news_items else "情報を取得できませんでした"
    embassy_body = f"最新{len(news_items)}件のお知らせを取得しました。" if news_items else "大使館サイトからの情報取得に失敗しました。"

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

    # 既存のニュースで重複しないものを追加
    for item in existing_news:
        if item.get("url") and item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            all_news.append(item)

    # 最新10件に制限
    all_news = all_news[:10]

    # content.jsonを組み立て
    content = {
        "lastCollected": now_iso,
        "security": {
            "lastUpdated": now_iso,
            "mofa": mofa_data if mofa_data else existing.get("security", {}).get("mofa"),
            "embassy": embassy_data if embassy_data else existing.get("security", {}).get("embassy"),
            "gov": existing.get("security", {}).get("gov")
        },
        "system": existing.get("system", {
            "lastUpdated": None,
            "visa": None,
            "health": None,
            "tax": None,
            "labor": None
        }),
        "news": {
            "lastUpdated": now_iso if (embassy_news or mofa_data) else existing.get("news", {}).get("lastUpdated"),
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
    print(f"     News items: {len(all_news)}")


if __name__ == "__main__":
    main()
