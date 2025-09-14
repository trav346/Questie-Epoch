#!/usr/bin/env python3
"""
Cross Reference Validator - Validate against multiple sources
Cross-checks data against external sources and databases
"""

import logging
from typing import Dict, List, Tuple, Optional
import re


class CrossReferenceValidator:
    """
    Validates quest and NPC data against multiple external sources
    Ensures consistency across different data sources
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Known valid zone IDs from WoW 3.3.5
        self.valid_zones = {
            # Eastern Kingdoms
            1: 'Dun Morogh',
            3: 'Badlands',
            4: 'Blasted Lands',
            8: 'Swamp of Sorrows',
            10: 'Duskwood',
            11: 'Wetlands',
            12: 'Elwynn Forest',
            14: 'Durotar',
            15: 'Dustwallow Marsh',
            16: 'Azshara',
            17: 'The Barrens',
            28: 'Western Plaguelands',
            33: 'Stranglethorn Vale',
            36: 'Alterac Mountains',
            38: 'Loch Modan',
            40: 'Westfall',
            41: 'Deadwind Pass',
            44: 'Redridge Mountains',
            45: 'Arathi Highlands',
            46: 'Burning Steppes',
            47: 'The Hinterlands',
            51: 'Searing Gorge',
            85: 'Tirisfal Glades',
            130: 'Silverpine Forest',
            139: 'Eastern Plaguelands',
            267: 'Hillsbrad Foothills',
            1497: 'Undercity',
            1519: 'Stormwind City',
            1537: 'Ironforge',
            # Kalimdor
            141: 'Teldrassil',
            148: 'Darkshore',
            215: 'Mulgore',
            331: 'Ashenvale',
            357: 'Feralas',
            361: 'Felwood',
            400: 'Thousand Needles',
            405: 'Desolace',
            406: 'Stonetalon Mountains',
            440: 'Tanaris',
            490: 'Un\'Goro Crater',
            493: 'Moonglade',
            618: 'Winterspring',
            1377: 'Silithus',
            1637: 'Orgrimmar',
            1638: 'Thunder Bluff',
            1657: 'Darnassus',
            # Outland
            3483: 'Hellfire Peninsula',
            3518: 'Nagrand',
            3519: 'Terokkar Forest',
            3520: 'Shadowmoon Valley',
            3521: 'Zangarmarsh',
            3522: 'Blade\'s Edge Mountains',
            3523: 'Netherstorm',
            3703: 'Shattrath City',
            # Northrend
            65: 'Dragonblight',
            66: 'Zul\'Drak',
            67: 'The Storm Peaks',
            210: 'Icecrown',
            394: 'Grizzly Hills',
            495: 'Howling Fjord',
            3537: 'Borean Tundra',
            3711: 'Sholazar Basin',
            4197: 'Wintergrasp',
            4395: 'Dalaran',
        }
        
        # Valid NPC ranks
        self.valid_npc_ranks = {
            0: 'Normal',
            1: 'Elite',
            2: 'Rare Elite',
            3: 'Boss',
            4: 'Rare',
        }
        
        # Valid factions
        self.valid_factions = ['Alliance', 'Horde', 'Neutral', 'Hostile']
        
        # Known quest types
        self.quest_types = {
            1: 'Elite',
            21: 'Life',
            41: 'PvP',
            62: 'Raid',
            81: 'Dungeon',
            82: 'World Event',
            83: 'Legendary',
            84: 'Escort',
            85: 'Heroic',
            88: 'Raid (10)',
            89: 'Raid (25)',
        }
    
    def validate(self, data: Dict, data_type: str = 'quest') -> Tuple[bool, List[str], List[str]]:
        """
        Cross-reference validate data
        
        Returns:
            (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        if data_type == 'quest':
            self._validate_quest(data, errors, warnings)
        else:
            self._validate_npc(data, errors, warnings)
        
        return len(errors) == 0, errors, warnings
    
    def _validate_quest(self, quest: Dict, errors: List[str], warnings: List[str]):
        """Validate quest against known references"""
        quest_id = quest.get('quest_id')
        
        # Validate zone
        zone = quest.get('zoneOrSort')
        if zone and zone > 0:
            if zone not in self.valid_zones:
                warnings.append(f"Quest {quest_id}: Unknown zone ID {zone}")
        
        # Validate quest level ranges
        quest_level = quest.get('questLevel')
        if quest_level:
            if quest_level < 1 or quest_level > 85:
                errors.append(f"Quest {quest_id}: Invalid level {quest_level} (must be 1-85)")
        
        # Validate NPCs exist
        self._validate_npc_references(quest, errors, warnings)
        
        # Validate quest chains
        self._validate_quest_chains(quest, errors, warnings)
        
        # Validate race/class restrictions
        self._validate_restrictions(quest, errors, warnings)
        
        # Validate coordinates
        self._validate_coordinates(quest, errors, warnings)
    
    def _validate_npc(self, npc: Dict, errors: List[str], warnings: List[str]):
        """Validate NPC against known references"""
        npc_id = npc.get('npc_id')
        
        # Validate rank
        rank = npc.get('rank')
        if rank is not None and rank not in self.valid_npc_ranks:
            warnings.append(f"NPC {npc_id}: Unknown rank {rank}")
        
        # Validate zone
        zone_id = npc.get('zoneID')
        if zone_id and zone_id not in self.valid_zones:
            warnings.append(f"NPC {npc_id}: Unknown zone ID {zone_id}")
        
        # Validate spawns
        spawns = npc.get('spawns', {})
        for spawn_zone, coords in spawns.items():
            if spawn_zone not in self.valid_zones:
                warnings.append(f"NPC {npc_id}: Unknown spawn zone {spawn_zone}")
            
            for coord in coords:
                if not self._is_valid_coordinate(coord):
                    errors.append(f"NPC {npc_id}: Invalid coordinate {coord}")
        
        # Validate faction
        faction = npc.get('friendlyToFaction')
        if faction and faction not in ['A', 'H', 'AH']:
            errors.append(f"NPC {npc_id}: Invalid faction '{faction}'")
        
        # Validate levels
        min_level = npc.get('minLevel')
        max_level = npc.get('maxLevel')
        if min_level and max_level:
            if min_level > max_level:
                errors.append(f"NPC {npc_id}: minLevel > maxLevel")
            if min_level < 1 or max_level > 85:
                errors.append(f"NPC {npc_id}: Invalid level range")
    
    def _validate_npc_references(self, quest: Dict, errors: List[str], warnings: List[str]):
        """Validate NPC references in quest"""
        quest_id = quest.get('quest_id')
        
        # Check startedBy NPCs
        started_by = quest.get('startedBy', (None, None, None))
        if started_by and started_by[0]:
            for npc_id in started_by[0]:
                if npc_id < 1:
                    errors.append(f"Quest {quest_id}: Invalid starter NPC ID {npc_id}")
        
        # Check finishedBy NPCs
        finished_by = quest.get('finishedBy', (None, None))
        if finished_by and finished_by[0]:
            for npc_id in finished_by[0]:
                if npc_id < 1:
                    errors.append(f"Quest {quest_id}: Invalid finisher NPC ID {npc_id}")
        
        # Check objective NPCs
        objectives = quest.get('objectives', {})
        if objectives and 'creatures' in objectives:
            for creature in objectives['creatures']:
                if isinstance(creature, dict):
                    npc_id = creature.get('npc_id')
                    if npc_id and npc_id < 1:
                        errors.append(f"Quest {quest_id}: Invalid objective NPC ID {npc_id}")
    
    def _validate_quest_chains(self, quest: Dict, errors: List[str], warnings: List[str]):
        """Validate quest chain references"""
        quest_id = quest.get('quest_id')
        
        # Check for self-references
        parent = quest.get('parentQuest')
        if parent and parent == quest_id:
            errors.append(f"Quest {quest_id}: Self-reference as parent")
        
        next_quest = quest.get('nextQuestInChain')
        if next_quest and next_quest == quest_id:
            errors.append(f"Quest {quest_id}: Self-reference as next quest")
        
        # Check prerequisite logic
        pre_group = quest.get('preQuestGroup', [])
        pre_single = quest.get('preQuestSingle', [])
        
        if quest_id in pre_group:
            errors.append(f"Quest {quest_id}: Self in prerequisite group")
        if quest_id in pre_single:
            errors.append(f"Quest {quest_id}: Self in prerequisite single")
        
        # Check for circular dependencies
        children = quest.get('childQuests', [])
        if parent and parent in children:
            errors.append(f"Quest {quest_id}: Circular dependency with parent")
    
    def _validate_restrictions(self, quest: Dict, errors: List[str], warnings: List[str]):
        """Validate race and class restrictions"""
        quest_id = quest.get('quest_id')
        
        # Race restrictions (bitmask)
        races = quest.get('requiredRaces')
        if races and races < 0:
            errors.append(f"Quest {quest_id}: Invalid race bitmask {races}")
        
        # Class restrictions (bitmask)
        classes = quest.get('requiredClasses')
        if classes and classes < 0:
            errors.append(f"Quest {quest_id}: Invalid class bitmask {classes}")
        
        # Level restrictions
        min_level = quest.get('requiredLevel')
        max_level = quest.get('requiredMaxLevel')
        
        if min_level and max_level:
            if min_level >= max_level:
                errors.append(f"Quest {quest_id}: requiredLevel >= requiredMaxLevel")
        
        if min_level and (min_level < 1 or min_level > 85):
            errors.append(f"Quest {quest_id}: Invalid required level {min_level}")
        
        if max_level and (max_level < 1 or max_level > 85):
            errors.append(f"Quest {quest_id}: Invalid max level {max_level}")
    
    def _validate_coordinates(self, data: Dict, errors: List[str], warnings: List[str]):
        """Validate coordinate data"""
        entity_id = data.get('quest_id') or data.get('npc_id')
        entity_type = 'Quest' if 'quest_id' in data else 'NPC'
        
        # Check various coordinate fields
        coord_fields = ['spawns', 'waypoints', 'quest_giver_location', 'turn_in_location']
        
        for field in coord_fields:
            if field not in data:
                continue
            
            coords = data[field]
            if isinstance(coords, dict):
                # Zone-based coordinates
                for zone, coord_list in coords.items():
                    for coord in coord_list:
                        if not self._is_valid_coordinate(coord):
                            errors.append(
                                f"{entity_type} {entity_id}: "
                                f"Invalid coordinate in {field}: {coord}"
                            )
            elif isinstance(coords, (list, tuple)):
                # Direct coordinate
                if not self._is_valid_coordinate(coords):
                    errors.append(
                        f"{entity_type} {entity_id}: "
                        f"Invalid coordinate in {field}: {coords}"
                    )
    
    def _is_valid_coordinate(self, coord) -> bool:
        """Check if coordinate is valid"""
        if not isinstance(coord, (list, tuple)):
            return False
        if len(coord) < 2:
            return False
        
        x, y = coord[0], coord[1]
        
        # WoW uses 0-100 coordinate system
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return False
        
        if x < 0 or x > 100 or y < 0 or y > 100:
            return False
        
        return True
    
    def cross_reference_batch(self, data_list: List[Dict]) -> Dict:
        """Cross-reference validate batch of data"""
        results = {
            'total': len(data_list),
            'valid': 0,
            'invalid': 0,
            'errors': [],
            'warnings': [],
        }
        
        for data in data_list:
            data_type = 'quest' if 'quest_id' in data else 'npc'
            entity_id = data.get(f'{data_type}_id')
            
            is_valid, errors, warnings = self.validate(data, data_type)
            
            if is_valid:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                results['errors'].append({
                    'entity_id': entity_id,
                    'errors': errors,
                })
            
            if warnings:
                results['warnings'].append({
                    'entity_id': entity_id,
                    'warnings': warnings,
                })
        
        return results


def main():
    """Test the cross reference validator"""
    validator = CrossReferenceValidator()
    
    # Test quest validation
    test_quest = {
        'quest_id': 12345,
        'name': 'Test Quest',
        'questLevel': 10,
        'requiredLevel': 8,
        'requiredMaxLevel': 15,
        'zoneOrSort': 12,  # Valid zone (Elwynn Forest)
        'startedBy': ([100], None, None),
        'finishedBy': ([101], None),
        'spawns': {12: [[50.5, 60.2]]},  # Valid coordinates
    }
    
    is_valid, errors, warnings = validator.validate(test_quest, 'quest')
    print(f"Quest valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")
    if warnings:
        print(f"Warnings: {warnings}")
    
    # Test invalid data
    invalid_quest = {
        'quest_id': 99999,
        'questLevel': 100,  # Invalid level
        'zoneOrSort': 99999,  # Invalid zone
        'requiredLevel': 90,  # Invalid level
        'spawns': {99999: [[150, 200]]},  # Invalid coordinates
    }
    
    is_valid, errors, warnings = validator.validate(invalid_quest, 'quest')
    print(f"\nInvalid quest valid: {is_valid}")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")


if __name__ == "__main__":
    main()