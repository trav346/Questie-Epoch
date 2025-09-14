#!/usr/bin/env python3
"""
Pipeline State Tracker - Deduplication and processing state management
Tracks what's been processed and what's already in the database
"""

import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, List, Optional

class PipelineStateTracker:
    """
    Tracks pipeline state to avoid reprocessing and duplicates
    """
    
    def __init__(self, state_dir: str = ".pipeline_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        
        # Files to track state
        self.processed_files_db = self.state_dir / "processed_files.db"
        self.existing_quests_cache = self.state_dir / "existing_quests.json"
        self.existing_npcs_cache = self.state_dir / "existing_npcs.json"
        
        # Cache for quick lookups
        self.existing_quests = set()
        self.existing_npcs = set()
        self.processed_files = set()
        
        self._init_database()
        self._load_caches()
        
    def _init_database(self):
        """Initialize SQLite database for tracking processed files"""
        conn = sqlite3.connect(str(self.processed_files_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                filename TEXT PRIMARY KEY,
                processed_date TEXT NOT NULL,
                file_hash TEXT,
                quests_extracted INTEGER,
                npcs_extracted INTEGER,
                items_extracted INTEGER,
                status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_quests (
                quest_id INTEGER PRIMARY KEY,
                quest_name TEXT,
                first_seen TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                times_seen INTEGER DEFAULT 1,
                in_database BOOLEAN DEFAULT 0,
                needs_update BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_npcs (
                npc_id INTEGER PRIMARY KEY,
                npc_name TEXT,
                first_seen TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                times_seen INTEGER DEFAULT 1,
                in_database BOOLEAN DEFAULT 0,
                needs_update BOOLEAN DEFAULT 0
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_quest_database ON processed_quests(in_database)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_npc_database ON processed_npcs(in_database)')
        
        conn.commit()
        conn.close()
    
    def _load_caches(self):
        """Load cached data for quick lookups"""
        # Load existing quests cache
        if self.existing_quests_cache.exists():
            with open(self.existing_quests_cache, 'r') as f:
                self.existing_quests = set(json.load(f))
        
        # Load existing NPCs cache
        if self.existing_npcs_cache.exists():
            with open(self.existing_npcs_cache, 'r') as f:
                self.existing_npcs = set(json.load(f))
        
        # Load processed files from database
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM processed_files WHERE status = 'completed'")
        self.processed_files = set(row[0] for row in cursor.fetchall())
        conn.close()
    
    def is_file_processed(self, filename: str) -> bool:
        """Check if a file has already been processed"""
        # Quick cache check first
        if filename in self.processed_files:
            return True
            
        # Database check for confirmation
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT status FROM processed_files WHERE filename = ?",
            (filename,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == 'completed':
            self.processed_files.add(filename)
            return True
        return False
    
    def mark_file_processed(self, filename: str, quests: int = 0, npcs: int = 0, items: int = 0, file_hash: str = None):
        """Mark a file as processed"""
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO processed_files 
            (filename, processed_date, file_hash, quests_extracted, npcs_extracted, items_extracted, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename, datetime.now().isoformat(), file_hash, quests, npcs, items, 'completed'))
        
        conn.commit()
        conn.close()
        
        # Update cache
        self.processed_files.add(filename)
    
    def is_quest_in_database(self, quest_id: int) -> bool:
        """Check if a quest is already in the database"""
        return quest_id in self.existing_quests
    
    def is_npc_in_database(self, npc_id: int) -> bool:
        """Check if an NPC is already in the database"""
        return npc_id in self.existing_npcs
    
    def track_quest(self, quest_id: int, quest_name: str = None, in_database: bool = False):
        """Track that we've seen this quest"""
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Use UPSERT syntax for SQLite 3.24+
        cursor.execute('''
            INSERT INTO processed_quests (quest_id, quest_name, first_seen, last_updated, in_database)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(quest_id) DO UPDATE SET
                quest_name = COALESCE(excluded.quest_name, quest_name),
                last_updated = excluded.last_updated,
                times_seen = times_seen + 1,
                in_database = in_database OR excluded.in_database
        ''', (quest_id, quest_name, now, now, in_database))
        
        conn.commit()
        conn.close()
    
    def track_npc(self, npc_id: int, npc_name: str = None, in_database: bool = False):
        """Track that we've seen this NPC"""
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO processed_npcs (npc_id, npc_name, first_seen, last_updated, in_database)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(npc_id) DO UPDATE SET
                npc_name = COALESCE(excluded.npc_name, npc_name),
                last_updated = excluded.last_updated,
                times_seen = times_seen + 1,
                in_database = in_database OR excluded.in_database
        ''', (npc_id, npc_name, now, now, in_database))
        
        conn.commit()
        conn.close()
    
    def load_existing_database_ids(self, quest_db_path: str = None, npc_db_path: str = None) -> tuple:
        """Load IDs that are already in the database files"""
        import re
        
        # Default paths if not provided
        if not quest_db_path:
            # Update this path to your Questie installation
            quest_db_path = "../../Database/Epoch/epochQuestDB.lua"
        if not npc_db_path:
            # Update this path to your Questie installation
            npc_db_path = "../../Database/Epoch/epochNpcDB.lua"
        
        existing_quests = set()
        existing_npcs = set()
        
        # Parse quest database
        if Path(quest_db_path).exists():
            with open(quest_db_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract quest IDs using regex
                quest_matches = re.findall(r'\[(\d+)\]\s*=\s*{', content)
                existing_quests = set(int(id) for id in quest_matches)
                print(f"   Loaded {len(existing_quests)} existing quests from database")
        
        # Parse NPC database
        if Path(npc_db_path).exists():
            with open(npc_db_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract NPC IDs using regex
                npc_matches = re.findall(r'\[(\d+)\]\s*=\s*{', content)
                existing_npcs = set(int(id) for id in npc_matches)
                print(f"   Loaded {len(existing_npcs)} existing NPCs from database")
        
        # Save to cache
        with open(self.existing_quests_cache, 'w') as f:
            json.dump(list(existing_quests), f)
        
        with open(self.existing_npcs_cache, 'w') as f:
            json.dump(list(existing_npcs), f)
        
        # Update memory cache
        self.existing_quests = existing_quests
        self.existing_npcs = existing_npcs
        
        # Update database records
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        # Mark existing quests
        for quest_id in existing_quests:
            cursor.execute('''
                INSERT OR IGNORE INTO processed_quests 
                (quest_id, first_seen, last_updated, in_database)
                VALUES (?, 'existing', ?, 1)
            ''', (quest_id, datetime.now().isoformat()))
        
        # Mark existing NPCs
        for npc_id in existing_npcs:
            cursor.execute('''
                INSERT OR IGNORE INTO processed_npcs
                (npc_id, first_seen, last_updated, in_database)
                VALUES (?, 'existing', ?, 1)
            ''', (npc_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return existing_quests, existing_npcs
    
    def get_unprocessed_files(self, directory: str) -> List[Path]:
        """Get list of files that haven't been processed yet"""
        all_files = list(Path(directory).glob("issue_*.txt"))
        unprocessed = [f for f in all_files if f.name not in self.processed_files]
        return sorted(unprocessed)  # Sort for consistent processing order
    
    def get_new_quests(self) -> Set[int]:
        """Get quest IDs that are not in the database yet"""
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT quest_id FROM processed_quests 
            WHERE in_database = 0 AND times_seen >= 1
        """)
        new_quests = set(row[0] for row in cursor.fetchall())
        conn.close()
        
        return new_quests
    
    def get_new_npcs(self) -> Set[int]:
        """Get NPC IDs that are not in the database yet"""
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT npc_id FROM processed_npcs 
            WHERE in_database = 0 AND times_seen >= 1
        """)
        new_npcs = set(row[0] for row in cursor.fetchall())
        conn.close()
        
        return new_npcs
    
    def get_statistics(self) -> Dict:
        """Get processing statistics"""
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        stats = {}
        
        # Files
        cursor.execute("SELECT COUNT(*) FROM processed_files")
        stats['total_files_processed'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(quests_extracted), SUM(npcs_extracted), SUM(items_extracted) FROM processed_files")
        result = cursor.fetchone()
        stats['total_quests_extracted'] = result[0] or 0
        stats['total_npcs_extracted'] = result[1] or 0
        stats['total_items_extracted'] = result[2] or 0
        
        # Quests
        cursor.execute("SELECT COUNT(*) FROM processed_quests")
        stats['unique_quests_seen'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_quests WHERE in_database = 1")
        stats['quests_already_in_database'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_quests WHERE in_database = 0")
        stats['new_quests_found'] = cursor.fetchone()[0]
        
        # NPCs
        cursor.execute("SELECT COUNT(*) FROM processed_npcs")
        stats['unique_npcs_seen'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_npcs WHERE in_database = 1")
        stats['npcs_already_in_database'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_npcs WHERE in_database = 0")
        stats['new_npcs_found'] = cursor.fetchone()[0]
        
        conn.close()
        
        return stats
    
    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file for change detection"""
        md5_hash = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def reset_processing_state(self):
        """Reset all processing state (for testing or fresh start)"""
        conn = sqlite3.connect(str(self.processed_files_db))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM processed_files")
        cursor.execute("UPDATE processed_quests SET times_seen = 0 WHERE first_seen != 'existing'")
        cursor.execute("UPDATE processed_npcs SET times_seen = 0 WHERE first_seen != 'existing'")
        
        conn.commit()
        conn.close()
        
        # Clear memory cache
        self.processed_files.clear()
        
        print("⚠️  Processing state reset - files can be reprocessed")