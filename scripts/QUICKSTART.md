# Quick Start Guide

## Installation

Ensure dependencies are installed:

```bash
pip install beautifulsoup4 requests --break-system-packages
```

## Basic Usage

### 1. Collect Content

Fetch the latest content from all sources:

```bash
python3 scripts/kb_collector.py
```

This will:
- Visit all 7 categories of sources
- Extract key content
- Save files to `knowledge-base/[category]/auto_[topic]_[date].md`
- Create/update `knowledge-base/_review_queue.md`
- Log all activity to `knowledge-base/_collection_log.txt`

### 2. Review & Approve

Start interactive review:

```bash
python3 scripts/kb_review.py
```

For each file, you can:
- **approve** (a) — Mark as verified (medium confidence)
- **promote** (p) — Mark as high confidence
- **reject** (r) — Delete the file
- **skip** (s) — Review later
- **quit** (q) — Exit

### 3. Specific Category

Collect only visa-related content:

```bash
python3 scripts/kb_collector.py --category visa
```

Available categories: visa, transport, telecom, finance, safety, medical, general

### 4. Dry Run

Preview what would be collected without saving:

```bash
python3 scripts/kb_collector.py --dry-run
```

### 5. Command-Line Approvals

Approve or promote files directly:

```bash
python3 scripts/kb_review.py approve visa/auto_evisa_20260330.md
python3 scripts/kb_review.py promote transport/auto_metro_20260330.md
python3 scripts/kb_review.py reject finance/auto_sama_20260330.md
```

## Key Features

✓ **7 source categories** with 14+ official URLs
✓ **Smart diff detection** — only saves meaningful changes
✓ **YAML frontmatter** — includes source, date, confidence level
✓ **Rate limiting** — respects server resources (1s between requests)
✓ **Error handling** — graceful timeouts and failures
✓ **Review queue** — tracks all pending files
✓ **Logging** — complete audit trail in `_collection_log.txt`

## File Structure

```
knowledge-base/
├── visa/
│   ├── evisa-requirements_20260330.md (manual)
│   └── auto_evisa_20260330.md (auto-collected)
├── transport/
│   └── auto_saudia_20260330.md
├── telecom/
├── finance/
├── safety/
├── medical/
├── general/
├── _review_queue.md (auto-generated)
└── _collection_log.txt (auto-generated)
```

## Understanding Confidence Levels

| Level | Status | Next Step |
|-------|--------|-----------|
| low | Auto-collected, unreviewed | Run `kb_review.py approve` |
| medium | Approved by human | Ready for publication |
| high | Verified & trusted | Featured content |

## Example Workflow

```bash
# 1. Collect new content
python3 scripts/kb_collector.py

# Check what was collected:
cat knowledge-base/_review_queue.md

# 2. Review interactively
python3 scripts/kb_review.py

# 3. Or approve specific files
python3 scripts/kb_review.py approve visa/auto_evisa_20260330.md
python3 scripts/kb_review.py promote transport/auto_metro_20260330.md

# 4. Check logs
tail knowledge-base/_collection_log.txt
```

## Tips & Tricks

- **Dry runs first**: Use `--dry-run` to test without saving
- **Single category**: Collect only one category with `--category`
- **Schedule it**: Set up a cron job to run collection daily
- **Log monitoring**: Check `_collection_log.txt` for issues
- **Review queue**: Always check `_review_queue.md` before approving

## Troubleshooting

**"Required packages not found"**
→ Run: `pip install beautifulsoup4 requests --break-system-packages`

**"Connection errors on all URLs"**
→ Normal in sandboxed environments; real deployment will work

**"Review queue is empty"**
→ Run `kb_collector.py` first to generate files

**"File not found error"**
→ Use relative paths from `knowledge-base/` directory

---

For detailed documentation, see [KB_COLLECTOR_README.md](KB_COLLECTOR_README.md)
