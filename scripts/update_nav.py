#!/usr/bin/env python3
"""
全HTMLファイルのナビゲーションを新しい構造に一括更新するスクリプト。
- モバイルメニュー（nav-links）: 主要項目をグループ化
- デスクトップバー（nav-desktop）: 6項目 + その他▼
"""
import re
import os
import glob

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'public')

# ===== NEW NAV TEMPLATES =====

# Mobile nav (full menu)
MOBILE_NAV = """  <div class="nav-links" id="navLinks">
    <a href="index.html">🏠 ホーム</a>
    <a href="for-first-visit.html">✈️ 初めての方へ</a>
    <a href="travel-info.html">🛂 渡航情報</a>
    <a href="news.html">📰 治安・ニュース</a>
    <a href="life.html">🏠 生活ガイド</a>
    <a href="money.html">💰 お金・通信</a>
    <a href="business.html">💼 ビジネス</a>
    <a href="food.html">🍽️ サウジ料理</a>
    <a href="transport.html">🚗 国内交通</a>
    <a href="events.html">📅 イベント</a>
    <a href="entertainment.html">🎡 娯楽</a>
    <a href="misunderstandings.html">⚠️ 誤解しやすいこと</a>
    <a href="emergency.html">🚨 緊急連絡先</a>
    <a href="saudi-time.html">🕐 サウジ時間</a>
    <a href="city-guide.html">🏙️ 都市ガイド</a>
    <a href="vision2030.html">🏗️ VISION 2030</a>
    <a href="history-culture.html">🕌 歴史・文化</a>
    <a href="telecom.html">📱 通信・アプリ</a>
    <a href="medical.html">🏥 医療</a>
    <a href="links.html">🔗 リンク集</a>
    <a href="glossary.html">📖 用語集</a>
  </div>"""

# Desktop nav (compact with dropdown)
DESKTOP_NAV = """  <div class="nav-desktop" id="navDesktop">
    <a href="index.html">🏠 ホーム</a>
    <a href="for-first-visit.html">✈️ 初めての方へ</a>
    <a href="travel-info.html">🛂 渡航情報</a>
    <a href="news.html">📰 治安・ニュース</a>
    <a href="life.html">🏠 生活ガイド</a>
    <a href="money.html">💰 お金・通信</a>
    <div class="nav-more" id="navMore">
      <button class="nav-more-btn" id="navMoreBtn">その他 ▼</button>
      <div class="nav-more-dropdown" id="navMoreDropdown">
        <a href="business.html">💼 ビジネス</a>
        <a href="food.html">🍽️ サウジ料理</a>
        <a href="transport.html">🚗 国内交通</a>
        <a href="events.html">📅 イベント</a>
        <a href="entertainment.html">🎡 娯楽</a>
        <a href="misunderstandings.html">⚠️ 誤解しやすいこと</a>
        <a href="emergency.html">🚨 緊急連絡先</a>
        <a href="saudi-time.html">🕐 サウジ時間</a>
        <a href="city-guide.html">🏙️ 都市ガイド</a>
        <a href="vision2030.html">🏗️ VISION 2030</a>
        <a href="history-culture.html">🕌 歴史・文化</a>
        <a href="telecom.html">📱 通信・アプリ</a>
        <a href="medical.html">🏥 医療</a>
        <a href="links.html">🔗 リンク集</a>
        <a href="glossary.html">📖 用語集</a>
      </div>
    </div>
    <div class="search-wrap" style="margin-left:auto;">
      <button class="search-toggle" id="searchToggleDesktop" aria-label="検索">🔍</button>
    </div>
  </div>"""

# Pages that should NOT be modified
SKIP_FILES = {'404.html', 'about.html', 'disclaimer.html'}

def get_page_slug(filepath):
    return os.path.basename(filepath)

def add_active_class(nav_html, page_slug):
    """Add class="active" to the link matching the current page."""
    # Find the href that matches this page
    pattern = rf'(<a href="{re.escape(page_slug)}")(>)'
    replacement = r'\1 class="active"\2'
    return re.sub(pattern, replacement, nav_html)

def update_nav(filepath):
    page_slug = get_page_slug(filepath)
    if page_slug in SKIP_FILES:
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if file has nav
    if '<div class="nav-links"' not in content:
        return False

    original = content

    # Replace mobile nav (nav-links)
    mobile_nav = add_active_class(MOBILE_NAV, page_slug)
    content = re.sub(
        r'  <div class="nav-links" id="navLinks">.*?</div>',
        mobile_nav,
        content,
        count=1,
        flags=re.DOTALL
    )

    # Replace desktop nav (nav-desktop)
    desktop_nav = add_active_class(DESKTOP_NAV, page_slug)
    content = re.sub(
        r'  <div class="nav-desktop" id="navDesktop">.*?</div>\s*</div>\s*</div>',
        desktop_nav,
        content,
        count=1,
        flags=re.DOTALL
    )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    html_files = glob.glob(os.path.join(PUBLIC_DIR, '*.html'))
    updated = 0
    skipped = 0
    for filepath in sorted(html_files):
        slug = get_page_slug(filepath)
        if slug in SKIP_FILES:
            print(f"  SKIP: {slug}")
            skipped += 1
            continue
        if update_nav(filepath):
            print(f"  OK:   {slug}")
            updated += 1
        else:
            print(f"  NONE: {slug} (no nav found or no change)")
            skipped += 1
    print(f"\nDone: {updated} updated, {skipped} skipped")

if __name__ == '__main__':
    main()
