# Knowledge Base Auto-Collection Pipeline

This directory contains two Python scripts for managing the Saudi Navi knowledge base:

1. **kb_collector.py** — Automated content collection from official sources
2. **kb_review.py** — Interactive review and approval workflow for collected content

## kb_collector.py

### Overview
Fetches content from official Saudi government and service URLs, extracts key information, and saves it as markdown files with YAML frontmatter for human review.

### Defined Sources by Category

The script monitors the following source URLs:

- **Visa**: https://visa.visitsaudi.com/, https://www.mofa.gov.sa/
- **Transport**: https://www.saudia.com/, https://www.sar.com.sa/, https://www.riyadhmetro.sa/
- **Telecom**: https://www.stc.com.sa/, https://www.mobily.com.sa/, https://www.zain.com/
- **Finance**: https://www.sama.gov.sa/
- **Safety**: https://www.anzen.mofa.go.jp/
- **Medical**: https://www.moh.gov.sa/
- **General**: https://www.my.gov.sa/, https://www.visitsaudi.com/en/events

### Features

1. **Content Extraction**: Uses BeautifulSoup to extract:
   - Page title
   - Main text content (first 500 lines)
   - Dates mentioned in the page
   - Source URL

2. **YAML Frontmatter**: All collected files include:
   ```yaml
   ---
   source: "https://..."
   verified_date: "2026-03-30"
   confidence: "low"
   verified_by: "auto-collector"
   notes: "Auto-collected, needs human review"
   previous_version: "auto_topic_20260329.md"  (if updated)
   ---
   ```

3. **File Naming**: `knowledge-base/[category]/auto_[topic]_[YYYYMMDD].md`

4. **Diff Detection**: Compares new content with existing files (80% similarity threshold)
   - Only saves if there are meaningful changes
   - Links to previous version in frontmatter if updated

5. **Review Queue**: Generates `_review_queue.md` listing all files pending human review

6. **Error Handling**:
   - 10-second timeout per request
   - 1-second delay between requests (rate limiting)
   - Graceful failure with logging
   - Logs to `_collection_log.txt`

### Usage

```bash
# Full collection run (all categories)
python3 scripts/kb_collector.py

# Collect only one category
python3 scripts/kb_collector.py --category visa
python3 scripts/kb_collector.py --category transport

# Available categories: visa, transport, telecom, finance, safety, medical, general

# Dry run (preview without saving)
python3 scripts/kb_collector.py --dry-run
python3 scripts/kb_collector.py --category finance --dry-run

# Show current review queue
python3 scripts/kb_collector.py --review

# Help
python3 scripts/kb_collector.py --help
```

### Output Files

- **Knowledge Base Files**: `knowledge-base/[category]/auto_[topic]_YYYYMMDD.md`
- **Review Queue**: `knowledge-base/_review_queue.md` (created after each collection)
- **Collection Log**: `knowledge-base/_collection_log.txt` (appended with each run)

### Example Output Structure

```
knowledge-base/
├── visa/
│   ├── auto_evisa_20260330.md
│   └── auto_mofa_20260330.md
├── transport/
│   ├── auto_saudia_20260330.md
│   └── auto_metro_20260330.md
├── _review_queue.md
└── _collection_log.txt
```

---

## kb_review.py

### Overview
Interactive tool for reviewing, approving, promoting, or rejecting auto-collected KB files. Updates confidence levels and frontmatter metadata.

### Features

1. **Interactive Review Mode**: One file at a time with actions
2. **Command Mode**: Direct file operations
3. **Frontmatter Updates**: Modifies confidence, verified_date, verified_by fields
4. **Review Queue Management**: Maintains `_review_queue.md`

### Usage

#### Interactive Mode (recommended for batch review)

```bash
python3 scripts/kb_review.py
```

Shows files one by one with options:
- `approve` or `a` — Mark as approved (confidence: medium)
- `promote` or `p` — Mark as high confidence
- `reject` or `r` — Delete the file
- `skip` or `s` — Skip to next
- `quit` or `q` — Exit review

#### Command Mode (for single actions)

```bash
# Approve a file (sets confidence to "medium")
python3 scripts/kb_review.py approve visa/auto_evisa_20260330.md

# Promote a file (sets confidence to "high")
python3 scripts/kb_review.py promote transport/auto_saudia_20260330.md

# Reject a file (deletes it)
python3 scripts/kb_review.py reject finance/auto_sama_20260330.md

# Show file summary
python3 scripts/kb_review.py show visa/auto_test_20260330.md

# List all pending items
python3 scripts/kb_review.py list

# Show review queue
python3 scripts/kb_review.py queue

# Help
python3 scripts/kb_review.py help
```

### Confidence Levels

| Level | Meaning | Usage |
|-------|---------|-------|
| `low` | Auto-collected, unreviewed | Default from collector |
| `medium` | Approved by human | Use `approve` command |
| `high` | High confidence, verified | Use `promote` command |

### Frontmatter Changes

When you approve or promote a file, the script updates:
- `confidence`: low → medium → high
- `verified_date`: Set to today's date
- `verified_by`: Changed from "auto-collector" to "human-reviewer"

### Example Workflow

```bash
# 1. Run collection
python3 scripts/kb_collector.py

# 2. Review files interactively
python3 scripts/kb_review.py

# 3. Or approve specific file
python3 scripts/kb_review.py approve visa/auto_evisa_20260330.md

# 4. Check review queue status
python3 scripts/kb_review.py queue
```

---

## Requirements

- Python 3.7+
- `beautifulsoup4` (HTML parsing)
- `requests` (HTTP client)

### Installation

```bash
pip install beautifulsoup4 requests --break-system-packages
```

Both scripts will print installation instructions if dependencies are missing.

---

## Log Files

### _collection_log.txt

Appended log of all collection runs with timestamps:

```
2026-03-30 00:41:47 - INFO - Starting collection run
2026-03-30 00:41:50 - INFO - Fetching visa: https://visa.visitsaudi.com/
2026-03-30 00:41:51 - INFO - SAVED: knowledge-base/visa/auto_evisa_20260330.md
2026-03-30 00:42:12 - INFO - Updated frontmatter for auto_test_20260330.md
```

### _review_queue.md

Shows pending items with checkbox format:

```markdown
# Knowledge Base Review Queue

**Summary:** 5 file(s) pending human review

## Pending Items

- [ ] `visa/auto_evisa_20260330.md` — https://visa.visitsaudi.com/
- [ ] `transport/auto_saudia_20260330.md` — https://www.saudia.com/
- [ ] `finance/auto_sama_20260330.md` — https://www.sama.gov.sa/
```

---

## Typical Workflow

1. **Schedule collection**: Run `kb_collector.py` daily or weekly
2. **Review queue**: Check `_review_queue.md` for pending items
3. **Approve/promote**: Run `kb_review.py` to review each file
4. **Publish**: Approved files (confidence: medium/high) are ready for the site

---

## Notes

- The collector respects rate limits (1 second between requests)
- Failed requests timeout after 10 seconds
- Content extraction is smart about finding main content areas
- Diff detection prevents duplicate/minimal-change saves
- All operations are logged to `_collection_log.txt`
- Review queue is regenerated after each collection run

---

## Troubleshooting

### Script can't find beautifulsoup4/requests

```bash
pip install beautifulsoup4 requests --break-system-packages
```

### Files won't update with approve/promote

- Ensure the file path is correct (relative to knowledge-base/)
- Check file permissions
- View logs in `_collection_log.txt`

### Review queue is empty

Run `kb_collector.py` first to generate files:

```bash
python3 scripts/kb_collector.py
```

---

## Future Enhancements

- Scheduled collection using cron or task scheduler
- Email notifications for pending reviews
- Automated confidence scoring based on content quality
- Version history tracking
- Integration with CI/CD pipeline
