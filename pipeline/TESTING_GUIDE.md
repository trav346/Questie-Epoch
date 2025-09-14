# GitHub Pipeline Testing Guide

## Overview
This guide provides step-by-step testing procedures to safely validate the GitHub quest data processing pipeline before running it on production data.

## Test Phases

### Phase 1: Automated Test Suite (Safest)
Run the comprehensive test suite that uses isolated test environments:

```bash
python test_pipeline.py
```

This will:
- ✅ Create isolated copies of database files
- ✅ Test parsing without touching original data  
- ✅ Verify all components work together
- ✅ Clean up automatically when done

**Expected Output:**
```
🧪 Starting Pipeline Test Suite
==================================================

🔍 Running Database Copy...
[10:30:15] ✅ PASS: Database Copy - Copied 156789 chars

🔍 Running Database Parsing...
[10:30:16] ✅ PASS: Database Parsing - Parsed 580 entries, table=epochQuestData

🔍 Running GitHub Fetcher Dry Run...
[10:30:16] ✅ PASS: GitHub Fetcher - Would fetch 1 submissions

🔍 Running Submission Processing...
[10:30:17] ✅ PASS: Submission Processing - Created 2 update files

🔍 Running Database Application...
[10:30:18] ✅ PASS: Database Application - Applied 1 changes successfully

==================================================
📊 Test Results Summary:
  ✅ Database Copy
  ✅ Database Parsing  
  ✅ GitHub Fetcher Dry Run
  ✅ Submission Processing
  ✅ Database Application

🎯 Overall: 5/5 tests passed
🚀 All tests passed! Pipeline is ready for production.
```

---

### Phase 2: Manual Component Testing (More Control)

#### Step 2.1: Test Database Parsing Only
```bash
python -c "
from apply_to_database import DatabaseUpdater
updater = DatabaseUpdater()
entries, header, footer, table_name = updater.load_database(updater.db_files['quest'])
print(f'✅ Parsed {len(entries)} entries')
print(f'✅ Table name: {table_name}')
print(f'✅ Header length: {len(header)}')
print(f'✅ Footer length: {len(footer)}')
"
```

#### Step 2.2: Test GitHub Fetcher (Dry Run)
```bash
python -c "
from fetch_github_issues import GitHubIssueFetcher
fetcher = GitHubIssueFetcher()
print('Config loaded:', 'github_token' in fetcher.config)
print('Would fetch from:', fetcher.repo)
"
```

#### Step 2.3: Create Test Submissions
```bash
mkdir -p test_submissions
cat > test_submissions/issue_999.txt << 'EOF'
GitHub Issue #999
Title: Missing Quest: Test Quest (ID: 99999)
User: testuser
Created: 2024-01-01T10:00:00Z
============================================================

**Quest Data Collection Export**

**Version:** Questie v1.1.2
**Quest ID:** 99999
**Quest Name:** Test Quest
**Quest Level:** 25
**Zone:** Stranglethorn Vale

**Quest Giver:**
- NPC: Test Questgiver (ID: 12345)
- Location: Stranglethorn Vale (45.2, 67.8)

**Turn-in NPC:**
- NPC: Test Turnin (ID: 12346)
- Location: Stranglethorn Vale (44.8, 67.1)
EOF

echo "✅ Test submission created"
ls -la test_submissions/
```

#### Step 2.4: Test Processing (Safe)
```bash
# Backup original pending_submissions if it exists
if [ -d "pending_submissions" ]; then
    mv pending_submissions pending_submissions_backup
fi

# Use test data
mv test_submissions pending_submissions

# Run processor
python process_submissions.py

# Check results
echo "Generated files:"
ls -la ready_to_apply/

# Restore original
if [ -d "pending_submissions_backup" ]; then
    rm -rf pending_submissions
    mv pending_submissions_backup pending_submissions
fi
```

---

### Phase 3: Production Test (With Backups)

⚠️ **Only proceed if Phase 1 and 2 passed completely**

#### Step 3.1: Create Full Backup
```bash
# Create timestamped backup
BACKUP_DIR="database_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r ../../Database/Epoch/*.lua "$BACKUP_DIR/"
echo "✅ Full backup created at: $BACKUP_DIR"
```

#### Step 3.2: Test with Single Real Issue (Safest Production Test)

```bash
# Configure GitHub token first
cp config.json config.json.backup
nano config.json  # Add your GitHub token

# Fetch just 1 issue for testing
python -c "
from fetch_github_issues import GitHubIssueFetcher
import requests

fetcher = GitHubIssueFetcher()
issues = fetcher.fetch_issues()
print(f'Found {len(issues)} issues')

if issues:
    # Process just the first one
    first_issue = issues[0]
    print(f'First issue: #{first_issue[\"number\"]} - {first_issue[\"title\"]}')
    
    # Save just this one
    metadata = fetcher.save_submission(first_issue)
    print('✅ Saved single issue for testing')
else:
    print('No issues found - check labels and repo config')
"
```

#### Step 3.3: Process Single Issue
```bash
# Check what we downloaded
ls -la pending_submissions/
cat pending_submissions/manifest.json

# Process it
python process_submissions.py

# Review the processing report
ls -la ready_to_apply/processing_report_*.txt
cat ready_to_apply/processing_report_*.txt
```

#### Step 3.4: Apply to Database (Final Test)
```bash
# This will modify the actual database - make sure backup exists!
python apply_to_database.py --backup

# Check the results
echo "Database update complete. Check for errors above."

# Verify database integrity
python -c "
import re
with open('../../Database/Epoch/epochQuestDB.lua', 'r') as f:
    content = f.read()

# Check basic structure
if content.count('{') == content.count('}'):
    print('✅ Braces balanced')
else:
    print('❌ Braces unbalanced - RESTORE BACKUP!')
    
if 'QuestieDB._epochQuestData = epochQuestData' in content:
    print('✅ Footer intact')
else:
    print('❌ Footer missing - RESTORE BACKUP!')
    
# Count entries
entries = len(re.findall(r'^\[\d+\] =', content, re.MULTILINE))
print(f'✅ Found {entries} quest entries')
"
```

---

## Emergency Procedures

### If Tests Fail
1. **Stop immediately** - Don't proceed to next phase
2. Check the error messages in detail
3. Fix the underlying issue
4. Re-run tests from the beginning

### If Database Gets Corrupted
```bash
# Restore from backup (adjust path as needed)
cp database_backup_*/epochQuestDB.lua ../../Database/Epoch/
echo "✅ Database restored from backup"

# Verify restoration
python -c "
from apply_to_database import DatabaseUpdater
updater = DatabaseUpdater()
entries, _, _, _ = updater.load_database(updater.db_files['quest'])
print(f'✅ Verified: {len(entries)} entries loaded')
"
```

### If Git State Gets Messy
```bash
# Reset to last known good state
cd ../../
git status
git checkout -- Database/Epoch/epochQuestDB.lua
git clean -fd
echo "✅ Git state reset"
```

---

## Success Criteria

### Phase 1 (Automated Tests)
- [ ] All 5 tests pass
- [ ] No exceptions thrown
- [ ] Test environment auto-cleaned

### Phase 2 (Manual Components)  
- [ ] Database parsing finds 580+ entries
- [ ] No regex errors or malformed patterns
- [ ] Test submissions process correctly
- [ ] Generated .lua files have valid syntax

### Phase 3 (Production Test)
- [ ] Single issue downloads successfully
- [ ] Processing report shows valid quest data
- [ ] Database applies changes without syntax errors
- [ ] Backup verified and accessible

**Only proceed to full production run if ALL criteria pass!**

## Full Production Command (Final Step)
```bash
# Only run this after all tests pass
python run_pipeline.py --auto
```

This will:
1. Fetch all pending GitHub issues
2. Process quest data 
3. Apply to database with backup
4. Close processed issues
5. Purge files with audit logging

---

## Monitoring During Production Run

Watch for these outputs:
- ✅ `Found X issues to process`
- ✅ `Created processing report`  
- ✅ `Applied X changes successfully`
- ✅ `Purged X files`
- ✅ `Audit trail saved`

Stop immediately if you see:
- ❌ `Syntax validation failed`
- ❌ `Unbalanced braces`
- ❌ `Failed to apply updates`
- ❌ Any Python exceptions