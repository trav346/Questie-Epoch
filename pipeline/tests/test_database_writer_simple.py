#!/usr/bin/env python3
"""Simple test of database_writer core functionality"""

import sys
from pathlib import Path

# Add modules to path
modules_dir = Path("../../Development Tools/GitHub Workflow/Modular Pipeline/modules")
sys.path.insert(0, str(modules_dir))

from database_writer import DatabaseWriter

def main():
    print("="*60)
    print("TESTING DATABASE WRITER CORE FUNCTIONALITY")
    print("="*60)
    
    # Initialize writer
    writer = DatabaseWriter()
    
    # Test 1: Check class and race flag definitions
    print("\n📋 TEST 1: Verify flag definitions")
    print("-"*50)
    
    print("Class flags:")
    for class_name, flag in writer.CLASS_FLAGS.items():
        print(f"  {class_name}: {flag}")
    
    print("\nRace flags:")
    for race_name, flag in writer.RACE_FLAGS.items():
        print(f"  {race_name}: {flag}")
    
    print("\nFaction race combinations:")
    for faction, flags in writer.FACTION_RACES.items():
        print(f"  {faction}: {flags} (binary: {bin(flags)})")
    
    # Test 2: Test the write methods with simple data
    print("\n📋 TEST 2: Test write methods")
    print("-"*50)
    
    # Simple quest data that doesn't require tracker lookup
    simple_quests = [
        {
            'id': 99999,  # Use 'id' as expected by the writer
            'name': 'Test Quest Alpha',
            'level': 40,
            'min_level': 35,
            'quest_giver': {'npc_id': 50000, 'name': 'Test Giver'},
            'turn_in': {'npc_id': 50001, 'name': 'Test Turn-in'},
            'zone_id': 14,
            'objectives': {
                'kill': [{'npc_id': 50002, 'count': 10, 'name': 'Test Mob'}]
            }
        }
    ]
    
    simple_npcs = [
        {
            'id': 50000,  # Use 'id' as expected
            'name': 'Test Quest Giver',
            'spawns': {14: [[70.9, 45.9]]},
            'quest_starts': [99999],
            'npc_flags': 2
        },
        {
            'id': 50001,
            'name': 'Test Turn-in NPC',
            'spawns': {14: [[71.2, 46.1]]},  
            'quest_ends': [99999],
            'npc_flags': 2
        }
    ]
    
    # Try writing with the actual method signature
    output_file = "test_quest_output.lua"
    
    try:
        writer.write_quests_to_file(simple_quests, output_file)
        print(f"✅ Successfully wrote quests to {output_file}")
        
        # Check if file was created and show content
        if Path(output_file).exists():
            with open(output_file, 'r') as f:
                content = f.read()
                print(f"\nFile content ({len(content)} bytes):")
                lines = content.split('\n')[:10]
                for line in lines:
                    print(f"  {line}")
            
            # Clean up
            Path(output_file).unlink()
            print(f"\n🧹 Cleaned up {output_file}")
        else:
            print(f"❌ File {output_file} was not created")
            
    except Exception as e:
        print(f"❌ Error writing quests: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test the _generate_enhanced_quest_entry method directly
    print("\n📋 TEST 3: Test quest entry generation")
    print("-"*50)
    
    test_quest = {
        'id': 88888,
        'name': 'Direct Test Quest',
        'level': 50,
        'min_level': 45,
        'zone_id': 1519,  # Stormwind
        'quest_giver': {'npc_id': 60000},
        'turn_in': {'npc_id': 60001},
        'objectives': {
            'kill': [
                {'npc_id': 60002, 'count': 5, 'name': 'Test Enemy'}
            ],
            'collect': [
                {'item_id': 70000, 'count': 3}
            ]
        }
    }
    
    try:
        # Call the internal method directly
        entry = writer._generate_enhanced_quest_entry(test_quest)
        print(f"Generated entry:\n{entry}")
        
        # Count fields
        # Remove the [id] = { and final }
        fields_part = entry.split(' = {')[1].rstrip('},')
        fields = fields_part.split(',')
        print(f"\nField count: {len(fields)}")
        
        if len(fields) == 30:
            print("✅ Correct field count (30)")
        else:
            print(f"❌ Wrong field count (expected 30, got {len(fields)})")
            
    except Exception as e:
        print(f"❌ Error generating entry: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("DATABASE WRITER TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()