#!/usr/bin/env python3
"""
RAGインデックスビルダー — サウジナビ
KBファイル + search-index.js からチャットボット用のJSONインデックスを生成。

出力: public/data/rag-index.json
  各チャンク = { id, title, category, content, tags, source_url }

使い方:
  python scripts/build_rag_index.py
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
KB_DIR = BASE_DIR / "knowledge-base"
SEARCH_INDEX = BASE_DIR / "public" / "assets" / "search-index.js"
OUTPUT = BASE_DIR / "public" / "data" / "rag-index.json"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                import yaml
                meta = yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
            body = parts[2].strip()
    return meta, body


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """テキストを段落ベースでチャンク分割"""
    paragraphs = re.split(r'\n\n+', text.strip())
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text[:max_chars]]


def load_kb_chunks() -> list[dict]:
    """KB .md / .json をチャンクに分割して返す"""
    chunks = []
    for md_path in sorted(KB_DIR.rglob("*.md")):
        if md_path.name.startswith("_"):
            continue
        text = md_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if not meta or not body.strip():
            continue

        category = md_path.parent.name
        base_id = meta.get("id", md_path.stem)
        title = meta.get("title", meta.get("topic", md_path.stem))
        tags = meta.get("tags", [])
        source_url = meta.get("source_url", "")

        text_chunks = chunk_text(body)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "id": f"{base_id}_chunk{i}",
                "title": title,
                "category": category,
                "content": chunk,
                "tags": tags if isinstance(tags, list) else [tags],
                "source_url": source_url,
            })

    for json_path in sorted(KB_DIR.rglob("*.json")):
        if json_path.name.startswith("_"):
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            content = data.get("content", data)
            if isinstance(content, dict):
                content_str = json.dumps(content, ensure_ascii=False)
            elif isinstance(content, list):
                content_str = "\n".join(
                    json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else str(item)
                    for item in content
                )
            else:
                content_str = str(content)

            category = json_path.parent.name
            chunks.append({
                "id": json_path.stem,
                "title": data.get("title", json_path.stem),
                "category": category,
                "content": content_str[:1200],
                "tags": data.get("tags", []),
                "source_url": data.get("source_url", ""),
            })
        except Exception:
            pass

    return chunks


def load_search_index_chunks() -> list[dict]:
    """search-index.js からサイトナビ情報をチャンクとして追加"""
    if not SEARCH_INDEX.exists():
        return []

    text = SEARCH_INDEX.read_text(encoding="utf-8")
    # JSのオブジェクト配列をパースする簡易方法
    chunks = []
    for m in re.finditer(
        r"\{page:\s*'([^']+)',\s*pageTitle:\s*'([^']+)',\s*title:\s*'([^']+)',\s*desc:\s*'([^']+)'\}",
        text
    ):
        page, page_title, title, desc = m.groups()
        chunks.append({
            "id": f"nav_{page}_{title}",
            "title": title,
            "category": "navigation",
            "content": f"{page_title} - {title}: {desc}",
            "tags": [],
            "source_url": page,
        })
    return chunks


def extract_text_from_html(html: str) -> str:
    """HTMLからメインコンテンツのテキストを抽出（ヘッダー/フッター/ナビ除去、段落構造を保持）"""
    # <main>タグがあればその中身だけを使う（ヘッダー/フッター/ナビを一括除去）
    main_match = re.search(r'<main[^>]*>(.*?)</main>', html, flags=re.DOTALL | re.IGNORECASE)
    if main_match:
        html = main_match.group(1)
    else:
        # <main>がない場合はhead/header/footer/nav等を個別に除去
        html = re.sub(r'<head[^>]*>.*?</head>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # script, style, nav, noscript タグの中身を除去
    html = re.sub(r'<(script|style|nav|noscript)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # ブロック要素の前後に改行を挿入（段落構造を保持）
    block_tags = r'</?(h[1-6]|p|div|section|article|li|tr|br|hr)[^>]*>'
    html = re.sub(block_tags, '\n', html, flags=re.IGNORECASE)
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', ' ', html)
    # HTMLエンティティをデコード
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ').replace('&#x27;', "'").replace('&quot;', '"')
    # 各行の前後空白を整理
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    text = '\n\n'.join(lines)
    return text


# ページ名→カテゴリのマッピング
PAGE_CATEGORY_MAP = {
    "food.html": "food",
    "transport.html": "transport",
    "money.html": "finance",
    "telecom.html": "telecom",
    "medical.html": "medical",
    "business.html": "business",
    "history-culture.html": "culture",
    "entertainment.html": "culture",
    "for-first-visit.html": "travel",
    "for-family.html": "living",
    "city-guide.html": "living",
    "saudi-time.html": "living",
    "events.html": "culture",
    "misunderstandings.html": "culture",
    "glossary.html": "reference",
    "links.html": "reference",
}

# RAGに含めないページ
SKIP_PAGES = {"index.html", "404.html", "news.html"}


def load_html_chunks() -> list[dict]:
    """public/ の各HTMLページからテキストを抽出しチャンクとして追加"""
    html_dir = BASE_DIR / "public"
    chunks = []
    for html_path in sorted(html_dir.glob("*.html")):
        if html_path.name in SKIP_PAGES:
            continue
        html = html_path.read_text(encoding="utf-8")

        # タイトル抽出
        title_match = re.search(r'<title>([^<]+)</title>', html)
        title = title_match.group(1).split('|')[0].strip() if title_match else html_path.stem

        text = extract_text_from_html(html)
        if len(text) < 50:
            continue

        category = PAGE_CATEGORY_MAP.get(html_path.name, "general")

        # タグを自動生成（ページ名とタイトルから）
        tags = [html_path.stem, title]

        text_chunks = chunk_text(text, max_chars=600)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "id": f"page_{html_path.stem}_chunk{i}",
                "title": title,
                "category": category,
                "content": chunk,
                "tags": tags,
                "source_url": html_path.name,
            })
    return chunks


def main():
    kb_chunks = load_kb_chunks()
    nav_chunks = load_search_index_chunks()
    html_chunks = load_html_chunks()
    all_chunks = kb_chunks + html_chunks + nav_chunks

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"RAGインデックス生成完了: {len(all_chunks)} チャンク")
    print(f"  KB チャンク: {len(kb_chunks)}")
    print(f"  HTML チャンク: {len(html_chunks)}")
    print(f"  ナビ チャンク: {len(nav_chunks)}")
    print(f"  出力: {OUTPUT}")


if __name__ == "__main__":
    main()
