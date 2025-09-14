# Lua Generation Issues Tracker

*Created: 2025-09-07*  
*Purpose: Track all Lua syntax issues, attempted fixes, and lessons learned*

## Critical Issues History

### Issue #0: DataAggregator Timeout with Full Dataset
**Date**: 2025-09-07
**Problem**: DataAggregator times out when processing all 1,320 submission files

**What Happened**:
- Processing 3 files works fine
- Processing 50 files works fine (6.2s total, 0.12s average per file)
- Processing 100 files works fine
- Processing all 1,320 files causes hang/timeout
- Individual file processing is fast (~0.02s to 0.6s per file)
- Python script hangs before even printing first line when trying to process all files

**Investigation Results**:
1. **Diagnostic tests successful**: 
   - 10 files: 2.06s total
   - 50 files: 6.2s total (8.3 files/sec)
   - Average: 0.12s per file
2. **Memory not the issue**: Small batches process fine repeatedly
3. **SQLite trackers likely culprit**: submission_tracker and state_tracker load 1290 quests + 1722 NPCs on init
4. **Streaming approach failed**: Script hangs on import, suggesting initialization issue

**Root Cause**: Likely the submission_tracker.db and state_tracker loading entire databases into memory during DataAggregator.__init__(), causing exponential slowdown with accumulated data

**Solution**: Batch processing with fresh aggregator instances

**Workaround**: Process in batches of 50-100 files with fresh aggregator per batch

---

### CRITICAL BUG: Zone Mapper Using Parent Zones Instead of Subzones
**Date**: 2025-09-07  
**Status**: ❌ BROKEN - MUST FIX

**The Problem**:
- Questie REQUIRES subzone IDs, not parent zone IDs
- Zone mapper is using parent zones (e.g., 85 for all of Tirisfal Glades)
- Should use subzone IDs (e.g., 159 for Brill, 154 for Deathknell)

**Example**:
- Historian Todd Page is in Brill at [60.6, 51.0]
- Pipeline gives zone 85 (Tirisfal Glades parent zone) ❌
- Should be zone 159 (Brill subzone) ✅

**Why This Matters**:
- NPCs won't appear on map with wrong zone IDs
- Quest markers won't show in correct locations
- Subzones are required for proper map display

**Known Subzones in Tirisfal Glades**:
- Deathknell (starting area): zone 154
- Brill (main town): zone 159  
- Undercity entrance: transitions to zone 1497

**Solution Needed**:
- Zone mapper must detect subzones from coordinates
- Use coordinate-based subzone detection
- Never use parent zone IDs when subzone exists

---

## Critical Issues History

### Issue #1: Regex Pattern Matching for Quest Replacement
**Date**: 2025-09-07  
**Problem**: Attempted to replace quest 26939 using regex pattern, resulted in malformed entry with 60+ fields

**What Happened**:
```lua
# Original quest 26939:
[26939] = {"Peace in Death",nil,nil,nil,1,nil,nil,{"[Needs data collection]"},nil,nil,nil,nil,nil,nil,nil,nil,1,nil,nil,nil,nil,nil,nil,0,nil,nil,nil,nil,nil,nil}, -- UPDATED 2025-09-06 with pipeline data

# After failed replacement:
[26939] = {"Plundering Pirates",{{46718},nil,nil},{{46718},nil},nil,60,nil,nil,{"Collect 8 Pirate Booty"},nil,{nil,nil,{{60385,8}},nil,nil,nil},nil,nil,nil,nil,nil,nil,14,nil,nil,nil,nil,nil,0,0,nil,nil,nil,nil,nil,nil},nil,nil,nil,nil,nil,nil,nil,nil,1,nil,nil,nil,nil,nil,nil,0,nil,nil,nil,nil,nil,nil}, -- UPDATED 2025-09-06 with pipeline data
```

**Error**: Line 409: unexpected symbol near '['

**Root Cause**: 
- Pattern `r'\[26939\]\s*=\s*\{[^}]+(?:\{[^}]*\}[^}]*)*\}'` didn't properly match the full entry
- It failed to include the trailing comment `-- UPDATED 2025-09-06 with pipeline data`
- The replacement APPENDED instead of REPLACED, leaving remnants of the old entry

**Attempted Fix #1**: Use more complex regex with comment matching
- **Result**: FAILED - Pattern too complex, still didn't match correctly

**Attempted Fix #2**: Use simple string operations instead of regex
- **Result**: SUCCESS - No regex, just line insertion

**Lesson Learned**: 
- Lua database entries are SINGLE LINES, not multi-line
- Each entry includes potential trailing comments that must be captured
- Regex patterns with nested braces are extremely error-prone
- AVOID REGEX for Lua database modifications

---

### Issue #2: Field Count Validation Confusion
**Date**: 2025-09-07  
**Problem**: Validation showed 42 fields when expecting 30

**What Happened**:
- Generated: `[99001] = {"Quest",{{100},nil,nil},{{200},nil},...}`
- Field count validation showed 42 commas instead of expected 30

**Root Cause**:
- Was counting ALL commas including those inside nested structures
- `{{100},nil,nil}` contains 2 internal commas that shouldn't count toward field total

**Analysis**:
```
Correct counting for epochQuestDB entries:
- 30 fields total
- 29 commas BETWEEN fields
- 1 trailing comma after closing brace
- Do NOT count commas inside nested structures like {{100},nil,nil}
```

**Fix Applied**: 
- Recognized that the generation was actually CORRECT
- The "extra" commas were from valid nested structures
- No fix needed, just understanding

**Validation Method**:
1. Count only top-level commas (between main fields)
2. Verify exactly 30 fields present
3. Check for trailing comma after closing brace
4. Ensure no comma after field 30 (inside the brace)

---

### Issue #3: String Escaping
**Date**: 2025-09-07  
**Problem**: Quotes in quest names and objectives breaking Lua syntax

**Patterns That Work**:
```lua
# CORRECT:
"Quest with \"Quotes\""  -- Escaped with backslash
"Bob's Quest"            -- Apostrophes don't need escaping
{"Find the \"Ancient\" Artifact"}  -- Escaped in tables too

# WRONG:
"Quest with "Quotes""    -- Unescaped quotes break syntax
```

**Escaping Function That Works**:
```python
def _escape_lua_string(self, s: str) -> str:
    if s is None:
        return ""
    s = s.replace('\\', '\\\\')  # Escape backslashes FIRST
    s = s.replace('"', '\\"')    # Then escape quotes
    s = s.replace('\n', '\\n')   # Newlines
    s = s.replace('\r', '\\r')   # Carriage returns
    return s
```

**Critical**: Must escape backslashes FIRST, before escaping quotes

---

### Issue #4: Comma Placement Rules
**Date**: 2025-09-07  
**Problem**: Incorrect comma placement causing Lua errors

**Rules Discovered**:
1. **Between fields**: Comma after each field EXCEPT the last
2. **After quest entry**: Comma after closing brace (unless last entry in database)
3. **Inside tables**: Normal comma rules apply
4. **Last field**: NO comma after field 30

**Correct Format**:
```lua
[12345] = {field1,field2,field3,...,field30},  -- Comma after brace
[12346] = {field1,field2,field3,...,field30}   -- NO comma if last entry
```

**Common Mistakes**:
- Trailing comma after field 30: `...,nil,nil,}`  ❌
- No comma between entries: `}[next]`  ❌
- Double commas: `nil,,nil`  ❌

---

### Issue #5: Variable Name Confusion
**Date**: 2025-09-07  
**Problem**: Database variable name doesn't match filename

**Critical Discovery**:
- **File name**: `epochQuestDB.lua`
- **Variable inside**: `epochQuestData = { ... }`
- **Wrong command**: `/dump epochQuestDB[99001]` ❌
- **Correct command**: `/dump epochQuestData[99001]` ✅

**Impact**: 
- Wasted time debugging "nil" errors
- Test commands failing unnecessarily
- Confusion in documentation

**Lesson Learned**:
- ALWAYS verify the actual variable name in the file
- Don't assume filename matches variable name
- Check with: `head -50 epochQuestDB.lua | grep "^[a-zA-Z]"`

---

## Validation Checklist

Before applying ANY database changes:

### 1. Entry Structure
- [ ] Each quest on a SINGLE line
- [ ] Exactly 30 fields (29 commas between them)
- [ ] Trailing comma after closing brace (except last entry)
- [ ] No trailing comma after field 30

### 2. String Escaping
- [ ] All quotes escaped with \"
- [ ] Backslashes escaped with \\
- [ ] No unescaped quotes in any field

### 3. Nested Structures
- [ ] startedBy format: `{{npcs},{objects},{items}}` or `nil`
- [ ] finishedBy format: `{{npcs},{objects}}` or `nil`
- [ ] objectives format: `{{creatures},{objects},{items},nil,nil,nil}` or `nil`

### 4. Testing Protocol
- [ ] Generate 3-5 test entries first
- [ ] Manually verify format matches existing entries
- [ ] Test in-game with /reload
- [ ] Check for Lua errors
- [ ] Verify with /dump epochQuestDB[questId]

---

## Safe Approach (What Works)

### DO:
1. Use simple string operations for insertion
2. Find closing brace and insert before it
3. Test with 3-5 quests first
4. Create backups before EVERY change
5. Verify brace balance after changes

### DON'T:
1. Use regex for replacing existing entries
2. Try to match nested Lua structures with regex
3. Assume multi-line format
4. Forget trailing comments
5. Process more than 5 quests without testing

---

## Current Pipeline Status

### Fixed Issues:
- ✅ String escaping function implemented correctly
- ✅ Single-line format generation
- ✅ Proper field structure (30 fields)
- ✅ Simple insertion method (no regex)

### Remaining Concerns:
- ⚠️ Replacing existing entries still risky
- ⚠️ Need to handle comments in existing entries
- ⚠️ Large-scale processing untested

### Next Steps:
1. Test the 3 added quests in-game
2. If successful, process 10 more quests
3. If those work, process 50 quests
4. Finally, run full pipeline

---

## Test Results Log

### Test Run #1 (2025-09-07 08:44)
- **Action**: Attempted to replace quest 26939 and add 4 new quests
- **Method**: Regex replacement
- **Result**: FAILED - Lua error line 409
- **Issue**: Malformed quest entry with 60+ fields

### Test Run #2 (2025-09-07 08:51)
- **Action**: Added 3 test quests (99001, 99002, 99003)
- **Method**: Simple string insertion
- **Result**: PARTIAL - Quests added to file but not accessible in-game
- **Verification**: Brace balance OK (3707/3707)
- **Issue**: epochQuestDB is nil when trying to access in-game

### Test Run #3 (2025-09-07 08:55)
- **Action**: Attempted /dump epochQuestDB[99001]
- **Result**: FAILED - "attempt to index global 'epochQuestDB' (a nil value)"
- **Analysis**: WRONG VARIABLE NAME
- **Root Cause**: The database is called `epochQuestData` NOT `epochQuestDB`!

### CRITICAL DISCOVERY (2025-09-07 09:00)
- **Issue**: Was using wrong variable name all along
- **Correct name**: `epochQuestData` (not epochQuestDB)
- **File name**: `epochQuestDB.lua` (confusing!)
- **Variable inside**: `epochQuestData = { ... }`
- **Correct test command**: `/dump epochQuestData[99001]`

### Test Run #4 (2025-09-07 09:05)
- **Action**: Test quests with CORRECT variable name
- **Result**: ✅ SUCCESS - Quest data loaded correctly!
- **Test output for quest 99001**:
```lua
[1]="Test Quest One",          -- Name
[2]={{100}},                   -- startedBy (NPC 100)
[3]={{200}},                   -- finishedBy (NPC 200)
[5]=1,                         -- questLevel
[17]=1,                        -- zoneOrSort
[23]=0,                        -- questFlags
[24]=0                         -- specialFlags
```
- **Analysis**: Lua only shows non-nil fields in dump (expected behavior)
- **Validation**: All fields present and correctly formatted

### Test Run #5 (2025-09-07 09:10)
- **Action**: Test all 3 quests for different edge cases
- **Result**: ✅ COMPLETE SUCCESS - All features working!

**Quest 99002 - String Escaping Test**:
- ✅ Quotes properly escaped: `"Quest with \"Quotes\""`
- ✅ Objectives text with escaping works: `"Find the \"Ancient\" Artifact"`

**Quest 99003 - Complex Objectives Test**:
- ✅ Multiple objectives text entries work
- ✅ Creature objectives with count and name: `{1001, 10, "Wolf"}`
- ✅ Item objectives: `{2001, 5}`
- ✅ Nested table structure preserved correctly
- ⚠️ Field [6]=77 unexpected (should investigate)

**VALIDATION**: Pipeline Lua generation is WORKING CORRECTLY!

### Test Run #6 (2025-09-07 09:01)
- **Action**: Add 9 real quests from pipeline data
- **Method**: Using database_writer_v2 from pipeline
- **Quests Added**:
  - 28373: The Rite of the Medicant (new)
  - 27559: Quality Reagents (new)
  - 26332: Plundering Pirates (runtime stub replacement)
  - 27580: Shadow of the Vilehorn (missing objectives)
  - 27303: Containing the Contamination (missing NPCs)
  - 28462: Commission for Tok'Kar
  - 28723: Thievin' Crabs (has creature objectives)
  - 26126: Springsocket Eels (has item objectives)
  - 27307: The Shrine of the Deceiver
- **Result**: ✅ SUCCESS - Real quests loading correctly!
- **Backup**: epochQuestDB_backup_10real_20250907_090113.lua

**Quest 28373 Test**:
- ✅ Name loaded: "The Rite of the Medicant"
- ✅ Levels correct: requiredLevel=60, questLevel=60
- ⚠️ No NPCs (data might be missing in pipeline)

**Quest 26332 Test** (Runtime stub replacement):
- ✅ Name loaded: "Plundering Pirates" (no longer shows [Epoch] prefix!)
- ✅ Quest giver: NPC 3453
- ✅ Multiple turn-in NPCs: 11063, 1284, 9023
- ✅ Zone 139 (Eastern Plaguelands)
- ✅ Successfully replaced runtime stub!

**READY FOR FULL PIPELINE RUN!**

### FULL PIPELINE RUN (Generated 2025-09-07 09:51)
- **Action**: Processed all 1,127 quests from pipeline
- **Method**: database_writer_v2 with single-line generation
- **Result**: ❌ CRITICAL ISSUE - Created 602 duplicate entries
- **Backup**: epochQuestDB_FULL_PIPELINE_1127_quests_20250907_095158.lua
- **Report**: FULL_PIPELINE_REPORT_20250907_095158.txt
- **Issue**: Pipeline blindly appended ALL quests without checking for existing entries
- **Impact**: 602 quests already in database were duplicated, old data still used

### Issue #6: Duplicate Quest Entries (2025-09-07 10:00)
- **Problem**: Pipeline created 602 duplicate quest entries
- **Example**: Quest 26927 existed twice - old placeholder and new data
- **Root Cause**: `run_full_pipeline.py` used simple `.insert()` without deduplication logic
- **Analysis**:
  - Pipeline had 1,127 quests
  - Database had 763 existing quests
  - Overlap: 602 quests existed in BOTH
  - Result: 602 duplicates created
- **Why Critical**: Lua uses FIRST occurrence, so new data ignored

### Solution Developed: Intelligent Merge System (2025-09-07 11:00)
- **Components Created**:
  1. `QuestScorer` - Scores quest completeness (0-100 points)
  2. `intelligent_database_merger.py` - Analyzes and creates merge plan
  3. `deduplicate_database.py` - Removes existing duplicates
  4. `apply_intelligent_merge.py` - Applies intelligent merging

**Scoring System**:
- Name quality: 20 points (not placeholder)
- NPC data: 20 points (quest giver + turn-in)
- Objectives: 30 points (real objectives, not placeholder)
- Zone data: 15 points (valid zone, not 85)
- Level data: 15 points (quest level + required level)

**Merge Logic**:
- If pipeline score > database score: REPLACE
- If scores equal: MERGE fields
- If database score > pipeline: SKIP
- Special: "[Needs data collection]" → ALWAYS REPLACE

### Deduplication Analysis (2025-09-07 11:30)
- **Found**: 7 pre-existing duplicates in restored database
- **Duplicates from test runs**:
  - 26126: Springsocket Eels
  - 26332: Plundering Pirates  
  - 27303: Containing the Contamination
  - 27307: The Shrine of the Deceiver
  - 27580: Shadow of the Vilehorn
  - 28462: Commission for Tok'Kar
  - 28723: Thievin' Crabs
- **Deduplication keeps highest scoring entry**

### Intelligent Merge Plan Results (2025-09-07 11:45)
- **Analysis of 1,127 pipeline quests**:
  - ➕ Add new: 525 quests (don't exist in DB)
  - 🔄 Replace: 566 quests (placeholders/inferior data)
  - 🔀 Merge fields: 36 quests (combine best of both)
  - ⏭️ Skip: 0 quests (none where DB is better)
- **No duplicates will be created with new system**

### FULL PIPELINE RUN (Generated 2025-09-07 10:59)
- **Action**: Processed all 1,127 quests from pipeline
- **Method**: database_writer_v2 with single-line generation
- **Result**: PENDING TEST
- **Backup**: epochQuestDB_FULL_PIPELINE_1127_quests_20250907_105937.lua
- **Report**: FULL_PIPELINE_REPORT_20250907_105937.txt
- **Categories**:
  - New: 0
  - Runtime stubs: 0
  - With objectives: 1,127
  - With NPCs: 0

---

## Code Snippets That Work

### Simple Quest Insertion (WORKING):
```python
# Find closing brace
for i in range(len(lines) - 1, -1, -1):
    if lines[i].strip() == '}':
        insert_line = i
        break

# Insert before closing brace
for quest in test_quests:
    lines.insert(insert_line, quest + '\n')
    insert_line += 1
```

### Lua Entry Format (VERIFIED):
```lua
[questId] = {"Name",startedBy,finishedBy,reqLevel,questLevel,reqRaces,reqClasses,objectives,trigger,objectiveData,sourceItem,preGroup,preSingle,childQuests,inGroup,exclusive,zone,skill,minRep,maxRep,sourceItems,nextQuest,questFlags,specialFlags,parentQuest,repReward,extraObj,reqSpell,reqSpec,maxLevel},
```

---

## Debugging Commands

### In-Game Testing:
```lua
/reload                          -- Reload UI
/dump epochQuestData[99001]     -- Check if quest exists (NOTE: epochQuestData, NOT epochQuestDB!)
/questie journey 99001          -- Open quest in Questie
/console scriptErrors 1         -- Enable Lua error display
```

**CRITICAL**: The variable is `epochQuestData` not `epochQuestDB` despite the filename!

### File Verification:
```bash
# Count quests in database
grep -c "^\[" epochQuestDB.lua

# Check specific quest
grep "^\[99001\]" epochQuestDB.lua

# Verify brace balance
echo "Open: $(grep -o '{' epochQuestDB.lua | wc -l), Close: $(grep -o '}' epochQuestDB.lua | wc -l)"
```

---

## Memory Notes

**REMEMBER**: 
- Every time we modify the database, we're dealing with 700+ existing quests
- One malformed entry breaks the ENTIRE database
- Test with 3, then 10, then 50, then all
- Regex and Lua nested structures DO NOT MIX WELL
- When in doubt, use simple string operations

### CRITICAL DISCOVERY: Database Architecture Issue (2025-09-07 13:30)

**Issue #7: Fundamental Database Loading Architecture Problem**
- **Discovery**: Attempted to disable Classic DB and enable WotLK DB
- **Result**: Complete addon failure with nil reference errors
- **Root Cause**: Database loading architecture fundamentally broken

**What We Found**:
1. **Classic database MUST be loaded** - It initializes core data structures:
   - Sets `QuestieDB.npcData = [[return {`
   - Sets `QuestieDB.questData = [[return {`
   - Sets `QuestieDB.itemData = [[return {`
   - Sets `QuestieDB.objectData = [[return {`

2. **WotLK databases are incompatible**:
   - Don't set `QuestieDB.npcData` at all
   - Use different format (direct table vs string)
   - Were never properly integrated
   - Comments say "Disabled: Project Epoch is Vanilla only" (WRONG!)

3. **Database precedence is broken**:
   - Classic DB provides fallback data even when wrong
   - Example: NPC 1499 (Magistrate Sevren) overrides Epoch data
   - Can't disable Classic without breaking entire addon
   - Can't enable WotLK without refactoring

**Impact**:
- Quest 26927 shows wrong turn-in NPC (Classic's 1499 instead of Epoch's 45886)
- Can't achieve proper Epoch → WotLK → (no Classic) hierarchy
- Classic flag values (wrong for 3.3.5) contaminate data
- 602 replaced quests may still use Classic fallback data

**Technical Details**:
```lua
-- Classic format (REQUIRED for addon to work):
QuestieDB.npcData = [[return {
[1] = {"NPC Name", ...},
...
}]]

-- WotLK format (INCOMPATIBLE):
[1] = {"NPC Name", ...},
-- No QuestieDB.npcData assignment!
```

**Error When Classic Disabled**:
```
1x ...ns\Questie\Database\Corrections\AutoTableUpdates.lua:435: 
attempt to index field '?' (a nil value)
-- QuestieDB.npcData is nil because Classic didn't initialize it
```

**Required Fix**:
1. Refactor database loading to not depend on Classic
2. Convert WotLK databases to proper format
3. OR create initialization module separate from Classic
4. OR completely fork for Project Epoch without Classic

**Workaround (Current)**:
- Keep Classic enabled (causes data conflicts)
- Manually fix conflicts case-by-case
- Live with wrong NPC flags and fallback data

---

### Issue #8: Pipeline Failed to Capture NPC Quest Linkage (2025-09-07 14:00)

**CRITICAL FAILURE**: Pipeline processed 1,505 NPCs but captured ZERO quest linkage data!

**Discovery**:
- Quest 26927 wouldn't show Historian Eva (45886) as turn-in NPC
- Investigation revealed NPC 45886 had `questEnds: {}` (empty)
- Submissions clearly showed `questEnds: {26927}`
- Pipeline output shows ALL NPCs have empty questStarts/questEnds

**Impact**:
- **1,505 NPCs** added without quest linkage
- NPCs won't appear as quest givers on map
- NPCs won't show quest turn-in indicators
- Quest chains broken due to missing NPC connections

**Evidence**:
```json
// What submissions provided:
[45886] = {"Historian Eva",nil,nil,9,9,0,{...},nil,85,nil,{26927},nil,nil,nil,0}
                                                         ^^^^^^^^ questEnds

// What pipeline produced:
"questStarts": [],  // EMPTY!
"questEnds": [],    // EMPTY!
```

**Root Cause Analysis**:
- NPC parser modules don't extract questStarts/questEnds from submissions
- Data aggregator doesn't parse the NPC database entries properly
- The `[45886] = {...}` format isn't being parsed for positions 10 & 11

**Immediate Fix Applied**:
- Manually fixed NPC 45886: Added `{26927}` to questEnds, set npcFlags to 2

**Required Pipeline Fix**:
1. Update NPC parser to extract questStarts (position 10) and questEnds (position 11)
2. Re-run pipeline on all 1,127 submissions
3. Update all 1,505 NPCs with correct quest linkage

**Verification**:
```python
# Check pipeline NPCs with quest data:
Total NPCs in pipeline: 1505
NPCs with quest data: 0  # SHOULD NOT BE ZERO!
```

---

### Issue #9: Data Aggregator Discards NPC Quest Linkage (2025-09-07 15:30)

**THE REAL BUG FOUND**: NPC parser works correctly, but aggregator throws away the data!

**Discovery Process**:
1. NPC parser correctly extracts questStarts/questEnds from TURN-IN NPC sections
2. Parser returns: `NPCInfo(...questEnds=[26927]...)`  ✅
3. Aggregator calls `_create_npc_entry()` which hardcodes:
   ```python
   'questStarts': [],  # ALWAYS EMPTY!
   'questEnds': [],    # ALWAYS EMPTY!
   ```
4. All quest linkage data is discarded!

**Why This Happened**:
- `_create_npc_entry()` was written to create a blank template
- It never extracts questStarts/questEnds from the parsed NPCInfo objects
- The NPCInfo objects have the data but it's ignored

**Fix Required**:
```python
# WRONG (current):
'questStarts': [],
'questEnds': [],

# RIGHT (should be):
'questStarts': npc_info.quest_starts if hasattr(npc_info, 'quest_starts') else [],
'questEnds': npc_info.quest_ends if hasattr(npc_info, 'quest_ends') else [],
```

**Additional Logic Needed**:
- When same NPC appears in multiple quests, MERGE the arrays
- Don't overwrite, ACCUMULATE: `existing_starts + new_starts`
- Deduplicate: `list(set(existing + new))`

---

**Last Updated**: 2025-09-07 15:30
**Next Action**: Fix _create_npc_entry and _aggregate_npcs to preserve and merge quest linkage data