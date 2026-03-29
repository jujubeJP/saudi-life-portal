#!/usr/bin/env python3
"""
Knowledge Base Expiry Checker

Scans all KB files and identifies those where review_by is past or within 7 days.
Outputs both human-readable and machine-readable (JSON) reports.
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configuration
BASE_DIR = Path(__file__).parent.parent
KB_DIR = BASE_DIR / "knowledge-base"

# ANSI color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'


def parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 2:
            fm_text = parts[1].strip()
            result = {}
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    result[key] = value
            return result
    return {}


def parse_json_metadata(filepath: Path) -> Dict[str, Any]:
    """Parse metadata from JSON file."""
    try:
        content = filepath.read_text(encoding='utf-8')
        data = json.loads(content)

        if isinstance(data, dict) and 'metadata' in data:
            return data['metadata']
    except:
        pass

    return {}


def extract_frontmatter(filepath: Path) -> Dict[str, Any]:
    """Extract frontmatter from KB file (MD or JSON)."""
    if filepath.suffix == '.json':
        return parse_json_metadata(filepath)
    else:
        content = filepath.read_text(encoding='utf-8')
        return parse_yaml_frontmatter(content)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO date string to datetime."""
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def check_file_status(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Check a single file's review status.
    Returns None if file is OK, or a dict with status info if action needed.
    """
    try:
        frontmatter = extract_frontmatter(filepath)

        if not frontmatter:
            return None

        review_by = frontmatter.get('review_by', '')
        review_date = parse_date(review_by)

        if not review_date:
            return None

        today = datetime.now()
        days_until = (review_date - today).days

        # Check if within 7 days or past
        if days_until <= 7:
            return {
                'filepath': str(filepath.relative_to(KB_DIR)),
                'id': frontmatter.get('id', 'unknown'),
                'title': frontmatter.get('title', 'Untitled'),
                'review_by': review_by,
                'days_until_review': days_until,
                'status': 'overdue' if days_until < 0 else 'due_soon',
                'confidence': frontmatter.get('confidence', 'unknown'),
                'source_url': frontmatter.get('source_url', ''),
                'verified_by': frontmatter.get('verified_by', ''),
                'notes': frontmatter.get('notes', ''),
            }

        return None

    except Exception as e:
        print(f"Error checking {filepath}: {e}", file=sys.stderr)
        return None


def main():
    """Main function to check all KB files."""
    print("=" * 80)
    print("Knowledge Base Review Expiry Checker")
    print("=" * 80)
    print()

    # Find all KB files
    kb_files = []
    for pattern in ["**/*.md", "**/*.json"]:
        for filepath in KB_DIR.glob(pattern):
            if filepath.name in ("README.md", "_migration_report.json", "_collection_log.txt", "_review_queue.md"):
                continue
            kb_files.append(filepath)

    kb_files.sort()

    print(f"Scanning {len(kb_files)} KB files...\n")

    files_needing_review = []
    overdue_files = []

    # Check each file
    for filepath in kb_files:
        status = check_file_status(filepath)
        if status:
            files_needing_review.append(status)

            if status['status'] == 'overdue':
                overdue_files.append(status)

    # Sort by days_until_review (most urgent first)
    files_needing_review.sort(key=lambda x: x['days_until_review'])

    # Human-readable report
    print()
    if not files_needing_review:
        print(f"{GREEN}✓ All KB files are up to date!{RESET}")
        print()
    else:
        if overdue_files:
            print(f"{RED}{BOLD}⚠ OVERDUE FILES ({len(overdue_files)}){RESET}")
            print("-" * 80)
            for item in overdue_files:
                days_ago = abs(item['days_until_review'])
                print(f"{RED}✗ {item['filepath']}{RESET}")
                print(f"  ID: {item['id']}")
                print(f"  Title: {item['title']}")
                print(f"  Review was due {days_ago} day(s) ago ({item['review_by']})")
                print(f"  Confidence: {item['confidence']}")
                print(f"  Verified by: {item['verified_by']}")
                if item['source_url']:
                    print(f"  Source: {item['source_url']}")
                print()

        files_due_soon = [f for f in files_needing_review if f['status'] == 'due_soon']
        if files_due_soon:
            print(f"{YELLOW}{BOLD}⚠ FILES DUE SOON ({len(files_due_soon)}){RESET}")
            print("-" * 80)
            for item in files_due_soon:
                print(f"{YELLOW}◐ {item['filepath']}{RESET}")
                print(f"  ID: {item['id']}")
                print(f"  Title: {item['title']}")
                print(f"  Review due in {item['days_until_review']} day(s) ({item['review_by']})")
                print(f"  Confidence: {item['confidence']}")
                print(f"  Verified by: {item['verified_by']}")
                if item['source_url']:
                    print(f"  Source: {item['source_url']}")
                print()

    # Machine-readable JSON report
    print()
    print("=" * 80)
    print("Machine-Readable Report (JSON)")
    print("=" * 80)

    json_report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_files_checked': len(kb_files),
            'files_needing_review': len(files_needing_review),
            'overdue_files': len(overdue_files),
            'due_soon_files': len([f for f in files_needing_review if f['status'] == 'due_soon']),
        },
        'files_needing_review': files_needing_review,
    }

    print(json.dumps(json_report, ensure_ascii=False, indent=2))
    print()

    # Save JSON report to file
    report_file = KB_DIR / "_review_expiry_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)

    print(f"Report saved to: {report_file}")
    print()

    # Summary line
    print("=" * 80)
    if overdue_files:
        print(f"{RED}✗ {len(overdue_files)} file(s) overdue for review{RESET}")
        return 1
    elif files_needing_review:
        print(f"{YELLOW}⚠ {len(files_needing_review)} file(s) due for review within 7 days{RESET}")
        return 1
    else:
        print(f"{GREEN}✓ All files are current (no reviews due within 7 days){RESET}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
