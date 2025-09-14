#!/usr/bin/env python3
"""Test the database_writer module with real pipeline data"""

import sys
from pathlib import Path

# Add modules to path
modules_dir = Path(__file__).parent.parent / "modules"
sys.path.insert(0, str(modules_dir))

from database_writer import DatabaseWriter
from pipeline_state_tracker import PipelineStateTracker

def main():
    print("="*60)
    print("TESTING DATABASE WRITER MODULE")
    print("="*60)
    
    # Initialize components
    writer = DatabaseWriter()
    state_tracker = PipelineStateTracker()
    
    # Get some NEW quests to test with
    new_quests = list(state_tracker.get_new_quests())[:5]  # Test with first 5
    
    print(f"\n📋 Testing with {len(new_quests)} NEW quests: {new_quests}")
    
    # Test the analyze_and_build_entry method for each quest
    for quest_id in new_quests:
        print(f"\n{'='*50}")
        print(f"Quest ID: {quest_id}")
        
        # Minimal quest data for testing
        quest_data = {
            'quest_id': quest_id,
            'quest_name': f'Test Quest {quest_id}',
            'level': 40,
            'min_level': 35
        }
        
        try:
            # Build the entry with restriction analysis
            entry = writer.analyze_and_build_entry(quest_data)
            
            print(f"Generated entry:")
            print(entry)
            
            # Check if restrictions were detected
            if "Alliance" in entry or "Horde" in entry:
                print("✅ Faction restriction detected!")
            
            if any(class_name in entry.upper() for class_name in ['WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST']):
                print("✅ Class restriction detected!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test the formatting functions
    print("\n" + "="*50)
    print("TESTING LUA FORMATTING:")
    
    # Test triple brace formatting for objectives
    test_objectives = {
        'kill': [
            {'npc_id': 45543, 'count': 1, 'name': 'Baron Valimar Mordis'}
        ]
    }
    
    formatted = writer._format_objectives(test_objectives)
    print(f"\nObjectives formatting test:")
    print(f"Input: {test_objectives}")
    print(f"Output: {formatted}")
    
    # Check brace count
    open_braces = formatted.count('{')
    close_braces = formatted.count('}')
    print(f"Brace check: {open_braces} open, {close_braces} close")
    
    if open_braces == close_braces and open_braces >= 3:
        print("✅ Correct triple-brace formatting!")
    else:
        print("❌ Incorrect brace formatting!")
    
    print("\n" + "="*60)
    print("DATABASE WRITER TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()