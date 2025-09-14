#!/usr/bin/env python3
"""
Database Writer V2 - Enhanced to work with comparator merge instructions
Processes merge instructions from database_comparator_v2 and generates appropriate database updates
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

class DatabaseWriterV2:
    """
    Enhanced database writer that processes merge instructions from the comparator
    and applies them to the database files with proper additive merging strategies
    """
    
    def __init__(self, database_paths: Dict = None):
        self.logger = logging.getLogger(__name__)
        
        # Default database paths - update to your Questie installation
        default_base = Path("../../Database/Epoch")
        self.quest_db_path = database_paths.get('quest_db', default_base / "epochQuestDB.lua") if database_paths else default_base / "epochQuestDB.lua"
        self.npc_db_path = database_paths.get('npc_db', default_base / "epochNpcDB.lua") if database_paths else default_base / "epochNpcDB.lua"
        
        # Statistics
        self.stats = {
            'new_quests_added': 0,
            'runtime_stubs_replaced': 0,
            'objectives_added': 0,
            'npcs_added': 0,
            'coordinates_added': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Track changes for reporting
        self.changes = []
        
    def process_merge_instructions(self, merge_instructions: Dict, dry_run: bool = False) -> Dict:
        """
        Process merge instructions from the comparator and apply them
        
        Args:
            merge_instructions: Output from database_comparator_v2
            dry_run: If True, don't actually write to files
            
        Returns:
            Dictionary with results and statistics
        """
        self.logger.info("Processing merge instructions...")
        
        # Reset statistics
        self.stats = {key: 0 for key in self.stats}
        self.changes = []
        
        results = {
            'success': True,
            'stats': {},
            'changes': [],
            'errors': []
        }
        
        try:
            # Process each category of merge instructions
            for category, data in merge_instructions.items():
                if category == 'metadata':
                    continue  # Skip metadata
                    
                self.logger.info(f"Processing {category}...")
                
                if category == 'new_quests':
                    self._process_new_quests(data, dry_run)
                elif category == 'runtime_stubs':
                    self._process_runtime_stubs(data, dry_run)
                elif category == 'missing_objectives':
                    self._process_missing_objectives(data, dry_run)
                elif category == 'missing_npcs':
                    self._process_missing_npcs(data, dry_run)
                elif category == 'missing_coordinates':
                    self._process_missing_coordinates(data, dry_run)
                else:
                    self.logger.debug(f"Skipping category: {category}")
            
            # Generate output files if not dry run
            if not dry_run:
                self._write_changes_to_files()
            
            results['stats'] = self.stats.copy()
            results['changes'] = self.changes.copy()
            
            self.logger.info(f"Processing complete: {self.stats}")
            
        except Exception as e:
            self.logger.error(f"Error processing merge instructions: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        return results
    
    def _process_new_quests(self, data: Dict, dry_run: bool):
        """Process new quests to be added to database"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = quest.get('id')
            quest_data = quest.get('data', {})
            
            # Generate the Lua entry for this quest
            lua_entry = self._generate_quest_entry(quest_id, quest_data)
            
            self.changes.append({
                'type': 'NEW_QUEST',
                'id': quest_id,
                'entry': lua_entry,
                'target': 'epochQuestDB.lua'
            })
            
            self.stats['new_quests_added'] += 1
            
            # Also add associated NPCs if present
            self._extract_and_add_npcs(quest_data)
    
    def _process_runtime_stubs(self, data: Dict, dry_run: bool):
        """Replace runtime stubs with real quest data"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = quest.get('id')
            quest_data = quest.get('data', {})
            
            # Generate replacement entry
            lua_entry = self._generate_quest_entry(quest_id, quest_data)
            
            self.changes.append({
                'type': 'REPLACE_STUB',
                'id': quest_id,
                'entry': lua_entry,
                'target': 'epochQuestDB.lua'
            })
            
            self.stats['runtime_stubs_replaced'] += 1
    
    def _process_missing_objectives(self, data: Dict, dry_run: bool):
        """Add missing objectives to existing quests"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = quest.get('id')
            quest_data = quest.get('data', {})
            objectives = quest_data.get('objectives', {})
            
            if objectives:
                self.changes.append({
                    'type': 'ADD_OBJECTIVES',
                    'id': quest_id,
                    'objectives': objectives,
                    'target': 'epochQuestDB.lua'
                })
                
                self.stats['objectives_added'] += 1
    
    def _process_missing_npcs(self, data: Dict, dry_run: bool):
        """Add missing quest giver and turn-in NPCs"""
        if 'quests' not in data:
            return
        
        for quest in data['quests']:
            quest_id = quest.get('id')
            quest_data = quest.get('data', {})
            
            # Check for startedBy NPCs
            started_by = quest_data.get('startedBy', {})
            finished_by = quest_data.get('finishedBy', {})
            
            if started_by.get('npcs') or finished_by.get('npcs'):
                self.changes.append({
                    'type': 'ADD_NPCS',
                    'id': quest_id,
                    'startedBy': started_by,
                    'finishedBy': finished_by,
                    'target': 'epochQuestDB.lua'
                })
                
                self.stats['npcs_added'] += 1
                
                # Extract and add the actual NPC data
                self._extract_and_add_npcs(quest_data)
    
    def _process_missing_coordinates(self, data: Dict, dry_run: bool):
        """Add missing spawn coordinates (additive merge)"""
        if 'quests' not in data:
            return
        
        # This would handle coordinate merging
        # Currently no quests in this category based on the report
        pass
    
    def _extract_and_add_npcs(self, quest_data: Dict):
        """Extract NPC data from quest and add to NPC database"""
        # Extract NPCs from startedBy and finishedBy
        npcs_to_add = []
        
        started_by = quest_data.get('startedBy', {})
        if started_by.get('npcs'):
            for npc_id in started_by['npcs']:
                # In real implementation, would look up NPC data
                # For now, create placeholder
                npcs_to_add.append(npc_id)
        
        finished_by = quest_data.get('finishedBy', {})
        if finished_by.get('npcs'):
            for npc_id in finished_by['npcs']:
                npcs_to_add.append(npc_id)
        
        # Add NPC entries if we have additional NPC data
        # This would be enhanced with actual NPC data from the pipeline
        for npc_id in set(npcs_to_add):
            # Check if we have NPC data in the pipeline results
            # For now, we'll skip actual NPC database updates
            pass
    
    def _generate_quest_entry(self, quest_id: str, quest_data: Dict) -> str:
        """Generate a Lua quest database entry on a SINGLE LINE"""
        # Extract and format each field
        name = self._escape_lua_string(quest_data.get('name', f'[Quest {quest_id}]'))
        
        # Format startedBy
        started_by = self._format_started_by(quest_data.get('startedBy', {}))
        
        # Format finishedBy
        finished_by = self._format_finished_by(quest_data.get('finishedBy', {}))
        
        # Levels
        required_level = quest_data.get('requiredLevel') or "nil"
        quest_level = quest_data.get('questLevel') or 1
        
        # Restrictions
        required_races = quest_data.get('requiredRaces') or "nil"
        required_classes = quest_data.get('requiredClasses') or "nil"
        
        # Objectives text
        objectives_text = self._format_objectives_text(quest_data.get('objectivesText', []))
        
        # Objectives (kills, items, etc.)
        objectives = self._format_objectives(quest_data.get('objectives', {}))
        
        # Zone
        zone = quest_data.get('zoneOrSort') or 1
        
        # Build the complete entry as a SINGLE LINE with NO spaces after commas
        # This matches the exact format of the existing database
        fields = [
            f'"{name}"',                # [1] name
            started_by,                 # [2] startedBy
            finished_by,                # [3] finishedBy
            str(required_level),        # [4] requiredLevel
            str(quest_level),           # [5] questLevel
            str(required_races),        # [6] requiredRaces
            str(required_classes),      # [7] requiredClasses
            objectives_text,            # [8] objectivesText
            'nil',                      # [9] triggerEnd
            objectives,                 # [10] objectives
            'nil',                      # [11] sourceItemId
            'nil',                      # [12] preQuestGroup
            'nil',                      # [13] preQuestSingle
            'nil',                      # [14] childQuests
            'nil',                      # [15] inGroupWith
            'nil',                      # [16] exclusiveTo
            str(zone),                  # [17] zoneOrSort
            'nil',                      # [18] requiredSkill
            'nil',                      # [19] requiredMinRep
            'nil',                      # [20] requiredMaxRep
            'nil',                      # [21] requiredSourceItems
            'nil',                      # [22] nextQuestInChain
            '0',                        # [23] questFlags
            '0',                        # [24] specialFlags
            'nil',                      # [25] parentQuest
            'nil',                      # [26] reputationReward
            'nil',                      # [27] extraObjectives
            'nil',                      # [28] requiredSpell
            'nil',                      # [29] requiredSpecialization
            'nil'                       # [30] requiredMaxLevel - NO COMMA!
        ]
        
        # Join with commas (no spaces) and create single-line entry
        entry = f'[{quest_id}] = {{' + ','.join(fields) + '},'
        
        return entry
    
    def _escape_lua_string(self, s: str) -> str:
        """Properly escape a string for Lua"""
        if s is None:
            return ""
        # Escape backslashes first, then quotes
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '\\r')
        return s
    
    def _format_started_by(self, started_by: Dict) -> str:
        """Format startedBy field"""
        if not started_by:
            return "nil"
        
        npcs = started_by.get('npcs', [])
        objects = started_by.get('objects', [])
        items = started_by.get('items', [])
        
        if not any([npcs, objects, items]):
            return "nil"
        
        # Format each component
        npcs_str = "{" + ",".join(map(str, npcs)) + "}" if npcs else "nil"
        objs_str = "{" + ",".join(map(str, objects)) + "}" if objects else "nil"
        items_str = "{" + ",".join(map(str, items)) + "}" if items else "nil"
        
        return f"{{{npcs_str},{objs_str},{items_str}}}"
    
    def _format_finished_by(self, finished_by: Dict) -> str:
        """Format finishedBy field"""
        if not finished_by:
            return "nil"
        
        npcs = finished_by.get('npcs', [])
        objects = finished_by.get('objects', [])
        
        if not any([npcs, objects]):
            return "nil"
        
        npcs_str = "{" + ",".join(map(str, npcs)) + "}" if npcs else "nil"
        objs_str = "{" + ",".join(map(str, objects)) + "}" if objects else "nil"
        
        return f"{{{npcs_str},{objs_str}}}"
    
    def _format_objectives_text(self, objectives_text: List) -> str:
        """Format objectives text"""
        if not objectives_text:
            return 'nil'  # Use nil for missing objectives text, not placeholder
        
        # Escape quotes and format
        formatted = []
        for text in objectives_text:
            # Use the proper escape function
            escaped = self._escape_lua_string(text)
            formatted.append(f'"{escaped}"')
        
        return "{" + ",".join(formatted) + "}"
    
    def _format_objectives(self, objectives: Dict) -> str:
        """Format objectives field"""
        if not objectives:
            return "nil"
        
        items = objectives.get('items', [])
        creatures = objectives.get('creatures', [])
        objects = objectives.get('objects', [])
        
        if not any([items, creatures, objects]):
            return "nil"
        
        # Format creatures
        creatures_str = "nil"
        if creatures:
            creature_parts = []
            for creature in creatures:
                if isinstance(creature, dict):
                    cid = creature.get('id', 0)
                    count = creature.get('count', 1)
                    name = creature.get('name', '')
                    if name:
                        creature_parts.append(f'{{{cid},{count},"{name}"}}')
                    else:
                        creature_parts.append(f'{{{cid},{count}}}')
            if creature_parts:
                creatures_str = "{" + ",".join(creature_parts) + "}"
        
        # Format objects
        objects_str = "nil"
        if objects:
            object_parts = []
            for obj in objects:
                if isinstance(obj, dict):
                    oid = obj.get('id', 0)
                    count = obj.get('count', 1)
                    object_parts.append(f'{{{oid},{count}}}')
            if object_parts:
                objects_str = "{" + ",".join(object_parts) + "}"
        
        # Format items
        items_str = "nil"
        if items:
            item_parts = []
            for item in items:
                if isinstance(item, dict):
                    iid = item.get('id', 0)
                    count = item.get('count', 1)
                    item_parts.append(f'{{{iid},{count}}}')
            if item_parts:
                items_str = "{" + ",".join(item_parts) + "}"
        
        # Build complete objectives
        # Format: {creatures, objects, items, reputation, killCredit, spells}
        return f"{{{creatures_str},{objects_str},{items_str},nil,nil,nil}}"
    
    def _write_changes_to_files(self):
        """Write all changes to appropriate database files"""
        # Group changes by target file
        quest_changes = [c for c in self.changes if c['target'] == 'epochQuestDB.lua']
        npc_changes = [c for c in self.changes if c['target'] == 'epochNpcDB.lua']
        
        # Generate output files
        if quest_changes:
            self._write_quest_updates(quest_changes)
        
        if npc_changes:
            self._write_npc_updates(npc_changes)
    
    def _write_quest_updates(self, changes: List[Dict]):
        """Write quest database updates to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"quest_updates_{timestamp}.lua")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- Quest Database Updates\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Total updates: {len(changes)}\n\n")
            
            # Group by change type
            new_quests = [c for c in changes if c['type'] == 'NEW_QUEST']
            replacements = [c for c in changes if c['type'] == 'REPLACE_STUB']
            objective_adds = [c for c in changes if c['type'] == 'ADD_OBJECTIVES']
            npc_adds = [c for c in changes if c['type'] == 'ADD_NPCS']
            
            # Write new quests
            if new_quests:
                f.write("-- NEW QUESTS TO ADD\n")
                f.write("-- Add these entries to epochQuestDB\n\n")
                for change in new_quests:
                    f.write(change['entry'] + "\n")
                f.write("\n")
            
            # Write replacements
            if replacements:
                f.write("-- RUNTIME STUBS TO REPLACE\n")
                f.write("-- Replace existing [Epoch] stub entries with these\n\n")
                for change in replacements:
                    f.write(f"-- Replace quest {change['id']}\n")
                    f.write(change['entry'] + "\n")
                f.write("\n")
            
            # Write objective additions
            if objective_adds:
                f.write("-- OBJECTIVES TO ADD\n")
                f.write("-- Update these quests with missing objectives\n\n")
                for change in objective_adds:
                    f.write(f"-- Quest {change['id']}: Add objectives at position [10]\n")
                    f.write(f"-- Objectives: {change['objectives']}\n\n")
            
            # Write NPC additions
            if npc_adds:
                f.write("-- NPCS TO ADD\n")
                f.write("-- Update these quests with missing NPCs\n\n")
                for change in npc_adds:
                    f.write(f"-- Quest {change['id']}:\n")
                    if change.get('startedBy', {}).get('npcs'):
                        f.write(f"--   StartedBy NPCs: {change['startedBy']['npcs']}\n")
                    if change.get('finishedBy', {}).get('npcs'):
                        f.write(f"--   FinishedBy NPCs: {change['finishedBy']['npcs']}\n")
                    f.write("\n")
        
        self.logger.info(f"Wrote quest updates to {output_file}")
    
    def _write_npc_updates(self, changes: List[Dict]):
        """Write NPC database updates to file"""
        # Implementation would be similar to quest updates
        pass

def main():
    """Test the enhanced database writer"""
    # Load a comparison report
    report_file = Path("comparison_reports/comparison_report_20250906_231414.json")
    
    if not report_file.exists():
        print(f"Report file not found: {report_file}")
        return
    
    with open(report_file, 'r') as f:
        comparison_report = json.load(f)
    
    # Extract merge instructions
    merge_instructions = comparison_report.get('merge_instructions', {})
    
    # Create writer and process
    writer = DatabaseWriterV2()
    results = writer.process_merge_instructions(merge_instructions, dry_run=False)
    
    # Print results
    print("\n=== DATABASE WRITER RESULTS ===")
    print(f"Success: {results['success']}")
    print(f"\nStatistics:")
    for key, value in results['stats'].items():
        print(f"  {key}: {value}")
    
    if results.get('errors'):
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")

if __name__ == "__main__":
    main()