# ⚠️ PIPELINE DISCLAIMER - PLEASE READ

## Status: EXPERIMENTAL / WORK IN PROGRESS

This pipeline is **NOT a finished product**. It's a collection of tools developed for the Questie-Epoch project to help process community-submitted quest data.

## Known Issues & Limitations

### Data Quality
- **False Objectives**: The pipeline may capture 10-20x more objectives than actually exist
- **Zone Mapping**: Some zones are incorrectly identified (e.g., Zone 85 bug)
- **NPC Data Loss**: Approximately 35% of NPC data doesn't make it to the final database
- **Coordinate Accuracy**: GPS coordinates from player submissions can be inaccurate

### Technical Issues
- **String Escaping**: Unescaped special characters can cause Lua syntax errors
- **Memory Issues**: Processing 1000+ files may cause timeouts or crashes
- **Path Dependencies**: Hardcoded paths need manual configuration
- **Incomplete Validation**: Not all data is properly validated before insertion

### Process Issues
- **Manual Review Required**: Low-confidence data needs human verification
- **No Rollback**: Changes are permanent unless you have backups
- **Merge Conflicts**: May overwrite existing correct data with incorrect submissions
- **Version Mismatch**: Designed for WotLK 3.3.5a, may not work with other versions

## Before Using This Pipeline

### MANDATORY Steps:
1. **BACKUP YOUR DATABASE** - Cannot stress this enough!
2. **Test on a copy** - Never run on your live addon first
3. **Review output** - Check generated Lua files before applying
4. **Start small** - Process a few submissions before doing bulk operations
5. **Verify in-game** - Test changes in WoW before distributing

### You Should:
- Understand Lua syntax basics
- Know how Questie database structure works
- Be comfortable with command-line tools
- Have time to verify and fix issues
- Be prepared to restore from backup

## Success Rate

Based on testing:
- **Quest Names/Levels**: ~98% accurate
- **Quest Objectives**: ~60-70% accurate (many false positives)
- **NPC Locations**: ~65% make it through
- **Overall Usability**: ~70% of processed data is usable

## Why This Exists

Project Epoch has 1,300+ custom quests not in standard databases. This pipeline was created to:
- Crowdsource quest data from players
- Automate the tedious parts of data entry
- Build a community database

It's a tool born from necessity, not a polished product.

## Recommendations

### Good Use Cases:
✅ Processing quest submissions for Project Epoch
✅ Learning how quest data extraction works
✅ Building upon for your own tools
✅ Contributing improvements back to the project

### Bad Use Cases:
❌ Production use without modifications
❌ Processing data for other WoW versions without testing
❌ Expecting perfect results without manual review
❌ Using without understanding the risks

## Support

This is provided AS-IS with no warranty. The original developer has moved on from the project. Use at your own risk and:
- Expect to fix issues yourself
- Don't expect regular updates
- Consider it a starting point, not a solution

## Alternative

If you need reliable quest data, consider:
- Manual data entry (more accurate)
- Using established databases
- Waiting for a more mature solution
- Contributing to improve this pipeline

---

**Remember**: This tool can help, but it can also harm your database. Respect the experimental nature and always protect your data with backups!