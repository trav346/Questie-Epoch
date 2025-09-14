#!/usr/bin/env python3
"""Test script to verify aggregator output functionality"""

import sys
from pathlib import Path

# Add modules directory to path
sys.path.insert(0, 'modules')

from data_aggregator import DataAggregator

def main():
    # Initialize aggregator
    print("Initializing DataAggregator...")
    aggregator = DataAggregator()
    
    # Process a single test file
    test_file = Path("../pending_submissions/issue_691.txt")
    
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    print(f"Processing test file: {test_file}")
    
    # Read the file content first
    with open(test_file, 'r') as f:
        content = f.read()
    print(f"  File size: {len(content)} characters")
    print(f"  First 100 chars: {content[:100]}")
    
    # Process the file content (not the path!)
    try:
        result = aggregator.process_submission(content, source_file=str(test_file))
        
        print("\nProcessing Results:")
        print(f"  Result keys: {result.keys()}")
        print(f"  Quests extracted: {len(result.get('quests', []))}")
        print(f"  NPCs extracted: {len(result.get('npcs', []))}")
        print(f"  Items extracted: {len(result.get('items', []))}")
        
        # Check for errors or warnings
        if result.get('errors'):
            print(f"  Errors: {result['errors']}")
        if result.get('warnings'):
            print(f"  Warnings: {result['warnings'][:3]}")  # First 3 warnings
        
        # Show what was extracted
        if result.get('quests'):
            for quest in result['quests']:
                print(f"\n  Quest {quest.get('id')}: {quest.get('name')}")
                
        if result.get('npcs'):
            for npc in result['npcs']:
                print(f"  NPC {npc.get('id')}: {npc.get('name')}")
        
        # Save to file
        print("\nSaving aggregated data to file...")
        output_file = aggregator.save_aggregated_data_to_file("test_aggregator_output.txt")
        print(f"✓ Data saved to: {output_file}")
        
        # Also get summary
        summary = aggregator.get_summary()
        print(f"\nAggregator Summary:")
        print(f"  Total quests in memory: {summary['total_quests']}")
        print(f"  Total NPCs in memory: {summary['total_npcs']}")
        print(f"  Total items in memory: {summary['total_items']}")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()