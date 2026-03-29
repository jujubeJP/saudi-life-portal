#!/usr/bin/env python3
"""
AI Auto-Collection Pipeline for Saudi Navi Knowledge Base

This script fetches content from official Saudi government and service URLs,
extracts key information, and saves it as markdown files with YAML frontmatter
for human review.
"""

import os
import sys
import json
import time
import argparse
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from difflib import SequenceMatcher

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not found.")
    print("Install them with: pip install beautifulsoup4 requests --break-system-packages")
    sys.exit(1)

# Configuration
BASE_DIR = Path(__file__).parent.parent
KB_DIR = BASE_DIR / "knowledge-base"
SCRIPT_DIR = BASE_DIR / "scripts"

# Request configuration
REQUEST_TIMEOUT = 10
REQUEST_DELAY = 1  # seconds between requests for rate limiting
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Source URLs organized by category
SOURCES = {
    "visa": [
        "https://visa.visitsaudi.com/",
        "https://www.mofa.gov.sa/",
    ],
    "transport": [
        "https://www.saudia.com/",
        "https://www.sar.com.sa/",
        "https://www.riyadhmetro.sa/",
    ],
    "telecom": [
        "https://www.stc.com.sa/",
        "https://www.mobily.com.sa/",
        "https://www.zain.com/",
    ],
    "finance": [
        "https://www.sama.gov.sa/",
    ],
    "safety": [
        "https://www.anzen.mofa.go.jp/",
    ],
    "medical": [
        "https://www.moh.gov.sa/",
    ],
    "general": [
        "https://www.my.gov.sa/",
        "https://www.visitsaudi.com/en/events",
    ],
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(KB_DIR / "_collection_log.txt", mode='a')
    ]
)
logger = logging.getLogger(__name__)


def get_request_headers():
    """Return headers for HTTP requests."""
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


def extract_text_content(html_content, url):
    """
    Extract key text content from HTML.
    Returns a dict with title, main text, and metadata.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract title
        title = "Unknown"
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else "Unknown"
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)

        # Extract main content
        # Try to find main content area
        main_content = soup.find(['main', 'article', 'div.content', 'div.main'])
        if not main_content:
            main_content = soup.body if soup.body else soup

        # Extract text
        text_lines = []
        for paragraph in main_content.find_all(['p', 'h1', 'h2', 'h3', 'li']):
            text = paragraph.get_text(strip=True)
            if text and len(text) > 10:  # Skip very short text
                text_lines.append(text)

        main_text = "\n".join(text_lines[:500])  # Limit to first 500 lines

        # Extract dates (look for common date patterns)
        dates_found = []
        for text in text_lines[:50]:
            if any(month in text for month in ['January', 'February', 'March', 'April',
                                                'May', 'June', 'July', 'August',
                                                'September', 'October', 'November', 'December',
                                                '2024', '2025', '2026']):
                dates_found.append(text)

        return {
            'title': title,
            'content': main_text,
            'dates': dates_found[:5],
            'url': url,
            'success': True
        }
    except Exception as e:
        logger.warning(f"Failed to parse HTML from {url}: {e}")
        return {
            'title': '',
            'content': '',
            'dates': [],
            'url': url,
            'success': False,
            'error': str(e)
        }


def fetch_url_content(url):
    """
    Fetch content from a URL with timeout and error handling.
    Returns raw HTML or None on failure.
    """
    try:
        response = requests.get(
            url,
            headers=get_request_headers(),
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        logger.warning(f"TIMEOUT: {url}")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning(f"CONNECTION ERROR: {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP ERROR {e.response.status_code}: {url}")
        return None
    except Exception as e:
        logger.warning(f"ERROR fetching {url}: {e}")
        return None


def generate_topic_name(url, extracted_title):
    """Generate a topic name from URL and extracted title."""
    # Prefer extracted title, fall back to URL domain
    if extracted_title and extracted_title != "Unknown":
        # Sanitize title for filename
        topic = extracted_title.lower()
        topic = ''.join(c if c.isalnum() or c in '-_' else '_' for c in topic)
        topic = topic.replace('_' * 2, '_').strip('_')[:40]
        return topic
    else:
        # Generate from domain
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        domain = domain.split('.')[0]
        return domain


def content_hash(text):
    """Generate a hash of content for comparison."""
    return hashlib.md5(text.encode()).hexdigest()


def find_existing_file(category, topic):
    """Find existing file for a topic in a category."""
    category_dir = KB_DIR / category
    if not category_dir.exists():
        return None

    pattern = f"auto_{topic}_*.md"
    files = list(category_dir.glob(pattern))
    return files[-1] if files else None


def has_significant_change(old_content, new_content, threshold=0.8):
    """
    Compare old and new content. Return True if they're significantly different.
    threshold: ratio of matching content (0.8 = 20% different is considered significant)
    """
    matcher = SequenceMatcher(None, old_content, new_content)
    ratio = matcher.ratio()
    return ratio < threshold


def save_kb_file(category, topic, url, extracted_data, dry_run=False, previous_version=None):
    """
    Save extracted content as a KB markdown file with YAML frontmatter.
    """
    category_dir = KB_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    filename = f"auto_{topic}_{today}.md"
    filepath = category_dir / filename

    # Prepare frontmatter
    frontmatter = {
        'source': extracted_data['url'],
        'verified_date': datetime.now().strftime("%Y-%m-%d"),
        'confidence': 'low',
        'verified_by': 'auto-collector',
        'notes': 'Auto-collected, needs human review',
    }

    if previous_version:
        frontmatter['previous_version'] = previous_version

    # Build markdown content
    yaml_str = "---\n"
    for key, value in frontmatter.items():
        yaml_str += f'{key}: "{value}"\n'
    yaml_str += "---\n\n"

    title = extracted_data['title'] or f"Auto-collected from {urlparse(url).netloc}"
    markdown_content = yaml_str + f"# {title}\n\n"

    if extracted_data['dates']:
        markdown_content += "## Dates Found\n"
        for date_text in extracted_data['dates']:
            markdown_content += f"- {date_text}\n"
        markdown_content += "\n"

    markdown_content += "## Content\n\n"
    markdown_content += extracted_data['content']
    markdown_content += "\n\n---\n*Auto-collected on " + datetime.now().isoformat() + "*\n"

    if dry_run:
        logger.info(f"[DRY RUN] Would save: {filepath}")
        logger.info(f"[DRY RUN] Content length: {len(markdown_content)} chars")
        return filepath, False
    else:
        try:
            filepath.write_text(markdown_content, encoding='utf-8')
            logger.info(f"SAVED: {filepath}")
            return filepath, True
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")
            return None, False


def collect_from_url(category, url, dry_run=False):
    """
    Collect content from a single URL and save it.
    Returns (success, file_path, needs_review)
    """
    logger.info(f"Fetching {category}: {url}")

    html_content = fetch_url_content(url)
    if not html_content:
        logger.warning(f"Skipped (fetch failed): {url}")
        return False, None, False

    # Extract content
    extracted = extract_text_content(html_content, url)
    if not extracted['success'] or not extracted['content']:
        logger.warning(f"Skipped (parse failed): {url}")
        return False, None, False

    # Generate topic name
    topic = generate_topic_name(url, extracted['title'])

    # Check for existing file
    existing_file = find_existing_file(category, topic)
    previous_version = None
    needs_review = True

    if existing_file:
        existing_content = existing_file.read_text(encoding='utf-8')
        # Extract just the content part (after frontmatter)
        existing_text = existing_content.split('---')[-1] if '---' in existing_content else existing_content

        if not has_significant_change(existing_text, extracted['content']):
            logger.info(f"Skipped (no significant changes): {topic}")
            return False, existing_file, False

        previous_version = existing_file.name
        logger.info(f"Update detected for {topic}, saving new version")

    # Save the file
    filepath, saved = save_kb_file(
        category, topic, url, extracted,
        dry_run=dry_run,
        previous_version=previous_version
    )

    return saved, filepath, needs_review if saved else False


def collect_category(category, dry_run=False):
    """Collect all sources for a specific category."""
    if category not in SOURCES:
        logger.error(f"Unknown category: {category}")
        return []

    files_collected = []
    urls = SOURCES[category]

    logger.info(f"\n=== Collecting {category.upper()} ===")

    for url in urls:
        success, filepath, needs_review = collect_from_url(category, url, dry_run=dry_run)
        if success and filepath:
            files_collected.append({
                'file': str(filepath),
                'url': url,
                'category': category,
                'needs_review': needs_review
            })
        time.sleep(REQUEST_DELAY)

    return files_collected


def collect_all(dry_run=False):
    """Collect all sources across all categories."""
    logger.info("=" * 60)
    logger.info(f"Starting collection run at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    all_files = []
    for category in SOURCES.keys():
        files = collect_category(category, dry_run=dry_run)
        all_files.extend(files)

    return all_files


def update_review_queue(collected_files):
    """
    Generate _review_queue.md file listing all files that need review.
    """
    review_file = KB_DIR / "_review_queue.md"

    if not collected_files:
        logger.info("No new files to review")
        return

    # Build review queue content
    content = "# Knowledge Base Review Queue\n\n"
    content += f"**Summary:** {len(collected_files)} file(s) pending human review\n\n"
    content += f"*Generated: {datetime.now().isoformat()}*\n\n"
    content += "## Pending Items\n\n"

    for item in collected_files:
        file_path = item['file']
        rel_path = Path(file_path).relative_to(KB_DIR)
        content += f"- [ ] `{rel_path}` — {item['url']}\n"
        content += f"  - Collected: {item['category']}\n"

    content += "\n## Review Actions\n\n"
    content += "Use `kb_review.py` to manage this queue:\n"
    content += "- `approve [file]` — Mark as verified (confidence: medium)\n"
    content += "- `promote [file]` — Mark as high confidence\n"
    content += "- `reject [file]` — Delete the file\n"

    try:
        review_file.write_text(content, encoding='utf-8')
        logger.info(f"REVIEW QUEUE: {review_file}")
        print(f"\nReview queue saved to: {review_file}")
    except Exception as e:
        logger.error(f"Failed to write review queue: {e}")


def show_review_queue():
    """Display current review queue."""
    review_file = KB_DIR / "_review_queue.md"

    if not review_file.exists():
        print("No review queue found. Run collection first.")
        return

    print(review_file.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(
        description="AI Auto-Collection Pipeline for Saudi Navi Knowledge Base"
    )
    parser.add_argument(
        '--category',
        choices=list(SOURCES.keys()),
        help='Collect only specific category'
    )
    parser.add_argument(
        '--review',
        action='store_true',
        help='Show current review queue'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be collected without saving'
    )

    args = parser.parse_args()

    if args.review:
        show_review_queue()
        return

    # Run collection
    if args.category:
        collected = collect_category(args.category, dry_run=args.dry_run)
    else:
        collected = collect_all(dry_run=args.dry_run)

    # Update review queue
    if collected and not args.dry_run:
        update_review_queue(collected)

    # Summary
    logger.info("=" * 60)
    logger.info(f"Collection complete: {len(collected)} file(s) collected")
    logger.info("=" * 60)

    if args.dry_run:
        print(f"\n[DRY RUN] Would have collected {len(collected)} file(s)")


if __name__ == '__main__':
    main()
