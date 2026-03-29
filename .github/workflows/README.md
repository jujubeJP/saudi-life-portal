# GitHub Actions Workflows

This directory contains automated workflows that help manage the Saudi Navi knowledge base and content collection.

## Available Workflows

### 1. Collect Content (`collect-content.yml`)

**Purpose**: Automatically collect and process content for the knowledge base.

**Schedule**:
- Every day at 13:30 JST (10:30 UTC) - After morning prayer
- Every day at 19:00 JST (16:00 UTC) - After evening prayer
- Can be manually triggered

**What it does**:
1. Checks out the repository
2. Sets up Python 3.12
3. Installs dependencies (pdfplumber)
4. Runs the content collection script
5. Automatically commits and pushes changes if new content is found

**Permissions**: Write access to contents (for committing changes)

**Manual Trigger**: Go to Actions > Collect Content > Run workflow

---

### 2. KB Review Check (`kb-review-check.yml`)

**Purpose**: Periodically check for knowledge base files that are due for review and create tracking issues.

**Schedule**:
- Every Monday at 9:00 AM JST (Sunday 0:00 UTC)
- Can be manually triggered

**What it does**:
1. Checks out the repository
2. Sets up Python 3.10
3. Installs dependencies (pyyaml)
4. Runs the KB expiry check script (`scripts/kb_check_expiry.py`)
5. Parses the results to identify expired or expiring files
6. Closes any previous open KB review issues (to avoid duplicates)
7. Creates a new GitHub issue with:
   - A checklist of all files that need review
   - File path, topic, last checked date, and review deadline for each file
   - Direct links to each file in the repository
   - Clear instructions on how to mark files as reviewed

**Permissions**: Read access to contents, Write access to issues (for creating/closing issues)

**Manual Trigger**: Go to Actions > KB Review Check > Run workflow

**Review Process**:
- Open the generated issue to see which files need review
- Click the links to view each file
- Verify the content is accurate and up-to-date
- Update the `verified_date` in the file's frontmatter to the current date
- Check the checkbox next to the file in the issue

---

## File Format

Knowledge base files use YAML frontmatter with the following fields:

```yaml
---
source: "Source of information"
verified_date: "YYYY-MM-DD"
confidence: "high|medium|low"
verified_by: "username or auto"
notes: "Any relevant notes"
review_by: "YYYY-MM-DD"  # Optional: when to review by
---

# Content starts here
```

---

## Related Scripts

- `scripts/collect_content.py` - Collects and processes content from various sources
- `scripts/kb_check_expiry.py` - Checks for KB files that need review (outputs JSON)
- `scripts/kb_review.py` - Interactive tool for manually reviewing and approving KB files
- `scripts/kb_collector.py` - Handles KB file organization and metadata

---

## Troubleshooting

**Issue: Workflow fails to run**
- Check that the required scripts exist in the `scripts/` directory
- Verify Python dependencies are correctly specified (pyyaml, pdfplumber)
- Check workflow logs for specific error messages

**Issue: Issues not being created**
- Ensure `GITHUB_TOKEN` is available (automatically provided by GitHub)
- Check that the KB check script outputs valid JSON
- Verify the `kb-review` label exists in the repository

**Issue: Cron schedule not triggering**
- GitHub Actions cron schedules run in UTC timezone
- 9:00 AM JST = 0:00 UTC (Sunday night/Monday morning)
- Workflows must be in the default branch to be scheduled

---

## Monitoring and Logs

- View workflow runs: Go to repository > Actions tab
- View workflow logs: Click on a workflow run > Click a job > View logs
- Check commits from workflows: Look for commits by `github-actions[bot]`

---

## Configuration

To modify workflow schedules or behavior:
1. Edit the relevant `.yml` file
2. Update the `cron` expression if changing the schedule (uses UTC)
3. Commit and push to the default branch
4. Changes take effect immediately

For cron syntax help: https://crontab.guru/

---

## Permissions Reference

| Workflow | Contents | Issues | Notes |
|----------|----------|--------|-------|
| Collect Content | write | - | Commits changes to repo |
| KB Review Check | read | write | Creates issues, closes old ones |
