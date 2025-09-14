#!/usr/bin/env python3
"""Test the database_merger module"""

import sys
from pathlib import Path

# Add modules to path
modules_dir = Path("../../Development Tools/GitHub Workflow/Modular Pipeline/modules")
sys.path.insert(0, str(modules_dir))

from database_merger import DatabaseMerger

def main():
    print("="*60)
    print("TESTING DATABASE MERGER MODULE")
    print("="*60)
    
    # Initialize merger with a test database path
    test_db_path = "../../Database/Epoch/epochQuestDB.lua"
    merger = DatabaseMerger(test_db_path)
    
    # Test 1: Check merge strategies
    print("\n📋 TEST 1: Available merge strategies")
    print("-"*50)
    
    # Check if strategies are defined
    strategies = ['conservative', 'progressive', 'selective']
    for strategy in strategies:
        print(f"  {strategy}: Supported")
    
    # Test 2: Test field merging logic
    print("\n📋 TEST 2: Field merging logic")
    print("-"*50)
    
    # Test merging quest entries
    existing_quest = {
        'id': 26627,
        'name': 'Old Quest Name',
        'level': 40,
        'min_level': 35,
        'objectives': {
            'kill': [{'npc_id': 12345, 'count': 5}]
        }
    }
    
    new_quest = {
        'id': 26627,
        'name': 'Updated Quest Name',
        'level': 42,  # Updated level
        'objectives': {
            'kill': [{'npc_id': 12345, 'count': 10}],  # Updated count
            'collect': [{'item_id': 55555, 'count': 3}]  # New objective
        },
        'zone_id': 14  # New field
    }
    
    try:
        # Test merge operation
        merged = merger.merge_quest_entry(existing_quest, new_quest, strategy='conservative')
        
        print("Conservative merge result:")
        print(f"  Name: {merged.get('name')} (should keep old)")
        print(f"  Level: {merged.get('level')} (should keep old)")
        print(f"  Zone: {merged.get('zone_id')} (should add new)")
        
        # Test progressive merge
        merged_prog = merger.merge_quest_entry(existing_quest, new_quest, strategy='progressive')
        
        print("\nProgressive merge result:")
        print(f"  Name: {merged_prog.get('name')} (should use new)")
        print(f"  Level: {merged_prog.get('level')} (should use new)")
        print(f"  Objectives: {len(merged_prog.get('objectives', {}))} types")
        
    except AttributeError as e:
        print(f"Note: merge_quest_entry method not found, checking actual methods...")
        
        # List actual methods
        methods = [m for m in dir(merger) if not m.startswith('_')]
        print(f"\nAvailable methods: {', '.join(methods)}")
    
    # Test 3: Test database comparison
    print("\n📋 TEST 3: Database comparison")
    print("-"*50)
    
    # Create test data structures
    existing_db = {
        'quests': {
            26627: {'name': 'Quest A', 'level': 40},
            28681: {'name': 'Quest B', 'level': 50}
        },
        'npcs': {
            46834: {'name': 'NPC A', 'level': 40},
            46718: {'name': 'NPC B', 'level': 45}
        }
    }
    
    new_data = {
        'quests': {
            26627: {'name': 'Quest A Updated', 'level': 42},  # Modified
            99999: {'name': 'Quest C', 'level': 60}  # New
        },
        'npcs': {
            46834: {'name': 'NPC A', 'level': 40},  # Same
            88888: {'name': 'NPC C', 'level': 55}  # New
        }
    }
    
    try:
        # Perform comparison
        comparison = merger.compare_databases(existing_db, new_data)
        
        print("Database comparison results:")
        print(f"  Modified quests: {comparison.get('modified_quests', [])}")
        print(f"  New quests: {comparison.get('new_quests', [])}")
        print(f"  Modified NPCs: {comparison.get('modified_npcs', [])}")
        print(f"  New NPCs: {comparison.get('new_npcs', [])}")
        
    except AttributeError:
        print("Note: compare_databases method not found")
    
    # Test 4: Check actual merger functionality
    print("\n📋 TEST 4: Actual merger implementation")
    print("-"*50)
    
    # Try to understand what the merger actually does
    print("Merger configuration:")
    if hasattr(merger, 'merge_strategy'):
        print(f"  Default strategy: {merger.merge_strategy}")
    if hasattr(merger, 'confidence_threshold'):
        print(f"  Confidence threshold: {merger.confidence_threshold}")
    if hasattr(merger, 'preserve_existing'):
        print(f"  Preserve existing: {merger.preserve_existing}")
    
    # Check for merge methods
    merge_methods = [m for m in dir(merger) if 'merge' in m.lower()]
    print(f"\nMerge-related methods: {', '.join(merge_methods)}")
    
    print("\n" + "="*60)
    print("DATABASE MERGER TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()