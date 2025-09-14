#!/usr/bin/env python3

import re
from datetime import datetime

def parse_questie_db(filepath):
    """Parse existing Questie database"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    quests = {}
    
    # Extract quest entries
    pattern = r'\[(\d+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
    
    for match in re.finditer(pattern, content):
        quest_id = int(match.group(1))
        quest_data = match.group(2)
        
        # Extract quest name (first field)
        name_match = re.search(r'^"([^"]+)"', quest_data)
        if name_match:
            quests[quest_id] = {
                'name': name_match.group(1),
                'raw': '{' + quest_data + '}'
            }
    
    return quests

def parse_converted_db(filepath):
    """Parse converted pfQuest database"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    quests = {}
    
    # Extract quest entries
    pattern = r'\[(\d+)\]\s*=\s*(\{[^}]+(?:\{[^}]*\}[^}]*)*\})'
    
    for match in re.finditer(pattern, content):
        quest_id = int(match.group(1))
        quest_data = match.group(2)
        
        # Extract quest name
        name_match = re.search(r'\{"([^"]+)"', quest_data)
        if name_match:
            quests[quest_id] = {
                'name': name_match.group(1),
                'raw': quest_data
            }
    
    return quests

def merge_databases(questie_db, pfquest_db):
    """Merge databases with intelligent conflict resolution"""
    merged = {}
    stats = {
        'kept_questie': 0,
        'added_from_pfquest': 0,
        'updated_placeholders': 0,
        'conflicts': []
    }
    
    # First, add all Questie quests
    for quest_id, quest_data in questie_db.items():
        merged[quest_id] = quest_data
        stats['kept_questie'] += 1
    
    # Then process pfQuest quests
    for quest_id, pf_quest in pfquest_db.items():
        if quest_id not in merged:
            # New quest from pfQuest
            merged[quest_id] = pf_quest
            stats['added_from_pfquest'] += 1
        elif merged[quest_id]['name'].startswith('[Epoch] Quest'):
            # Update placeholder with real name
            print(f"  Updating placeholder: [{quest_id}] {merged[quest_id]['name']} -> {pf_quest['name']}")
            merged[quest_id] = pf_quest
            stats['updated_placeholders'] += 1
        else:
            # Quest exists with different data
            if merged[quest_id]['name'] != pf_quest['name']:
                stats['conflicts'].append({
                    'id': quest_id,
                    'questie': merged[quest_id]['name'],
                    'pfquest': pf_quest['name']
                })
    
    return merged, stats

def generate_merged_database(merged_db):
    """Generate the final merged database file"""
    output = []
    
    # Header
    output.append("---@type QuestieDB")
    output.append("local QuestieLoader = {}")
    output.append("QuestieLoader.ImportModule = function() return {} end")
    output.append("local QuestieDB = QuestieLoader:ImportModule(\"QuestieDB\")")
    output.append("")
    output.append("-- MERGED DATABASE: Questie-Epoch + pfQuest-epoch")
    output.append(f"-- Generated on {datetime.now()}")
    output.append("-- This file combines original Questie data with converted pfQuest data")
    output.append("")
    output.append("epochQuestDataMerged = {")
    
    # Sort by quest ID for consistency
    for quest_id in sorted(merged_db.keys()):
        quest = merged_db[quest_id]
        
        # Add the quest entry
        line = f"  [{quest_id}] = {quest['raw']},"
        
        # Add source comment
        if '[Epoch]' not in quest['name'] and 'pfQuest' not in quest['raw']:
            line += " -- Original Questie"
        elif 'pfQuest' in quest['raw']:
            line += " -- From pfQuest"
        
        output.append(line)
    
    output.append("}")
    output.append("")
    output.append("-- Stage the merged questData for compilation")
    output.append("QuestieDB._epochQuestDataMerged = epochQuestDataMerged")
    
    return '\n'.join(output)

def main():
    workspace = "/Users/travisheryford/Library/CloudStorage/Dropbox/WoW Interfaces/epoch/AddOns/Questie/pfquest_conversion_workspace/"
    
    print("Loading databases...")
    
    # Load original Questie database
    questie_db = parse_questie_db(workspace + "epochQuestDB_original.lua")
    print(f"Loaded {len(questie_db)} quests from Questie")
    
    # Load converted pfQuest database
    pfquest_db = parse_converted_db(workspace + "pfquest_converted_quests.lua")
    print(f"Loaded {len(pfquest_db)} quests from pfQuest conversion")
    
    # Merge databases
    print("\nMerging databases...")
    merged_db, stats = merge_databases(questie_db, pfquest_db)
    
    print(f"\n=== MERGE STATISTICS ===")
    print(f"Original Questie quests kept: {stats['kept_questie']}")
    print(f"New quests added from pfQuest: {stats['added_from_pfquest']}")
    print(f"Placeholder names updated: {stats['updated_placeholders']}")
    print(f"Total quests in merged database: {len(merged_db)}")
    
    if stats['conflicts']:
        print(f"\nConflicts detected: {len(stats['conflicts'])}")
        print("First 10 conflicts:")
        for conflict in stats['conflicts'][:10]:
            print(f"  [{conflict['id']}]")
            print(f"    Questie: {conflict['questie']}")
            print(f"    pfQuest: {conflict['pfquest']}")
    
    # Generate merged database file
    print("\nGenerating merged database...")
    merged_content = generate_merged_database(merged_db)
    
    # Save merged database
    output_file = workspace + "epochQuestDB_MERGED.lua"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    
    print(f"\nMerged database saved to: epochQuestDB_MERGED.lua")
    print(f"Total quests: {len(merged_db)}")
    
    # Generate summary report
    report_file = workspace + "merge_report.txt"
    with open(report_file, 'w') as f:
        f.write("DATABASE MERGE REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Date: {datetime.now()}\n\n")
        f.write("STATISTICS:\n")
        f.write(f"  Original Questie quests: {len(questie_db)}\n")
        f.write(f"  pfQuest converted quests: {len(pfquest_db)}\n")
        f.write(f"  Merged total: {len(merged_db)}\n")
        f.write(f"  New quests added: {stats['added_from_pfquest']}\n")
        f.write(f"  Placeholders updated: {stats['updated_placeholders']}\n")
        f.write(f"  Conflicts: {len(stats['conflicts'])}\n")
        
        if stats['conflicts']:
            f.write("\nCONFLICTS:\n")
            for conflict in stats['conflicts']:
                f.write(f"\n  Quest {conflict['id']}:\n")
                f.write(f"    Questie: {conflict['questie']}\n")
                f.write(f"    pfQuest: {conflict['pfquest']}\n")
    
    print(f"Merge report saved to: merge_report.txt")
    
    print("\n=== NEXT STEPS ===")
    print("1. Review epochQuestDB_MERGED.lua for the combined database")
    print("2. Check merge_report.txt for detailed statistics")
    print("3. To test in-game:")
    print("   - Back up your current epochQuestDB.lua")
    print("   - Replace it with epochQuestDB_MERGED.lua (rename to epochQuestDB.lua)")
    print("   - Restart WoW completely (not just /reload)")
    print("   - Test quest availability and functionality")

if __name__ == "__main__":
    main()