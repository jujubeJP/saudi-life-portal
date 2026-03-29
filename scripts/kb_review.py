#!/usr/bin/env python3
"""
Knowledge Base Review Helper Script

Interactive tool for reviewing and managing auto-collected KB files.
Approve, promote, or reject files from the review queue.
"""

import os
import sys
import re
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
KB_DIR = Path(__file__).parent.parent / "knowledge-base"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(KB_DIR / "_collection_log.txt", mode='a')
    ]
)
logger = logging.getLogger(__name__)


def load_review_queue():
    """Load the _review_queue.md file and parse pending items."""
    review_file = KB_DIR / "_review_queue.md"

    if not review_file.exists():
        print("No review queue found.")
        return []

    content = review_file.read_text(encoding='utf-8')

    # Extract pending items (lines starting with - [ ])
    items = []
    lines = content.split('\n')

    for line in lines:
        if line.strip().startswith('- [ ] `'):
            # Extract file path from markdown
            match = re.search(r'`([^`]+)`', line)
            if match:
                file_path = KB_DIR / match.group(1)
                items.append({
                    'file_path': file_path,
                    'relative_path': match.group(1),
                    'checked': False
                })
        elif line.strip().startswith('- [x] `'):
            match = re.search(r'`([^`]+)`', line)
            if match:
                file_path = KB_DIR / match.group(1)
                items.append({
                    'file_path': file_path,
                    'relative_path': match.group(1),
                    'checked': True
                })

    return items


def show_file_summary(file_path):
    """Display a summary of a KB file for review."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    try:
        content = file_path.read_text(encoding='utf-8')

        # Parse YAML frontmatter
        if content.startswith('---'):
            _, frontmatter, body = content.split('---', 2)
        else:
            frontmatter = ""
            body = content

        # Extract frontmatter fields
        print("\n" + "=" * 70)
        print(f"File: {file_path.relative_to(KB_DIR)}")
        print("=" * 70)
        print("\nFrontmatter:")
        print(frontmatter)

        # Show first part of content
        print("\nContent Preview:")
        lines = body.strip().split('\n')
        for i, line in enumerate(lines[:20]):
            print(line)
        if len(lines) > 20:
            print(f"\n... ({len(lines) - 20} more lines)")

        return True

    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return False


def update_frontmatter(file_path, **kwargs):
    """Update YAML frontmatter fields in a KB file."""
    try:
        content = file_path.read_text(encoding='utf-8')

        if not content.startswith('---'):
            logger.error("File doesn't have YAML frontmatter")
            return False

        # Split content
        parts = content.split('---', 2)
        if len(parts) != 3:
            logger.error("Invalid YAML frontmatter format")
            return False

        _, frontmatter, body = parts

        # Parse and update frontmatter
        lines = frontmatter.strip().split('\n')
        updated_lines = []
        updated_keys = set()

        for line in lines:
            if ':' in line:
                key = line.split(':')[0].strip()
                if key in kwargs:
                    updated_lines.append(f'{key}: "{kwargs[key]}"')
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # Add any new keys
        for key, value in kwargs.items():
            if key not in updated_keys:
                updated_lines.append(f'{key}: "{value}"')

        # Rebuild content
        new_content = '---\n' + '\n'.join(updated_lines) + '\n---' + body

        file_path.write_text(new_content, encoding='utf-8')
        logger.info(f"Updated frontmatter for {file_path.name}: {kwargs}")
        return True

    except Exception as e:
        logger.error(f"Failed to update {file_path}: {e}")
        return False


def approve_file(file_path):
    """Mark file as approved (medium confidence)."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    success = update_frontmatter(
        file_path,
        confidence='medium',
        verified_by='human-reviewer',
        verified_date=datetime.now().strftime("%Y-%m-%d")
    )

    if success:
        print(f"✓ APPROVED: {file_path.name}")
        print(f"  Confidence set to 'medium'")
    return success


def promote_file(file_path):
    """Mark file as high confidence."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    success = update_frontmatter(
        file_path,
        confidence='high',
        verified_by='human-reviewer',
        verified_date=datetime.now().strftime("%Y-%m-%d")
    )

    if success:
        print(f"✓ PROMOTED: {file_path.name}")
        print(f"  Confidence set to 'high'")
    return success


def reject_file(file_path):
    """Delete a file and remove from review."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    try:
        file_path.unlink()
        logger.info(f"Deleted: {file_path}")
        print(f"✓ REJECTED: {file_path.name} deleted")
        return True
    except Exception as e:
        logger.error(f"Failed to delete {file_path}: {e}")
        return False


def interactive_review():
    """Interactive review mode - show files one by one."""
    items = load_review_queue()

    if not items:
        print("Review queue is empty!")
        return

    pending = [item for item in items if not item['checked']]
    if not pending:
        print("No pending items to review.")
        return

    print(f"\n{len(pending)} file(s) to review\n")

    for idx, item in enumerate(pending, 1):
        file_path = item['file_path']
        print(f"\n[{idx}/{len(pending)}] Reviewing: {item['relative_path']}")

        show_file_summary(file_path)

        while True:
            action = input("\nAction (approve/a, promote/p, reject/r, skip/s, quit/q)? ").strip().lower()

            if action in ['approve', 'a']:
                approve_file(file_path)
                break
            elif action in ['promote', 'p']:
                promote_file(file_path)
                break
            elif action in ['reject', 'r']:
                confirm = input("Are you sure? (yes/no) ").strip().lower()
                if confirm == 'yes':
                    reject_file(file_path)
                break
            elif action in ['skip', 's']:
                print("Skipped")
                break
            elif action in ['quit', 'q']:
                print("Exiting review")
                return
            else:
                print("Invalid action. Try: approve, promote, reject, skip, quit")


def process_command(command, arg):
    """Process a single review command."""
    command = command.strip().lower()

    if command == 'approve' and arg:
        file_path = KB_DIR / arg
        if file_path.exists():
            approve_file(file_path)
        else:
            print(f"File not found: {arg}")

    elif command == 'promote' and arg:
        file_path = KB_DIR / arg
        if file_path.exists():
            promote_file(file_path)
        else:
            print(f"File not found: {arg}")

    elif command == 'reject' and arg:
        file_path = KB_DIR / arg
        if file_path.exists():
            reject_file(file_path)
        else:
            print(f"File not found: {arg}")

    elif command == 'show' and arg:
        file_path = KB_DIR / arg
        show_file_summary(file_path)

    elif command == 'list':
        items = load_review_queue()
        if not items:
            print("Review queue is empty")
        else:
            print(f"\nReview Queue ({len(items)} item(s)):\n")
            for item in items:
                status = "✓" if item['checked'] else "◯"
                print(f"{status} {item['relative_path']}")

    elif command == 'queue':
        review_file = KB_DIR / "_review_queue.md"
        if review_file.exists():
            print(review_file.read_text(encoding='utf-8'))
        else:
            print("Review queue file not found")

    else:
        print("Unknown command or missing argument")


def show_help():
    """Display help information."""
    print("""
Knowledge Base Review Helper

INTERACTIVE MODE:
  python3 scripts/kb_review.py
    Start interactive review of pending files

COMMAND MODE:
  python3 scripts/kb_review.py approve <file_path>
    Mark file as approved (confidence: medium)

  python3 scripts/kb_review.py promote <file_path>
    Mark file as high confidence

  python3 scripts/kb_review.py reject <file_path>
    Delete file and remove from review

  python3 scripts/kb_review.py show <file_path>
    Display file summary

  python3 scripts/kb_review.py list
    List all pending review items

  python3 scripts/kb_review.py queue
    Show current review queue

EXAMPLES:
  python3 scripts/kb_review.py approve visa/auto_evisa_20260330.md
  python3 scripts/kb_review.py promote transport/auto_saudia_20260330.md
  python3 scripts/kb_review.py reject finance/auto_sama_20260330.md
    """)


def main():
    if len(sys.argv) == 1:
        # No arguments - interactive mode
        interactive_review()
    elif len(sys.argv) == 2:
        cmd = sys.argv[1].lower()
        if cmd in ['help', '-h', '--help']:
            show_help()
        elif cmd == 'list':
            process_command('list', '')
        elif cmd == 'queue':
            process_command('queue', '')
        else:
            print("Invalid command. Use 'help' for usage information.")
    elif len(sys.argv) >= 3:
        command = sys.argv[1].lower()
        arg = ' '.join(sys.argv[2:])
        process_command(command, arg)
    else:
        show_help()


if __name__ == '__main__':
    main()
