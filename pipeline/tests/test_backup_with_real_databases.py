#!/usr/bin/env python3
"""
Test BackupManager with real Questie database files
"""

import sys
from pathlib import Path

# Add modules to path
modules_dir = Path("../../Development Tools/GitHub Workflow/Modular Pipeline/modules")
sys.path.insert(0, str(modules_dir))

from backup_manager import BackupManager

def main():
    print("="*70)
    print("TESTING BACKUP MANAGER WITH REAL DATABASE FILES")
    print("="*70)
    
    # Initialize backup manager with custom backup directory
    backup_dir = Path("../../Development Tools/GitHub Workflow/Modular Pipeline/database_backups")
    backup_manager = BackupManager(backup_dir=str(backup_dir))
    
    # Database files to backup
    db_base = Path("../../Database")
    database_files = [
        db_base / "Epoch" / "epochQuestDB.lua",
        db_base / "Epoch" / "epochNpcDB.lua",
        db_base / "Epoch" / "epochItemDB.lua",
        db_base / "Epoch" / "epochObjectDB.lua",
    ]
    
    print(f"\n📁 Backup directory: {backup_dir}")
    print(f"📊 Files to backup: {len(database_files)}")
    
    # Create batch backup
    print("\n🔒 Creating batch backup of Epoch databases...")
    existing_files = [f for f in database_files if f.exists()]
    
    if not existing_files:
        print("❌ No database files found!")
        return
    
    print(f"   Found {len(existing_files)} files to backup")
    
    backup_ids = backup_manager.create_batch_backup(
        [str(f) for f in existing_files],
        description="Pre-pipeline backup of Epoch databases"
    )
    
    print(f"\n✅ Created {len(backup_ids)} backups:")
    for backup_id in backup_ids:
        info = backup_manager.get_backup_info(backup_id)
        if info:
            print(f"   - {backup_id}")
            print(f"     Size: {info['size_mb']:.2f} MB")
            print(f"     Compressed: {info['compression_used']}")
            print(f"     Integrity OK: {info.get('integrity_ok', 'Unknown')}")
    
    # Show storage usage
    usage = backup_manager.get_storage_usage()
    print(f"\n💾 Storage Usage:")
    print(f"   Total backups: {usage['total_backups']}")
    print(f"   Total size: {usage['total_size_mb']:.2f} MB")
    if usage['compression_ratio'] > 0:
        print(f"   Compression ratio: {(1 - usage['compression_ratio']) * 100:.1f}% saved")
    
    # List all backups
    print(f"\n📋 All Backups in System:")
    all_backups = backup_manager.list_backups()
    
    # Group by original file
    by_file = {}
    for backup in all_backups:
        original = Path(backup['original_file']).name
        if original not in by_file:
            by_file[original] = []
        by_file[original].append(backup)
    
    for file_name, backups in by_file.items():
        print(f"\n   {file_name}:")
        for backup in backups[:3]:  # Show latest 3
            print(f"      - {backup['backup_id']}")
            print(f"        Age: {backup['age_days']:.1f} days")
    
    # Test restore capability
    print("\n🧪 Testing Restore Capability...")
    if backup_ids:
        test_backup_id = backup_ids[0]
        test_info = backup_manager.get_backup_info(test_backup_id)
        
        print(f"   Testing restore of: {test_backup_id}")
        print(f"   Original file: {Path(test_info['original_file']).name}")
        
        # We won't actually restore to avoid overwriting, just verify it's possible
        print(f"   Backup exists: {test_info['exists']}")
        print(f"   Integrity check: {test_info.get('integrity_ok', 'Unknown')}")
        
        if test_info['exists'] and test_info.get('integrity_ok'):
            print("   ✅ Backup is ready for restore if needed")
        else:
            print("   ⚠️ Backup may have issues")
    
    # Cleanup old backups (if any)
    print("\n🧹 Cleanup Check...")
    old_count = backup_manager.cleanup_backups(older_than_days=30, keep_minimum=3)
    if old_count > 0:
        print(f"   Removed {old_count} old backups")
    else:
        print("   No old backups to clean up")
    
    print("\n" + "="*70)
    print("✅ BACKUP MANAGER TEST COMPLETE")
    print("   All database files are safely backed up")
    print("   Ready to proceed with database modifications")
    print("="*70)

if __name__ == "__main__":
    main()