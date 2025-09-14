#!/usr/bin/env python3
"""
Data Aggregator Module - The "Coin Sorter" that combines all parser outputs
Aggregates data from all specialized parsers into complete database entries
"""

import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys
from datetime import datetime

# Import all parser modules
from quest_parser import QuestParser
from objective_parser import ObjectiveParser  
from zone_mapper import ZoneMapper

# Import surgical coordinate parsers
from quest_npc_coordinate_parser import QuestNPCCoordinateParser
from mob_kill_coordinate_parser import MobKillCoordinateParser
from loot_coordinate_parser import LootCoordinateParser
from interact_coordinate_parser import InteractCoordinateParser

# Import all new parser modules
try:
    from npc_parser import NPCParser
except ImportError:
    NPCParser = None

try:
    from item_parser import ItemParser
except ImportError:
    ItemParser = None

try:
    from quest_chain_parser import QuestChainParser
except ImportError:
    QuestChainParser = None

try:
    from flag_parser import FlagParser
except ImportError:
    FlagParser = None

try:
    from reputation_parser import ReputationParser
except ImportError:
    ReputationParser = None

try:
    from profession_parser import ProfessionParser
except ImportError:
    ProfessionParser = None

try:
    from validation_engine import ValidationEngine
except ImportError:
    ValidationEngine = None

try:
    from restriction_analyzer import RestrictionAnalyzer
except ImportError:
    RestrictionAnalyzer = None

try:
    from unified_parser import UnifiedParser
except ImportError:
    UnifiedParser = None

try:
    from database_comparator import DatabaseComparator
except ImportError:
    DatabaseComparator = None

try:
    from merge_decision_engine import MergeDecisionEngine
except ImportError:
    MergeDecisionEngine = None

class DataAggregator:
    """
    The central 'coin sorter' that runs all parsers and combines their outputs
    into complete quest and NPC database entries
    """
    
    # Date when zone ID bug was fixed in data collector (September 6, 2025)  
    ZONE_FIX_DATE = datetime(2025, 9, 6)
    
    def __init__(self, enable_tracking: bool = False, *_, **__):
        # Initialize all available parsers
        self.quest_parser = QuestParser()
        self.objective_parser = ObjectiveParser()
        self.zone_mapper = ZoneMapper()
        
        # Known quest zone mappings (from verified data)
        self.known_quest_zones = {
            26538: 267,  # The Barony Mordis -> Hillsbrad Foothills
            # Add more known mappings as discovered
        }
        
        # Initialize surgical coordinate parsers
        self.quest_npc_coord_parser = QuestNPCCoordinateParser()
        self.mob_kill_coord_parser = MobKillCoordinateParser()
        self.loot_coord_parser = LootCoordinateParser()
        self.interact_coord_parser = InteractCoordinateParser()
        
        # Optional parsers
        self.npc_parser = NPCParser() if NPCParser else None
        self.item_parser = ItemParser() if ItemParser else None
        
        # Initialize submission tracker for pattern analysis (disabled by default in experiments)
        self.submission_tracker = None
        if enable_tracking:
            try:
                from submission_tracker import SubmissionTracker
                self.submission_tracker = SubmissionTracker(db_path="pipeline_submissions.db")
                print("📊 Submission tracker initialized for pattern analysis")
            except Exception:
                self.submission_tracker = None
        
        # Initialize pipeline state tracker for deduplication
        self.state_tracker = None
        if enable_tracking:
            try:
                from pipeline_state_tracker import PipelineStateTracker
                self.state_tracker = PipelineStateTracker()
                # Load existing database IDs on initialization
                self.state_tracker.load_existing_database_ids()
                print("🔍 Pipeline state tracker initialized for deduplication")
            except Exception as e:
                self.state_tracker = None
                print(f"⚠️  Pipeline state tracker not available: {e}")
        self.chain_parser = QuestChainParser() if QuestChainParser else None
        self.flag_parser = FlagParser() if FlagParser else None
        self.reputation_parser = ReputationParser() if ReputationParser else None
        self.profession_parser = ProfessionParser() if ProfessionParser else None
        
        # Advanced processing modules
        self.validation_engine = ValidationEngine() if ValidationEngine else None
        self.restriction_analyzer = RestrictionAnalyzer() if RestrictionAnalyzer else None
        self.unified_parser = UnifiedParser() if UnifiedParser else None
        self.database_comparator = DatabaseComparator() if DatabaseComparator else None
        self.merge_decision_engine = MergeDecisionEngine() if MergeDecisionEngine else None
        
        # Aggregated data storage
        self.quests = {}
        self.npcs = {}
        self.items = {}
        
        # Track quest variations for conflict detection
        self.quest_variations = {}  # quest_id -> list of different versions
        
        # Load NPC database for zone lookups
        self.npc_database = self._load_npc_database()
        self.objects = {}
        
    def should_process_file(self, filename: str) -> bool:
        """Check if a file should be processed based on deduplication state"""
        if not self.state_tracker:
            return True  # No state tracker, process everything
        
        return not self.state_tracker.is_file_processed(filename)
    
    def mark_file_processed(self, filename: str, quests: int = 0, npcs: int = 0, items: int = 0):
        """Mark a file as processed in the state tracker"""
        if self.state_tracker:
            self.state_tracker.mark_file_processed(filename, quests, npcs, items)
    
    def process_submission(self, content: str, source_file: str = None, submission_date: Optional[datetime] = None) -> Dict:
        """
        Process a submission through all parsers and aggregate the results
        
        Args:
            content: Raw submission content
            source_file: Source file path for tracking
            submission_date: When the submission was created (for zone validation)
            
        Returns:
            Dictionary with aggregated quest and NPC data
        """
        results = {
            'quests': [],
            'npcs': [],
            'items': [],
            'objects': [],
            'errors': [],
            'warnings': []
        }
        
        # Determine if this submission has the zone bug
        self.has_zone_bug = True  # Default to buggy
        if submission_date:
            self.has_zone_bug = submission_date < self.ZONE_FIX_DATE
        else:
            # Try to extract date from submission content
            import re as regex
            date_match = regex.search(r'Created: (\d{4}-\d{2}-\d{2})', content)
            if date_match:
                try:
                    sub_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    self.has_zone_bug = sub_date < self.ZONE_FIX_DATE
                except:
                    pass
        
        if self.has_zone_bug:
            results['warnings'].append(f"Submission from before {self.ZONE_FIX_DATE.date()} - zone IDs may be incorrect")
        
        # Step 1: Parse basic quest data (may be multiple quests)
        quests = self.quest_parser.parse(content, source_file)
        
        if not quests:
            results['errors'].append("No quest data found in submission")
            return results
        
        # Step 1.5: Skip UnifiedParser - it's disabled as redundant
        # The individual parsers already handle all format variations
        # if self.unified_parser:
        #     try:
        #         normalized_content = self.unified_parser.normalize_format(content)
        #         content = normalized_content.get('normalized_content', content)
        #         results['format_info'] = {
        #             'detected_format': normalized_content.get('detected_format'),
        #             'format_confidence': normalized_content.get('format_confidence')
        #         }
        #     except Exception as e:
        #         results['warnings'].append(f"Format normalization failed: {e}")
        
        # Step 2: Process each quest through all parsers
        for quest_data in quests:
            quest_id = quest_data.get('quest_id')
            if not quest_id:
                results['warnings'].append("Quest missing ID, skipping")
                continue
            
            # Create aggregated quest entry
            aggregated_quest = self._create_quest_entry(quest_id)
            
            # Step 3: Run quest-specific content through each parser
            quest_content = self._extract_quest_content(content, quest_id)
            
            # 3a. Basic quest info (already have from quest_parser)
            self._aggregate_basic_info(aggregated_quest, quest_data)
            
            # 3b. Parse objectives
            objectives = self.objective_parser.parse(quest_content, quest_id)
            self._aggregate_objectives(aggregated_quest, objectives)
            
            # 3c. Parse coordinates using surgical parsers
            coords = self._parse_all_coordinates(quest_content, quest_id)
            self._aggregate_coordinates(aggregated_quest, coords)
            
            # 3d. Map zones
            self._aggregate_zones(aggregated_quest, quest_data, coords)
            
            # 3e. Parse NPCs (if parser available)
            if self.npc_parser:
                npcs = self.npc_parser.parse(quest_content, quest_id)
                self._aggregate_npcs(aggregated_quest, npcs, results)
            
            # 3f. Parse items (if parser available)
            if self.item_parser:
                items = self.item_parser.parse(quest_content, quest_id)
                self._aggregate_items(aggregated_quest, items, results)
            
            # 3g. Parse quest chains (if parser available)
            if self.chain_parser:
                chains = self.chain_parser.parse(quest_content, quest_id)
                self._aggregate_chains(aggregated_quest, chains)
            
            # 3h. Parse flags (if parser available)
            if self.flag_parser:
                flags = self.flag_parser.parse(quest_content, quest_id)
                self._aggregate_flags(aggregated_quest, flags)
            
            # 3i. Parse reputation (if parser available)
            if self.reputation_parser:
                rep = self.reputation_parser.parse(quest_content, quest_id)
                self._aggregate_reputation(aggregated_quest, rep)
            
            # 3j. Parse professions (if parser available)
            if self.profession_parser:
                prof = self.profession_parser.parse(quest_content, quest_id)
                self._aggregate_professions(aggregated_quest, prof)
            
            # 3k. Analyze restrictions (if analyzer available)
            if self.restriction_analyzer:
                try:
                    restrictions = self.restriction_analyzer.analyze(aggregated_quest)
                    self._aggregate_restrictions(aggregated_quest, restrictions)
                except Exception as e:
                    results['warnings'].append(f"Restriction analysis failed for quest {quest_id}: {e}")
            
            # 3l. Validate quest data (if validation engine available)
            if self.validation_engine:
                try:
                    validation = self.validation_engine.validate_quest(aggregated_quest)
                    aggregated_quest['validation_score'] = validation.get('overall_score', 0)
                    aggregated_quest['quality_level'] = validation.get('quality_level', 'unknown')
                    if validation.get('errors'):
                        results['warnings'].extend([f"Quest {quest_id}: {err}" for err in validation['errors']])
                except Exception as e:
                    results['warnings'].append(f"Validation failed for quest {quest_id}: {e}")
            
            # Step 4: Merge or store aggregated quest
            if quest_id in self.quests:
                # Quest already exists - MERGE the data (coin sorter approach)
                existing_quest = self.quests[quest_id]
                
                # Merge quest giver NPCs (add new ones)
                for npc in aggregated_quest['startedBy']['npcs']:
                    if npc and npc not in existing_quest['startedBy']['npcs']:
                        existing_quest['startedBy']['npcs'].append(npc)
                
                # Merge turn-in NPCs (add new ones)
                for npc in aggregated_quest['finishedBy']['npcs']:
                    if npc and npc not in existing_quest['finishedBy']['npcs']:
                        existing_quest['finishedBy']['npcs'].append(npc)
                
                # Merge objectives (combine unique ones)
                for creature in aggregated_quest['objectives']['creatures']:
                    if creature not in existing_quest['objectives']['creatures']:
                        existing_quest['objectives']['creatures'].append(creature)
                
                for item in aggregated_quest['objectives']['items']:
                    if item not in existing_quest['objectives']['items']:
                        existing_quest['objectives']['items'].append(item)
                
                for obj in aggregated_quest['objectives']['objects']:
                    if obj not in existing_quest['objectives']['objects']:
                        existing_quest['objectives']['objects'].append(obj)
                
                # Update zone if we have better info
                if not existing_quest.get('zoneOrSort') and aggregated_quest.get('zoneOrSort'):
                    existing_quest['zoneOrSort'] = aggregated_quest['zoneOrSort']
                
                # Update level info if missing
                if not existing_quest.get('questLevel') and aggregated_quest.get('questLevel'):
                    existing_quest['questLevel'] = aggregated_quest['questLevel']
                if not existing_quest.get('requiredLevel') and aggregated_quest.get('requiredLevel'):
                    existing_quest['requiredLevel'] = aggregated_quest['requiredLevel']
                
                # Check for actual conflicts (different levels, different zones)
                conflicts = []
                if (existing_quest.get('questLevel') and aggregated_quest.get('questLevel') and
                    existing_quest['questLevel'] != aggregated_quest['questLevel']):
                    conflicts.append(f"Different quest levels: {existing_quest['questLevel']} vs {aggregated_quest['questLevel']}")
                
                if (existing_quest.get('zoneOrSort') and aggregated_quest.get('zoneOrSort') and
                    existing_quest['zoneOrSort'] != aggregated_quest['zoneOrSort']):
                    conflicts.append(f"Different zones: {existing_quest['zoneOrSort']} vs {aggregated_quest['zoneOrSort']}")
                
                # Track sources
                if not hasattr(existing_quest, '_sources'):
                    existing_quest['_sources'] = []
                existing_quest['_sources'].append(source_file)
                
                # Only warn about real conflicts
                if conflicts:
                    results['warnings'].append(
                        f"Quest {quest_id} has conflicts: {', '.join(conflicts)}. Manual review needed."
                    )
                
                # Return the merged quest
                results['quests'].append(existing_quest)
            else:
                # First time seeing this quest
                self.quests[quest_id] = aggregated_quest
                aggregated_quest['_sources'] = [source_file]
                
                # Extract GitHub issue number if available
                import re
                issue_match = re.search(r'issue_(\d+)', source_file) if source_file else None
                if issue_match:
                    aggregated_quest['_github_issue'] = int(issue_match.group(1))
                    aggregated_quest['_github_url'] = f"https://github.com/trav346/Questie/issues/{issue_match.group(1)}"
                
                results['quests'].append(aggregated_quest)
            
            # Track in state tracker for deduplication
            if self.state_tracker:
                # Check if quest is already in database
                is_in_db = self.state_tracker.is_quest_in_database(quest_id)
                self.state_tracker.track_quest(quest_id, aggregated_quest.get('name'), is_in_db)
                
                # Track NPCs
                for npc_id in aggregated_quest.get('startedBy', {}).get('npcs', []):
                    if npc_id:
                        is_npc_in_db = self.state_tracker.is_npc_in_database(npc_id)
                        self.state_tracker.track_npc(npc_id, in_database=is_npc_in_db)
                
                for npc_id in aggregated_quest.get('finishedBy', {}).get('npcs', []):
                    if npc_id:
                        is_npc_in_db = self.state_tracker.is_npc_in_database(npc_id)
                        self.state_tracker.track_npc(npc_id, in_database=is_npc_in_db)
            
            # Track submission in database for pattern analysis
            if self.submission_tracker and aggregated_quest:
                try:
                    submission_data = {
                        'quest_id': quest_id,
                        'quest_name': aggregated_quest.get('name'),
                        'quest_level': aggregated_quest.get('questLevel'),
                        'zone_name': self._get_zone_name(aggregated_quest.get('zoneOrSort')),
                        'quest_giver_npc': aggregated_quest.get('startedBy', {}).get('npcs', [None])[0],
                        'turn_in_npc': aggregated_quest.get('finishedBy', {}).get('npcs', [None])[0],
                        'has_objectives': bool(aggregated_quest.get('objectives', {}).get('creatures')),
                        'raw_data': source_file,
                        'addon_version': quest_data.get('addon_version'),
                        'player_faction': quest_data.get('faction'),
                        'github_issue': aggregated_quest.get('_github_issue'),
                        'submission_date': submission_date or datetime.now().isoformat()
                    }
                    
                    # Extract GitHub user from content if available
                    user_match = re.search(r'User: (.+)', content)
                    if user_match:
                        submission_data['github_user'] = user_match.group(1).strip()
                    
                    self.submission_tracker.record_submission(submission_data)
                except Exception as e:
                    # Don't fail processing if tracking fails
                    pass
        
        # Step 5: Process any standalone NPCs (service NPCs, flight masters, etc)
        self._process_service_npcs(content, results)
        
        return results
    
    def _create_quest_entry(self, quest_id: int) -> Dict:
        """Create empty quest entry with all 30 fields"""
        return {
            'id': quest_id,
            'name': None,                    # 1
            'startedBy': {'npcs': [], 'objects': [], 'items': []},  # 2
            'finishedBy': {'npcs': [], 'objects': []},  # 3
            'requiredLevel': None,            # 4
            'questLevel': None,               # 5
            'requiredRaces': None,            # 6
            'requiredClasses': None,          # 7
            'objectivesText': [],             # 8
            'triggerEnd': None,               # 9
            'objectives': {                   # 10
                'creatures': [],
                'objects': [],
                'items': [],
                'reputation': None,
                'killCredit': [],
                'spells': []
            },
            'sourceItemId': None,            # 11
            'preQuestGroup': [],             # 12
            'preQuestSingle': [],            # 13
            'childQuests': [],               # 14
            'inGroupWith': [],               # 15
            'exclusiveTo': [],               # 16
            'zoneOrSort': None,              # 17
            'requiredSkill': None,           # 18
            'requiredMinRep': None,          # 19
            'requiredMaxRep': None,          # 20
            'requiredSourceItems': [],       # 21
            'nextQuestInChain': None,        # 22
            'questFlags': 0,                 # 23
            'specialFlags': 0,               # 24
            'parentQuest': None,             # 25
            'reputationReward': [],          # 26
            'extraObjectives': [],           # 27
            'requiredSpell': None,           # 28
            'requiredSpecialization': None,  # 29
            'requiredMaxLevel': None,        # 30
            # Metadata (not in database)
            'source_file': None,
            'completeness_score': 0,
            'has_coordinates': False,
            'has_objectives': False
        }
    
    def _parse_all_coordinates(self, content: str, quest_id: int) -> Dict:
        """Parse coordinates using all surgical parsers"""
        coords = {
            'quest_npcs': {},
            'mob_kills': {},
            'loot_locations': {},
            'interactions': {},
            'all_coordinates': []
        }
        
        # Parse quest NPCs (quest giver and turn-in)
        npc_coords = self.quest_npc_coord_parser.parse(content, quest_id)
        if npc_coords.get('quest_giver'):
            coords['quest_npcs']['quest_giver'] = npc_coords['quest_giver']
            coords['all_coordinates'].append(npc_coords['quest_giver'])
        if npc_coords.get('turn_in_npc'):
            coords['quest_npcs']['turn_in'] = npc_coords['turn_in_npc']
            coords['all_coordinates'].append(npc_coords['turn_in_npc'])
        
        # Parse mob kill locations
        mob_coords = self.mob_kill_coord_parser.parse(content, quest_id)
        coords['mob_kills'] = mob_coords.get('mobs', {})
        for mob_name, locations in coords['mob_kills'].items():
            coords['all_coordinates'].extend(locations)
        
        # Parse loot locations
        loot_coords = self.loot_coord_parser.parse(content, quest_id)
        coords['loot_locations']['items'] = loot_coords.get('item_locations', {})
        coords['loot_locations']['containers'] = loot_coords.get('container_locations', {})
        for item_name, locations in coords['loot_locations']['items'].items():
            coords['all_coordinates'].extend(locations)
        
        # Parse interaction points
        interact_coords = self.interact_coord_parser.parse(content, quest_id)
        coords['interactions'] = interact_coords.get('interactions', {})
        for obj_name, locations in coords['interactions'].items():
            coords['all_coordinates'].extend(locations)
        
        return coords
    
    def _extract_quest_content(self, content: str, quest_id: int) -> str:
        """Extract the section for a specific quest from multi-quest submission"""
        # Look for quest-specific section
        pattern = rf'Quest ID:\s*{quest_id}\s*\n(.*?)(?:={50,}|DATABASE ENTRIES|\Z)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return f"Quest ID: {quest_id}\n" + match.group(1)
        
        # Fallback to full content if not found
        return content
    
    def _aggregate_basic_info(self, quest: Dict, quest_data: Dict):
        """Aggregate basic quest information"""
        quest['name'] = quest_data.get('quest_name', f"[Quest {quest['id']}]")
        quest['questLevel'] = quest_data.get('quest_level') or quest_data.get('level')
        quest['requiredLevel'] = quest_data.get('min_level') or quest_data.get('level')
        quest['source_file'] = quest_data.get('source_file')
        
        # Add quest giver/turn-in NPCs
        if quest_data.get('quest_giver_npc_id'):
            quest['startedBy']['npcs'].append(quest_data['quest_giver_npc_id'])
        if quest_data.get('turn_in_npc_id'):
            quest['finishedBy']['npcs'].append(quest_data['turn_in_npc_id'])
        
        # Add objectives text
        if quest_data.get('objectives_text'):
            quest['objectivesText'].append(quest_data['objectives_text'])
    
    def _aggregate_objectives(self, quest: Dict, objectives: Dict):
        """Aggregate objective data"""
        if not objectives:
            return
        
        quest['has_objectives'] = objectives.get('has_complete_data', False)
        
        # Add creature objectives
        for creature in objectives.get('creatures', []):
            if creature.get('id'):
                quest['objectives']['creatures'].append({
                    'id': creature['id'],
                    'count': creature.get('required', 1),
                    'name': creature.get('name')
                })
        
        # Add item objectives
        for item in objectives.get('items', []):
            if item.get('id'):
                quest['objectives']['items'].append({
                    'id': item['id'],
                    'count': item.get('required', 1),
                    'name': item.get('name')
                })
        
        # Add object interactions
        for obj in objectives.get('objects', []):
            # Objects rarely have IDs in submissions
            quest['objectives']['objects'].append({
                'name': obj.get('name'),
                'coordinates': obj.get('coordinates', [])
            })
    
    def _aggregate_coordinates(self, quest: Dict, coords: Dict):
        """Aggregate coordinate data from surgical parsers"""
        if not coords:
            return
        
        quest['has_coordinates'] = bool(coords.get('all_coordinates'))
        
        # Store raw coordinate data for NPCs to use
        quest['_coord_data'] = coords
        
        # Add NPC spawn coordinates to quest data
        if coords.get('quest_npcs'):
            if coords['quest_npcs'].get('quest_giver'):
                giver = coords['quest_npcs']['quest_giver']
                quest['_quest_giver_coords'] = {'x': giver['x'], 'y': giver['y'], 'zone': giver.get('zone')}
            if coords['quest_npcs'].get('turn_in'):
                turnin = coords['quest_npcs']['turn_in']
                quest['_turn_in_coords'] = {'x': turnin['x'], 'y': turnin['y'], 'zone': turnin.get('zone')}
    
    def _aggregate_zones(self, quest: Dict, quest_data: Dict, coords: Dict):
        """Aggregate zone information with date-based validation"""
        quest_id = quest.get('id')
        
        # Check if we have a known zone mapping for this quest
        if quest_id in self.known_quest_zones:
            quest['zoneOrSort'] = self.known_quest_zones[quest_id]
            return
        
        # Try to get zone from quest data
        zone_name = quest_data.get('zone')
        if zone_name:
            zone_id = self.zone_mapper.get_zone_id(zone_name)
            
            # If submission has zone bug (pre-Dec 6 2025), need to fix it
            if self.has_zone_bug and zone_id:
                # For buggy submissions, try to get proper zone from quest giver NPC
                if quest['startedBy']['npcs']:
                    for npc_id in quest['startedBy']['npcs']:
                        npc_zone = self._get_npc_zone(npc_id)
                        # Only use NPC zone if it's a subzone (not a parent zone)
                        if npc_zone and npc_zone != zone_id and self._is_subzone(npc_zone):
                            quest['zoneOrSort'] = npc_zone
                            return
                # If no better zone found, use the zone we have (better than None)
                quest['zoneOrSort'] = zone_id
                return
            elif zone_id:
                # Post-fix submissions have correct zones
                quest['zoneOrSort'] = zone_id
                return
        
        # Try to get zone from coordinates
        if coords and coords.get('quest_giver'):
            zone_name = coords['quest_giver'].get('zone')
            if zone_name:
                zone_id = self.zone_mapper.get_zone_id(zone_name)
                
                # Same validation for coordinate-based zones
                if self.has_zone_bug and zone_id:
                    if quest['startedBy']['npcs']:
                        for npc_id in quest['startedBy']['npcs']:
                            npc_zone = self._get_npc_zone(npc_id)
                            if npc_zone and npc_zone != zone_id and self._is_subzone(npc_zone):
                                quest['zoneOrSort'] = npc_zone
                                return
                    return
                elif zone_id:
                    quest['zoneOrSort'] = zone_id
    
    def _aggregate_npcs(self, quest: Dict, npcs: Dict, results: Dict):
        """Aggregate NPC data"""
        if not npcs:
            return
        
        # Handle npc_parser's database entries format
        if 'npc_database_entries' in npcs:
            # Process NPCs from npc_database_entries
            for npc_id, npc_data in npcs.get('npc_database_entries', {}).items():
                # Check if NPC already exists to merge data
                if npc_id in self.npcs:
                    # Merge with existing NPC
                    self._merge_npc_data(self.npcs[npc_id], npc_data)
                else:
                    # Create new NPC entry
                    npc_entry = self._create_npc_entry(npc_id, npc_data)
                    
                    # Add coordinates if available
                    if quest.get('_coord_data'):
                        self._add_npc_coordinates(npc_entry, quest['_coord_data'])
                    
                    # Store NPC
                    self.npcs[npc_id] = npc_entry
                    results['npcs'].append(npc_entry)
        else:
            # Fallback for different format
            for npc_id, npc_data in npcs.items():
                if isinstance(npc_data, dict):
                    if npc_id in self.npcs:
                        # Merge with existing NPC
                        self._merge_npc_data(self.npcs[npc_id], npc_data)
                    else:
                        # Create new NPC entry
                        npc_entry = self._create_npc_entry(npc_id, npc_data)
                        
                        # Add coordinates if available
                        if quest.get('_coord_data'):
                            self._add_npc_coordinates(npc_entry, quest['_coord_data'])
                        
                        # Store NPC
                        self.npcs[npc_id] = npc_entry
                        results['npcs'].append(npc_entry)
    
    def _create_npc_entry(self, npc_id: int, npc_data: Dict) -> Dict:
        """Create NPC database entry"""
        # Extract NPCInfo object if it exists
        npc_info = npc_data.get('npc_info')
        
        # Build the entry, extracting from NPCInfo if available
        entry = {
            'id': int(npc_id) if isinstance(npc_id, str) else npc_id,
            'name': None,
            'minLevelHealth': None,
            'maxLevelHealth': None,
            'minLevel': None,
            'maxLevel': None,
            'rank': 0,
            'spawns': {},
            'waypoints': None,
            'zoneID': None,
            'questStarts': [],
            'questEnds': [],
            'factionID': None,
            'friendlyToFaction': None,
            'subName': None,
            'npcFlags': 0
        }
        
        if npc_info:
            # Extract from NPCInfo object
            entry['name'] = npc_info.name if hasattr(npc_info, 'name') else npc_data.get('name')
            
            # Extract level range
            if hasattr(npc_info, 'level_range') and npc_info.level_range:
                entry['minLevel'] = npc_info.level_range[0]
                entry['maxLevel'] = npc_info.level_range[1]
            
            # Extract rank
            entry['rank'] = npc_info.rank if hasattr(npc_info, 'rank') else 0
            
            # Extract zone
            entry['zoneID'] = npc_info.zone_id if hasattr(npc_info, 'zone_id') else None
            
            # CRITICAL: Extract quest linkage data
            entry['questStarts'] = list(npc_info.quest_starts) if hasattr(npc_info, 'quest_starts') and npc_info.quest_starts else []
            entry['questEnds'] = list(npc_info.quest_ends) if hasattr(npc_info, 'quest_ends') and npc_info.quest_ends else []
            
            # Extract faction
            if hasattr(npc_info, 'faction'):
                faction_map = {'Alliance': 'A', 'Horde': 'H', 'Neutral': 'AH'}
                entry['friendlyToFaction'] = faction_map.get(npc_info.faction)
            
            # Extract subname/title
            entry['subName'] = npc_info.sub_name if hasattr(npc_info, 'sub_name') else None
            
            # Extract NPC flags (for service NPCs)
            entry['npcFlags'] = npc_info.npc_flags if hasattr(npc_info, 'npc_flags') else 0
            
            # Extract coordinates
            if hasattr(npc_info, 'coordinates') and npc_info.coordinates and hasattr(npc_info, 'zone_id'):
                entry['spawns'][npc_info.zone_id] = [
                    {'x': coord[0], 'y': coord[1]} for coord in npc_info.coordinates
                ]
        else:
            # Fallback to direct dictionary access
            entry['name'] = npc_data.get('name')
            entry['minLevelHealth'] = npc_data.get('min_hp')
            entry['maxLevelHealth'] = npc_data.get('max_hp')
            entry['minLevel'] = npc_data.get('min_level')
            entry['maxLevel'] = npc_data.get('max_level')
            entry['rank'] = npc_data.get('rank', 0)
            entry['zoneID'] = npc_data.get('zone_id')
            entry['questStarts'] = npc_data.get('questStarts', [])
            entry['questEnds'] = npc_data.get('questEnds', [])
            entry['factionID'] = npc_data.get('faction_id')
            entry['friendlyToFaction'] = npc_data.get('friendly_to')
            entry['subName'] = npc_data.get('title')
            entry['npcFlags'] = npc_data.get('flags', 0)
        
        return entry
    
    def _merge_npc_data(self, existing_npc: Dict, new_npc_data: Dict):
        """Merge new NPC data into existing NPC entry"""
        # Extract NPCInfo object if it exists
        npc_info = new_npc_data.get('npc_info')
        
        if npc_info:
            # Merge quest starts (deduplicate)
            if hasattr(npc_info, 'quest_starts') and npc_info.quest_starts:
                existing_starts = set(existing_npc.get('questStarts', []))
                new_starts = set(npc_info.quest_starts)
                existing_npc['questStarts'] = list(existing_starts | new_starts)
            
            # Merge quest ends (deduplicate)
            if hasattr(npc_info, 'quest_ends') and npc_info.quest_ends:
                existing_ends = set(existing_npc.get('questEnds', []))
                new_ends = set(npc_info.quest_ends)
                existing_npc['questEnds'] = list(existing_ends | new_ends)
            
            # Merge coordinates
            if hasattr(npc_info, 'coordinates') and npc_info.coordinates and hasattr(npc_info, 'zone_id'):
                zone_id = npc_info.zone_id
                if zone_id not in existing_npc['spawns']:
                    existing_npc['spawns'][zone_id] = []
                
                # Add new coordinates
                for coord in npc_info.coordinates:
                    new_coord = {'x': coord[0], 'y': coord[1]}
                    # Check if coordinate doesn't already exist
                    if not any(abs(c['x'] - new_coord['x']) < 0.5 and abs(c['y'] - new_coord['y']) < 0.5 
                              for c in existing_npc['spawns'][zone_id]):
                        existing_npc['spawns'][zone_id].append(new_coord)
            
            # Update NPC flags if new one has service flags
            if hasattr(npc_info, 'npc_flags') and npc_info.npc_flags:
                # Combine flags using bitwise OR
                existing_npc['npcFlags'] = existing_npc.get('npcFlags', 0) | npc_info.npc_flags
            
            # Update other fields if they were empty
            if not existing_npc.get('name') and hasattr(npc_info, 'name'):
                existing_npc['name'] = npc_info.name
            if not existing_npc.get('subName') and hasattr(npc_info, 'sub_name'):
                existing_npc['subName'] = npc_info.sub_name
            if not existing_npc.get('friendlyToFaction') and hasattr(npc_info, 'faction'):
                faction_map = {'Alliance': 'A', 'Horde': 'H', 'Neutral': 'AH'}
                existing_npc['friendlyToFaction'] = faction_map.get(npc_info.faction)
    
    def _add_npc_coordinates(self, npc: Dict, coord_data: Dict):
        """Add spawn coordinates to NPC entry"""
        # Check if this NPC has coordinates in monster data
        for monster_key, monster_data in coord_data.get('monsters', {}).items():
            if monster_data.get('id') == npc['id']:
                # Get zone and deduplicated coordinates
                zone_id = npc.get('zoneID') or 1
                coords = self.coordinate_parser.deduplicate_coordinates(
                    monster_data.get('coordinates', [])
                )
                
                if coords:
                    npc['spawns'][zone_id] = [
                        {'x': c['x'], 'y': c['y']} for c in coords
                    ]
    
    def _aggregate_items(self, quest: Dict, items: Dict, results: Dict):
        """Aggregate item data"""
        if not items:
            return
        
        # Handle item_parser's format
        if 'source_items' in items:
            # Process source items (provided by quest giver)
            for item in items.get('source_items', []):
                if isinstance(item, dict) and item.get('id'):
                    quest['sourceItemId'] = item['id']
                    self.items[item['id']] = item
                    results['items'].append(item)
            
            # Process required items (needed to start quest)
            for item in items.get('required_items', []):
                if isinstance(item, dict) and item.get('id'):
                    quest['requiredSourceItems'].append(item['id'])
                    self.items[item['id']] = item
                    results['items'].append(item)
            
            # Process quest items (objectives)
            for item in items.get('quest_items', []):
                if isinstance(item, dict) and item.get('id'):
                    # Add to objectives if not already there
                    if not any(obj['id'] == item['id'] for obj in quest['objectives']['items'] if 'id' in obj):
                        quest['objectives']['items'].append({
                            'id': item['id'],
                            'count': item.get('count', 1),
                            'name': item.get('name')
                        })
                    self.items[item['id']] = item
                    results['items'].append(item)
        else:
            # Fallback for different format
            for item_id, item_data in items.items():
                if isinstance(item_data, dict):
                    # Check if this is a source item
                    if item_data.get('is_source_item'):
                        quest['sourceItemId'] = item_id
                    
                    # Check if required to start quest
                    if item_data.get('required_to_start'):
                        quest['requiredSourceItems'].append(item_id)
                    
                    # Store item data
                    self.items[item_id] = item_data
                    results['items'].append(item_data)
    
    def _aggregate_chains(self, quest: Dict, chains: Dict):
        """Aggregate quest chain data"""
        if not chains:
            return
        
        if chains.get('prerequisites'):
            quest['preQuestSingle'] = chains['prerequisites']
        if chains.get('required_all'):
            quest['preQuestGroup'] = chains['required_all']
        if chains.get('next_quest'):
            quest['nextQuestInChain'] = chains['next_quest']
        if chains.get('parent'):
            quest['parentQuest'] = chains['parent']
        if chains.get('children'):
            quest['childQuests'] = chains['children']
    
    def _aggregate_flags(self, quest: Dict, flags: Dict):
        """Aggregate quest flags"""
        if not flags:
            return
        
        quest['questFlags'] = flags.get('quest_flags', 0)
        quest['specialFlags'] = flags.get('special_flags', 0)
        
        # Set race/class restrictions
        if flags.get('required_races'):
            quest['requiredRaces'] = flags['required_races']
        if flags.get('required_classes'):
            quest['requiredClasses'] = flags['required_classes']
    
    def _aggregate_reputation(self, quest: Dict, rep: Dict):
        """Aggregate reputation data"""
        if not rep:
            return
        
        if rep.get('required_min'):
            quest['requiredMinRep'] = rep['required_min']
        if rep.get('required_max'):
            quest['requiredMaxRep'] = rep['required_max']
        if rep.get('rewards'):
            quest['reputationReward'] = rep['rewards']
    
    def _aggregate_professions(self, quest: Dict, prof: Dict):
        """Aggregate profession requirements"""
        if not prof:
            return
        
        if prof.get('required_skill'):
            quest['requiredSkill'] = prof['required_skill']
        if prof.get('required_spell'):
            quest['requiredSpell'] = prof['required_spell']
    
    def _aggregate_restrictions(self, quest: Dict, restrictions: Dict):
        """Aggregate restriction analysis results"""
        if not restrictions:
            return
        
        detected = restrictions.get('detected_restrictions', {})
        
        # Apply high-confidence race restrictions
        if detected.get('race') and restrictions.get('confidence_scores', {}).get('race', 0) > 0.8:
            quest['requiredRaces'] = detected['race']
        
        # Apply high-confidence class restrictions  
        if detected.get('class') and restrictions.get('confidence_scores', {}).get('class', 0) > 0.8:
            quest['requiredClasses'] = detected['class']
        
        # Store restriction analysis metadata
        quest['_restriction_analysis'] = {
            'confidence_scores': restrictions.get('confidence_scores', {}),
            'evidence': restrictions.get('evidence', {})
        }
    
    def _process_service_npcs(self, content: str, results: Dict):
        """Process standalone service NPCs (flight masters, vendors, etc)"""
        # Look for SERVICE NPCs section
        service_section = re.search(r'SERVICE NPCs ENCOUNTERED:?\s*\n(.*?)(?:\n\n=|\Z)', 
                                   content, re.DOTALL | re.IGNORECASE)
        
        if service_section:
            lines = service_section.group(1).split('\n\n')
            for block in lines:
                if 'NPC:' in block:
                    self._parse_service_npc_block(block, results)
        
        # Look for FLIGHT MASTERS section
        flight_section = re.search(r'FLIGHT MASTERS:?\s*\n(.*?)(?:\n\n=|\Z)', 
                                  content, re.DOTALL | re.IGNORECASE)
        
        if flight_section:
            lines = flight_section.group(1).split('\n\n')
            for block in lines:
                if 'Flight Master:' in block:
                    self._parse_flight_master_block(block, results)
    
    def _parse_service_npc_block(self, block: str, results: Dict):
        """Parse a service NPC block"""
        # Extract NPC info
        npc_match = re.search(r'NPC:\s*(.+?)\s*\(ID:\s*(\d+)\)', block)
        if not npc_match:
            return
        
        name = npc_match.group(1).strip()
        npc_id = int(npc_match.group(2))
        
        # Extract services
        services = []
        service_match = re.search(r'Services?:\s*(.+)', block, re.IGNORECASE)
        if service_match:
            services = [s.strip() for s in service_match.group(1).split(',')]
        
        # Extract locations
        locations = []
        loc_pattern = r'\*?\s*(.+?)\s+at\s+([\d.]+),\s*([\d.]+)'
        for match in re.findall(loc_pattern, block):
            zone_name = match[0].strip()
            x, y = float(match[1]), float(match[2])
            
            zone_id = self.zone_mapper.get_zone_id(zone_name)
            if zone_id:
                locations.append({'zone': zone_id, 'x': x, 'y': y})
        
        # Calculate NPC flags based on services
        flags = self._calculate_service_flags(services)
        
        # Create NPC entry
        npc_entry = {
            'id': npc_id,
            'name': name,
            'services': services,
            'npcFlags': flags,
            'spawns': {}
        }
        
        # Add spawn locations
        for loc in locations:
            zone = loc['zone']
            if zone not in npc_entry['spawns']:
                npc_entry['spawns'][zone] = []
            npc_entry['spawns'][zone].append({'x': loc['x'], 'y': loc['y']})
        
        results['npcs'].append(npc_entry)
    
    def _parse_flight_master_block(self, block: str, results: Dict):
        """Parse a flight master block"""
        # Extract flight master info
        fm_match = re.search(r'Flight Master:\s*(.+?)\s*\(ID:\s*(\d+)\)', block)
        if not fm_match:
            return
        
        name = fm_match.group(1).strip()
        npc_id = int(fm_match.group(2))
        
        # Extract location
        loc_match = re.search(r'Location:\s*(.+?)\s+at\s+([\d.]+),\s*([\d.]+)', block)
        if not loc_match:
            return
        
        zone_name = loc_match.group(1).strip()
        x, y = float(loc_match.group(2)), float(loc_match.group(3))
        
        zone_id = self.zone_mapper.get_zone_id(zone_name)
        
        # Create NPC entry for flight master
        npc_entry = {
            'id': npc_id,
            'name': name,
            'services': ['flight master'],
            'npcFlags': 8192,  # Flight master flag
            'spawns': {}
        }
        
        if zone_id:
            npc_entry['spawns'][zone_id] = [{'x': x, 'y': y}]
        
        results['npcs'].append(npc_entry)
    
    def _calculate_service_flags(self, services: List[str]) -> int:
        """Calculate NPC flags from services list"""
        flags = 0
        service_flags = {
            'questgiver': 2,
            'vendor': 128,
            'repair': 4096,
            'flight master': 8192,
            'innkeeper': 65536,
            'banker': 131072,
            'trainer': 16,
            'stable master': 4194304,
            'battlemaster': 1048576,
            'auctioneer': 2097152,
            'gossip': 1
        }
        
        for service in services:
            service_lower = service.lower()
            for key, flag in service_flags.items():
                if key in service_lower:
                    flags |= flag
        
        return flags
    
    def generate_database_entries(self, results: Dict) -> Dict:
        """Generate Lua database entries from aggregated data"""
        lua_entries = {
            'quests': [],
            'npcs': []
        }
        
        # Generate quest entries
        for quest in results.get('quests', []):
            entry = self._generate_quest_lua(quest)
            lua_entries['quests'].append(entry)
        
        # Generate NPC entries
        for npc in results.get('npcs', []):
            entry = self._generate_npc_lua(npc)
            lua_entries['npcs'].append(entry)
        
        return lua_entries
    
    def _generate_quest_lua(self, quest: Dict) -> str:
        """Generate Lua entry for a quest with all 30 fields"""
        quest_id = quest['id']
        
        def _esc(s):
            if s is None:
                return ""
            s = str(s)
            s = s.replace('\\', r'\\')
            s = s.replace('\n', r'\n').replace('\r', '')
            s = s.replace('"', r'\"')
            return s
        
        # Build startedBy (field 2)
        started_by = "nil"
        if quest['startedBy']['npcs'] or quest['startedBy']['objects'] or quest['startedBy']['items']:
            npcs = "{" + ",".join(str(n) for n in quest['startedBy']['npcs']) + "}" if quest['startedBy']['npcs'] else "nil"
            objs = "{" + ",".join(str(o) for o in quest['startedBy']['objects']) + "}" if quest['startedBy']['objects'] else "nil"
            items = "{" + ",".join(str(i) for i in quest['startedBy']['items']) + "}" if quest['startedBy']['items'] else "nil"
            started_by = f"{{{npcs},{objs},{items}}}"
        
        # Build finishedBy (field 3)
        finished_by = "nil"
        if quest['finishedBy']['npcs'] or quest['finishedBy']['objects']:
            npcs = "{" + ",".join(str(n) for n in quest['finishedBy']['npcs']) + "}" if quest['finishedBy']['npcs'] else "nil"
            objs = "{" + ",".join(str(o) for o in quest['finishedBy']['objects']) + "}" if quest['finishedBy']['objects'] else "nil"
            finished_by = f"{{{npcs},{objs}}}"
        
        # Build objectives text (field 8)
        obj_text = "nil"
        if quest['objectivesText']:
            texts = '","'.join(_esc(t) for t in quest['objectivesText'])
            obj_text = f'{{"{texts}"}}'
        
        # Build objectives (field 10)
        objectives = "nil"
        if any([quest['objectives']['creatures'], quest['objectives']['objects'], quest['objectives']['items']]):
            # Creatures
            creatures = "nil"
            if quest['objectives']['creatures']:
                creature_parts = []
                for c in quest['objectives']['creatures']:
                    if isinstance(c, dict):
                        creature_parts.append(f"{{{c.get('id', 0)},{c.get('count', 1)}}}")
                if creature_parts:
                    creatures = "{" + ",".join(creature_parts) + "}"
            
            # Objects: only include if object ID is known; omit name-only
            objects = "nil"
            if quest['objectives']['objects']:
                obj_parts = []
                for o in quest['objectives']['objects']:
                    if isinstance(o, dict) and o.get('id'):
                        if o.get('name'):
                            obj_parts.append(f"{{{o.get('id')} ,\"{_esc(o.get('name'))}\"}}")
                        else:
                            obj_parts.append(f"{{{o.get('id')}}}")
                if obj_parts:
                    objects = "{" + ",".join(obj_parts) + "}"
            
            # Items
            items = "nil"
            if quest['objectives']['items']:
                item_parts = []
                for i in quest['objectives']['items']:
                    if isinstance(i, dict):
                        item_parts.append(f"{{{i.get('id', 0)},{i.get('count', 1)}}}")
                if item_parts:
                    items = "{" + ",".join(item_parts) + "}"
            
            objectives = f"{{{creatures},{objects},{items},nil,nil,nil}}"
        
        # Build all 30 fields
        fields = [
            f'"{_esc(quest["name"]) }"',                                           # 1
            started_by,                                                     # 2
            finished_by,                                                     # 3
            str(quest["requiredLevel"]) if quest["requiredLevel"] else "nil",  # 4
            str(quest["questLevel"]) if quest["questLevel"] else "1",         # 5
            str(quest["requiredRaces"]) if quest["requiredRaces"] else "nil",  # 6
            str(quest["requiredClasses"]) if quest["requiredClasses"] else "nil",  # 7
            obj_text,                                                        # 8
            "nil",  # triggerEnd                                           # 9
            objectives,                                                      # 10
            str(quest["sourceItemId"]) if quest["sourceItemId"] else "nil",  # 11
            "{" + ",".join(str(q) for q in quest["preQuestGroup"]) + "}" if quest["preQuestGroup"] else "nil",  # 12
            "{" + ",".join(str(q) for q in quest["preQuestSingle"]) + "}" if quest["preQuestSingle"] else "nil",  # 13
            "{" + ",".join(str(q) for q in quest["childQuests"]) + "}" if quest["childQuests"] else "nil",  # 14
            "{" + ",".join(str(q) for q in quest["inGroupWith"]) + "}" if quest["inGroupWith"] else "nil",  # 15
            "{" + ",".join(str(q) for q in quest["exclusiveTo"]) + "}" if quest["exclusiveTo"] else "nil",  # 16
            str(quest["zoneOrSort"]) if quest["zoneOrSort"] else "nil",  # 17
            "nil",  # requiredSkill                                        # 18
            "nil",  # requiredMinRep                                       # 19
            "nil",  # requiredMaxRep                                       # 20
            "{" + ",".join(str(i) for i in quest["requiredSourceItems"]) + "}" if quest["requiredSourceItems"] else "nil",  # 21
            str(quest["nextQuestInChain"]) if quest["nextQuestInChain"] else "nil",  # 22
            str(quest["questFlags"]) if quest["questFlags"] else "0",     # 23
            str(quest["specialFlags"]) if quest["specialFlags"] else "0",  # 24
            str(quest["parentQuest"]) if quest["parentQuest"] else "nil",  # 25
            "nil",  # reputationReward                                     # 26
            "nil",  # extraObjectives                                      # 27
            "nil",  # requiredSpell                                        # 28
            "nil",  # requiredSpecialization                              # 29
            "nil"   # requiredMaxLevel                                     # 30
        ]
        
        entry = f"[{quest_id}] = {{" + ",".join(fields) + "},"
        
        return entry
    
    def _generate_npc_lua(self, npc: Dict) -> str:
        """Generate Lua entry for an NPC with all 15 fields"""
        npc_id = npc['id']
        
        # Build spawns (field 7)
        spawns = "nil"
        if npc.get('spawns'):
            spawn_parts = []
            for zone_id, coords in npc['spawns'].items():
                coord_str = ",".join(f"{{{c['x']},{c['y']}}}" for c in coords)
                spawn_parts.append(f"[{zone_id}]={{{coord_str}}}")
            spawns = "{" + ",".join(spawn_parts) + "}"
        
        # Build quest starts (field 10)
        quest_starts = "nil"
        if npc.get('questStarts'):
            quest_starts = "{" + ",".join(str(q) for q in npc['questStarts']) + "}"
        
        # Build quest ends (field 11)
        quest_ends = "nil"
        if npc.get('questEnds'):
            quest_ends = "{" + ",".join(str(q) for q in npc['questEnds']) + "}"
        
        # Build all 15 fields
        def _esc(s):
            if s is None:
                return ""
            s = str(s)
            s = s.replace('\\', r'\\').replace('\n', r'\n').replace('\r','').replace('"', r'\"')
            return s

        fields = [
            f'"{_esc(npc.get("name", "Unknown NPC"))}"',                    # 1
            str(npc.get("minLevelHealth")) if npc.get("minLevelHealth") else "nil",  # 2
            str(npc.get("maxLevelHealth")) if npc.get("maxLevelHealth") else "nil",  # 3
            str(npc.get("minLevel")) if npc.get("minLevel") else "nil",              # 4
            str(npc.get("maxLevel")) if npc.get("maxLevel") else "nil",              # 5
            str(npc.get("rank", 0)),                                  # 6
            spawns,                                                    # 7
            "nil",  # waypoints                                       # 8
            str(npc.get("zoneID")) if npc.get("zoneID") else "nil",  # 9
            quest_starts,                                             # 10
            quest_ends,                                               # 11
            str(npc.get("factionID")) if npc.get("factionID") else "nil",  # 12
            f'"{_esc(npc.get("friendlyToFaction"))}"' if npc.get("friendlyToFaction") else "nil",  # 13
            f'"{_esc(npc.get("subName"))}"' if npc.get("subName") else "nil",  # 14
            str(npc.get("npcFlags", 0))                              # 15
        ]
        
        entry = f"[{npc_id}] = {{" + ",".join(fields) + "},"
        
        return entry
    
    def get_summary(self) -> Dict:
        """Get aggregation summary"""
        return {
            'total_quests': len(self.quests),
            'total_npcs': len(self.npcs),
            'total_items': len(self.items),
            'total_objects': len(self.objects),
            'quests_with_objectives': sum(1 for q in self.quests.values() if q.get('has_objectives')),
            'quests_with_coordinates': sum(1 for q in self.quests.values() if q.get('has_coordinates')),
            'complete_quests': sum(1 for q in self.quests.values() if q.get('completeness_score', 0) > 70),
            'validated_quests': sum(1 for q in self.quests.values() if q.get('validation_score', 0) > 50),
            'high_quality_quests': sum(1 for q in self.quests.values() if q.get('quality_level') == 'excellent'),
            'quests_with_restrictions': sum(1 for q in self.quests.values() if q.get('_restriction_analysis')),
            'available_parsers': {
                'npc_parser': self.npc_parser is not None,
                'item_parser': self.item_parser is not None,
                'chain_parser': self.chain_parser is not None,
                'flag_parser': self.flag_parser is not None,
                'reputation_parser': self.reputation_parser is not None,
                'profession_parser': self.profession_parser is not None,
                'validation_engine': self.validation_engine is not None,
                'restriction_analyzer': self.restriction_analyzer is not None,
                'unified_parser': self.unified_parser is not None,
                'database_comparator': self.database_comparator is not None,
                'merge_decision_engine': self.merge_decision_engine is not None
            }
        }
    
    def save_aggregated_data_to_file(self, output_file: str = None) -> str:
        """Save all aggregated data to a human-readable text file for inspection
        
        Returns:
            Path to the generated file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"aggregated_data_{timestamp}.txt"
        
        output_path = Path(output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write("AGGREGATED DATA OUTPUT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write summary
            summary = self.get_summary()
            f.write("SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Quests: {summary['total_quests']}\n")
            f.write(f"Total NPCs: {summary['total_npcs']}\n")
            f.write(f"Total Items: {summary['total_items']}\n")
            f.write(f"Total Objects: {summary['total_objects']}\n")
            f.write(f"Complete Quests (>70 score): {summary['complete_quests']}\n")
            f.write(f"High Quality Quests: {summary['high_quality_quests']}\n")
            f.write("\n")
            
            # Write Quests section
            f.write("=" * 80 + "\n")
            f.write(f"QUESTS ({len(self.quests)} total)\n")
            f.write("=" * 80 + "\n\n")
            
            for quest_id in sorted(self.quests.keys()):
                quest = self.quests[quest_id]
                f.write(f"Quest ID: {quest_id}\n")
                f.write("-" * 40 + "\n")
                
                # Basic info
                f.write(f"  Name: {quest.get('name', 'Unknown')}\n")
                f.write(f"  Level: {quest.get('level', 'Unknown')}\n")
                f.write(f"  Required Level: {quest.get('requiredLevel', 'Unknown')}\n")
                f.write(f"  Zone: {quest.get('zone', 'Unknown')} (ID: {quest.get('zoneID', 'Unknown')})\n")
                
                # Quest givers
                if quest.get('questGivers'):
                    f.write(f"  Quest Givers:\n")
                    for giver in quest['questGivers']:
                        if isinstance(giver, dict):
                            f.write(f"    - NPC {giver.get('id', '?')}: {giver.get('name', 'Unknown')}\n")
                        else:
                            f.write(f"    - NPC ID: {giver}\n")
                
                # Turn-in NPCs
                if quest.get('turnIn'):
                    f.write(f"  Turn-in NPCs:\n")
                    for turnin in quest['turnIn']:
                        if isinstance(turnin, dict):
                            f.write(f"    - NPC {turnin.get('id', '?')}: {turnin.get('name', 'Unknown')}\n")
                        else:
                            f.write(f"    - NPC ID: {turnin}\n")
                
                # Objectives
                if quest.get('objectives'):
                    f.write(f"  Objectives:\n")
                    objs = quest['objectives']
                    if objs.get('creatures'):
                        for creature in objs['creatures']:
                            f.write(f"    - Kill: {creature.get('name', 'Unknown')} (ID: {creature.get('id', '?')}) x{creature.get('count', 1)}\n")
                    if objs.get('items'):
                        for item in objs['items']:
                            f.write(f"    - Collect: {item.get('name', 'Unknown')} (ID: {item.get('id', '?')}) x{item.get('count', 1)}\n")
                    if objs.get('objects'):
                        for obj in objs['objects']:
                            f.write(f"    - Interact: {obj.get('name', 'Unknown')} (ID: {obj.get('id', '?')}) x{obj.get('count', 1)}\n")
                
                # Quest chain info
                if quest.get('preQuestSingle'):
                    f.write(f"  Requires one of: {quest['preQuestSingle']}\n")
                if quest.get('preQuestGroup'):
                    f.write(f"  Requires all of: {quest['preQuestGroup']}\n")
                if quest.get('nextQuestInChain'):
                    f.write(f"  Next quest: {quest['nextQuestInChain']}\n")
                
                # Restrictions
                if quest.get('requiredRaces'):
                    f.write(f"  Race restriction: {quest['requiredRaces']}\n")
                if quest.get('requiredClasses'):
                    f.write(f"  Class restriction: {quest['requiredClasses']}\n")
                if quest.get('requiredFaction'):
                    f.write(f"  Faction: {quest['requiredFaction']}\n")
                
                # Quality metrics
                f.write(f"  Completeness Score: {quest.get('completeness_score', 0)}\n")
                f.write(f"  Validation Score: {quest.get('validation_score', 0)}\n")
                f.write(f"  Quality Level: {quest.get('quality_level', 'unknown')}\n")
                
                # Raw data for debugging
                if quest.get('_raw_data'):
                    f.write(f"  Source file: {quest['_raw_data'].get('source_file', 'Unknown')}\n")
                
                f.write("\n")
            
            # Write NPCs section
            f.write("=" * 80 + "\n")
            f.write(f"NPCS ({len(self.npcs)} total)\n")
            f.write("=" * 80 + "\n\n")
            
            for npc_id in sorted(self.npcs.keys()):
                npc = self.npcs[npc_id]
                f.write(f"NPC ID: {npc_id}\n")
                f.write("-" * 40 + "\n")
                
                f.write(f"  Name: {npc.get('name', 'Unknown')}\n")
                f.write(f"  Level: {npc.get('minLevel', '?')}-{npc.get('maxLevel', '?')}\n")
                f.write(f"  Zone: {npc.get('zoneID', 'Unknown')}\n")
                
                # Spawn locations
                if npc.get('spawns'):
                    f.write(f"  Spawn Locations:\n")
                    for zone_id, coords in npc['spawns'].items():
                        f.write(f"    Zone {zone_id}:\n")
                        for coord in coords:
                            f.write(f"      - [{coord['x']}, {coord['y']}]\n")
                
                # Quest associations
                if npc.get('questStarts'):
                    f.write(f"  Starts quests: {npc['questStarts']}\n")
                if npc.get('questEnds'):
                    f.write(f"  Ends quests: {npc['questEnds']}\n")
                
                # NPC flags (vendor, flight master, etc.)
                if npc.get('npcFlags'):
                    f.write(f"  NPC Flags: {npc['npcFlags']}")
                    # Decode common flags
                    flags = npc['npcFlags']
                    flag_names = []
                    if flags & 2: flag_names.append("QuestGiver")
                    if flags & 128: flag_names.append("Vendor")
                    if flags & 4096: flag_names.append("Repair")
                    if flags & 8192: flag_names.append("FlightMaster")
                    if flags & 65536: flag_names.append("Innkeeper")
                    if flags & 131072: flag_names.append("Banker")
                    if flag_names:
                        f.write(f" ({', '.join(flag_names)})")
                    f.write("\n")
                
                f.write("\n")
            
            # Write Items section
            if self.items:
                f.write("=" * 80 + "\n")
                f.write(f"ITEMS ({len(self.items)} total)\n")
                f.write("=" * 80 + "\n\n")
                
                for item_id in sorted(self.items.keys()):
                    item = self.items[item_id]
                    f.write(f"Item ID: {item_id}\n")
                    f.write(f"  Name: {item.get('name', 'Unknown')}\n")
                    if item.get('questID'):
                        f.write(f"  Associated Quest: {item['questID']}\n")
                    if item.get('droppers'):
                        f.write(f"  Dropped by NPCs: {item['droppers']}\n")
                    f.write("\n")
            
            # Write Objects section
            if self.objects:
                f.write("=" * 80 + "\n")
                f.write(f"OBJECTS ({len(self.objects)} total)\n")
                f.write("=" * 80 + "\n\n")
                
                for obj_id in sorted(self.objects.keys()):
                    obj = self.objects[obj_id]
                    f.write(f"Object ID: {obj_id}\n")
                    f.write(f"  Name: {obj.get('name', 'Unknown')}\n")
                    if obj.get('spawns'):
                        f.write(f"  Spawn Locations:\n")
                        for zone_id, coords in obj['spawns'].items():
                            f.write(f"    Zone {zone_id}: {coords}\n")
                    f.write("\n")
            
            # Write Lua output samples
            f.write("=" * 80 + "\n")
            f.write("LUA OUTPUT SAMPLES\n")
            f.write("=" * 80 + "\n\n")
            
            # Show first 3 quests as Lua
            if self.quests:
                f.write("Sample Quest Lua Entries:\n")
                f.write("-" * 40 + "\n")
                for quest_id in list(sorted(self.quests.keys()))[:3]:
                    lua_entry = self._generate_quest_lua(self.quests[quest_id])
                    f.write(f"{lua_entry}\n")
                f.write("\n")
            
            # Show first 3 NPCs as Lua
            if self.npcs:
                f.write("Sample NPC Lua Entries:\n")
                f.write("-" * 40 + "\n")
                for npc_id in list(sorted(self.npcs.keys()))[:3]:
                    lua_entry = self._generate_npc_lua(self.npcs[npc_id])
                    f.write(f"{lua_entry}\n")
                f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("END OF AGGREGATED DATA\n")
            f.write("=" * 80 + "\n")
        
        print(f"✓ Aggregated data saved to: {output_path.absolute()}")
        return str(output_path.absolute())
    
    def _load_npc_database(self) -> Dict:
        """Load epochNpcDB.lua for NPC zone lookups"""
        npc_db = {}
        try:
            # Look for epochNpcDB.lua
            db_path = Path(__file__).parent.parent.parent.parent / "Database" / "Epoch" / "epochNpcDB.lua"
            if not db_path.exists():
                # Try alternative path - update to your Questie installation
                db_path = Path("../../Database/Epoch/epochNpcDB.lua")
            
            if db_path.exists():
                with open(db_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse NPC entries: [npcId] = {name, ...fields...}
                # Field 9 is the zoneID
                pattern = r'\[(\d+)\]\s*=\s*\{([^}]+)\}'
                for match in re.finditer(pattern, content):
                    npc_id = int(match.group(1))
                    fields = match.group(2)
                    
                    # Parse fields (comma-separated, handling nested tables)
                    # We only need field 9 (zoneID)
                    field_count = 0
                    in_table = 0
                    current_field = ""
                    
                    for char in fields:
                        if char == '{': 
                            in_table += 1
                        elif char == '}':
                            in_table -= 1
                        elif char == ',' and in_table == 0:
                            field_count += 1
                            if field_count == 9:  # Just passed field 9
                                # Extract zone ID from current_field
                                zone_match = re.search(r'(\d+)', current_field)
                                if zone_match:
                                    npc_db[npc_id] = int(zone_match.group(1))
                                break
                            current_field = ""
                        else:
                            if field_count == 8:  # Building field 9
                                current_field += char
        except Exception as e:
            print(f"Warning: Could not load NPC database for zone lookups: {e}")
        
        return npc_db
    
    def _get_zone_name(self, zone_id: int) -> Optional[str]:
        """Get zone name from ID for tracking"""
        if not zone_id:
            return None
        
        # Would need reverse mapping from zone_mapper
        # For now just return the ID as string
        return f"Zone_{zone_id}"
    
    def _get_npc_zone(self, npc_id: int) -> Optional[int]:
        """Get zone ID for an NPC from the database"""
        try:
            return self.npc_database.get(int(npc_id))
        except (ValueError, TypeError):
            return None
    
    def _is_conflicting_variation(self, new_quest: Dict, existing_variations: List[Dict]) -> bool:
        """
        Check if new quest data conflicts with existing variations
        Focus on critical fields that shouldn't vary:
        - Quest giver NPCs
        - Turn-in NPCs
        - Quest level
        
        Ignore fields that naturally vary:
        - Coordinates (slightly different positions)
        - Objective progress
        - Items looted along the way
        """
        for existing in existing_variations:
            # Check quest giver NPCs
            new_starters = set(new_quest.get('startedBy', {}).get('npcs', []))
            existing_starters = set(existing.get('startedBy', {}).get('npcs', []))
            if new_starters != existing_starters and (new_starters and existing_starters):
                return True  # Different quest givers = conflict
            
            # Check turn-in NPCs
            new_finishers = set(new_quest.get('finishedBy', {}).get('npcs', []))
            existing_finishers = set(existing.get('finishedBy', {}).get('npcs', []))
            if new_finishers != existing_finishers and (new_finishers and existing_finishers):
                return True  # Different turn-in NPCs = conflict
            
            # Check quest level (shouldn't vary)
            if (new_quest.get('questLevel') != existing.get('questLevel') and
                new_quest.get('questLevel') is not None and 
                existing.get('questLevel') is not None):
                return True  # Different levels = conflict
        
        return False  # No significant conflicts
    
    def _is_subzone(self, zone_id: int) -> bool:
        """Check if a zone ID is a subzone (not a parent zone)
        
        Parent zones are typically: 1-100, 1337, 1497, 1519, 1537, 1637, etc.
        Subzones are typically: 100-999 (excluding special parent zones)
        """
        # Known parent zones from zoneTables.lua
        parent_zones = {
            1, 3, 4, 8, 10, 11, 12, 14, 15, 16, 17, 28, 33, 36, 38, 40, 41, 44, 45, 46, 47,
            51, 65, 66, 67, 85, 130, 139, 141, 148, 215, 267, 331, 357, 361, 394, 400, 405,
            406, 440, 490, 491, 493, 495, 618, 719, 796, 876, 1176, 1337, 1377, 1497, 1519,
            1537, 1581, 1637, 1638, 1657, 1977, 2017, 2057, 2100, 2159, 2257, 2366, 2367,
            2437, 2557, 2597, 2677, 2717, 2797, 2817, 2837, 2897, 2917, 3277, 3357, 3358,
            3428, 3429, 3430, 3433, 3456, 3457, 3477, 3478, 3479, 3483, 3487, 3518, 3519,
            3520, 3521, 3522, 3523, 3524, 3525, 3537, 3557, 3606, 3607, 3703, 3711, 3713,
            3714, 3715, 3716, 3717, 3820, 3905, 3959, 4080, 4100, 4196, 4197, 4228, 4264,
            4265, 4272, 4273, 4384, 4395, 4415, 4416, 4493, 4494, 4500, 4603, 4710, 4714,
            4720, 4722, 4723, 4742, 4755, 4809, 4812, 4813, 4815, 4820, 4922, 4987, 5034,
            5035, 5042, 5088, 5144, 5145, 5146, 5287, 5339, 5389
        }
        
        return zone_id not in parent_zones

def main():
    """Test the data aggregator"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_aggregator.py <submission_file>")
        sys.exit(1)
    
    aggregator = DataAggregator()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    results = aggregator.process_submission(content, sys.argv[1])
    
    print(f"\nAggregation Results:")
    print(f"Quests Found: {len(results['quests'])}")
    print(f"NPCs Found: {len(results['npcs'])}")
    print(f"Items Found: {len(results['items'])}")
    print(f"Objects Found: {len(results['objects'])}")
    
    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['warnings']:
        print(f"\nWarnings:")
        for warning in results['warnings']:
            print(f"  - {warning}")
    
    # Show quest details
    for quest in results['quests']:
        print(f"\nQuest {quest['id']}: {quest['name']}")
        print(f"  Level: {quest['questLevel']}")
        print(f"  Zone: {quest.get('zoneOrSort', 'Unknown')}")
        print(f"  Has Objectives: {quest.get('has_objectives', False)}")
        print(f"  Has Coordinates: {quest.get('has_coordinates', False)}")
    
    print(f"\nSummary: {json.dumps(aggregator.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()
