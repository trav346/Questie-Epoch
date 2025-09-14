# ⚠️ EXPERIMENTAL PFQUEST CONVERSION

## Purpose
These tools are an **EXPERIMENT** to test whether pfQuest addon data can be converted to work with Questie format.

## Status: PROOF OF CONCEPT
- Not production-ready
- May produce incorrect or incomplete data
- Requires manual verification of converted data

## Why This Exists
The Questie-Epoch project needed more quest data. pfQuest is another popular quest helper addon with its own database. These scripts were created to explore if we could:
1. Extract data from pfQuest's Lua format
2. Convert it to Questie's structure
3. Merge it with existing Questie data

## Known Limitations
- pfQuest uses different zone IDs than Questie
- Coordinate systems may not align perfectly
- Quest chains and prerequisites may not convert correctly
- NPC faction data uses different encoding
- Some data fields have no equivalent between addons

## Before Using
1. **BACKUP YOUR DATABASE** - These tools modify existing data
2. Test on a copy first
3. Verify converted data in-game
4. Expect manual fixes to be needed

## Results So Far
Initial tests showed partial success:
- Basic quest data (names, levels) converts well
- NPC locations often need adjustment
- Quest objectives may be incomplete
- About 60-70% of data is usable after conversion

## Recommendation
Use these tools only if you:
- Understand both addon formats
- Can verify and fix data issues
- Have time to test thoroughly
- Are comfortable with experimental tools

This is a research project, not a finished solution!