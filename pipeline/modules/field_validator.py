#!/usr/bin/env python3
"""
Field Validator - Validate each database field meets requirements
Ensures data types, ranges, and constraints for all fields
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any


class FieldValidator:
    """
    Validates individual database fields against their requirements
    Ensures type correctness, value ranges, and referential integrity
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.errors = []
        self.warnings = []
        
        # Quest field definitions (30 fields)
        self.quest_fields = {
            1: {'name': 'name', 'type': str, 'required': True, 'min_length': 3, 'max_length': 100},
            2: {'name': 'startedBy', 'type': tuple, 'required': True, 'structure': 'triple_array'},
            3: {'name': 'finishedBy', 'type': tuple, 'required': True, 'structure': 'double_array'},
            4: {'name': 'requiredLevel', 'type': int, 'required': False, 'min': 1, 'max': 85},
            5: {'name': 'questLevel', 'type': int, 'required': True, 'min': 1, 'max': 85},
            6: {'name': 'requiredRaces', 'type': int, 'required': False, 'bitmask': True},
            7: {'name': 'requiredClasses', 'type': int, 'required': False, 'bitmask': True},
            8: {'name': 'objectivesText', 'type': list, 'required': False, 'element_type': str},
            9: {'name': 'triggerEnd', 'type': tuple, 'required': False, 'structure': 'trigger'},
            10: {'name': 'objectives', 'type': dict, 'required': False, 'structure': 'objectives'},
            11: {'name': 'sourceItemId', 'type': int, 'required': False, 'min': 1},
            12: {'name': 'preQuestGroup', 'type': list, 'required': False, 'element_type': int},
            13: {'name': 'preQuestSingle', 'type': list, 'required': False, 'element_type': int},
            14: {'name': 'childQuests', 'type': list, 'required': False, 'element_type': int},
            15: {'name': 'inGroupWith', 'type': list, 'required': False, 'element_type': int},
            16: {'name': 'exclusiveTo', 'type': list, 'required': False, 'element_type': int},
            17: {'name': 'zoneOrSort', 'type': int, 'required': False},
            18: {'name': 'requiredSkill', 'type': tuple, 'required': False, 'structure': 'skill'},
            19: {'name': 'requiredMinRep', 'type': tuple, 'required': False, 'structure': 'reputation'},
            20: {'name': 'requiredMaxRep', 'type': tuple, 'required': False, 'structure': 'reputation'},
            21: {'name': 'requiredSourceItems', 'type': list, 'required': False, 'element_type': int},
            22: {'name': 'nextQuestInChain', 'type': int, 'required': False, 'min': 1},
            23: {'name': 'questFlags', 'type': int, 'required': False, 'bitmask': True},
            24: {'name': 'specialFlags', 'type': int, 'required': False, 'bitmask': True},
            25: {'name': 'parentQuest', 'type': int, 'required': False, 'min': 1},
            26: {'name': 'reputationReward', 'type': list, 'required': False, 'structure': 'rep_reward'},
            27: {'name': 'extraObjectives', 'type': list, 'required': False, 'structure': 'spell_objectives'},
            28: {'name': 'requiredSpell', 'type': int, 'required': False, 'min': 1},
            29: {'name': 'requiredSpecialization', 'type': int, 'required': False, 'min': 1},
            30: {'name': 'requiredMaxLevel', 'type': int, 'required': False, 'min': 1, 'max': 85},
        }
        
        # NPC field definitions (15 fields)
        self.npc_fields = {
            1: {'name': 'name', 'type': str, 'required': True, 'min_length': 2, 'max_length': 100},
            2: {'name': 'minLevelHealth', 'type': int, 'required': False, 'min': 1},
            3: {'name': 'maxLevelHealth', 'type': int, 'required': False, 'min': 1},
            4: {'name': 'minLevel', 'type': int, 'required': True, 'min': 1, 'max': 85},
            5: {'name': 'maxLevel', 'type': int, 'required': True, 'min': 1, 'max': 85},
            6: {'name': 'rank', 'type': int, 'required': False, 'min': 0, 'max': 4},
            7: {'name': 'spawns', 'type': dict, 'required': False, 'structure': 'spawn_dict'},
            8: {'name': 'waypoints', 'type': dict, 'required': False, 'structure': 'waypoint_dict'},
            9: {'name': 'zoneID', 'type': int, 'required': False, 'min': 1},
            10: {'name': 'questStarts', 'type': list, 'required': False, 'element_type': int},
            11: {'name': 'questEnds', 'type': list, 'required': False, 'element_type': int},
            12: {'name': 'factionID', 'type': int, 'required': False, 'min': 1},
            13: {'name': 'friendlyToFaction', 'type': str, 'required': False, 'values': ['A', 'H', 'AH']},
            14: {'name': 'subName', 'type': str, 'required': False, 'max_length': 100},
            15: {'name': 'npcFlags', 'type': int, 'required': False, 'bitmask': True},
        }
        
        # Valid quest flags
        self.valid_quest_flags = {
            1: 'QUEST_FLAGS_STAY_ALIVE',
            2: 'QUEST_FLAGS_PARTY_ACCEPT',
            8: 'QUEST_FLAGS_EXPLORATION',
            32: 'QUEST_FLAGS_SHARABLE',
            64: 'QUEST_FLAGS_EPIC',
            128: 'QUEST_FLAGS_RAID',
            256: 'QUEST_FLAGS_TBC',
            512: 'QUEST_FLAGS_NO_MONEY_FROM_XP',
            1024: 'QUEST_FLAGS_HIDDEN_REWARDS',
            2048: 'QUEST_FLAGS_TRACKING',
            4096: 'QUEST_FLAGS_DAILY',
            8192: 'QUEST_FLAGS_WEEKLY',
            32768: 'QUEST_FLAGS_AUTO_COMPLETE',
        }
        
        # Valid NPC flags
        self.valid_npc_flags = {
            1: 'GOSSIP',
            2: 'QUESTGIVER',
            16: 'TRAINER',
            128: 'VENDOR',
            512: 'REPAIR',
            4096: 'FLIGHTMASTER',
            8192: 'INNKEEPER',
            16384: 'BANKER',
            65536: 'BATTLEMASTER',
            131072: 'AUCTIONEER',
            262144: 'STABLEMASTER',
            524288: 'GUILD_BANKER',
        }
    
    def validate_quest(self, quest_data: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a complete quest entry
        
        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        quest_id = quest_data.get('quest_id')
        if not quest_id:
            self.errors.append("Missing quest_id")
            return False, self.errors, self.warnings
        
        # Validate each field
        for field_num, field_def in self.quest_fields.items():
            field_name = field_def['name']
            value = quest_data.get(field_name)
            
            self._validate_field(value, field_def, f"Quest {quest_id} field {field_num} ({field_name})")
        
        # Cross-field validations
        self._validate_quest_cross_fields(quest_data)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def validate_npc(self, npc_data: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a complete NPC entry
        
        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        npc_id = npc_data.get('npc_id')
        if not npc_id:
            self.errors.append("Missing npc_id")
            return False, self.errors, self.warnings
        
        # Validate each field
        for field_num, field_def in self.npc_fields.items():
            field_name = field_def['name']
            value = npc_data.get(field_name)
            
            self._validate_field(value, field_def, f"NPC {npc_id} field {field_num} ({field_name})")
        
        # Cross-field validations
        self._validate_npc_cross_fields(npc_data)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_field(self, value: Any, field_def: Dict, context: str):
        """Validate a single field against its definition"""
        # Check required
        if field_def['required'] and value is None:
            self.errors.append(f"{context}: Required field is missing")
            return
        
        # Allow None for optional fields
        if not field_def['required'] and value is None:
            return
        
        # Type checking
        expected_type = field_def['type']
        if not isinstance(value, expected_type):
            self.errors.append(f"{context}: Expected {expected_type.__name__}, got {type(value).__name__}")
            return
        
        # String validations
        if expected_type == str:
            if 'min_length' in field_def and len(value) < field_def['min_length']:
                self.errors.append(f"{context}: String too short (min: {field_def['min_length']})")
            if 'max_length' in field_def and len(value) > field_def['max_length']:
                self.warnings.append(f"{context}: String too long (max: {field_def['max_length']})")
            if 'values' in field_def and value not in field_def['values']:
                self.errors.append(f"{context}: Invalid value '{value}', must be one of {field_def['values']}")
        
        # Integer validations
        elif expected_type == int:
            if 'min' in field_def and value < field_def['min']:
                self.errors.append(f"{context}: Value {value} below minimum ({field_def['min']})")
            if 'max' in field_def and value > field_def['max']:
                self.errors.append(f"{context}: Value {value} above maximum ({field_def['max']})")
            if field_def.get('bitmask'):
                self._validate_bitmask(value, context)
        
        # List validations
        elif expected_type == list:
            if 'element_type' in field_def:
                for i, element in enumerate(value):
                    if not isinstance(element, field_def['element_type']):
                        self.errors.append(f"{context}[{i}]: Expected {field_def['element_type'].__name__}")
            if 'structure' in field_def:
                self._validate_structure(value, field_def['structure'], context)
        
        # Tuple validations
        elif expected_type == tuple:
            if 'structure' in field_def:
                self._validate_structure(value, field_def['structure'], context)
        
        # Dict validations
        elif expected_type == dict:
            if 'structure' in field_def:
                self._validate_structure(value, field_def['structure'], context)
    
    def _validate_structure(self, value: Any, structure: str, context: str):
        """Validate complex data structures"""
        if structure == 'triple_array':
            # startedBy format: ((NPCs), (Objects), (Items))
            if not isinstance(value, (tuple, list)) or len(value) != 3:
                self.errors.append(f"{context}: Must be 3-element array")
                return
            for i, subarray in enumerate(value):
                if subarray is not None and not isinstance(subarray, (list, tuple)):
                    self.errors.append(f"{context}[{i}]: Must be array or None")
        
        elif structure == 'double_array':
            # finishedBy format: ((NPCs), (Objects))
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                self.errors.append(f"{context}: Must be 2-element array")
                return
            for i, subarray in enumerate(value):
                if subarray is not None and not isinstance(subarray, (list, tuple)):
                    self.errors.append(f"{context}[{i}]: Must be array or None")
        
        elif structure == 'objectives':
            # objectives format: {creatures, objects, items, reputation, killCredit, spells}
            valid_keys = {'creatures', 'objects', 'items', 'reputation', 'killCredit', 'spells'}
            for key in value.keys():
                if key not in valid_keys:
                    self.warnings.append(f"{context}: Unknown objective type '{key}'")
        
        elif structure == 'trigger':
            # triggerEnd format: (text, {[zoneID]: [(x,y)]})
            if len(value) != 2:
                self.errors.append(f"{context}: Must be (text, locations)")
        
        elif structure == 'skill':
            # requiredSkill format: (skillId, value)
            if len(value) != 2:
                self.errors.append(f"{context}: Must be (skillId, value)")
        
        elif structure == 'reputation':
            # reputation format: (factionId, value)
            if len(value) != 2:
                self.errors.append(f"{context}: Must be (factionId, value)")
        
        elif structure == 'spawn_dict':
            # spawns format: {[zoneId]: [(x,y)]}
            for zone_id, coords in value.items():
                if not isinstance(zone_id, int):
                    self.errors.append(f"{context}: Zone ID must be integer")
                if not isinstance(coords, (list, tuple)):
                    self.errors.append(f"{context}[{zone_id}]: Coords must be array")
                for coord in coords:
                    if not isinstance(coord, (list, tuple)) or len(coord) != 2:
                        self.errors.append(f"{context}[{zone_id}]: Each coord must be (x,y)")
                    else:
                        x, y = coord
                        if not (0 <= x <= 100 and 0 <= y <= 100):
                            self.warnings.append(f"{context}[{zone_id}]: Coordinates should be 0-100")
    
    def _validate_bitmask(self, value: int, context: str):
        """Validate bitmask fields"""
        if value < 0:
            self.errors.append(f"{context}: Bitmask cannot be negative")
        
        # Check if it's a valid combination of flags
        if 'quest' in context.lower() and 'flags' in context.lower():
            unknown_flags = value
            for flag_value in self.valid_quest_flags.keys():
                if value & flag_value:
                    unknown_flags &= ~flag_value
            if unknown_flags:
                self.warnings.append(f"{context}: Contains unknown flags: {unknown_flags}")
        
        elif 'npc' in context.lower() and 'flags' in context.lower():
            unknown_flags = value
            for flag_value in self.valid_npc_flags.keys():
                if value & flag_value:
                    unknown_flags &= ~flag_value
            if unknown_flags:
                self.warnings.append(f"{context}: Contains unknown flags: {unknown_flags}")
    
    def _validate_quest_cross_fields(self, quest_data: Dict):
        """Validate cross-field constraints for quests"""
        # Level validations
        req_level = quest_data.get('requiredLevel')
        quest_level = quest_data.get('questLevel')
        max_level = quest_data.get('requiredMaxLevel')
        
        if req_level and quest_level and req_level > quest_level + 5:
            self.warnings.append(f"Required level {req_level} unusually high for quest level {quest_level}")
        
        if req_level and max_level and req_level >= max_level:
            self.errors.append(f"Required level {req_level} >= max level {max_level}")
        
        # Quest chain validations
        parent = quest_data.get('parentQuest')
        children = quest_data.get('childQuests', [])
        
        if parent and children and parent in children:
            self.errors.append("Quest cannot be both parent and child of same quest")
        
        # Exclusive quest validation
        exclusive = quest_data.get('exclusiveTo', [])
        quest_id = quest_data.get('quest_id')
        
        if quest_id and exclusive and quest_id in exclusive:
            self.errors.append("Quest cannot be exclusive with itself")
    
    def _validate_npc_cross_fields(self, npc_data: Dict):
        """Validate cross-field constraints for NPCs"""
        # Level validations
        min_level = npc_data.get('minLevel')
        max_level = npc_data.get('maxLevel')
        
        if min_level and max_level and min_level > max_level:
            self.errors.append(f"Min level {min_level} > max level {max_level}")
        
        # Health validations
        min_health = npc_data.get('minLevelHealth')
        max_health = npc_data.get('maxLevelHealth')
        
        if min_health and max_health and min_health > max_health:
            self.warnings.append(f"Min health {min_health} > max health {max_health}")
        
        # Flag validations
        npc_flags = npc_data.get('npcFlags', 0)
        quest_starts = npc_data.get('questStarts', [])
        quest_ends = npc_data.get('questEnds', [])
        
        if (quest_starts or quest_ends) and not (npc_flags & 2):  # QUESTGIVER flag
            self.warnings.append("NPC has quests but missing QUESTGIVER flag")


def main():
    """Test the field validator"""
    validator = FieldValidator()
    
    # Test quest validation
    test_quest = {
        'quest_id': 12345,
        'name': 'Test Quest',
        'startedBy': ([46834], None, None),
        'finishedBy': ([46718], None),
        'questLevel': 10,
        'requiredLevel': 8,
        'objectives': {
            'creatures': [{'npc_id': 100, 'count': 10}]
        }
    }
    
    is_valid, errors, warnings = validator.validate_quest(test_quest)
    print(f"Quest Valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    if warnings:
        print(f"Warnings: {warnings}")


if __name__ == "__main__":
    main()