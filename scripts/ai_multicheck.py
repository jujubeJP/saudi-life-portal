#!/usr/bin/env python3
"""
AI マルチチェックパイプライン — サウジナビ
収集済みコンテンツ（KB / content.json）を複数の観点で交差検証する。

3段階チェック:
  1. ファクトチェック — 情報の正確性を検証
  2. 鮮度チェック   — 古い情報・期限切れを検出
  3. 一貫性チェック — KB間の矛盾を検出

使い方:
  python scripts/ai_multicheck.py                    # 全チェック実行
  python scripts/ai_multicheck.py --check fact       # ファクトチェックのみ
  python scripts/ai_multicheck.py --check freshness  # 鮮度チェックのみ
  python scripts/ai_multicheck.py --check consistency # 一貫性チェックのみ
  python scripts/ai_multicheck.py --dry-run          # API呼び出しなし（構造確認のみ）
"""

import os
import sys
import json
import re
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
KB_DIR = BASE_DIR / "knowledge-base"
CONTENT_JSON = BASE_DIR / "public" / "data" / "content.json"
REPORT_DIR = KB_DIR / "_reports"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("multicheck")

# ─── KB Loader ───────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """YAML frontmatter と本文を分離して返す"""
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            import yaml
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
            body = parts[2].strip()
    return meta, body


def load_all_kb() -> list[dict]:
    """全KBファイルを読み込んで [{meta, body, path}] を返す"""
    entries = []
    for md_path in sorted(KB_DIR.rglob("*.md")):
        if md_path.name.startswith("_"):
            continue
        text = md_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if meta:
            entries.append({
                "meta": meta,
                "body": body[:2000],  # API に渡すので先頭2000文字に制限
                "path": str(md_path.relative_to(BASE_DIR)),
            })
    for json_path in sorted(KB_DIR.rglob("*.json")):
        if json_path.name.startswith("_"):
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            entries.append({
                "meta": {k: v for k, v in data.items() if k != "content"},
                "body": json.dumps(data.get("content", data), ensure_ascii=False)[:2000],
                "path": str(json_path.relative_to(BASE_DIR)),
            })
        except Exception:
            pass
    return entries


def load_content_json() -> dict:
    """public/data/content.json を読み込む"""
    if CONTENT_JSON.exists():
        return json.loads(CONTENT_JSON.read_text(encoding="utf-8"))
    return {}


# ─── Claude API Helper ──────────────────────────────────────────

def call_claude(system_prompt: str, user_message: str) -> str:
    """Claude Haiku API を呼び出してテキストを返す"""
    if not ANTHROPIC_API_KEY:
        log.warning("ANTHROPIC_API_KEY が未設定。スキップします。")
        return ""

    import urllib.request
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("x-api-key", ANTHROPIC_API_KEY)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]
    except Exception as e:
        log.error(f"Claude API error: {e}")
        return ""


# ─── Check 1: ファクトチェック ────────────────────────────────────

FACT_CHECK_SYSTEM = """あなたはサウジアラビアの情報に詳しいファクトチェッカーです。
与えられたKBエントリの内容を検証し、以下をJSON形式で返してください:
{
  "issues": [
    {"field": "フィールド名", "problem": "問題の内容", "severity": "high|medium|low"}
  ],
  "overall_confidence": "high|medium|low",
  "notes": "総合コメント"
}
問題がなければ issues を空配列にしてください。JSONのみ出力してください。"""


def check_facts(entries: list[dict], dry_run: bool = False) -> list[dict]:
    """各KBエントリのファクトチェック"""
    results = []
    for entry in entries:
        meta = entry["meta"]
        log.info(f"[ファクトチェック] {meta.get('id', entry['path'])}")

        if dry_run:
            results.append({
                "file": entry["path"],
                "id": meta.get("id", ""),
                "check": "fact",
                "result": {"issues": [], "overall_confidence": "skipped", "notes": "dry-run"},
            })
            continue

        user_msg = f"""以下のKBエントリを検証してください。

タイトル: {meta.get('title', '')}
カテゴリ: {meta.get('topic', '')}
情報源: {meta.get('source_url', '')}
ソース種別: {meta.get('source_type', '')}
確認日: {meta.get('checked_at', '')}
信頼度: {meta.get('confidence', '')}

本文（抜粋）:
{entry['body'][:1500]}"""

        response = call_claude(FACT_CHECK_SYSTEM, user_msg)
        try:
            parsed = json.loads(response)
        except Exception:
            parsed = {"issues": [], "overall_confidence": "unknown", "notes": response[:200]}

        results.append({
            "file": entry["path"],
            "id": meta.get("id", ""),
            "check": "fact",
            "result": parsed,
        })
    return results


# ─── Check 2: 鮮度チェック ───────────────────────────────────────

def check_freshness(entries: list[dict]) -> list[dict]:
    """review_by / checked_at に基づく鮮度チェック（APIなしで実行）"""
    today = datetime.now().strftime("%Y-%m-%d")
    results = []

    for entry in entries:
        meta = entry["meta"]
        file_id = meta.get("id", entry["path"])
        issues = []

        # review_by チェック
        review_by = str(meta.get("review_by", ""))
        if review_by and review_by != "TBD":
            try:
                rb_date = datetime.strptime(review_by, "%Y-%m-%d")
                days_left = (rb_date - datetime.now()).days
                if days_left < 0:
                    issues.append({
                        "field": "review_by",
                        "problem": f"レビュー期限を {abs(days_left)} 日超過",
                        "severity": "high",
                    })
                elif days_left <= 14:
                    issues.append({
                        "field": "review_by",
                        "problem": f"レビュー期限まで残り {days_left} 日",
                        "severity": "medium",
                    })
            except ValueError:
                issues.append({
                    "field": "review_by",
                    "problem": f"日付フォーマット不正: {review_by}",
                    "severity": "low",
                })

        # checked_at の古さ
        checked_at = str(meta.get("checked_at", ""))
        if checked_at:
            try:
                ca_date = datetime.strptime(checked_at, "%Y-%m-%d")
                days_old = (datetime.now() - ca_date).days
                if days_old > 180:
                    issues.append({
                        "field": "checked_at",
                        "problem": f"最終確認から {days_old} 日経過（6ヶ月超）",
                        "severity": "high",
                    })
                elif days_old > 90:
                    issues.append({
                        "field": "checked_at",
                        "problem": f"最終確認から {days_old} 日経過（3ヶ月超）",
                        "severity": "medium",
                    })
            except ValueError:
                pass

        # valid_until チェック
        valid_until = str(meta.get("valid_until", ""))
        if valid_until and valid_until not in ("TBD", "None", ""):
            try:
                vu_date = datetime.strptime(valid_until, "%Y-%m-%d")
                if vu_date < datetime.now():
                    issues.append({
                        "field": "valid_until",
                        "problem": f"有効期限切れ: {valid_until}",
                        "severity": "high",
                    })
            except ValueError:
                pass

        # confidence が low のまま
        if meta.get("confidence") == "low":
            issues.append({
                "field": "confidence",
                "problem": "信頼度が low のまま — 要レビュー",
                "severity": "medium",
            })

        results.append({
            "file": entry["path"],
            "id": file_id,
            "check": "freshness",
            "result": {
                "issues": issues,
                "days_since_check": checked_at,
                "review_by": review_by,
            },
        })

    return results


# ─── Check 2.5: 正本ルール重複検出（ローカル、APIなし）──────────

SOURCE_TYPE_PRIORITY = {
    "公的一次情報": 1,
    "公的二次情報": 2,
    "準公的情報": 3,
    "メディア報道": 4,
    "コミュニティ情報": 5,
    "AI生成": 6,
}


def check_canonical(entries: list[dict]) -> list[dict]:
    """正本ルールに基づくローカル重複検出（API不要）"""
    results = []

    # 1. source_url 重複検出
    url_map: dict[str, list[dict]] = {}
    for entry in entries:
        url = str(entry["meta"].get("source_url", "")).strip()
        if url and url != "None":
            url_map.setdefault(url, []).append(entry)

    for url, dupes in url_map.items():
        if len(dupes) < 2:
            continue
        # 正本を判定: source_type 優先度 → checked_at → confidence
        sorted_dupes = sorted(dupes, key=lambda e: (
            SOURCE_TYPE_PRIORITY.get(str(e["meta"].get("source_type", "")), 99),
            -len(str(e["meta"].get("checked_at", ""))),  # 新しい日付の方が長い文字列
            0 if e["meta"].get("confidence") == "high" else 1,
        ))
        canonical = sorted_dupes[0]
        for non_canon in sorted_dupes[1:]:
            results.append({
                "check": "canonical",
                "type": "duplicate_source_url",
                "canonical_file": canonical["path"],
                "duplicate_file": non_canon["path"],
                "source_url": url,
                "recommendation": f"正本: {canonical['path']} → 非正本に derived_from を設定",
                "severity": "medium",
            })

    # 2. tags 重複検出（80%以上重複）
    for i, entry_a in enumerate(entries):
        tags_a = set(entry_a["meta"].get("tags", []) or [])
        if len(tags_a) < 2:
            continue
        for entry_b in entries[i + 1:]:
            tags_b = set(entry_b["meta"].get("tags", []) or [])
            if len(tags_b) < 2:
                continue
            overlap = tags_a & tags_b
            union = tags_a | tags_b
            if union and len(overlap) / len(union) >= 0.8:
                # タイトルも類似チェック
                title_a = str(entry_a["meta"].get("title", ""))
                title_b = str(entry_b["meta"].get("title", ""))
                if title_a == title_b or (title_a and title_a in title_b) or (title_b and title_b in title_a):
                    results.append({
                        "check": "canonical",
                        "type": "high_tag_overlap",
                        "files": [entry_a["path"], entry_b["path"]],
                        "overlap_tags": sorted(overlap),
                        "recommendation": "タイトル・タグが類似。統合または derived_from を検討",
                        "severity": "low",
                    })

    # 3. canonical フラグ未設定の検出
    for entry in entries:
        meta = entry["meta"]
        if meta.get("derived_from") and not meta.get("canonical") is False:
            results.append({
                "check": "canonical",
                "type": "missing_canonical_flag",
                "file": entry["path"],
                "recommendation": "derived_from が設定されているが canonical: false が未設定",
                "severity": "low",
            })

    return results


# ─── Check 3: 一貫性チェック ─────────────────────────────────────

CONSISTENCY_SYSTEM = """あなたはサウジアラビア情報ナレッジベースの品質管理者です。
複数のKBエントリ間で矛盾や重複がないか検証してください。
以下をJSON形式で返してください:
{
  "conflicts": [
    {
      "files": ["ファイル1", "ファイル2"],
      "field": "矛盾のあるフィールド/トピック",
      "description": "矛盾の内容",
      "severity": "high|medium|low"
    }
  ],
  "duplicates": [
    {
      "files": ["ファイル1", "ファイル2"],
      "overlap": "重複している内容の概要"
    }
  ],
  "notes": "総合コメント"
}
JSONのみ出力してください。"""


def check_consistency(entries: list[dict], dry_run: bool = False) -> list[dict]:
    """KB全体の一貫性チェック"""
    if dry_run:
        return [{
            "check": "consistency",
            "result": {"conflicts": [], "duplicates": [], "notes": "dry-run"},
        }]

    # カテゴリごとにグルーピングして比較
    by_category = {}
    for entry in entries:
        cat = entry["path"].split("/")[1] if "/" in entry["path"] else "other"
        by_category.setdefault(cat, []).append(entry)

    all_results = []

    # 同一カテゴリ内の比較
    for cat, cat_entries in by_category.items():
        if len(cat_entries) < 2:
            continue

        summaries = []
        for e in cat_entries:
            m = e["meta"]
            summaries.append(
                f"[{e['path']}]\n"
                f"タイトル: {m.get('title', '')}\n"
                f"要約: {m.get('summary', '')}\n"
                f"本文冒頭: {e['body'][:500]}\n"
            )

        user_msg = f"カテゴリ「{cat}」内の {len(cat_entries)} 件のKBエントリを比較してください:\n\n" + "\n---\n".join(summaries)

        log.info(f"[一貫性チェック] カテゴリ: {cat} ({len(cat_entries)}件)")
        response = call_claude(CONSISTENCY_SYSTEM, user_msg)
        try:
            parsed = json.loads(response)
        except Exception:
            parsed = {"conflicts": [], "duplicates": [], "notes": response[:200]}

        all_results.append({
            "check": "consistency",
            "category": cat,
            "result": parsed,
        })

    # クロスカテゴリ：visa × safety, finance × living など関連カテゴリ間
    cross_pairs = [
        ("visa", "safety"),
        ("finance", "living"),
        ("transport", "living"),
        ("medical", "safety"),
    ]
    for cat_a, cat_b in cross_pairs:
        entries_a = by_category.get(cat_a, [])
        entries_b = by_category.get(cat_b, [])
        if not entries_a or not entries_b:
            continue

        summaries = []
        for e in entries_a + entries_b:
            m = e["meta"]
            summaries.append(
                f"[{e['path']}] {m.get('title', '')}: {m.get('summary', '')[:200]}"
            )

        user_msg = f"カテゴリ「{cat_a}」と「{cat_b}」間の矛盾・重複を確認してください:\n\n" + "\n".join(summaries)

        log.info(f"[クロスチェック] {cat_a} × {cat_b}")
        response = call_claude(CONSISTENCY_SYSTEM, user_msg)
        try:
            parsed = json.loads(response)
        except Exception:
            parsed = {"conflicts": [], "duplicates": [], "notes": response[:200]}

        all_results.append({
            "check": "consistency_cross",
            "categories": f"{cat_a} × {cat_b}",
            "result": parsed,
        })

    return all_results


# ─── Report Generator ────────────────────────────────────────────

def generate_report(fact_results: list, freshness_results: list, consistency_results: list, canonical_results: list = None) -> dict:
    """全チェック結果を統合レポートにまとめる"""
    if canonical_results is None:
        canonical_results = []
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_files_checked": 0,
            "fact_issues": 0,
            "freshness_issues": 0,
            "canonical_duplicates": 0,
            "consistency_conflicts": 0,
            "consistency_duplicates": 0,
            "high_severity_count": 0,
        },
        "fact_check": fact_results,
        "freshness_check": freshness_results,
        "canonical_check": canonical_results,
        "consistency_check": consistency_results,
    }
    report["summary"]["canonical_duplicates"] = len(canonical_results)

    files_checked = set()

    for r in fact_results:
        files_checked.add(r.get("file", ""))
        issues = r.get("result", {}).get("issues", [])
        report["summary"]["fact_issues"] += len(issues)
        report["summary"]["high_severity_count"] += sum(
            1 for i in issues if i.get("severity") == "high"
        )

    for r in freshness_results:
        files_checked.add(r.get("file", ""))
        issues = r.get("result", {}).get("issues", [])
        report["summary"]["freshness_issues"] += len(issues)
        report["summary"]["high_severity_count"] += sum(
            1 for i in issues if i.get("severity") == "high"
        )

    for r in consistency_results:
        result = r.get("result", {})
        report["summary"]["consistency_conflicts"] += len(result.get("conflicts", []))
        report["summary"]["consistency_duplicates"] += len(result.get("duplicates", []))

    report["summary"]["total_files_checked"] = len(files_checked - {""})
    return report


def print_summary(report: dict):
    """コンソール用サマリー表示"""
    s = report["summary"]
    print("\n" + "=" * 60)
    print("  📋 サウジナビ AI マルチチェック レポート")
    print("=" * 60)
    print(f"  検査ファイル数     : {s['total_files_checked']}")
    print(f"  ファクト問題       : {s['fact_issues']}")
    print(f"  鮮度問題           : {s['freshness_issues']}")
    print(f"  正本ルール重複      : {s['canonical_duplicates']}")
    print(f"  一貫性の矛盾       : {s['consistency_conflicts']}")
    print(f"  重複検出           : {s['consistency_duplicates']}")
    print(f"  高深刻度 (high)    : {s['high_severity_count']}")
    print("=" * 60)

    # 高深刻度の問題を列挙
    highs = []
    for r in report.get("fact_check", []) + report.get("freshness_check", []):
        for issue in r.get("result", {}).get("issues", []):
            if issue.get("severity") == "high":
                highs.append(f"  ⚠️  [{r.get('file', '?')}] {issue['problem']}")

    if highs:
        print("\n  🔴 要対応（high severity）:")
        for h in highs:
            print(h)
        print()

    total_issues = s["fact_issues"] + s["freshness_issues"] + s["consistency_conflicts"]
    if total_issues == 0:
        print("\n  ✅ 問題は検出されませんでした\n")
    else:
        print(f"\n  合計 {total_issues} 件の問題を検出しました。")
        print(f"  詳細レポート: knowledge-base/_reports/\n")


# ─── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="サウジナビ AI マルチチェックパイプライン")
    parser.add_argument("--check", choices=["fact", "freshness", "canonical", "consistency", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="API呼び出しなし")
    args = parser.parse_args()

    entries = load_all_kb()
    log.info(f"KB ファイル数: {len(entries)}")

    fact_results = []
    freshness_results = []
    canonical_results = []
    consistency_results = []

    if args.check in ("fact", "all"):
        log.info("=== ファクトチェック開始 ===")
        fact_results = check_facts(entries, dry_run=args.dry_run)

    if args.check in ("freshness", "all"):
        log.info("=== 鮮度チェック開始 ===")
        freshness_results = check_freshness(entries)

    if args.check in ("canonical", "all"):
        log.info("=== 正本ルール重複検出 ===")
        canonical_results = check_canonical(entries)

    if args.check in ("consistency", "all"):
        log.info("=== 一貫性チェック開始 ===")
        consistency_results = check_consistency(entries, dry_run=args.dry_run)

    report = generate_report(fact_results, freshness_results, consistency_results, canonical_results)

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"multicheck_{timestamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"レポート保存: {report_path}")

    # 最新レポートへのシンボリックリンク
    latest_path = REPORT_DIR / "multicheck_latest.json"
    if latest_path.exists() or latest_path.is_symlink():
        latest_path.unlink()
    latest_path.symlink_to(report_path.name)

    print_summary(report)

    # 高深刻度が1件以上あれば exit code 1（GitHub Actions でalert化可能）
    if report["summary"]["high_severity_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
