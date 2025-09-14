#!/usr/bin/env python3
"""
Database Merger - Apply approved merges to database
Safely merges validated and resolved data into the database
"""

import logging
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pathlib import Path


class DatabaseMerger:
    """
    Merges approved data into the database
    Handles the actual database updates after all validation and resolution
    """
    
    def __init__(self, database_path: str, backup_manager=None):
        self.logger = logging.getLogger(__name__)
        self.database_path = Path(database_path)
        self.backup_manager = backup_manager
        
        # Track merge statistics
        self.merge_stats = {
            'quests_added': 0,
            'quests_updated': 0,
            'quests_skipped': 0,
            'npcs_added': 0,
            'npcs_updated': 0,
            'npcs_skipped': 0,
            'errors': 0,
        }
        
        # Merge history
        self.merge_history = []
    
    def merge(self, new_data: Dict, merge_decisions: Dict) -> Tuple[bool, Dict]:
        """
        Apply merge decisions to database
        
        Args:
            new_data: New data to merge
            merge_decisions: Decisions from merge_decision_engine
            
        Returns:
            (success, merge_report)
        """
        self.logger.info("Starting database merge")
        
        # Create backup before merge
        if self.backup_manager:
            backup_path = self.backup_manager.create_backup(
                'pre_merge', 
                {'merge_size': len(new_data)}
            )
            self.logger.info(f"Created backup: {backup_path}")
        
        # Reset stats
        self.merge_stats = {k: 0 for k in self.merge_stats}
        
        # Load current database
        current_db = self._load_database()
        
        # Apply merges
        success = True
        errors = []
        
        for entity_id, decision in merge_decisions.items():
            try:
                if decision['action'] == 'add':
                    self._add_entity(current_db, entity_id, new_data[entity_id])
                elif decision['action'] == 'update':
                    self._update_entity(current_db, entity_id, new_data[entity_id])
                elif decision['action'] == 'skip':
                    self._skip_entity(entity_id, decision.get('reason'))
                else:
                    self.logger.warning(f"Unknown action: {decision['action']} for {entity_id}")
            except Exception as e:
                self.logger.error(f"Error merging {entity_id}: {str(e)}")
                errors.append(f"{entity_id}: {str(e)}")
                self.merge_stats['errors'] += 1
                success = False
        
        # Save updated database if successful
        if success:
            self._save_database(current_db)
            self.logger.info("Database saved successfully")
        else:
            self.logger.error(f"Merge completed with {len(errors)} errors")
        
        # Generate merge report
        report = self._generate_merge_report(errors)
        
        # Record in history
        self.merge_history.append({
            'timestamp': datetime.now().isoformat(),
            'stats': self.merge_stats.copy(),
            'success': success,
        })
        
        return success, report
    
    def _load_database(self) -> Dict:
        """Load current database"""
        databases = {
            'quests': {},
            'npcs': {},
        }
        
        # Load quest database
        quest_db_path = self.database_path / 'epochQuestDB.lua'
        if quest_db_path.exists():
            databases['quests'] = self._parse_lua_database(quest_db_path)
        
        # Load NPC database
        npc_db_path = self.database_path / 'epochNpcDB.lua'
        if npc_db_path.exists():
            databases['npcs'] = self._parse_lua_database(npc_db_path)
        
        return databases
    
    def _save_database(self, databases: Dict):
        """Save updated database"""
        # Save quest database
        quest_db_path = self.database_path / 'Wotlk' / 'wotlkQuestDB.lua'
        self._write_lua_database(quest_db_path, databases['quests'], 'wotlkQuestDB')
        
        # Save NPC database
        npc_db_path = self.database_path / 'Wotlk' / 'wotlkNpcDB.lua'
        self._write_lua_database(npc_db_path, databases['npcs'], 'wotlkNpcDB')
    
    def _add_entity(self, database: Dict, entity_id: int, data: Dict):
        """Add new entity to database"""
        entity_type = 'quest' if 'quest_id' in data else 'npc'
        db_key = 'quests' if entity_type == 'quest' else 'npcs'
        
        if entity_id in database[db_key]:
            self.logger.warning(f"{entity_type} {entity_id} already exists, updating instead")
            self._update_entity(database, entity_id, data)
            return
        
        # Add to database
        database[db_key][entity_id] = self._format_for_database(data, entity_type)
        
        # Update stats
        if entity_type == 'quest':
            self.merge_stats['quests_added'] += 1
        else:
            self.merge_stats['npcs_added'] += 1
        
        self.logger.debug(f"Added {entity_type} {entity_id}")
    
    def _update_entity(self, database: Dict, entity_id: int, data: Dict):
        """Update existing entity in database"""
        entity_type = 'quest' if 'quest_id' in data else 'npc'
        db_key = 'quests' if entity_type == 'quest' else 'npcs'
        
        if entity_id not in database[db_key]:
            self.logger.warning(f"{entity_type} {entity_id} doesn't exist, adding instead")
            self._add_entity(database, entity_id, data)
            return
        
        # Update in database
        database[db_key][entity_id] = self._format_for_database(data, entity_type)
        
        # Update stats
        if entity_type == 'quest':
            self.merge_stats['quests_updated'] += 1
        else:
            self.merge_stats['npcs_updated'] += 1
        
        self.logger.debug(f"Updated {entity_type} {entity_id}")
    
    def _skip_entity(self, entity_id: int, reason: str = None):
        """Skip entity (no merge)"""
        # Determine type based on ID (simplified - would need better logic)
        entity_type = 'quest' if entity_id < 100000 else 'npc'
        
        # Update stats
        if entity_type == 'quest':
            self.merge_stats['quests_skipped'] += 1
        else:
            self.merge_stats['npcs_skipped'] += 1
        
        self.logger.debug(f"Skipped {entity_type} {entity_id}: {reason}")
    
    def _format_for_database(self, data: Dict, entity_type: str) -> List:
        """Format data for Lua database structure"""
        if entity_type == 'quest':
            # Format as 30-element array for quests
            return [
                data.get('name'),
                data.get('startedBy'),
                data.get('finishedBy'),
                data.get('requiredLevel'),
                data.get('questLevel'),
                data.get('requiredRaces'),
                data.get('requiredClasses'),
                data.get('objectivesText'),
                data.get('triggerEnd'),
                data.get('objectives'),
                data.get('sourceItemId'),
                data.get('preQuestGroup'),
                data.get('preQuestSingle'),
                data.get('childQuests'),
                data.get('inGroupWith'),
                data.get('exclusiveTo'),
                data.get('zoneOrSort'),
                data.get('requiredSkill'),
                data.get('requiredMinRep'),
                data.get('requiredMaxRep'),
                data.get('requiredSourceItems'),
                data.get('nextQuestInChain'),
                data.get('questFlags'),
                data.get('specialFlags'),
                data.get('parentQuest'),
                data.get('reputationReward'),
                data.get('extraObjectives'),
                data.get('requiredSpell'),
                data.get('requiredSpecialization'),
                data.get('requiredMaxLevel'),
            ]
        else:  # NPC
            # Format as 15-element array for NPCs
            return [
                data.get('name'),
                data.get('minLevelHealth'),
                data.get('maxLevelHealth'),
                data.get('minLevel'),
                data.get('maxLevel'),
                data.get('rank'),
                data.get('spawns'),
                data.get('waypoints'),
                data.get('zoneID'),
                data.get('questStarts'),
                data.get('questEnds'),
                data.get('factionID'),
                data.get('friendlyToFaction'),
                data.get('subName'),
                data.get('npcFlags'),
            ]
    
    def _parse_lua_database(self, path: Path) -> Dict:
        """Parse Lua database file into Python dict with improved robustness"""
        database = {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find the start of the database table
            start_match = re.search(r'\w+\s*=\s*{', content)
            if not start_match:
                self.logger.error(f"Could not find start of database table in {path}")
                return {}

            # Work with content from the start of the table
            content = content[start_match.end():]

            # Use a more robust way to find entries, accounting for nested tables
            entry_pattern = re.compile(r'\s*\[(\d+)\]\s*=\s*\{', re.DOTALL)
            
            last_pos = 0
            while True:
                match = entry_pattern.search(content, last_pos)
                if not match:
                    break

                entity_id = int(match.group(1))
                
                # Find the corresponding closing brace for this entry
                brace_level = 1
                start_index = match.end()
                end_index = -1
                
                for i in range(start_index, len(content)):
                    if content[i] == '{':
                        brace_level += 1
                    elif content[i] == '}':
                        brace_level -= 1
                    
                    if brace_level == 0:
                        end_index = i
                        break
                
                if end_index != -1:
                    # Extract the raw string content of the entry
                    entry_content = content[start_index:end_index]
                    database[entity_id] = entry_content
                    last_pos = end_index + 1
                else:
                    # Could not find matching brace, move to next potential entry
                    last_pos = match.end()

        except Exception as e:
            self.logger.error(f"Error parsing {path}: {str(e)}")

        return database
    
    def _write_lua_database(self, path: Path, database: Dict, db_name: str):
        """Write Python dict to Lua database file"""
        lines = []
        lines.append(f"{db_name} = {{")
        
        for entity_id, data in sorted(database.items()):
            # Format the Lua entry
            lua_entry = self._format_lua_entry(entity_id, data)
            lines.append(lua_entry)
        
        lines.append("}")
        
        # Write to file
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _format_lua_entry(self, entity_id: int, data) -> str:
        """Format single database entry as Lua"""
        # This would properly format the data as Lua
        # Simplified for demonstration
        if isinstance(data, list):
            # Format array data
            formatted = ', '.join([self._format_lua_value(v) for v in data])
            return f"    [{entity_id}] = {{{formatted}}},"
        else:
            # Already formatted string (from parsing)
            return f"    [{entity_id}] = {{{data}}},"
    
    def _format_lua_value(self, value) -> str:
        """Format a single value for Lua"""
        if value is None:
            return "nil"
        elif isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            formatted = ', '.join([self._format_lua_value(v) for v in value])
            return f"{{{formatted}}}"
        elif isinstance(value, dict):
            # Format dict as Lua table
            items = []
            for k, v in value.items():
                if isinstance(k, int):
                    items.append(f"[{k}] = {self._format_lua_value(v)}")
                else:
                    items.append(f'["{k}"] = {self._format_lua_value(v)}')
            return f"{{{', '.join(items)}}}"
        else:
            return str(value)
    
    def _generate_merge_report(self, errors: List[str]) -> Dict:
        """Generate detailed merge report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.merge_stats.copy(),
            'success': len(errors) == 0,
            'errors': errors,
            'summary': self._generate_summary(),
        }
        
        return report
    
    def _generate_summary(self) -> str:
        """Generate summary of merge operation"""
        lines = []
        lines.append("=== MERGE SUMMARY ===")
        lines.append(f"Quests: {self.merge_stats['quests_added']} added, "
                    f"{self.merge_stats['quests_updated']} updated, "
                    f"{self.merge_stats['quests_skipped']} skipped")
        lines.append(f"NPCs: {self.merge_stats['npcs_added']} added, "
                    f"{self.merge_stats['npcs_updated']} updated, "
                    f"{self.merge_stats['npcs_skipped']} skipped")
        
        if self.merge_stats['errors'] > 0:
            lines.append(f"Errors: {self.merge_stats['errors']}")
        
        total_changes = (self.merge_stats['quests_added'] + 
                        self.merge_stats['quests_updated'] +
                        self.merge_stats['npcs_added'] + 
                        self.merge_stats['npcs_updated'])
        
        lines.append(f"Total changes: {total_changes}")
        
        return '\n'.join(lines)
    
    def rollback(self, backup_name: str) -> bool:
        """Rollback to a previous backup"""
        if not self.backup_manager:
            self.logger.error("No backup manager configured")
            return False
        
        try:
            self.backup_manager.restore_backup(backup_name)
            self.logger.info(f"Successfully rolled back to {backup_name}")
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False
    
    def validate_merge(self, pre_merge_db: Dict, post_merge_db: Dict) -> bool:
        """Validate that merge was successful"""
        # Check that no data was lost
        for db_type in ['quests', 'npcs']:
            pre_ids = set(pre_merge_db.get(db_type, {}).keys())
            post_ids = set(post_merge_db.get(db_type, {}).keys())
            
            lost_ids = pre_ids - post_ids
            if lost_ids:
                self.logger.error(f"Lost {len(lost_ids)} {db_type} during merge: {lost_ids}")
                return False
        
        # Check that expected changes were made
        expected_additions = self.merge_stats['quests_added'] + self.merge_stats['npcs_added']
        expected_updates = self.merge_stats['quests_updated'] + self.merge_stats['npcs_updated']
        
        if expected_additions == 0 and expected_updates == 0:
            self.logger.warning("No changes were made during merge")
        
        return True


def main():
    """Test the database merger"""
    import tempfile
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        merger = DatabaseMerger(tmpdir)
        
        # Test data
        new_data = {
            12345: {
                'quest_id': 12345,
                'name': 'Test Quest',
                'questLevel': 10,
                'startedBy': ([100], None, None),
                'finishedBy': ([101], None),
            },
            46718: {
                'npc_id': 46718,
                'name': 'Test NPC',
                'minLevel': 10,
                'maxLevel': 10,
                'spawns': {14: [[70.9, 45.9]]},
            }
        }
        
        # Test merge decisions
        decisions = {
            12345: {'action': 'add'},
            46718: {'action': 'add'},
        }
        
        # Perform merge
        success, report = merger.merge(new_data, decisions)
        
        print(f"Merge successful: {success}")
        print(f"Report: {report['summary']}")


if __name__ == "__main__":
    main()