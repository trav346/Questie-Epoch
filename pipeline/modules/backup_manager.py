#!/usr/bin/env python3
"""
Backup Manager Module for Questie Pipeline

Manages backups of database files before making changes, ensuring safe rollback capability.
Provides versioned backups, compression, and automated cleanup of old backups.

Key Features:
- Automatic backup before any database modifications
- Timestamped backup versions with metadata
- Compression to save disk space
- Rollback capability to any previous version
- Automated cleanup of old backups
- Integrity verification of backup files
- Differential backups for efficiency
"""

import os
import shutil
import gzip
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import tempfile

@dataclass
class BackupMetadata:
    """Metadata for a backup file"""
    backup_id: str
    original_file: str
    backup_path: str
    timestamp: str
    file_size: int
    checksum: str
    compression_used: bool
    backup_type: str  # 'full', 'incremental', 'pre_merge'
    description: str
    pipeline_version: str = "1.0"
    
class BackupManager:
    """Manages database backups for safe pipeline operations"""
    
    def __init__(self, backup_dir: str = None, config: Dict = None):
        self.logger = logging.getLogger(__name__)
        
        # Default backup directory
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            # Use subdirectory in pipeline modules folder
            self.backup_dir = Path(__file__).parent / "backups"
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = config or self._get_default_config()
        
        # Metadata tracking
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self.metadata = self._load_metadata()
        
        # Compression settings
        self.compression_enabled = self.config.get('compression', True)
        self.compression_level = self.config.get('compression_level', 6)
        
        self.logger.info(f"BackupManager initialized with backup_dir: {self.backup_dir}")
    
    def create_backup(self, file_path: str, backup_type: str = "pre_merge", 
                     description: str = None) -> str:
        """
        Create a backup of the specified file
        
        Args:
            file_path: Path to file to backup
            backup_type: Type of backup ('full', 'incremental', 'pre_merge')
            description: Human readable description
            
        Returns:
            Backup ID for reference
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File to backup not found: {file_path}")
            
            # Generate backup ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"{file_path.stem}_{backup_type}_{timestamp}"
            
            # Create backup filename
            backup_filename = f"{backup_id}.lua"
            if self.compression_enabled:
                backup_filename += ".gz"
            
            backup_path = self.backup_dir / backup_filename
            
            # Create the backup
            file_size, checksum = self._copy_file(file_path, backup_path)
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                original_file=str(file_path),
                backup_path=str(backup_path),
                timestamp=datetime.now().isoformat(),
                file_size=file_size,
                checksum=checksum,
                compression_used=self.compression_enabled,
                backup_type=backup_type,
                description=description or f"Backup of {file_path.name}"
            )
            
            # Store metadata
            self.metadata[backup_id] = asdict(metadata)
            self._save_metadata()
            
            self.logger.info(f"Created backup {backup_id} for {file_path.name}")
            
            # Cleanup old backups if needed
            self._cleanup_old_backups(file_path.stem)
            
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Error creating backup for {file_path}: {e}")
            raise
    
    def restore_backup(self, backup_id: str, target_path: str = None) -> bool:
        """
        Restore a backup to the original location or specified path
        
        Args:
            backup_id: ID of backup to restore
            target_path: Optional target path, defaults to original location
            
        Returns:
            True if restoration successful
        """
        try:
            if backup_id not in self.metadata:
                raise ValueError(f"Backup {backup_id} not found")
            
            backup_info = self.metadata[backup_id]
            backup_path = Path(backup_info['backup_path'])
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # Determine target path
            if target_path:
                target = Path(target_path)
            else:
                target = Path(backup_info['original_file'])
            
            # Verify backup integrity
            if not self._verify_backup_integrity(backup_id):
                raise ValueError(f"Backup {backup_id} failed integrity check")
            
            # Create backup of current file before restoring
            if target.exists():
                restore_backup_id = self.create_backup(
                    str(target), 
                    backup_type="pre_restore",
                    description=f"Pre-restore backup before restoring {backup_id}"
                )
                self.logger.info(f"Created pre-restore backup: {restore_backup_id}")
            
            # Restore the file
            self._restore_file(backup_path, target)
            
            self.logger.info(f"Successfully restored {backup_id} to {target}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring backup {backup_id}: {e}")
            return False
    
    def list_backups(self, file_pattern: str = None, backup_type: str = None) -> List[Dict]:
        """
        List available backups with optional filtering
        
        Args:
            file_pattern: Filter by file name pattern
            backup_type: Filter by backup type
            
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        for backup_id, info in self.metadata.items():
            # Apply filters
            if file_pattern and file_pattern.lower() not in info['original_file'].lower():
                continue
            
            if backup_type and info['backup_type'] != backup_type:
                continue
            
            # Add computed information
            backup_info = info.copy()
            backup_info['age_days'] = self._calculate_backup_age(info['timestamp'])
            backup_info['size_mb'] = info['file_size'] / (1024 * 1024)
            
            backups.append(backup_info)
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return backups
    
    def cleanup_backups(self, older_than_days: int = None, keep_minimum: int = 3) -> int:
        """
        Cleanup old backups based on age and retention policy
        
        Args:
            older_than_days: Remove backups older than this many days
            keep_minimum: Always keep at least this many backups per file
            
        Returns:
            Number of backups removed
        """
        if older_than_days is None:
            older_than_days = self.config.get('retention_days', 30)
        
        removed_count = 0
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        # Group backups by original file
        file_backups = {}
        for backup_id, info in self.metadata.items():
            original_file = info['original_file']
            if original_file not in file_backups:
                file_backups[original_file] = []
            file_backups[original_file].append((backup_id, info))
        
        # Process each file's backups
        for original_file, backups in file_backups.items():
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x[1]['timestamp'], reverse=True)
            
            # Keep minimum number of recent backups
            backups_to_check = backups[keep_minimum:]
            
            # Remove old backups
            for backup_id, info in backups_to_check:
                backup_time = datetime.fromisoformat(info['timestamp'])
                if backup_time < cutoff_date:
                    if self._remove_backup(backup_id):
                        removed_count += 1
        
        self.logger.info(f"Cleaned up {removed_count} old backups")
        return removed_count
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """Get detailed information about a specific backup"""
        if backup_id not in self.metadata:
            return None
        
        info = self.metadata[backup_id].copy()
        info['age_days'] = self._calculate_backup_age(info['timestamp'])
        info['size_mb'] = info['file_size'] / (1024 * 1024)
        info['exists'] = Path(info['backup_path']).exists()
        
        if info['exists']:
            info['integrity_ok'] = self._verify_backup_integrity(backup_id)
        
        return info
    
    def create_batch_backup(self, file_paths: List[str], description: str = None) -> List[str]:
        """
        Create backups for multiple files in a batch
        
        Args:
            file_paths: List of file paths to backup
            description: Description for the batch backup
            
        Returns:
            List of backup IDs created
        """
        backup_ids = []
        batch_description = description or f"Batch backup of {len(file_paths)} files"
        
        for file_path in file_paths:
            try:
                backup_id = self.create_backup(
                    file_path, 
                    backup_type="batch",
                    description=f"{batch_description} - {Path(file_path).name}"
                )
                backup_ids.append(backup_id)
            except Exception as e:
                self.logger.error(f"Failed to backup {file_path} in batch: {e}")
        
        self.logger.info(f"Created batch backup with {len(backup_ids)} files")
        return backup_ids
    
    def _copy_file(self, source: Path, destination: Path) -> Tuple[int, str]:
        """Copy file with optional compression and return size and checksum"""
        if self.compression_enabled:
            return self._copy_compressed(source, destination)
        else:
            return self._copy_uncompressed(source, destination)
    
    def _copy_compressed(self, source: Path, destination: Path) -> Tuple[int, str]:
        """Copy file with gzip compression"""
        checksum = hashlib.md5()
        
        with open(source, 'rb') as src:
            with gzip.open(destination, 'wb', compresslevel=self.compression_level) as dst:
                while True:
                    chunk = src.read(8192)
                    if not chunk:
                        break
                    checksum.update(chunk)
                    dst.write(chunk)
        
        return destination.stat().st_size, checksum.hexdigest()
    
    def _copy_uncompressed(self, source: Path, destination: Path) -> Tuple[int, str]:
        """Copy file without compression"""
        checksum = hashlib.md5()
        
        with open(source, 'rb') as src:
            with open(destination, 'wb') as dst:
                while True:
                    chunk = src.read(8192)
                    if not chunk:
                        break
                    checksum.update(chunk)
                    dst.write(chunk)
        
        return destination.stat().st_size, checksum.hexdigest()
    
    def _restore_file(self, backup_path: Path, target_path: Path):
        """Restore file from backup with proper decompression"""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if backup_path.suffix == '.gz':
            # Decompress
            with gzip.open(backup_path, 'rb') as src:
                with open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        else:
            # Direct copy
            shutil.copy2(backup_path, target_path)
    
    def _verify_backup_integrity(self, backup_id: str) -> bool:
        """Verify backup file integrity using checksum"""
        try:
            info = self.metadata[backup_id]
            backup_path = Path(info['backup_path'])
            
            if not backup_path.exists():
                return False
            
            # Calculate current checksum
            if info['compression_used']:
                current_checksum = self._calculate_compressed_checksum(backup_path)
            else:
                current_checksum = self._calculate_file_checksum(backup_path)
            
            return current_checksum == info['checksum']
            
        except Exception as e:
            self.logger.error(f"Error verifying backup {backup_id}: {e}")
            return False
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file"""
        checksum = hashlib.md5()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                checksum.update(chunk)
        return checksum.hexdigest()
    
    def _calculate_compressed_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of compressed file content"""
        checksum = hashlib.md5()
        with gzip.open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                checksum.update(chunk)
        return checksum.hexdigest()
    
    def _remove_backup(self, backup_id: str) -> bool:
        """Remove a backup file and its metadata"""
        try:
            info = self.metadata[backup_id]
            backup_path = Path(info['backup_path'])
            
            if backup_path.exists():
                backup_path.unlink()
            
            del self.metadata[backup_id]
            self._save_metadata()
            
            self.logger.debug(f"Removed backup {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing backup {backup_id}: {e}")
            return False
    
    def _cleanup_old_backups(self, file_stem: str):
        """Cleanup old backups for a specific file"""
        max_backups = self.config.get('max_backups_per_file', 10)
        
        # Get all backups for this file
        file_backups = []
        for backup_id, info in self.metadata.items():
            if Path(info['original_file']).stem == file_stem:
                file_backups.append((backup_id, info))
        
        # Sort by timestamp (oldest first) 
        file_backups.sort(key=lambda x: x[1]['timestamp'])
        
        # Remove excess backups
        while len(file_backups) > max_backups:
            backup_id, _ = file_backups.pop(0)
            self._remove_backup(backup_id)
    
    def _calculate_backup_age(self, timestamp_str: str) -> float:
        """Calculate age of backup in days"""
        try:
            backup_time = datetime.fromisoformat(timestamp_str)
            return (datetime.now() - backup_time).total_seconds() / 86400
        except:
            return 0.0
    
    def _load_metadata(self) -> Dict:
        """Load backup metadata from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading backup metadata: {e}")
        
        return {}
    
    def _save_metadata(self):
        """Save backup metadata to file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving backup metadata: {e}")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'compression': True,
            'compression_level': 6,
            'retention_days': 30,
            'max_backups_per_file': 10,
            'auto_cleanup': True
        }
    
    def get_storage_usage(self) -> Dict:
        """Get backup storage usage statistics"""
        total_size = 0
        compressed_size = 0
        backup_count = 0
        
        for backup_id, info in self.metadata.items():
            backup_path = Path(info['backup_path'])
            if backup_path.exists():
                backup_count += 1
                size = backup_path.stat().st_size
                total_size += size
                
                if info['compression_used']:
                    compressed_size += size
        
        return {
            'total_backups': backup_count,
            'total_size_mb': total_size / (1024 * 1024),
            'compressed_size_mb': compressed_size / (1024 * 1024),
            'compression_ratio': (compressed_size / total_size) if total_size > 0 else 0,
            'backup_directory': str(self.backup_dir)
        }


def main():
    """Test the backup manager"""
    backup_manager = BackupManager()
    
    # Create a test file
    test_file = Path(tempfile.gettempdir()) / "test_database.lua"
    test_content = """-- Test database file
epochQuestDB = {
    [12345] = {
        "Test Quest",
        {{46834}},
        {{46718}},
        10,
        15
    }
}"""
    
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    print("Testing BackupManager...")
    
    # Create backup
    backup_id = backup_manager.create_backup(str(test_file), description="Test backup")
    print(f"Created backup: {backup_id}")
    
    # List backups
    backups = backup_manager.list_backups()
    print(f"Total backups: {len(backups)}")
    
    # Get backup info
    info = backup_manager.get_backup_info(backup_id)
    print(f"Backup info: {info['description']} ({info['size_mb']:.2f} MB)")
    
    # Storage usage
    usage = backup_manager.get_storage_usage()
    print(f"Storage usage: {usage['total_size_mb']:.2f} MB")
    
    # Test restore
    test_file.unlink()  # Delete original
    success = backup_manager.restore_backup(backup_id)
    print(f"Restore successful: {success}")
    print(f"File exists after restore: {test_file.exists()}")
    
    # Cleanup
    test_file.unlink(missing_ok=True)
    print("BackupManager test completed")


if __name__ == "__main__":
    main()