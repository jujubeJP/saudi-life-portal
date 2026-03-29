#!/usr/bin/env python3
"""
Knowledge Base Schema Migration Script

Upgrades all existing KB files from the old schema to the new enhanced schema.
Includes auto-generation of new fields based on inference rules.
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import yaml

# Configuration
BASE_DIR = Path(__file__).parent.parent
KB_DIR = BASE_DIR / "knowledge-base"

# Category mapping to review_by rules
REVIEW_BY_RULES = {
    "visa": 90,  # 3 months
    "safety": 90,  # 3 months
    "finance": 90,  # 3 months
    "telecom": 180,  # 6 months
    "transport": 180,  # 6 months
    "medical": 180,  # 6 months
    "culture": 365,  # 12 months
    "living": 365,  # 12 months
    "business": 365,  # 12 months
    "community": 365,  # 12 months
}


def infer_source_type(source_url: str, verified_by: str, notes: str) -> str:
    """Infer source_type based on URL and metadata."""
    if not source_url:
        return "公的二次情報"

    # Check for government domains
    gov_patterns = [r'\.gov\.', r'\.go\.jp', r'mofa\.go\.jp', r'\.gov\.sa', r'sama\.gov\.sa', r'moh\.gov\.sa']
    if any(re.search(pattern, source_url, re.IGNORECASE) for pattern in gov_patterns):
        return "一次情報"

    # Check for news domains
    news_patterns = [r'news\.', r'press\.', r'times\.', r'bbc\.', r'reuters\.']
    if any(re.search(pattern, source_url, re.IGNORECASE) for pattern in news_patterns):
        return "報道"

    # Check for collaborator or internal notes
    if "collaborator" in (notes or "").lower() or (verified_by and verified_by != "auto"):
        return "運営者整理"

    # Check for internal references (public/xxx.html pattern)
    if re.search(r'public/[a-z\-]+\.html', source_url, re.IGNORECASE):
        return "運営者整理"

    return "公的二次情報"


def infer_region_scope(filepath: Path, content: str) -> str:
    """Infer region_scope from content."""
    content_lower = content.lower()

    # City mentions
    city_patterns = {
        "リヤド": "リヤド",
        "riyadh": "リヤド",
        "ジェッダ": "ジェッダ",
        "jeddah": "ジェッダ",
        "東部州": "東部州",
        "eastern": "東部州",
        "メッカ": "メッカ",
        "mecca": "メッカ",
        "マディーナ": "マディーナ",
        "medina": "マディーナ",
    }

    cities_mentioned = []
    for pattern, city_jp in city_patterns.items():
        if re.search(pattern, content_lower):
            cities_mentioned.append(city_jp)

    # Remove duplicates
    cities_mentioned = list(dict.fromkeys(cities_mentioned))

    if len(cities_mentioned) > 1:
        return "複数都市"
    elif len(cities_mentioned) == 1:
        return cities_mentioned[0]

    # Check for comparison-related language
    if re.search(r'比較|違い|difference|vs', content, re.IGNORECASE):
        return "複数都市"

    return "全国"


def infer_audience(category: str, filepath: str, content: str) -> List[str]:
    """Infer audience based on category and content."""
    audience = []

    # Category-based rules
    if category == "visa":
        return ["全員"]

    if category == "safety":
        return ["全員"]

    if category == "telecom":
        return ["全員"]

    if category == "transport":
        return ["全員"]

    if category == "culture":
        return ["全員"]

    if category == "medical":
        return ["全員"]

    if category == "business":
        return ["出張者", "事業者"]

    # Living category - content-based
    if category == "living":
        content_lower = content.lower()
        has_school = re.search(r'学校|school', content_lower)
        has_family = re.search(r'家族|family|子供|children', content_lower)
        has_settlement = re.search(r'定住|settlement|長期', content_lower)

        if has_school or has_family:
            audience.extend(["家族帯同", "長期滞在"])
        elif has_settlement:
            audience.extend(["長期滞在"])
        else:
            audience.append("長期滞在")

        return list(dict.fromkeys(audience)) if audience else ["長期滞在"]

    # Community category
    if category == "community":
        return ["長期滞在", "家族帯同"]

    return ["全員"]


def infer_tags(category: str, content: str) -> List[str]:
    """Infer tags from category and content."""
    tags = [category]

    # Extract key Japanese terms
    # Common patterns for major topics
    patterns = {
        "visa": ["ビザ", "evisa", "電子ビザ", "査証", "入国"],
        "safety": ["緊急", "安全", "police", "警察", "事故"],
        "finance": ["銀行", "金融", "送金", "両替", "通貨"],
        "medical": ["医療", "病院", "保険", "健康", "薬"],
        "telecom": ["通信", "携帯", "sim", "回線", "アプリ"],
        "transport": ["交通", "飛行機", "タクシー", "移動", "駅"],
        "culture": ["文化", "歴史", "食事", "宗教", "イベント"],
        "business": ["ビジネス", "商習慣", "マナー", "会議", "交渉"],
        "living": ["生活", "住居", "学校", "日常", "生活用品"],
        "community": ["コミュニティ", "協力", "情報", "相談"],
    }

    content_lower = content.lower()

    if category in patterns:
        for keyword in patterns[category]:
            if keyword.lower() in content_lower:
                # Add both Japanese and English variants
                if keyword.isascii():
                    tags.append(keyword)
                else:
                    tags.append(keyword)

    return list(dict.fromkeys(tags))


def extract_first_h1(content: str) -> Optional[str]:
    """Extract the first H1 heading from markdown content."""
    match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_summary(content: str) -> str:
    """Extract first 1-2 sentences from content (after H1)."""
    # Remove H1 heading and section headings to get body text
    lines = content.split('\n')
    content_lines = []

    for line in lines:
        line = line.strip()
        # Skip empty lines and headings
        if not line or line.startswith("#"):
            continue
        # Skip lines that are just list items at the start
        if line.startswith(("- ", "* ", "+ ")):
            if content_lines:  # Only add if we have content already
                content_lines.append(line.lstrip("- * +").strip())
        else:
            content_lines.append(line)

    # Get first 1-2 sentences
    text = " ".join(content_lines[:50])  # First ~50 lines max

    # Split by common sentence endings
    sentences = re.split(r'[。．!！?？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    if len(sentences) >= 2:
        summary = sentences[0] + "。" + sentences[1]
        if not summary.endswith("。"):
            summary += "。"
    elif sentences:
        summary = sentences[0]
        if not summary.endswith(("。", ".")):
            summary += "。"
    else:
        summary = "Information about " + content.split('\n')[0][:50]

    # Limit to ~150 characters for display but preserve full meaning
    if len(summary) > 150:
        # Find last sentence ending within limit
        truncated = summary[:150]
        last_period = max(truncated.rfind("。"), truncated.rfind("."))
        if last_period > 20:
            summary = truncated[:last_period + 1]
        else:
            summary = truncated + "..."

    return summary


def generate_id_from_filepath(filepath: Path) -> str:
    """Generate id from filepath: category-filename-without-date."""
    category = filepath.parent.name
    filename = filepath.stem  # without extension

    # Remove date suffix (_YYYYMMDD)
    filename = re.sub(r'_\d{8}$', '', filename)

    return f"{category}-{filename}"


def calculate_review_by(category: str, checked_at: str) -> str:
    """Calculate review_by date based on category rules."""
    try:
        checked_date = datetime.strptime(checked_at, "%Y-%m-%d")
    except:
        checked_date = datetime.now()

    days_to_add = REVIEW_BY_RULES.get(category, 365)  # default 1 year
    review_date = checked_date + timedelta(days=days_to_add)

    return review_date.strftime("%Y-%m-%d")


def parse_existing_frontmatter(content: str) -> Dict[str, Any]:
    """Parse existing YAML frontmatter from markdown/json content."""
    if content.startswith("---"):
        # Markdown with YAML frontmatter
        # Find the second --- delimiter
        parts = content.split("---", 2)
        if len(parts) >= 2:
            fm_text = parts[1].strip()
            try:
                parsed = yaml.safe_load(fm_text)
                return parsed if isinstance(parsed, dict) else {}
            except Exception as e:
                # Fallback: parse as simple key: value pairs
                result = {}
                for line in fm_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        result[key] = value
                return result

    return {}


def migrate_markdown_file(filepath: Path) -> Dict[str, Any]:
    """Migrate a markdown file to the new schema."""
    content = filepath.read_text(encoding='utf-8')
    old_frontmatter = parse_existing_frontmatter(content)
    category = filepath.parent.name

    # Extract H1 and content (remove frontmatter)
    # Use split with maxsplit to only split on first two "---" delimiters
    parts = content.split("---", 2)
    if len(parts) >= 3:
        content_after_frontmatter = parts[2].strip()
    else:
        content_after_frontmatter = content.strip()

    first_h1 = extract_first_h1(content_after_frontmatter)
    summary = extract_summary(content_after_frontmatter)

    # Get old values
    source_url = old_frontmatter.get('source', '')
    verified_date = old_frontmatter.get('verified_date', datetime.now().strftime("%Y-%m-%d"))
    confidence = old_frontmatter.get('confidence', 'medium')
    verified_by = old_frontmatter.get('verified_by', 'auto')
    old_notes = old_frontmatter.get('notes', '')

    # Generate new schema
    new_frontmatter = {
        'id': generate_id_from_filepath(filepath),
        'topic': first_h1 or category,  # Use H1 or category
        'title': first_h1 or f"{category} information",
        'summary': summary,
        'source_url': source_url,
        'source_type': infer_source_type(source_url, verified_by, old_notes),
        'checked_at': verified_date,
        'valid_from': verified_date,
        'valid_until': "TBD",
        'review_by': calculate_review_by(category, verified_date),
        'confidence': confidence,
        'region_scope': infer_region_scope(filepath, content_after_frontmatter),
        'audience': infer_audience(category, str(filepath), content_after_frontmatter),
        'tags': infer_tags(category, content_after_frontmatter),
        'derived_from': None,
        'verified_by': verified_by,
        'notes_for_agent': "",
        'notes': old_notes,
    }

    return {
        'filepath': filepath,
        'frontmatter': new_frontmatter,
        'content': content_after_frontmatter,
        'is_json': False,
    }


def migrate_json_file(filepath: Path) -> Dict[str, Any]:
    """Migrate a JSON file to the new schema."""
    content = filepath.read_text(encoding='utf-8')
    data = json.loads(content)

    # Skip if this is not a proper KB file (e.g., report files)
    if isinstance(data, list):
        raise ValueError("File is not a valid KB JSON file")

    category = filepath.parent.name
    filename = filepath.stem

    # Extract metadata if present
    if isinstance(data, dict):
        metadata = data.get('metadata', {})
    else:
        metadata = {}
    source_url = metadata.get('source', '')
    verified_date = metadata.get('verified_date', datetime.now().strftime("%Y-%m-%d"))
    confidence = metadata.get('confidence', 'medium')
    verified_by = metadata.get('verified_by', 'auto')

    # Generate new schema
    new_frontmatter = {
        'id': f"{category}-{filename}",
        'topic': category,
        'title': filename.replace('-', ' ').title(),
        'summary': f"Structured {category} data",
        'source_url': source_url,
        'source_type': infer_source_type(source_url, verified_by, ""),
        'checked_at': verified_date,
        'valid_from': verified_date,
        'valid_until': "TBD",
        'review_by': calculate_review_by(category, verified_date),
        'confidence': confidence,
        'region_scope': "全国",
        'audience': infer_audience(category, str(filepath), ""),
        'tags': infer_tags(category, ""),
        'derived_from': None,
        'verified_by': verified_by,
        'notes_for_agent': "",
        'notes': metadata.get('notes', ''),
    }

    # For JSON, we'll embed the frontmatter in the metadata section
    return {
        'filepath': filepath,
        'frontmatter': new_frontmatter,
        'content': data,
        'is_json': True,
    }


def write_migrated_file(migrated_data: Dict[str, Any]) -> bool:
    """Write migrated file back to disk."""
    filepath = migrated_data['filepath']
    frontmatter = migrated_data['frontmatter']
    is_json = migrated_data['is_json']

    try:
        if is_json:
            # JSON: embed frontmatter in metadata
            content = migrated_data['content']
            content['metadata'] = {
                'id': frontmatter['id'],
                'topic': frontmatter['topic'],
                'title': frontmatter['title'],
                'summary': frontmatter['summary'],
                'source_url': frontmatter['source_url'],
                'source_type': frontmatter['source_type'],
                'checked_at': frontmatter['checked_at'],
                'valid_from': frontmatter['valid_from'],
                'valid_until': frontmatter['valid_until'],
                'review_by': frontmatter['review_by'],
                'confidence': frontmatter['confidence'],
                'region_scope': frontmatter['region_scope'],
                'audience': frontmatter['audience'],
                'tags': frontmatter['tags'],
                'derived_from': frontmatter['derived_from'],
                'verified_by': frontmatter['verified_by'],
                'notes_for_agent': frontmatter['notes_for_agent'],
                'notes': frontmatter['notes'],
            }
            filepath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
        else:
            # Markdown: YAML frontmatter + content
            yaml_str = "---\n"
            for key, value in frontmatter.items():
                if isinstance(value, list):
                    yaml_str += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
                elif value is None:
                    yaml_str += f"{key}: null\n"
                else:
                    yaml_str += f'{key}: "{value}"\n'
            yaml_str += "---\n\n"

            content = yaml_str + migrated_data['content']
            filepath.write_text(content, encoding='utf-8')

        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False


def main():
    """Main migration function."""
    print("=" * 70)
    print("Knowledge Base Schema Migration")
    print("=" * 70)
    print()

    # Find all KB files
    kb_files = []
    for pattern in ["**/*.md", "**/*.json"]:
        for filepath in KB_DIR.glob(pattern):
            if filepath.name in ("README.md", "_migration_report.json", "_collection_log.txt"):
                continue
            kb_files.append(filepath)

    kb_files.sort()

    print(f"Found {len(kb_files)} files to migrate\n")

    migrated_count = 0
    error_count = 0
    migration_results = []

    for i, filepath in enumerate(kb_files, 1):
        category = filepath.parent.name
        print(f"[{i}/{len(kb_files)}] Migrating {filepath.relative_to(KB_DIR)}...", end=" ")

        try:
            if filepath.suffix == '.json':
                migrated = migrate_json_file(filepath)
            else:
                migrated = migrate_markdown_file(filepath)

            if write_migrated_file(migrated):
                print("✓ OK")
                migrated_count += 1
                migration_results.append({
                    'file': str(filepath.relative_to(KB_DIR)),
                    'status': 'success',
                    'id': migrated['frontmatter']['id'],
                    'source_type': migrated['frontmatter']['source_type'],
                    'review_by': migrated['frontmatter']['review_by'],
                })
            else:
                print("✗ FAILED")
                error_count += 1
                migration_results.append({
                    'file': str(filepath.relative_to(KB_DIR)),
                    'status': 'error',
                })
        except Exception as e:
            print(f"✗ ERROR: {e}")
            error_count += 1
            migration_results.append({
                'file': str(filepath.relative_to(KB_DIR)),
                'status': 'error',
                'error': str(e),
            })

    # Print summary
    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"✓ Successfully migrated: {migrated_count} files")
    print(f"✗ Errors: {error_count} files")
    print()

    # Print migration report
    print("Migration Report (JSON):")
    print(json.dumps(migration_results, ensure_ascii=False, indent=2))

    # Save report to file
    report_file = KB_DIR / "_migration_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(migration_results, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to: {report_file}")

    return 0 if error_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
