#!/usr/bin/env python3
"""
Validation Engine Module - Validates completeness and quality of quest entries
Checks all 30 quest fields and 15 NPC fields for data quality and completeness
"""

import re
from typing import Dict, List, Optional, Tuple
import json

class ValidationEngine:
    """Validates quest and NPC data for completeness and quality"""
    
    def __init__(self):
        self.validation_results = {}
        self.validation_errors = []
        
        # Quest field requirements and validation rules
        self.quest_field_rules = {
            1: {'name': 'name', 'required': True, 'type': str, 'min_length': 3},
            2: {'name': 'startedBy', 'required': True, 'type': dict, 'validate_func': self._validate_started_by},
            3: {'name': 'finishedBy', 'required': True, 'type': dict, 'validate_func': self._validate_finished_by},
            4: {'name': 'requiredLevel', 'required': False, 'type': int, 'min_value': 1, 'max_value': 80},
            5: {'name': 'questLevel', 'required': True, 'type': int, 'min_value': 1, 'max_value': 80},
            6: {'name': 'requiredRaces', 'required': False, 'type': int, 'validate_func': self._validate_race_mask},
            7: {'name': 'requiredClasses', 'required': False, 'type': int, 'validate_func': self._validate_class_mask},
            8: {'name': 'objectivesText', 'required': True, 'type': list, 'min_items': 1},
            9: {'name': 'triggerEnd', 'required': False, 'type': dict, 'validate_func': self._validate_trigger_end},
            10: {'name': 'objectives', 'required': True, 'type': dict, 'validate_func': self._validate_objectives},
            11: {'name': 'sourceItemId', 'required': False, 'type': int, 'min_value': 1},
            12: {'name': 'preQuestGroup', 'required': False, 'type': list, 'validate_func': self._validate_quest_list},
            13: {'name': 'preQuestSingle', 'required': False, 'type': list, 'validate_func': self._validate_quest_list},
            14: {'name': 'childQuests', 'required': False, 'type': list, 'validate_func': self._validate_quest_list},
            15: {'name': 'inGroupWith', 'required': False, 'type': list, 'validate_func': self._validate_quest_list},
            16: {'name': 'exclusiveTo', 'required': False, 'type': list, 'validate_func': self._validate_quest_list},
            17: {'name': 'zoneOrSort', 'required': True, 'type': int, 'validate_func': self._validate_zone_or_sort},
            18: {'name': 'requiredSkill', 'required': False, 'type': dict, 'validate_func': self._validate_skill_req},
            19: {'name': 'requiredMinRep', 'required': False, 'type': dict, 'validate_func': self._validate_rep_req},
            20: {'name': 'requiredMaxRep', 'required': False, 'type': dict, 'validate_func': self._validate_rep_req},
            21: {'name': 'requiredSourceItems', 'required': False, 'type': list, 'validate_func': self._validate_item_list},
            22: {'name': 'nextQuestInChain', 'required': False, 'type': int, 'min_value': 1},
            23: {'name': 'questFlags', 'required': True, 'type': int, 'min_value': 0},
            24: {'name': 'specialFlags', 'required': True, 'type': int, 'min_value': 0},
            25: {'name': 'parentQuest', 'required': False, 'type': int, 'min_value': 1},
            26: {'name': 'reputationReward', 'required': False, 'type': list, 'validate_func': self._validate_rep_rewards},
            27: {'name': 'extraObjectives', 'required': False, 'type': list, 'validate_func': self._validate_extra_objectives},
            28: {'name': 'requiredSpell', 'required': False, 'type': int, 'min_value': 1},
            29: {'name': 'requiredSpecialization', 'required': False, 'type': int, 'min_value': 1},
            30: {'name': 'requiredMaxLevel', 'required': False, 'type': int, 'min_value': 1, 'max_value': 80}
        }
        
        # NPC field requirements
        self.npc_field_rules = {
            1: {'name': 'name', 'required': True, 'type': str, 'min_length': 2},
            2: {'name': 'minLevelHealth', 'required': False, 'type': int, 'min_value': 1},
            3: {'name': 'maxLevelHealth', 'required': False, 'type': int, 'min_value': 1},
            4: {'name': 'minLevel', 'required': True, 'type': int, 'min_value': 1, 'max_value': 80},
            5: {'name': 'maxLevel', 'required': True, 'type': int, 'min_value': 1, 'max_value': 80},
            6: {'name': 'rank', 'required': True, 'type': int, 'min_value': 0, 'max_value': 4},
            7: {'name': 'spawns', 'required': True, 'type': dict, 'validate_func': self._validate_spawns},
            8: {'name': 'waypoints', 'required': False, 'type': dict, 'validate_func': self._validate_waypoints},
            9: {'name': 'zoneID', 'required': True, 'type': int, 'min_value': 1},
            10: {'name': 'questStarts', 'required': False, 'type': list, 'validate_func': self._validate_quest_list},
            11: {'name': 'questEnds', 'required': False, 'type': list, 'validate_func': self._validate_quest_list},
            12: {'name': 'factionID', 'required': False, 'type': int, 'min_value': 1},
            13: {'name': 'friendlyToFaction', 'required': False, 'type': str, 'validate_func': self._validate_faction_friendly},
            14: {'name': 'subName', 'required': False, 'type': str, 'max_length': 100},
            15: {'name': 'npcFlags', 'required': True, 'type': int, 'min_value': 0}
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            'excellent': 90,
            'good': 75,
            'acceptable': 60,
            'poor': 40,
            'incomplete': 0
        }
        
    def validate_quest(self, quest_data: Dict) -> Dict:
        """
        Validate a complete quest entry
        
        Returns:
            Validation result with score, errors, warnings, and recommendations
        """
        quest_id = quest_data.get('id')
        result = {
            'quest_id': quest_id,
            'overall_score': 0,
            'field_scores': {},
            'errors': [],
            'warnings': [],
            'recommendations': [],
            'completeness': 0,
            'quality_level': 'incomplete',
            'required_fields_missing': [],
            'optional_fields_present': 0,
            'data_consistency': True
        }
        
        # Validate each field
        total_possible_score = 0
        total_actual_score = 0
        fields_present = 0
        
        for field_num, rules in self.quest_field_rules.items():
            field_name = rules['name']
            field_value = quest_data.get(field_name)
            
            field_result = self._validate_quest_field(field_num, field_name, field_value, rules)
            result['field_scores'][field_name] = field_result
            
            # Calculate scores
            if rules['required']:
                total_possible_score += 10
                if field_result['valid']:
                    total_actual_score += 10
                    fields_present += 1
                else:
                    result['required_fields_missing'].append(field_name)
                    result['errors'].extend(field_result['errors'])
            else:
                total_possible_score += 5
                if field_result['valid'] and field_value is not None:
                    total_actual_score += 5
                    result['optional_fields_present'] += 1
                    fields_present += 1
            
            # Collect warnings and recommendations
            result['warnings'].extend(field_result.get('warnings', []))
            result['recommendations'].extend(field_result.get('recommendations', []))
        
        # Calculate final scores
        if total_possible_score > 0:
            result['overall_score'] = (total_actual_score / total_possible_score) * 100
        
        result['completeness'] = (fields_present / len(self.quest_field_rules)) * 100
        
        # Determine quality level
        score = result['overall_score']
        if score >= self.quality_thresholds['excellent']:
            result['quality_level'] = 'excellent'
        elif score >= self.quality_thresholds['good']:
            result['quality_level'] = 'good'
        elif score >= self.quality_thresholds['acceptable']:
            result['quality_level'] = 'acceptable'
        elif score >= self.quality_thresholds['poor']:
            result['quality_level'] = 'poor'
        else:
            result['quality_level'] = 'incomplete'
        
        # Additional validation checks
        result = self._validate_quest_consistency(quest_data, result)
        
        self.validation_results[quest_id] = result
        return result
    
    def validate_npc(self, npc_data: Dict) -> Dict:
        """
        Validate a complete NPC entry
        
        Returns:
            Validation result with score, errors, warnings, and recommendations
        """
        npc_id = npc_data.get('id')
        result = {
            'npc_id': npc_id,
            'overall_score': 0,
            'field_scores': {},
            'errors': [],
            'warnings': [],
            'recommendations': [],
            'completeness': 0,
            'quality_level': 'incomplete',
            'required_fields_missing': [],
            'data_consistency': True
        }
        
        # Validate each field
        total_possible_score = 0
        total_actual_score = 0
        fields_present = 0
        
        for field_num, rules in self.npc_field_rules.items():
            field_name = rules['name']
            field_value = npc_data.get(field_name)
            
            field_result = self._validate_npc_field(field_num, field_name, field_value, rules)
            result['field_scores'][field_name] = field_result
            
            # Calculate scores
            if rules['required']:
                total_possible_score += 10
                if field_result['valid']:
                    total_actual_score += 10
                    fields_present += 1
                else:
                    result['required_fields_missing'].append(field_name)
                    result['errors'].extend(field_result['errors'])
            else:
                total_possible_score += 5
                if field_result['valid'] and field_value is not None:
                    total_actual_score += 5
                    fields_present += 1
            
            # Collect warnings and recommendations
            result['warnings'].extend(field_result.get('warnings', []))
            result['recommendations'].extend(field_result.get('recommendations', []))
        
        # Calculate final scores
        if total_possible_score > 0:
            result['overall_score'] = (total_actual_score / total_possible_score) * 100
        
        result['completeness'] = (fields_present / len(self.npc_field_rules)) * 100
        
        # Determine quality level
        score = result['overall_score']
        if score >= self.quality_thresholds['excellent']:
            result['quality_level'] = 'excellent'
        elif score >= self.quality_thresholds['good']:
            result['quality_level'] = 'good'
        elif score >= self.quality_thresholds['acceptable']:
            result['quality_level'] = 'acceptable'
        elif score >= self.quality_thresholds['poor']:
            result['quality_level'] = 'poor'
        else:
            result['quality_level'] = 'incomplete'
        
        return result
    
    def _validate_quest_field(self, field_num: int, field_name: str, value: any, rules: Dict) -> Dict:
        """Validate a single quest field"""
        result = {
            'field_num': field_num,
            'valid': False,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check if required field is missing
        if rules.get('required', False) and (value is None or value == ""):
            result['errors'].append(f"Required field '{field_name}' is missing")
            return result
        
        # Skip validation if optional field is None
        if not rules.get('required', False) and value is None:
            result['valid'] = True
            return result
        
        # Type validation
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            result['errors'].append(f"Field '{field_name}' should be {expected_type.__name__}, got {type(value).__name__}")
            return result
        
        # String validations
        if isinstance(value, str):
            min_length = rules.get('min_length', 0)
            max_length = rules.get('max_length', 1000)
            
            if len(value) < min_length:
                result['errors'].append(f"Field '{field_name}' too short (min {min_length} chars)")
                return result
            
            if len(value) > max_length:
                result['warnings'].append(f"Field '{field_name}' very long (>{max_length} chars)")
        
        # Numeric validations
        if isinstance(value, int):
            min_value = rules.get('min_value')
            max_value = rules.get('max_value')
            
            if min_value is not None and value < min_value:
                result['errors'].append(f"Field '{field_name}' too small (min {min_value})")
                return result
            
            if max_value is not None and value > max_value:
                result['warnings'].append(f"Field '{field_name}' very large (max {max_value})")
        
        # List validations
        if isinstance(value, list):
            min_items = rules.get('min_items', 0)
            max_items = rules.get('max_items', 100)
            
            if len(value) < min_items:
                result['errors'].append(f"Field '{field_name}' needs at least {min_items} items")
                return result
            
            if len(value) > max_items:
                result['warnings'].append(f"Field '{field_name}' has many items (>{max_items})")
        
        # Custom validation function
        validate_func = rules.get('validate_func')
        if validate_func:
            custom_result = validate_func(value, field_name)
            if not custom_result.get('valid', True):
                result['errors'].extend(custom_result.get('errors', []))
                result['warnings'].extend(custom_result.get('warnings', []))
                if custom_result.get('errors'):
                    return result
        
        result['valid'] = True
        return result
    
    def _validate_npc_field(self, field_num: int, field_name: str, value: any, rules: Dict) -> Dict:
        """Validate a single NPC field"""
        # Similar to quest field validation but for NPCs
        return self._validate_quest_field(field_num, field_name, value, rules)
    
    def _validate_started_by(self, value: Dict, field_name: str) -> Dict:
        """Validate startedBy field structure"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not isinstance(value, dict):
            result['errors'].append("startedBy must be a dictionary")
            result['valid'] = False
            return result
        
        # Should have npcs, objects, items keys
        required_keys = ['npcs', 'objects', 'items']
        for key in required_keys:
            if key not in value:
                result['warnings'].append(f"startedBy missing '{key}' key")
        
        # At least one should have content
        has_content = any(value.get(key) for key in required_keys)
        if not has_content:
            result['errors'].append("startedBy must have at least one starter (NPC, object, or item)")
            result['valid'] = False
        
        return result
    
    def _validate_finished_by(self, value: Dict, field_name: str) -> Dict:
        """Validate finishedBy field structure"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not isinstance(value, dict):
            result['errors'].append("finishedBy must be a dictionary")
            result['valid'] = False
            return result
        
        # Should have npcs, objects keys
        required_keys = ['npcs', 'objects']
        for key in required_keys:
            if key not in value:
                result['warnings'].append(f"finishedBy missing '{key}' key")
        
        # At least NPCs should have content
        if not value.get('npcs'):
            result['warnings'].append("Most quests turn in to NPCs")
        
        return result
    
    def _validate_objectives(self, value: Dict, field_name: str) -> Dict:
        """Validate objectives field structure"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not isinstance(value, dict):
            result['errors'].append("objectives must be a dictionary")
            result['valid'] = False
            return result
        
        # Should have standard objective types
        objective_types = ['creatures', 'objects', 'items', 'reputation', 'killCredit', 'spells']
        has_objectives = any(value.get(obj_type) for obj_type in objective_types)
        
        if not has_objectives:
            result['warnings'].append("Quest appears to have no objectives")
        
        return result
    
    def _validate_spawns(self, value: Dict, field_name: str) -> Dict:
        """Validate NPC spawns field structure"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if not isinstance(value, dict):
            result['errors'].append("spawns must be a dictionary")
            result['valid'] = False
            return result
        
        # Should have zone IDs as keys and coordinate arrays as values
        for zone_id, coords in value.items():
            if not isinstance(coords, list):
                result['errors'].append(f"Zone {zone_id} spawns must be a list")
                result['valid'] = False
                continue
            
            for coord in coords:
                if not isinstance(coord, dict) or 'x' not in coord or 'y' not in coord:
                    result['errors'].append(f"Invalid coordinate format in zone {zone_id}")
                    result['valid'] = False
        
        return result
    
    def _validate_quest_consistency(self, quest_data: Dict, result: Dict) -> Dict:
        """Validate logical consistency between quest fields"""
        
        # Check level consistency
        quest_level = quest_data.get('questLevel', 0)
        required_level = quest_data.get('requiredLevel', 0)
        
        if required_level and quest_level and required_level > quest_level:
            result['warnings'].append("Required level higher than quest level")
        
        # Check chain consistency
        next_quest = quest_data.get('nextQuestInChain')
        child_quests = quest_data.get('childQuests', [])
        
        if next_quest and child_quests and next_quest not in child_quests:
            result['recommendations'].append("Next quest should be in child quests list")
        
        # Check prerequisite logic
        prereq_group = quest_data.get('preQuestGroup', [])
        prereq_single = quest_data.get('preQuestSingle', [])
        
        if prereq_group and prereq_single:
            result['warnings'].append("Quest has both group and single prerequisites - verify logic")
        
        # Check faction/race consistency
        required_races = quest_data.get('requiredRaces')
        if required_races:
            # Alliance races: 1+4+8+64+1024 = 1101
            # Horde races: 2+16+32+128+512 = 690
            alliance_mask = 1 + 4 + 8 + 64 + 1024
            horde_mask = 2 + 16 + 32 + 128 + 512
            
            if required_races & alliance_mask and required_races & horde_mask:
                result['warnings'].append("Quest allows both Alliance and Horde races")
            elif required_races & alliance_mask:
                result['recommendations'].append("Consider setting faction restriction to Alliance")
            elif required_races & horde_mask:
                result['recommendations'].append("Consider setting faction restriction to Horde")
        
        return result
    
    # Additional validation helper methods
    def _validate_race_mask(self, value: int, field_name: str) -> Dict:
        """Validate race restriction bitmask"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Valid race bits: 1,2,4,8,16,32,64,128,256,512,1024
        valid_race_mask = 2047  # Sum of all valid race bits
        
        if value & ~valid_race_mask:
            result['warnings'].append("Race mask contains unknown race bits")
        
        return result
    
    def _validate_class_mask(self, value: int, field_name: str) -> Dict:
        """Validate class restriction bitmask"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        # Valid class bits: 1,2,4,8,16,32,64,128,256,1024
        valid_class_mask = 1535  # Sum of all valid class bits
        
        if value & ~valid_class_mask:
            result['warnings'].append("Class mask contains unknown class bits")
        
        return result
    
    def _validate_zone_or_sort(self, value: int, field_name: str) -> Dict:
        """Validate zoneOrSort field"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if value > 0:
            # Positive = zone ID
            if value > 5000:  # Reasonable max zone ID
                result['warnings'].append("Very high zone ID - verify correctness")
        elif value < 0:
            # Negative = quest sort category
            if value < -1000:  # Reasonable quest sort range
                result['warnings'].append("Very negative quest sort - verify correctness")
        else:
            result['errors'].append("zoneOrSort cannot be 0")
            result['valid'] = False
        
        return result
    
    def _validate_quest_list(self, value: List, field_name: str) -> Dict:
        """Validate list of quest IDs"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        for quest_id in value:
            if not isinstance(quest_id, int) or quest_id <= 0:
                result['errors'].append(f"Invalid quest ID in {field_name}: {quest_id}")
                result['valid'] = False
        
        return result
    
    def _validate_item_list(self, value: List, field_name: str) -> Dict:
        """Validate list of item IDs"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        for item_id in value:
            if not isinstance(item_id, int) or item_id <= 0:
                result['errors'].append(f"Invalid item ID in {field_name}: {item_id}")
                result['valid'] = False
        
        return result
    
    def _validate_skill_req(self, value: Dict, field_name: str) -> Dict:
        """Validate skill requirement"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if 'skill_id' not in value or 'level' not in value:
            result['errors'].append("Skill requirement needs skill_id and level")
            result['valid'] = False
        
        return result
    
    def _validate_rep_req(self, value: Dict, field_name: str) -> Dict:
        """Validate reputation requirement"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if 'faction_id' not in value or 'value' not in value:
            result['errors'].append("Reputation requirement needs faction_id and value")
            result['valid'] = False
        
        return result
    
    def _validate_rep_rewards(self, value: List, field_name: str) -> Dict:
        """Validate reputation rewards"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        for reward in value:
            if not isinstance(reward, dict) or 'faction_id' not in reward or 'value' not in reward:
                result['errors'].append("Invalid reputation reward format")
                result['valid'] = False
        
        return result
    
    def _validate_extra_objectives(self, value: List, field_name: str) -> Dict:
        """Validate extra objectives"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        for obj in value:
            if not isinstance(obj, dict) or 'spellId' not in obj:
                result['errors'].append("Invalid extra objective format")
                result['valid'] = False
        
        return result
    
    def _validate_trigger_end(self, value: Dict, field_name: str) -> Dict:
        """Validate exploration trigger"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        if 'text' not in value:
            result['warnings'].append("Exploration trigger missing text")
        
        return result
    
    def _validate_waypoints(self, value: Dict, field_name: str) -> Dict:
        """Validate waypoints (similar to spawns)"""
        return self._validate_spawns(value, field_name)
    
    def _validate_faction_friendly(self, value: str, field_name: str) -> Dict:
        """Validate faction friendly field"""
        result = {'valid': True, 'errors': [], 'warnings': []}
        
        valid_values = ['A', 'H', 'AH']
        if value not in valid_values:
            result['errors'].append(f"friendlyToFaction must be one of: {valid_values}")
            result['valid'] = False
        
        return result
    
    def get_summary(self) -> Dict:
        """Get validation summary across all validated entries"""
        if not self.validation_results:
            return {'message': 'No validations performed yet'}
        
        total_entries = len(self.validation_results)
        quality_counts = {}
        avg_score = 0
        avg_completeness = 0
        
        for result in self.validation_results.values():
            quality = result['quality_level']
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
            avg_score += result['overall_score']
            avg_completeness += result['completeness']
        
        return {
            'total_entries_validated': total_entries,
            'average_score': avg_score / total_entries,
            'average_completeness': avg_completeness / total_entries,
            'quality_distribution': quality_counts,
            'validation_errors': len(self.validation_errors)
        }

def main():
    """Test the validation engine"""
    import sys
    
    # Test with sample quest data
    sample_quest = {
        'id': 12345,
        'name': 'Test Quest',
        'startedBy': {'npcs': [1234], 'objects': [], 'items': []},
        'finishedBy': {'npcs': [1234], 'objects': []},
        'requiredLevel': 10,
        'questLevel': 15,
        'objectivesText': ['Kill 10 wolves'],
        'objectives': {'creatures': [{'id': 456, 'count': 10}], 'objects': [], 'items': []},
        'zoneOrSort': 12,
        'questFlags': 0,
        'specialFlags': 0
    }
    
    validator = ValidationEngine()
    result = validator.validate_quest(sample_quest)
    
    print(f"\nValidation Results:")
    print(f"Overall Score: {result['overall_score']:.1f}%")
    print(f"Quality Level: {result['quality_level']}")
    print(f"Completeness: {result['completeness']:.1f}%")
    
    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    if result['warnings']:
        print(f"\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    if result['recommendations']:
        print(f"\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  - {rec}")
    
    print(f"\nSummary: {json.dumps(validator.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()