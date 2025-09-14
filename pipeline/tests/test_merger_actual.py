#!/usr/bin/env python3
"""Test the actual merge functionality of database_merger"""

import sys
from pathlib import Path

# Add modules to path
modules_dir = Path("../../Development Tools/GitHub Workflow/Modular Pipeline/modules")
sys.path.insert(0, str(modules_dir))

from database_merger import DatabaseMerger

def main():
    print("="*60)
    print("TESTING DATABASE MERGER - ACTUAL MERGE")
    print("="*60)
    
    # Use a test database file
    test_db_path = "test_merge_db.lua"
    
    # Create a simple test database file
    with open(test_db_path, 'w') as f:
        f.write("""-- Test Database
epochQuestDB = {
    [26627] = {"Existing Quest", nil, nil, 35, 40},
    [28681] = {"Another Quest", nil, nil, 45, 50}
}
""")
    
    # Initialize merger
    merger = DatabaseMerger(test_db_path)
    
    # Test data to merge
    new_data = {
        'quests': [
            {
                'id': 99999,
                'name': 'New Quest to Add',
                'level': 60,
                'min_level': 55
            },
            {
                'id': 26627,  # Existing quest - should update
                'name': 'Updated Quest Name',
                'level': 42,
                'min_level': 37
            }
        ],
        'npcs': [
            {
                'id': 50000,
                'name': 'New NPC',
                'spawns': {14: [[70.9, 45.9]]}
            }
        ]
    }
    
    # Merge decisions (simulate what merge_decision_engine would provide)
    merge_decisions = {
        'approved_merges': [
            {
                'type': 'quest',
                'id': 99999,
                'action': 'add',
                'confidence': 0.95
            },
            {
                'type': 'quest',
                'id': 26627,
                'action': 'update',
                'confidence': 0.85
            },
            {
                'type': 'npc',
                'id': 50000,
                'action': 'add',
                'confidence': 0.90
            }
        ],
        'rejected_merges': [],
        'strategy': 'progressive'
    }
    
    print("\n📋 Testing merge operation")
    print("-"*50)
    
    try:
        # Perform the merge
        success, report = merger.merge(new_data, merge_decisions)
        
        print(f"Merge success: {success}")
        print("\nMerge statistics:")
        for key, value in merger.merge_stats.items():
            if value > 0:
                print(f"  {key}: {value}")
        
        if report:
            print("\nMerge report highlights:")
            if 'summary' in report:
                print(f"  Summary: {report['summary']}")
            if 'errors' in report and report['errors']:
                print(f"  Errors: {report['errors']}")
        
    except Exception as e:
        print(f"❌ Error during merge: {e}")
        import traceback
        traceback.print_exc()
    
    # Test rollback functionality
    print("\n📋 Testing rollback")
    print("-"*50)
    
    try:
        if hasattr(merger, 'rollback'):
            # Check if we have a backup to rollback to
            if merger.backup_manager:
                backups = merger.backup_manager.list_backups()
                if backups:
                    print(f"Found {len(backups)} backup(s)")
                    # Try rollback
                    success = merger.rollback()
                    print(f"Rollback success: {success}")
                else:
                    print("No backups available for rollback")
            else:
                print("No backup manager configured")
        else:
            print("Rollback method not available")
            
    except Exception as e:
        print(f"Note: Rollback test skipped - {e}")
    
    # Check merge history
    print("\n📋 Merge history")
    print("-"*50)
    
    if merger.merge_history:
        print(f"Total merges recorded: {len(merger.merge_history)}")
        for i, entry in enumerate(merger.merge_history[-3:], 1):  # Show last 3
            print(f"  {i}. {entry}")
    else:
        print("No merge history recorded")
    
    # Clean up test file
    if Path(test_db_path).exists():
        Path(test_db_path).unlink()
        print(f"\n🧹 Cleaned up {test_db_path}")
    
    print("\n" + "="*60)
    print("DATABASE MERGER TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()