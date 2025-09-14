#!/usr/bin/env python3
"""
Test Database Precedence Resolution
Demonstrates how to handle Epoch quests that reuse vanilla/WotLK IDs
"""

import sys
import json
import re
from pathlib import Path

# Add modules to path
modules_dir = Path("../../Development Tools/GitHub Workflow/Modular Pipeline/modules")
sys.path.insert(0, str(modules_dir))

from database_precedence_resolver import DatabasePrecedenceResolver, DatabaseSource

def load_quest_from_lua(db_file: Path, quest_id: int) -> dict:
    """Load a quest from a Lua database file"""
    if not db_file.exists():
        return None
    
    with open(db_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find the quest entry
    pattern = rf'\[{quest_id}\]\s*=\s*\{{([^}}]+)\}}'
    match = re.search(pattern, content)
    
    if not match:
        return None
    
    # Parse basic fields (simplified)
    quest_data = {'quest_id': quest_id}
    
    # Extract name
    name_match = re.search(r'"([^"]+)"', match.group(1))
    if name_match:
        quest_data['name'] = name_match.group(1)
    
    return quest_data

def main():
    print("="*70)
    print("DATABASE PRECEDENCE RESOLUTION TEST")
    print("="*70)
    print("\nTesting how Epoch quests should handle vanilla/WotLK collisions\n")
    
    resolver = DatabasePrecedenceResolver()
    
    # Database paths
    db_base = Path("../../Database")
    wotlk_db = db_base / "WotLK" / "wotlkQuestDB.lua"
    classic_db = db_base / "Classic" / "classicQuestDB.lua"
    
    # Load aggregated cache
    cache_file = Path(".pipeline_cache/aggregated_quests.json")
    if not cache_file.exists():
        print("❌ No aggregated data cache found")
        return
    
    with open(cache_file, 'r') as f:
        aggregated_quests = json.load(f)
    
    print(f"📊 Loaded {len(aggregated_quests)} aggregated quests\n")
    
    # Test scenarios
    test_scenarios = []
    
    # Scenario 1: Check known Epoch custom IDs (25000-30000 range)
    print("🔍 Scenario 1: Custom Epoch Quest IDs (25000-30000)")
    print("-" * 50)
    
    custom_range_quests = []
    for quest_id_str, quest_data in aggregated_quests.items():
        quest_id = int(quest_id_str)
        if 25000 <= quest_id <= 30000:
            custom_range_quests.append((quest_id, quest_data))
            if len(custom_range_quests) >= 3:
                break
    
    for quest_id, quest_data in custom_range_quests:
        # Check if exists in WotLK
        wotlk_quest = load_quest_from_lua(wotlk_db, quest_id)
        classic_quest = load_quest_from_lua(classic_db, quest_id)
        
        existing = {}
        if wotlk_quest:
            existing[DatabaseSource.WOTLK] = wotlk_quest
        if classic_quest:
            existing[DatabaseSource.CLASSIC] = classic_quest
        
        decision = resolver.analyze_quest_collision(quest_data, existing)
        
        print(f"\nQuest {quest_id}: {quest_data.get('name', 'Unknown')}")
        if existing:
            print(f"  ⚠️ EXISTS in: {', '.join(s.name for s in existing.keys())}")
            for source, data in existing.items():
                print(f"    {source.name}: {data.get('name', 'Unknown')}")
        else:
            print(f"  ✅ No collision - unique to Epoch")
        
        print(f"  Decision: {decision['action']}")
        if decision['comment_out']:
            print(f"  Action: Comment out in {', '.join(decision['comment_out'])}")
    
    # Scenario 2: Check low ID quests that might collide with vanilla
    print("\n🔍 Scenario 2: Low ID Quests (potential vanilla collisions)")
    print("-" * 50)
    
    low_id_quests = []
    for quest_id_str, quest_data in aggregated_quests.items():
        quest_id = int(quest_id_str)
        if quest_id < 10000:  # Vanilla range
            low_id_quests.append((quest_id, quest_data))
            if len(low_id_quests) >= 3:
                break
    
    for quest_id, quest_data in low_id_quests:
        wotlk_quest = load_quest_from_lua(wotlk_db, quest_id)
        classic_quest = load_quest_from_lua(classic_db, quest_id)
        
        existing = {}
        if wotlk_quest:
            existing[DatabaseSource.WOTLK] = wotlk_quest
        if classic_quest:
            existing[DatabaseSource.CLASSIC] = classic_quest
        
        decision = resolver.analyze_quest_collision(quest_data, existing)
        
        print(f"\nQuest {quest_id}: {quest_data.get('name', 'Unknown')}")
        if existing:
            for source, data in existing.items():
                print(f"  Existing {source.name}: {data.get('name', 'Unknown')}")
        
        print(f"  Similarity scores: {decision['similarity_scores']}")
        print(f"  Decision: {decision['action']}")
        
        if decision['conflicts']:
            print("  Conflicts detected:")
            for conflict in decision['conflicts']:
                print(f"    - {conflict['type']}: {conflict['similarity']:.1f}% similar")
    
    # Scenario 3: Check specific known problematic IDs
    print("\n🔍 Scenario 3: Known Problematic Quest IDs")
    print("-" * 50)
    
    # These are quests we know have issues
    problematic_ids = [26939, 27011, 27409]  # From your previous data
    
    for quest_id in problematic_ids:
        quest_id_str = str(quest_id)
        if quest_id_str not in aggregated_quests:
            continue
        
        quest_data = aggregated_quests[quest_id_str]
        
        # Create full quest data structure
        epoch_quest = {
            'quest_id': quest_id,
            'name': quest_data.get('name', f'Quest {quest_id}'),
            'startedBy': quest_data.get('startedBy', {}),
            'finishedBy': quest_data.get('finishedBy', {}),
            'objectivesText': quest_data.get('objectivesText', []),
            'zone': quest_data.get('zoneOrSort') or quest_data.get('zone')
        }
        
        # Check existing databases
        existing = {}
        wotlk_quest = load_quest_from_lua(wotlk_db, quest_id)
        if wotlk_quest:
            existing[DatabaseSource.WOTLK] = wotlk_quest
        
        decision = resolver.analyze_quest_collision(epoch_quest, existing)
        
        print(f"\nQuest {quest_id}: {epoch_quest['name']}")
        if wotlk_quest:
            print(f"  WotLK version: {wotlk_quest.get('name', 'Unknown')}")
            print(f"  Names match: {epoch_quest['name'] == wotlk_quest.get('name', '')}")
        
        print(f"  Decision: {decision['action']}")
        if decision['comment_out']:
            print(f"  ⚠️ REQUIRES: Comment out {', '.join(decision['comment_out'])} entry")
        
        for reason in decision['reasoning']:
            print(f"    Reason: {reason}")
    
    # Generate final report
    print("\n" + resolver.generate_precedence_report())
    
    # Summary
    print("\n" + "="*70)
    print("KEY FINDINGS:")
    print("-" * 50)
    
    total_collisions = sum(1 for d in resolver.decisions if d['action'] == 'REPLACE')
    
    print(f"Total quests analyzed: {len(resolver.decisions)}")
    print(f"ID collisions requiring action: {total_collisions}")
    
    if total_collisions > 0:
        print("\n⚠️ ACTION REQUIRED:")
        print("The following databases need entries commented out:")
        
        affected = {'WOTLK': 0, 'CLASSIC': 0}
        for decision in resolver.decisions:
            for db in decision.get('comment_out', []):
                if db in affected:
                    affected[db] += 1
        
        for db, count in affected.items():
            if count > 0:
                print(f"  - {db}: {count} entries")
        
        print("\nThis prevents Epoch quests from being overridden by vanilla data!")
    
    print("="*70)

if __name__ == "__main__":
    main()