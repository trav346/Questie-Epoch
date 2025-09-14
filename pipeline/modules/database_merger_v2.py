#!/usr/bin/env python3
"""
Database Merger V2 - Enhanced for additive merging with comparator integration
Implements smart merging strategies based on comparator categories
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
import shutil

class DatabaseMergerV2:
    """
    Enhanced database merger that implements additive merging strategies
    Works with database_comparator_v2 output to safely merge data
    """
    
    def __init__(self, database_paths: Dict = None):
        self.logger = logging.getLogger(__name__)
        
        # Database paths - update to your Questie installation
        default_base = Path("../../Database/Epoch")
        self.quest_db_path = database_paths.get('quest_db', default_base / "epochQuestDB.lua") if database_paths else default_base / "epochQuestDB.lua"
        self.npc_db_path = database_paths.get('npc_db', default_base / "epochNpcDB.lua") if database_paths else default_base / "epochNpcDB.lua"
        
        # Backup directory
        self.backup_dir = Path("database_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Current database in memory
        self.quest_db = {}
        self.npc_db = {}
        
        # Statistics
        self.stats = {
            'new_quests': 0,
            'replaced_stubs': 0,
            'added_objectives': 0,
            'added_npcs': 0,
            'merged_coordinates': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Track all changes for reporting
        self.changes_log = []
        
    def load_databases(self):
        """Load existing databases into memory"""
        self.logger.info("Loading existing databases...")
        
        # Load quest database
        if self.quest_db_path.exists():
            self.quest_db = self._parse_quest_database(self.quest_db_path)
            self.logger.info(f"Loaded {len(self.quest_db)} quests from database")
        
        # Load NPC database
        if self.npc_db_path.exists():
            self.npc_db = self._parse_npc_database(self.npc_db_path)
            self.logger.info(f"Loaded {len(self.npc_db)} NPCs from database")
    
    def apply_merge_instructions(self, merge_instructions: Dict, writer_output: Dict = None) -> Dict:
        """
        Apply merge instructions from comparator using additive merging
        
        Args:
            merge_instructions: Output from database_comparator_v2
            writer_output: Optional output from database_writer_v2 with formatted entries
            
        Returns:
            Dictionary with merge results and statistics
        """
        self.logger.info("Starting database merge...")
        
        # Reset statistics
        self.stats = {key: 0 for key in self.stats}
        self.changes_log = []
        
        # Create backup before merging
        backup_path = self._create_backup()
        
        # Load current databases
        self.load_databases()
        
        results = {
            'success': True,
            'backup_path': str(backup_path),
            'stats': {},
            'changes': [],
            'errors': []
        }
        
        try:
            # Process each category
            for category, data in merge_instructions.items():
                if category == 'metadata':
                    continue
                
                self.logger.info(f"Merging {category}...")
                
                if category == 'new_quests':
                    self._merge_new_quests(data)
                elif category == 'runtime_stubs':
                    self._merge_runtime_stubs(data)
                elif category == 'missing_objectives':
                    self._merge_missing_objectives(data)
                elif category == 'missing_npcs':
                    self._merge_missing_npcs(data)
                elif category == 'missing_coordinates':
                    self._merge_missing_coordinates(data)
            
            # Save merged databases
            self._save_databases()
            
            results['stats'] = self.stats.copy()
            results['changes'] = self.changes_log.copy()
            
            self.logger.info(f"Merge complete: {self.stats}")
            
        except Exception as e:
            self.logger.error(f"Error during merge: {e}")
            results['success'] = False
            results['errors'].append(str(e))
            
            # Offer to restore backup
            self.logger.info(f"Backup available at: {backup_path}")
        
        return results
    
    def _merge_new_quests(self, data: Dict):
        """Add new quests to database"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = str(quest.get('id'))
            quest_data = quest.get('data', {})
            
            # Check if already exists (shouldn't based on comparator)
            if quest_id in self.quest_db:
                self.logger.warning(f"Quest {quest_id} already exists, skipping")
                self.stats['skipped'] += 1
                continue
            
            # Add to database
            self.quest_db[quest_id] = quest_data
            self.stats['new_quests'] += 1
            
            self.changes_log.append({
                'action': 'ADD_QUEST',
                'id': quest_id,
                'name': quest_data.get('name', 'Unknown')
            })
    
    def _merge_runtime_stubs(self, data: Dict):
        """Replace runtime stubs with real data"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = str(quest.get('id'))
            quest_data = quest.get('data', {})
            
            # Verify it's actually a stub
            if quest_id in self.quest_db:
                existing = self.quest_db[quest_id]
                if isinstance(existing, dict) and existing.get('name', '').startswith('[Epoch]'):
                    # Replace the stub
                    self.quest_db[quest_id] = quest_data
                    self.stats['replaced_stubs'] += 1
                    
                    self.changes_log.append({
                        'action': 'REPLACE_STUB',
                        'id': quest_id,
                        'old_name': existing.get('name'),
                        'new_name': quest_data.get('name')
                    })
                else:
                    self.logger.warning(f"Quest {quest_id} is not a stub, using additive merge")
                    self._additive_merge_quest(quest_id, quest_data)
    
    def _merge_missing_objectives(self, data: Dict):
        """Add missing objectives to existing quests (additive)"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = str(quest.get('id'))
            new_objectives = quest.get('data', {}).get('objectives', {})
            
            if quest_id not in self.quest_db:
                self.logger.warning(f"Quest {quest_id} not found for objective merge")
                continue
            
            existing = self.quest_db[quest_id]
            existing_objectives = existing.get('objectives', {})
            
            # Additive merge of objectives
            merged_objectives = self._merge_objectives(existing_objectives, new_objectives)
            
            if merged_objectives != existing_objectives:
                existing['objectives'] = merged_objectives
                self.stats['added_objectives'] += 1
                
                self.changes_log.append({
                    'action': 'ADD_OBJECTIVES',
                    'id': quest_id,
                    'added': self._diff_objectives(existing_objectives, merged_objectives)
                })
    
    def _merge_missing_npcs(self, data: Dict):
        """Add missing quest giver and turn-in NPCs"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = str(quest.get('id'))
            quest_data = quest.get('data', {})
            
            if quest_id not in self.quest_db:
                self.logger.warning(f"Quest {quest_id} not found for NPC merge")
                continue
            
            existing = self.quest_db[quest_id]
            changes_made = False
            
            # Merge startedBy NPCs
            new_started = quest_data.get('startedBy', {})
            if new_started and new_started.get('npcs'):
                existing_started = existing.get('startedBy', {})
                merged_started = self._merge_started_by(existing_started, new_started)
                if merged_started != existing_started:
                    existing['startedBy'] = merged_started
                    changes_made = True
            
            # Merge finishedBy NPCs
            new_finished = quest_data.get('finishedBy', {})
            if new_finished and new_finished.get('npcs'):
                existing_finished = existing.get('finishedBy', {})
                merged_finished = self._merge_finished_by(existing_finished, new_finished)
                if merged_finished != existing_finished:
                    existing['finishedBy'] = merged_finished
                    changes_made = True
            
            if changes_made:
                self.stats['added_npcs'] += 1
                self.changes_log.append({
                    'action': 'ADD_NPCS',
                    'id': quest_id,
                    'startedBy': new_started.get('npcs', []),
                    'finishedBy': new_finished.get('npcs', [])
                })
    
    def _merge_missing_coordinates(self, data: Dict):
        """Additively merge spawn coordinates"""
        # This would handle coordinate merging for NPCs
        # Implementation depends on having NPC data with coordinates
        pass
    
    def _additive_merge_quest(self, quest_id: str, new_data: Dict):
        """Perform additive merge of quest data"""
        existing = self.quest_db[quest_id]
        
        # Merge objectives
        if new_data.get('objectives'):
            existing['objectives'] = self._merge_objectives(
                existing.get('objectives', {}),
                new_data['objectives']
            )
        
        # Merge NPCs
        if new_data.get('startedBy'):
            existing['startedBy'] = self._merge_started_by(
                existing.get('startedBy', {}),
                new_data['startedBy']
            )
        
        if new_data.get('finishedBy'):
            existing['finishedBy'] = self._merge_finished_by(
                existing.get('finishedBy', {}),
                new_data['finishedBy']
            )
        
        # Update text fields if missing
        if not existing.get('objectivesText') and new_data.get('objectivesText'):
            existing['objectivesText'] = new_data['objectivesText']
    
    def _merge_objectives(self, existing: Dict, new: Dict) -> Dict:
        """Additively merge quest objectives"""
        if not existing:
            return new
        if not new:
            return existing
        
        merged = existing.copy()
        
        # Merge items
        existing_items = set()
        for item in existing.get('items', []):
            if isinstance(item, dict):
                existing_items.add(item.get('id'))
        
        for item in new.get('items', []):
            if isinstance(item, dict) and item.get('id') not in existing_items:
                if 'items' not in merged:
                    merged['items'] = []
                merged['items'].append(item)
        
        # Merge creatures
        existing_creatures = set()
        for creature in existing.get('creatures', []):
            if isinstance(creature, dict):
                existing_creatures.add(creature.get('id'))
        
        for creature in new.get('creatures', []):
            if isinstance(creature, dict) and creature.get('id') not in existing_creatures:
                if 'creatures' not in merged:
                    merged['creatures'] = []
                merged['creatures'].append(creature)
        
        # Merge objects
        existing_objects = set()
        for obj in existing.get('objects', []):
            if isinstance(obj, dict):
                existing_objects.add(obj.get('id'))
        
        for obj in new.get('objects', []):
            if isinstance(obj, dict) and obj.get('id') not in existing_objects:
                if 'objects' not in merged:
                    merged['objects'] = []
                merged['objects'].append(obj)
        
        return merged
    
    def _merge_started_by(self, existing: Dict, new: Dict) -> Dict:
        """Additively merge startedBy data"""
        if not existing:
            return new
        if not new:
            return existing
        
        merged = existing.copy()
        
        # Merge NPCs
        existing_npcs = set(existing.get('npcs', []))
        for npc in new.get('npcs', []):
            if npc not in existing_npcs:
                if 'npcs' not in merged:
                    merged['npcs'] = []
                merged['npcs'].append(npc)
        
        # Merge objects
        existing_objs = set(existing.get('objects', []))
        for obj in new.get('objects', []):
            if obj not in existing_objs:
                if 'objects' not in merged:
                    merged['objects'] = []
                merged['objects'].append(obj)
        
        # Merge items
        existing_items = set(existing.get('items', []))
        for item in new.get('items', []):
            if item not in existing_items:
                if 'items' not in merged:
                    merged['items'] = []
                merged['items'].append(item)
        
        return merged
    
    def _merge_finished_by(self, existing: Dict, new: Dict) -> Dict:
        """Additively merge finishedBy data"""
        if not existing:
            return new
        if not new:
            return existing
        
        merged = existing.copy()
        
        # Merge NPCs
        existing_npcs = set(existing.get('npcs', []))
        for npc in new.get('npcs', []):
            if npc not in existing_npcs:
                if 'npcs' not in merged:
                    merged['npcs'] = []
                merged['npcs'].append(npc)
        
        # Merge objects
        existing_objs = set(existing.get('objects', []))
        for obj in new.get('objects', []):
            if obj not in existing_objs:
                if 'objects' not in merged:
                    merged['objects'] = []
                merged['objects'].append(obj)
        
        return merged
    
    def _diff_objectives(self, old: Dict, new: Dict) -> Dict:
        """Find what was added in objectives"""
        diff = {}
        
        # Check items
        old_items = set(i.get('id') for i in old.get('items', []) if isinstance(i, dict))
        new_items = [i for i in new.get('items', []) if isinstance(i, dict) and i.get('id') not in old_items]
        if new_items:
            diff['items'] = new_items
        
        # Check creatures
        old_creatures = set(c.get('id') for c in old.get('creatures', []) if isinstance(c, dict))
        new_creatures = [c for c in new.get('creatures', []) if isinstance(c, dict) and c.get('id') not in old_creatures]
        if new_creatures:
            diff['creatures'] = new_creatures
        
        # Check objects
        old_objects = set(o.get('id') for o in old.get('objects', []) if isinstance(o, dict))
        new_objects = [o for o in new.get('objects', []) if isinstance(o, dict) and o.get('id') not in old_objects]
        if new_objects:
            diff['objects'] = new_objects
        
        return diff
    
    def _create_backup(self) -> Path:
        """Create timestamped backup of databases"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / f"backup_{timestamp}"
        backup_subdir.mkdir(exist_ok=True)
        
        # Backup quest database
        if self.quest_db_path.exists():
            shutil.copy2(self.quest_db_path, backup_subdir / "epochQuestDB.lua")
        
        # Backup NPC database
        if self.npc_db_path.exists():
            shutil.copy2(self.npc_db_path, backup_subdir / "epochNpcDB.lua")
        
        self.logger.info(f"Created backup at: {backup_subdir}")
        return backup_subdir
    
    def _parse_quest_database(self, path: Path) -> Dict:
        """Parse quest database file"""
        quests = {}
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all quest entries
        pattern = r'\[(\d+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            quest_id = match.group(1)
            quest_data_str = match.group(2)
            
            # Parse the quest data (simplified - would need proper Lua parser)
            quest_data = self._parse_quest_entry(quest_data_str)
            quests[quest_id] = quest_data
        
        return quests
    
    def _parse_quest_entry(self, lua_str: str) -> Dict:
        """Parse a single quest entry from Lua string"""
        # This is a simplified parser
        # In production, would use a proper Lua parser
        quest = {}
        
        # Extract name (first quoted string)
        name_match = re.search(r'"([^"]+)"', lua_str)
        if name_match:
            quest['name'] = name_match.group(1)
            
            # Check if it's a runtime stub
            if quest['name'].startswith('[Epoch]'):
                quest['is_runtime_stub'] = True
        
        # Check for objectives
        if '{{{' in lua_str or '{{' in lua_str:
            quest['has_objectives'] = True
        
        return quest
    
    def _parse_npc_database(self, path: Path) -> Dict:
        """Parse NPC database file"""
        # Similar to quest parsing
        npcs = {}
        # Implementation would be similar to _parse_quest_database
        return npcs
    
    def _save_databases(self):
        """Save merged databases back to files"""
        # For now, generate merge instructions file
        # In production, would write directly to database files
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merge_file = Path(f"merged_database_{timestamp}.lua")
        
        with open(merge_file, 'w', encoding='utf-8') as f:
            f.write("-- Merged Database Changes\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Statistics: {self.stats}\n\n")
            
            f.write("-- Apply these changes to epochQuestDB.lua\n\n")
            
            # Write summary of changes
            for change in self.changes_log:
                f.write(f"-- {change}\n")
        
        self.logger.info(f"Merge instructions written to: {merge_file}")
    
    def restore_backup(self, backup_path: Path) -> bool:
        """Restore databases from backup"""
        try:
            # Restore quest database
            quest_backup = backup_path / "epochQuestDB.lua"
            if quest_backup.exists():
                shutil.copy2(quest_backup, self.quest_db_path)
            
            # Restore NPC database
            npc_backup = backup_path / "epochNpcDB.lua"
            if npc_backup.exists():
                shutil.copy2(npc_backup, self.npc_db_path)
            
            self.logger.info(f"Restored databases from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            return False

def main():
    """Test the enhanced database merger"""
    # Load comparison report
    report_file = Path("comparison_reports/comparison_report_20250906_231414.json")
    
    if not report_file.exists():
        print(f"Report file not found: {report_file}")
        return
    
    with open(report_file, 'r') as f:
        comparison_report = json.load(f)
    
    # Extract merge instructions
    merge_instructions = comparison_report.get('merge_instructions', {})
    
    # Create merger and apply
    merger = DatabaseMergerV2()
    results = merger.apply_merge_instructions(merge_instructions)
    
    # Print results
    print("\n=== DATABASE MERGER RESULTS ===")
    print(f"Success: {results['success']}")
    print(f"Backup: {results['backup_path']}")
    print(f"\nStatistics:")
    for key, value in results['stats'].items():
        print(f"  {key}: {value}")
    
    print(f"\nTotal changes logged: {len(results['changes'])}")
    
    if results.get('errors'):
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")

if __name__ == "__main__":
    main()