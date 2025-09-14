#!/usr/bin/env python3
"""Test script to run issue_1300.txt through the aggregator"""

import sys
from pathlib import Path

# Add modules directory to path
sys.path.insert(0, 'modules')

from data_aggregator import DataAggregator

def main():
    # Initialize aggregator
    print("=" * 60)
    print("TESTING ISSUE 1300 THROUGH AGGREGATOR")
    print("=" * 60)
    print("\nInitializing DataAggregator...")
    aggregator = DataAggregator()
    
    # Process issue_1300.txt
    test_file = Path("../pending_submissions/issue_1300.txt")
    
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    print(f"\n📄 Processing: {test_file.name}")
    
    # Read the file content
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"  File size: {len(content)} characters")
    
    # Process through aggregator
    try:
        result = aggregator.process_submission(content, source_file=test_file.name)
        
        print("\n📊 EXTRACTION RESULTS:")
        print("-" * 40)
        print(f"  Quests extracted: {len(result.get('quests', []))}")
        print(f"  NPCs extracted: {len(result.get('npcs', []))}")
        print(f"  Items extracted: {len(result.get('items', []))}")
        print(f"  Objects extracted: {len(result.get('objects', []))}")
        
        # Show errors and warnings
        if result.get('errors'):
            print(f"\n❌ Errors:")
            for error in result['errors']:
                print(f"    - {error}")
        
        if result.get('warnings'):
            print(f"\n⚠️  Warnings:")
            for warning in result['warnings'][:5]:  # First 5
                print(f"    - {warning}")
        
        # Show extracted quest details
        if result.get('quests'):
            print(f"\n✅ QUESTS EXTRACTED:")
            print("-" * 40)
            for quest in result['quests']:
                quest_data = aggregator.quests.get(quest['id'])
                if quest_data:
                    print(f"\nQuest ID: {quest['id']}")
                    print(f"  Name: {quest_data.get('name', 'Unknown')}")
                    print(f"  Level: {quest_data.get('questLevel', 'Unknown')}")
                    print(f"  Zone: {quest_data.get('zone', 'Unknown')} (ID: {quest_data.get('zoneID', 'Unknown')})")
                    
                    # Show quest givers
                    if quest_data.get('startedBy', {}).get('npcs'):
                        print(f"  Quest Giver NPCs: {quest_data['startedBy']['npcs']}")
                    
                    # Show turn-in NPCs
                    if quest_data.get('finishedBy', {}).get('npcs'):
                        print(f"  Turn-in NPCs: {quest_data['finishedBy']['npcs']}")
                    
                    # Show objectives
                    if quest_data.get('objectives'):
                        obj = quest_data['objectives']
                        if obj.get('creatures'):
                            print(f"  Kill objectives: {len(obj['creatures'])} creatures")
                        if obj.get('items'):
                            print(f"  Item objectives: {len(obj['items'])} items")
                            for item in obj['items']:
                                print(f"    - Item {item.get('id', '?')}: {item.get('name', 'Unknown')} x{item.get('count', 1)}")
                        if obj.get('objects'):
                            print(f"  Object objectives: {len(obj['objects'])} objects")
                    
                    print(f"  Completeness Score: {quest_data.get('completeness_score', 0)}")
                    print(f"  Validation Score: {quest_data.get('validation_score', 0)}")
                    print(f"  Quality Level: {quest_data.get('quality_level', 'unknown')}")
        
        # Show extracted NPC details
        if result.get('npcs'):
            print(f"\n✅ NPCS EXTRACTED:")
            print("-" * 40)
            for npc in result['npcs']:
                npc_data = aggregator.npcs.get(npc['id'])
                if npc_data:
                    print(f"\nNPC ID: {npc['id']}")
                    print(f"  Name: {npc_data.get('name', 'Unknown')}")
                    print(f"  Zone: {npc_data.get('zoneID', 'Unknown')}")
                    if npc_data.get('spawns'):
                        for zone_id, coords in npc_data['spawns'].items():
                            print(f"  Spawns in zone {zone_id}:")
                            for coord in coords[:3]:  # First 3 coords
                                print(f"    - [{coord['x']}, {coord['y']}]")
                    if npc_data.get('questStarts'):
                        print(f"  Starts quests: {npc_data['questStarts']}")
                    if npc_data.get('questEnds'):
                        print(f"  Ends quests: {npc_data['questEnds']}")
        
        # Save to file for detailed inspection
        output_file = f"issue_1300_aggregated_output.txt"
        saved_path = aggregator.save_aggregated_data_to_file(output_file)
        print(f"\n💾 Full aggregated data saved to: {output_file}")
        
        # Show Lua output samples
        print(f"\n📝 LUA OUTPUT SAMPLES:")
        print("-" * 40)
        
        if aggregator.quests:
            for quest_id in aggregator.quests:
                lua_entry = aggregator._generate_quest_lua(aggregator.quests[quest_id])
                print(f"\nQuest Lua:\n{lua_entry}")
                break  # Just show first one
        
        if aggregator.npcs:
            for npc_id in aggregator.npcs:
                lua_entry = aggregator._generate_npc_lua(aggregator.npcs[npc_id])
                print(f"\nNPC Lua:\n{lua_entry}")
                break  # Just show first one
        
    except Exception as e:
        print(f"\n❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()