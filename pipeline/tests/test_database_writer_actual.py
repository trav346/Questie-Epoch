#!/usr/bin/env python3
"""Test the database_writer module with its actual methods"""

import sys
from pathlib import Path
import json

# Add modules to path
modules_dir = Path(__file__).parent.parent / "modules"
sys.path.insert(0, str(modules_dir))

from database_writer import DatabaseWriter

def main():
    print("="*60)
    print("TESTING DATABASE WRITER MODULE")
    print("="*60)
    
    # Initialize writer
    writer = DatabaseWriter()
    
    # Test 1: Generate quest entry with restrictions
    print("\n📋 TEST 1: Generate quest entry with restrictions")
    print("-"*50)
    
    test_quest = {
        'quest_id': 26627,
        'quest_name': 'Test Alliance Quest',
        'level': 40,
        'min_level': 35,
        'quest_giver': {'npc_id': 46834, 'name': 'Test Giver'},
        'turn_in': {'npc_id': 46718, 'name': 'Test Turn-in'},
        'objectives': {
            'kill': [
                {'npc_id': 45543, 'count': 10, 'name': 'Test Mob'}
            ]
        }
    }
    
    try:
        # Generate entry using the actual method
        entry = writer.generate_quest_entry(test_quest)
        print(f"Generated entry:\n{entry}")
        
        # Check for faction/class restrictions
        if "Alliance" in entry or "Horde" in entry:
            print("✅ Faction restriction comment detected!")
        
        if "77" in entry or "690" in entry:  # Alliance/Horde race flags
            print("✅ Race restriction flags found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Test aggregated data writing
    print("\n📋 TEST 2: Write aggregated data")
    print("-"*50)
    
    aggregated_data = {
        'quests': [
            {
                'quest_id': 26627,
                'quest_name': 'Test Quest 1',
                'level': 40,
                'min_level': 35,
                'quest_giver': {'npc_id': 46834},
                'turn_in': {'npc_id': 46718},
                'objectives': {
                    'kill': [{'npc_id': 45543, 'count': 10, 'name': 'Test Mob'}]
                }
            },
            {
                'quest_id': 28681,
                'quest_name': 'Test Quest 2',
                'level': 50,
                'min_level': 45,
                'quest_giver': {'npc_id': 50000},
                'turn_in': {'npc_id': 50001}
            }
        ],
        'npcs': [
            {
                'npc_id': 46834,
                'name': 'Quest Giver NPC',
                'spawns': {14: [[70.9, 45.9]]},
                'quest_starts': [26627],
                'npc_flags': 2  # Quest giver
            },
            {
                'npc_id': 46718,
                'name': 'Turn-in NPC',
                'spawns': {14: [[71.2, 46.1]]},
                'quest_ends': [26627],
                'npc_flags': 2
            }
        ]
    }
    
    # Define test output paths
    test_paths = {
        'quest_db': 'test_output_quests.lua',
        'npc_db': 'test_output_npcs.lua'
    }
    
    try:
        results = writer.write_aggregated_data(aggregated_data, test_paths)
        print(f"Write results:")
        print(f"  Quests written: {results.get('quests_written', 0)}")
        print(f"  NPCs written: {results.get('npcs_written', 0)}")
        print(f"  Quest file: {results.get('quest_file', 'None')}")
        print(f"  NPC file: {results.get('npc_file', 'None')}")
        
        # Check if files were created
        for file_type, path in test_paths.items():
            if Path(path).exists():
                print(f"✅ {file_type} file created: {path}")
                # Show first few lines
                with open(path, 'r') as f:
                    lines = f.readlines()[:5]
                    print(f"  First few lines:")
                    for line in lines:
                        print(f"    {line.rstrip()}")
            else:
                print(f"❌ {file_type} file not created")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Check restriction detection from tracker
    print("\n📋 TEST 3: Restriction detection from tracker")
    print("-"*50)
    
    # Query the tracker for quest analysis
    quest_id = 26627
    analysis = writer.tracker.analyze_quest_restrictions(quest_id)
    
    print(f"Quest {quest_id} analysis:")
    print(f"  Submissions: {analysis.get('submission_count', 0)}")
    print(f"  Alliance only: {analysis.get('alliance_percentage', 0):.1f}%")
    print(f"  Horde only: {analysis.get('horde_percentage', 0):.1f}%")
    print(f"  Likely faction: {analysis.get('likely_faction', 'Neutral')}")
    
    if analysis.get('class_pattern'):
        print(f"  Class pattern detected: {analysis['class_pattern']}")
    
    # Clean up test files
    print("\n🧹 Cleaning up test files...")
    for path in test_paths.values():
        if Path(path).exists():
            Path(path).unlink()
            print(f"  Removed {path}")
    
    print("\n" + "="*60)
    print("DATABASE WRITER TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()