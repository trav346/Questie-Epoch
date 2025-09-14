# pfQuest to Questie Conversion Tools

These tools convert pfQuest database format to Questie format for WoW 3.3.5a (WotLK).

## ⚠️ IMPORTANT NOTE - EXPERIMENTAL TOOLS

**These scripts are provided to TEST if pfQuest data is compatible with Questie format.**

This is an experiment to see if data from the competing pfQuest addon can be successfully converted and used in Questie. The conversion may not work perfectly due to:

- **Different data structures** - pfQuest and Questie organize data differently
- **Version mismatches** - pfQuest data may be from Classic/Vanilla while Questie expects WotLK
- **Incomplete mappings** - Not all pfQuest fields have Questie equivalents
- **Coordinate differences** - Zone IDs and coordinate systems may differ
- **Data quality** - pfQuest data may have different accuracy standards

**ALWAYS backup your Questie database before attempting any conversion!**

## Overview

pfQuest is another quest helper addon with its own database format. These scripts extract data from pfQuest and attempt to convert it to Questie's database structure.

## Scripts

### convert_all_pfquest.py
Converts pfQuest quest, NPC, item, and object data to Questie format.

**Usage:**
```bash
python convert_all_pfquest.py --input pfquest_db.lua --output questie_db.lua
```

**Features:**
- Extracts quest levels, requirements, and objectives
- Converts NPC spawn locations and quest associations
- Maps item and object data
- Handles coordinate format conversion

### merge_databases.py
Merges converted pfQuest data with existing Questie database.

**Usage:**
```bash
python merge_databases.py --base questie_db.lua --new pfquest_converted.lua --output merged.lua
```

**Features:**
- Additive merging (doesn't overwrite existing data)
- Conflict detection and reporting
- Validates data integrity

## Data Structure Mapping

### pfQuest Format:
```lua
[questId] = {
  ["lvl"] = questLevel,
  ["min"] = minLevel,
  ["start"] = { ["U"] = {npcIds} },
  ["end"] = { ["U"] = {npcIds} },
  ["obj"] = { ["U"] = {}, ["I"] = {} }
}
```

### Questie Format:
```lua
[questId] = {
  name,           -- 1
  startedBy,      -- 2: {{npcIds},{objectIds},{itemIds}}
  finishedBy,     -- 3: {{npcIds},{objectIds}}
  requiredLevel,  -- 4
  questLevel,     -- 5
  -- ... up to 30 fields
}
```

## Notes

- pfQuest uses different zone IDs than Questie - conversion handles mapping
- Coordinates are percentage-based in both formats
- Some pfQuest data may not have Questie equivalents
- Always backup your database before merging

## Requirements

- Python 3.8+
- pfQuest database files (usually in pfQuest addon folder)
- Questie database structure knowledge

## See Also

- README.md - Original conversion notes
- ../README.md - Main pipeline documentation