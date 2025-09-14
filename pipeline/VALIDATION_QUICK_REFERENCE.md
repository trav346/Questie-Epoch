# Database Precedence Validation - Quick Reference

## Essential Commands

### Complete Workflow (ALWAYS USE)
```bash
cd "Development Tools/GitHub Workflow"
source venv/bin/activate  # Activate virtual environment

# 1. Process quest submissions
python3 enhanced_process_submissions.py

# 2. MANDATORY: Validate before applying
python3 pipeline_validator.py

# 3. Review validation results
cat pipeline_validation_report.txt

# 4. Apply conflict resolution if conflicts found
python3 resolve_conflicts.py  # Only if validation detected conflicts

# 5. Apply to database
python3 apply_to_database.py
```

### Validation Only (Analysis)
```bash
# Check all database conflicts (one-time analysis)
python3 database_precedence_validator.py

# Validate specific ready-to-apply files
python3 pipeline_validator.py
```

## Interpreting Results

### ✅ Safe to Apply (No Action Needed)
```
OVERALL CONFLICT SUMMARY:
  No Conflicts: 15
  ID Conflicts: 0
  Name Conflicts: 0
  Manual Review Needed: 0

No other database entries need commenting - all clear!
```

### ⚠️ Conflicts Detected (Resolution Required)
```
OVERALL CONFLICT SUMMARY:
  No Conflicts: 12
  ID Conflicts: 3        <- ACTION REQUIRED
  Name Conflicts: 1      <- REVIEW NEEDED
  Manual Review Needed: 2 <- MANUAL ATTENTION

OTHER DATABASE ENTRIES THAT SHOULD BE COMMENTED:
  WOTLK DATABASE:
    Quest 783: 'A Threat Within'    <- Will be auto-resolved
  CLASSIC DATABASE:  
    Quest 783: 'A Threat Within'    <- Will be auto-resolved
```

**Action:** Run `python3 resolve_conflicts.py`

### 🚨 High Risk (Manual Review)
```
  Manual Review Needed: 5
```

**Action:** Review specific conflicts in report, may need manual database editing

## Common Scenarios

### Scenario 1: ID Conflicts (Most Common)
**Problem:** Epoch quest 26789 conflicts with vanilla quest 26789
**Solution:** Auto-generated script comments out vanilla entry
**Result:** Epoch version takes precedence

### Scenario 2: Name Conflicts  
**Problem:** Same quest name exists with different IDs
**Solution:** Manual review - usually different quests with similar names
**Action:** Verify quest content, may need renaming

### Scenario 3: No Conflicts
**Problem:** None
**Solution:** Proceed directly to database application
**Result:** Safe to apply

## File Locations

### Input Files
- `ready_to_apply/*.lua` - Processed quest files to validate

### Output Files  
- `pipeline_validation_report.txt` - Detailed validation results
- `resolve_conflicts.py` - Auto-generated resolution script (if conflicts)
- `database_conflicts_report.txt` - Complete database analysis

### Backup Files
- `*.backup_YYYYMMDD_HHMMSS` - Timestamped backups before resolution

## Safety Checklist

- [ ] Virtual environment activated
- [ ] Validation completed without errors
- [ ] Validation report reviewed
- [ ] Conflicts resolved if detected  
- [ ] Backup files created
- [ ] Complete WoW restart after database changes (not /reload)

## Emergency Recovery

### If Resolution Script Breaks Database
1. Stop WoW immediately
2. Restore from backup files:
   ```bash
   cp wotlkQuestDB.lua.backup_20250905_103045 wotlkQuestDB.lua
   cp classicQuestDB.lua.backup_20250905_103045 classicQuestDB.lua
   ```
3. Restart WoW and test
4. Re-run validation with smaller batches

### If Validation Fails
1. Check file paths and permissions
2. Verify database file integrity
3. Run standalone database validation
4. Contact development team if persistent issues

## Critical Numbers

- **Total Database Conflicts:** 4,249+ (expected)
- **Validation Time:** 30-60 seconds
- **Resolution Time:** 10-30 seconds  
- **Backup Space:** ~10-20MB per resolution

These numbers help distinguish normal operation from actual problems.