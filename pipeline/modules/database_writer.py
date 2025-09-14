#!/usr/bin/env python3
"""
Database Writer Module - Writes quest data with restriction flags based on submission analysis
Consults the submission tracker before adding restriction flags
"""

from pathlib import Path
from submission_tracker import SubmissionTracker
from typing import Dict, Optional, List, Any
import logging

# Import pipeline modules for integration
try:
    from backup_manager import BackupManager
except ImportError:
    BackupManager = None

try:
    from database_comparator import DatabaseComparator
except ImportError:
    DatabaseComparator = None

try:
    from merge_decision_engine import MergeDecisionEngine
except ImportError:
    MergeDecisionEngine = None

try:
    from validation_engine import ValidationEngine
except ImportError:
    ValidationEngine = None

class DatabaseWriter:
    """
    Writes quest entries to Lua database files with proper restriction flags
    based on submission pattern analysis. Now integrated with full pipeline.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Get tracker_db from config or use default
        tracker_db = self.config.get('tracker_db', 'submission_tracker.db')
        self.tracker = SubmissionTracker(tracker_db)
        
        # Pipeline integration
        self.backup_manager = BackupManager() if BackupManager else None
        self.database_comparator = DatabaseComparator() if DatabaseComparator else None
        self.merge_engine = MergeDecisionEngine() if MergeDecisionEngine else None
        self.validator = ValidationEngine() if ValidationEngine else None
        
        # Track database files
        self.quest_db_path = None
        self.npc_db_path = None
        
        # WoW class bitmasks for requiredClasses field
        self.CLASS_FLAGS = {
            'WARRIOR': 1,
            'PALADIN': 2,
            'HUNTER': 4,
            'ROGUE': 8,
            'PRIEST': 16,
            'DEATHKNIGHT': 32,
            'SHAMAN': 64,
            'MAGE': 128,
            'WARLOCK': 256,
            'DRUID': 1024
        }
        
        # WoW race bitmasks for requiredRaces field
        self.RACE_FLAGS = {
            # Alliance
            'HUMAN': 1,
            'DWARF': 4,
            'NIGHTELF': 8,
            'GNOME': 64,
            'DRAENEI': 1024,
            # Horde
            'ORC': 2,
            'UNDEAD': 16,
            'TAUREN': 32,
            'TROLL': 128,
            'BLOODELF': 512,
        }
        
        # Faction to races mapping
        self.FACTION_RACES = {
            'Alliance': self.RACE_FLAGS['HUMAN'] | self.RACE_FLAGS['DWARF'] | 
                       self.RACE_FLAGS['NIGHTELF'] | self.RACE_FLAGS['GNOME'] | 
                       self.RACE_FLAGS['DRAENEI'],
            'Horde': self.RACE_FLAGS['ORC'] | self.RACE_FLAGS['UNDEAD'] | 
                    self.RACE_FLAGS['TAUREN'] | self.RACE_FLAGS['TROLL'] | 
                    self.RACE_FLAGS['BLOODELF']
        }
    
    def generate_quest_entry(self, quest_data: Dict) -> str:
        """
        Generate a Lua quest database entry with restriction flags
        based on submission analysis
        """
        quest_id = quest_data['quest_id']
        
        # Analyze restrictions from submission history
        analysis = self.tracker.analyze_quest_restrictions(quest_id)
        
        # Build the quest entry with appropriate restrictions
        name = quest_data.get('quest_name', f'[Quest {quest_id}]')
        
        # Determine class restrictions
        required_classes = self._determine_class_restriction(analysis)
        
        # Determine race/faction restrictions
        required_races = self._determine_race_restriction(analysis)
        
        # Build quest giver and turn-in NPCs from consensus
        started_by = self._build_started_by(analysis, quest_data)
        finished_by = self._build_finished_by(analysis, quest_data)
        
        # Levels from consensus
        level_info = analysis.get('level_analysis', {})
        min_level = level_info.get('min_level', quest_data.get('min_level', 1))
        quest_level = level_info.get('quest_level', quest_data.get('quest_level', 1))
        
        # Generate comment about restrictions
        comment = self._generate_restriction_comment(analysis)
        
        # Build the Lua entry
        entry = f"[{quest_id}] = {{"
        entry += f'"{name}",'                    # 1: name
        entry += f'{started_by},'                # 2: startedBy
        entry += f'{finished_by},'               # 3: finishedBy
        entry += f'{min_level},'                 # 4: requiredLevel
        entry += f'{quest_level},'               # 5: questLevel
        entry += f'{required_races},'            # 6: requiredRaces
        entry += f'{required_classes},'          # 7: requiredClasses
        
        # Add rest of fields with defaults
        objectives = quest_data.get('objectives_text', '[Needs data collection]')
        if isinstance(objectives, list):
            objectives = '", "'.join(objectives)
        entry += f'{{"{objectives}"}},nil,nil,nil,nil,nil,nil,nil,nil,1,nil,nil,nil,nil,nil,0,0,nil,nil,nil,nil,nil,nil'
        
        entry += f"}}, {comment}"
        
        return entry
    
    def _determine_class_restriction(self, analysis: Dict) -> str:
        """Determine class restriction flags based on analysis"""
        class_analysis = analysis.get('class_analysis', {})
        
        if not class_analysis.get('restricted'):
            return 'nil'
        
        # High confidence single-class restriction
        if class_analysis.get('class') and class_analysis.get('confidence', 0) > 0.5:
            class_name = class_analysis['class'].upper()
            if class_name in self.CLASS_FLAGS:
                return str(self.CLASS_FLAGS[class_name])
        
        # Multi-class restriction (less common)
        if class_analysis.get('classes'):
            flags = 0
            for class_name in class_analysis['classes']:
                if class_name.upper() in self.CLASS_FLAGS:
                    flags |= self.CLASS_FLAGS[class_name.upper()]
            if flags > 0:
                return str(flags)
        
        return 'nil'
    
    def _determine_race_restriction(self, analysis: Dict) -> str:
        """Determine race/faction restriction flags based on analysis"""
        
        # Check faction restriction first (more common)
        faction_analysis = analysis.get('faction_analysis', {})
        if faction_analysis.get('restricted') and faction_analysis.get('confidence', 0) > 0.6:
            faction = faction_analysis.get('faction')
            if faction in self.FACTION_RACES:
                return str(self.FACTION_RACES[faction])
        
        # Check specific race restriction
        race_analysis = analysis.get('race_analysis', {})
        if race_analysis.get('restricted') and race_analysis.get('confidence', 0) > 0.7:
            race = race_analysis.get('race', '').upper()
            if race in self.RACE_FLAGS:
                return str(self.RACE_FLAGS[race])
        
        return 'nil'
    
    def _build_started_by(self, analysis: Dict, quest_data: Dict) -> str:
        """Build startedBy field from consensus data"""
        npc_consensus = analysis.get('npc_consensus', {})
        
        if npc_consensus.get('quest_giver'):
            giver_npc = npc_consensus['quest_giver']['consensus_npc']
            confidence = npc_consensus['quest_giver']['confidence']
            
            # Use consensus NPC if high confidence
            if confidence > 0.7:
                return f"{{{{{giver_npc}}},nil,nil}}"
            
            # Include alternates as comment if low confidence
            all_givers = npc_consensus['quest_giver']['all_reported']
            if len(all_givers) > 1:
                # Add comment about disputed NPCs
                return f"{{{{{giver_npc}}},nil,nil}}  -- Disputed: {all_givers}"
        
        # Fallback to quest_data
        if quest_data.get('quest_giver_npc_id'):
            return f"{{{{{quest_data['quest_giver_npc_id']}}},nil,nil}}"
        
        return 'nil'
    
    def _build_finished_by(self, analysis: Dict, quest_data: Dict) -> str:
        """Build finishedBy field from consensus data"""
        npc_consensus = analysis.get('npc_consensus', {})
        
        if npc_consensus.get('turn_in'):
            turnin_npc = npc_consensus['turn_in']['consensus_npc']
            confidence = npc_consensus['turn_in']['confidence']
            
            if confidence > 0.7:
                return f"{{{{{turnin_npc}}},nil}}"
        
        # Fallback
        if quest_data.get('turn_in_npc_id'):
            return f"{{{{{quest_data['turn_in_npc_id']}}},nil}}"
        
        return 'nil'
    
    def _generate_restriction_comment(self, analysis: Dict) -> str:
        """Generate a comment about quest restrictions"""
        comments = []
        
        # Add submission stats
        comments.append(f"-- {analysis['total_submissions']} submissions from {analysis['unique_users']} users")
        
        # Add restriction notes
        restrictions = []
        
        faction = analysis.get('faction_analysis', {})
        if faction.get('restricted'):
            conf = faction.get('confidence', 0)
            restrictions.append(f"{faction.get('faction')}-only ({conf:.0%} confidence)")
        
        class_info = analysis.get('class_analysis', {})
        if class_info.get('restricted'):
            conf = class_info.get('confidence', 0)
            if class_info.get('class'):
                restrictions.append(f"{class_info['class']}-only ({conf:.0%} confidence)")
        
        if restrictions:
            comments.append(f"-- Restrictions: {', '.join(restrictions)}")
        
        return " ".join(comments) if comments else ""
    
    def write_aggregated_data(self, aggregated_results: Dict, database_paths: Dict = None) -> Dict:
        """
        Write aggregated data to database files using full pipeline integration
        
        Args:
            aggregated_results: Results from DataAggregator
            database_paths: Paths to quest and NPC database files
            
        Returns:
            Dictionary with write results and statistics
        """
        results = {
            'quests_written': 0,
            'npcs_written': 0,
            'backups_created': [],
            'merge_decisions': [],
            'validation_results': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Set database paths
            if database_paths:
                self.quest_db_path = database_paths.get('quest_db')
                self.npc_db_path = database_paths.get('npc_db')
            
            # Step 1: Create backups if backup manager available
            if self.backup_manager and (self.quest_db_path or self.npc_db_path):
                backup_files = []
                if self.quest_db_path and Path(self.quest_db_path).exists():
                    backup_files.append(self.quest_db_path)
                if self.npc_db_path and Path(self.npc_db_path).exists():
                    backup_files.append(self.npc_db_path)
                
                if backup_files:
                    backup_ids = self.backup_manager.create_batch_backup(
                        backup_files, 
                        "Pre-pipeline database update"
                    )
                    results['backups_created'] = backup_ids
                    self.logger.info(f"Created {len(backup_ids)} backup(s) before database update")
            
            # Step 2: Process quest data
            if aggregated_results.get('quests'):
                quest_results = self._write_quest_data(
                    aggregated_results['quests'], 
                    self.quest_db_path
                )
                results.update(quest_results)
            
            # Step 3: Process NPC data  
            if aggregated_results.get('npcs'):
                npc_results = self._write_npc_data(
                    aggregated_results['npcs'],
                    self.npc_db_path
                )
                results.update(npc_results)
            
            # Step 4: Validation summary
            if self.validator:
                validation_summary = self._generate_validation_summary(aggregated_results)
                results['validation_results'] = validation_summary
            
            self.logger.info(f"Database write completed: {results['quests_written']} quests, {results['npcs_written']} NPCs")
            
        except Exception as e:
            error_msg = f"Database write failed: {e}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def _write_quest_data(self, quest_data: List[Dict], quest_db_path: str = None) -> Dict:
        """Write quest data with merge decision support"""
        results = {'quests_written': 0, 'merge_decisions': [], 'validation_results': {}}
        
        if not quest_db_path:
            return results
        
        try:
            # Load existing database for comparison if comparator available
            existing_data = {}
            if self.database_comparator and Path(quest_db_path).exists():
                self.database_comparator.load_databases(quest_db_path)
                existing_data = self.database_comparator.quest_db
            
            # Process each quest
            quest_entries = []
            for quest in quest_data:
                quest_id = quest['id']
                
                # Make merge decision if engines available
                if self.merge_engine and quest_id in existing_data:
                    decision = self.merge_engine.decide_merge_strategy(
                        quest_id, 'quest', existing_data[quest_id], quest
                    )
                    results['merge_decisions'].append(decision)
                    
                    # Apply merge decision
                    if decision.strategy.value == 'preserve_existing':
                        continue  # Skip this quest
                    elif decision.strategy.value == 'manual_review':
                        self.logger.warning(f"Quest {quest_id} requires manual review")
                        continue
                
                # Generate quest entry
                entry = self._generate_enhanced_quest_entry(quest)
                quest_entries.append(entry)
                results['quests_written'] += 1
            
            # Write to file if we have entries
            if quest_entries:
                self._write_quest_file(quest_entries, quest_db_path)
            
        except Exception as e:
            self.logger.error(f"Error writing quest data: {e}")
        
        return results
    
    def _write_npc_data(self, npc_data: List[Dict], npc_db_path: str = None) -> Dict:
        """Write NPC data with merge decision support"""
        results = {'npcs_written': 0}
        
        if not npc_db_path or not npc_data:
            return results
        
        try:
            npc_entries = []
            for npc in npc_data:
                entry = self._generate_npc_entry(npc)
                npc_entries.append(entry)
                results['npcs_written'] += 1
            
            if npc_entries:
                self._write_npc_file(npc_entries, npc_db_path)
            
        except Exception as e:
            self.logger.error(f"Error writing NPC data: {e}")
        
        return results
    
    def _generate_enhanced_quest_entry(self, quest: Dict) -> str:
        """Generate enhanced quest entry using pipeline data"""
        quest_id = quest['id']
        
        # Get restriction analysis from tracker if available
        analysis = {}
        if hasattr(self.tracker, 'analyze_quest_restrictions'):
            try:
                analysis = self.tracker.analyze_quest_restrictions(quest_id)
            except:
                pass  # Tracker might not have data for this quest
        
        # Use enhanced data from pipeline
        name = quest.get('name', f'[Quest {quest_id}]')
        
        # Build startedBy from aggregated data
        started_by = "nil"
        if quest.get('startedBy'):
            npcs = quest['startedBy'].get('npcs', [])
            objects = quest['startedBy'].get('objects', [])
            items = quest['startedBy'].get('items', [])
            
            if npcs or objects or items:
                npcs_str = "{" + ",".join(map(str, npcs)) + "}" if npcs else "nil"
                objs_str = "{" + ",".join(map(str, objects)) + "}" if objects else "nil"
                items_str = "{" + ",".join(map(str, items)) + "}" if items else "nil"
                started_by = f"{{{npcs_str},{objs_str},{items_str}}}"
        
        # Build finishedBy
        finished_by = "nil"
        if quest.get('finishedBy'):
            npcs = quest['finishedBy'].get('npcs', [])
            objects = quest['finishedBy'].get('objects', [])
            
            if npcs or objects:
                npcs_str = "{" + ",".join(map(str, npcs)) + "}" if npcs else "nil"
                objs_str = "{" + ",".join(map(str, objects)) + "}" if objects else "nil"
                finished_by = f"{{{npcs_str},{objs_str}}}"
        
        # Get restriction flags (enhanced from pipeline analysis)
        required_races = quest.get('requiredRaces') or 'nil'
        required_classes = quest.get('requiredClasses') or 'nil'
        
        # Use tracker analysis to override if available
        if analysis:
            track_races = self._determine_race_restriction(analysis)
            track_classes = self._determine_class_restriction(analysis)
            if track_races != 'nil':
                required_races = track_races
            if track_classes != 'nil':
                required_classes = track_classes
        
        # Build objectives
        objectives_text = "nil"
        if quest.get('objectivesText'):
            texts = '","'.join(quest['objectivesText'])
            objectives_text = f'{{"{texts}"}}'
        
        # Generate the complete entry with all 30 fields
        entry = f"    [{quest_id}] = {{\n"
        entry += f'        "{name}",                    -- [1] name\n'
        entry += f'        {started_by},                 -- [2] startedBy\n'
        entry += f'        {finished_by},                -- [3] finishedBy\n'
        entry += f'        {quest.get("requiredLevel") or "nil"},            -- [4] requiredLevel\n'
        entry += f'        {quest.get("questLevel") or 1},               -- [5] questLevel\n'
        entry += f'        {required_races},             -- [6] requiredRaces\n'
        entry += f'        {required_classes},           -- [7] requiredClasses\n'
        entry += f'        {objectives_text},            -- [8] objectivesText\n'
        entry += f'        {quest.get("triggerEnd") or "nil"},           -- [9] triggerEnd\n'
        entry += f'        nil,                          -- [10] objectives (TODO)\n'
        entry += f'        {quest.get("sourceItemId") or "nil"},        -- [11] sourceItemId\n'
        entry += f'        nil,                          -- [12] preQuestGroup\n'
        entry += f'        nil,                          -- [13] preQuestSingle\n'
        entry += f'        nil,                          -- [14] childQuests\n'
        entry += f'        nil,                          -- [15] inGroupWith\n'
        entry += f'        nil,                          -- [16] exclusiveTo\n'
        entry += f'        {quest.get("zoneOrSort") or "nil"},         -- [17] zoneOrSort\n'
        entry += f'        {quest.get("requiredSkill") or "nil"},       -- [18] requiredSkill\n'
        entry += f'        {quest.get("requiredMinRep") or "nil"},      -- [19] requiredMinRep\n'
        entry += f'        {quest.get("requiredMaxRep") or "nil"},      -- [20] requiredMaxRep\n'
        entry += f'        nil,                          -- [21] requiredSourceItems\n'
        entry += f'        {quest.get("nextQuestInChain") or "nil"},   -- [22] nextQuestInChain\n'
        entry += f'        {quest.get("questFlags") or 0},             -- [23] questFlags\n'
        entry += f'        {quest.get("specialFlags") or 0},           -- [24] specialFlags\n'
        entry += f'        {quest.get("parentQuest") or "nil"},        -- [25] parentQuest\n'
        entry += f'        nil,                          -- [26] reputationReward\n'
        entry += f'        nil,                          -- [27] extraObjectives\n'
        entry += f'        {quest.get("requiredSpell") or "nil"},      -- [28] requiredSpell\n'
        entry += f'        nil,                          -- [29] requiredSpecialization\n'
        entry += f'        {quest.get("requiredMaxLevel") or "nil"}    -- [30] requiredMaxLevel\n'
        entry += "    },"
        
        # Add comment with pipeline metadata
        if quest.get('validation_score') or quest.get('quality_level'):
            entry += f" -- Validation: {quest.get('validation_score', 0)}% ({quest.get('quality_level', 'unknown')})"
        
        return entry
    
    def _generate_npc_entry(self, npc: Dict) -> str:
        """Generate NPC database entry"""
        npc_id = npc['id']
        name = npc.get('name', 'Unknown NPC')
        
        # Build spawns data
        spawns = "nil"
        if npc.get('spawns'):
            spawn_parts = []
            for zone_id, coords in npc['spawns'].items():
                if coords:
                    coord_strs = []
                    for coord in coords:
                        x = coord.get('x', 0)
                        y = coord.get('y', 0)
                        coord_strs.append(f"{{{x:.1f},{y:.1f}}}")
                    if coord_strs:
                        spawn_parts.append(f"[{zone_id}]={{{','.join(coord_strs)}}}")
            if spawn_parts:
                spawns = "{" + ",".join(spawn_parts) + "}"
        
        # Generate complete NPC entry
        entry = f"    [{npc_id}] = {{\n"
        entry += f'        "{name}",                    -- [1] name\n'
        entry += f'        {npc.get("minLevelHealth") or "nil"},        -- [2] minLevelHealth\n'
        entry += f'        {npc.get("maxLevelHealth") or "nil"},        -- [3] maxLevelHealth\n'
        entry += f'        {npc.get("minLevel") or 1},               -- [4] minLevel\n'
        entry += f'        {npc.get("maxLevel") or 1},               -- [5] maxLevel\n'
        entry += f'        {npc.get("rank") or 0},                   -- [6] rank\n'
        entry += f'        {spawns},                     -- [7] spawns\n'
        entry += f'        {npc.get("waypoints") or "nil"},           -- [8] waypoints\n'
        entry += f'        {npc.get("zoneID") or "nil"},              -- [9] zoneID\n'
        entry += f'        nil,                          -- [10] questStarts\n'
        entry += f'        nil,                          -- [11] questEnds\n'
        entry += f'        {npc.get("factionID") or "nil"},           -- [12] factionID\n'
        entry += f'        {npc.get("friendlyToFaction") or "nil"},   -- [13] friendlyToFaction\n'
        entry += f'        {npc.get("subName") or "nil"},             -- [14] subName\n'
        entry += f'        {npc.get("npcFlags") or 0}               -- [15] npcFlags\n'
        entry += "    },"
        
        return entry
    
    def _write_quest_file(self, quest_entries: List[str], output_path: str):
        """Write quest entries to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("-- Quest Database Entries\n")
            f.write("-- Generated by Questie Pipeline\n\n")
            f.write("epochQuestDB = {\n")
            
            for entry in quest_entries:
                f.write(entry + "\n")
            
            f.write("}\n")
    
    def _write_npc_file(self, npc_entries: List[str], output_path: str):
        """Write NPC entries to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("-- NPC Database Entries\n")
            f.write("-- Generated by Questie Pipeline\n\n")
            f.write("epochNpcDB = {\n")
            
            for entry in npc_entries:
                f.write(entry + "\n")
            
            f.write("}\n")
    
    def _generate_validation_summary(self, aggregated_results: Dict) -> Dict:
        """Generate validation summary for written data"""
        summary = {
            'total_entries': 0,
            'validation_scores': [],
            'quality_distribution': {}
        }
        
        if self.validator:
            for quest in aggregated_results.get('quests', []):
                if quest.get('validation_score'):
                    summary['validation_scores'].append(quest['validation_score'])
                    quality = quest.get('quality_level', 'unknown')
                    summary['quality_distribution'][quality] = summary['quality_distribution'].get(quality, 0) + 1
                    summary['total_entries'] += 1
        
        return summary
    
    def write_quests_to_file(self, quests: list, output_file: str):
        """Legacy method - Write multiple quests to a Lua file with restriction analysis"""
        output_path = Path(output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("-- Quest Database Entries with Restriction Analysis\n")
            f.write(f"-- Generated from submission tracker analysis\n")
            f.write(f"-- Total quests: {len(quests)}\n\n")
            
            for quest_data in quests:
                entry = self.generate_quest_entry(quest_data)
                f.write(entry + "\n")
        
        print(f"✅ Wrote {len(quests)} quests to {output_file}")
        
        # Generate restriction summary
        restricted_count = 0
        for quest_data in quests:
            analysis = self.tracker.analyze_quest_restrictions(quest_data['quest_id'])
            if (analysis.get('faction_analysis', {}).get('restricted') or
                analysis.get('class_analysis', {}).get('restricted')):
                restricted_count += 1
        
        if restricted_count > 0:
            print(f"   ⚠️  {restricted_count} quests have detected restrictions")

def main():
    """Test the database writer with restriction detection"""
    
    # Create test tracker with data
    tracker = SubmissionTracker("test_tracker.db")
    
    # Add some test submissions to build history
    test_submissions = [
        # Hunter-only quest (3 hunters submit it)
        {'quest_id': 99901, 'quest_name': 'Hunter Training', 'github_user': 'user1', 
         'player_class': 'HUNTER', 'player_faction': 'Alliance', 'quest_giver_npc_id': 100},
        {'quest_id': 99901, 'quest_name': 'Hunter Training', 'github_user': 'user2',
         'player_class': 'HUNTER', 'player_faction': 'Horde', 'quest_giver_npc_id': 100},
        {'quest_id': 99901, 'quest_name': 'Hunter Training', 'github_user': 'user3',
         'player_class': 'HUNTER', 'player_faction': 'Alliance', 'quest_giver_npc_id': 100},
         
        # Alliance-only quest
        {'quest_id': 99902, 'quest_name': 'For the Alliance', 'github_user': 'user1',
         'player_class': 'WARRIOR', 'player_faction': 'Alliance', 'quest_giver_npc_id': 200},
        {'quest_id': 99902, 'quest_name': 'For the Alliance', 'github_user': 'user4',
         'player_class': 'PRIEST', 'player_faction': 'Alliance', 'quest_giver_npc_id': 200},
         
        # Unrestricted quest
        {'quest_id': 99903, 'quest_name': 'General Quest', 'github_user': 'user1',
         'player_class': 'WARRIOR', 'player_faction': 'Alliance', 'quest_giver_npc_id': 300},
        {'quest_id': 99903, 'quest_name': 'General Quest', 'github_user': 'user2',
         'player_class': 'PRIEST', 'player_faction': 'Horde', 'quest_giver_npc_id': 300},
    ]
    
    for sub in test_submissions:
        tracker.record_submission(sub)
    
    tracker.close()
    
    # Now test the writer
    writer = DatabaseWriter("test_tracker.db")
    
    # Generate entries for our test quests
    test_quests = [
        {'quest_id': 99901, 'quest_name': 'Hunter Training', 'quest_level': 10},
        {'quest_id': 99902, 'quest_name': 'For the Alliance', 'quest_level': 20},
        {'quest_id': 99903, 'quest_name': 'General Quest', 'quest_level': 15},
    ]
    
    print("\nGenerated Quest Entries with Restrictions:\n")
    for quest in test_quests:
        entry = writer.generate_quest_entry(quest)
        print(entry)
        print()

if __name__ == "__main__":
    main()