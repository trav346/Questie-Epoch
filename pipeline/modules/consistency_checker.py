#!/usr/bin/env python3
"""
Consistency Checker - Check internal data consistency
Validates logical relationships and constraints within data
"""

import logging
from typing import Dict, List, Tuple, Set, Optional


class ConsistencyChecker:
    """
    Checks internal consistency of quest and NPC data
    Ensures logical relationships are maintained
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.errors = []
        self.warnings = []
        
        # Known faction conflicts
        self.faction_conflicts = {
            'Alliance': ['Horde'],
            'Horde': ['Alliance'],
        }
        
        # Race to faction mapping
        self.race_factions = {
            # Alliance races
            'Human': 'Alliance',
            'Dwarf': 'Alliance',
            'Night Elf': 'Alliance',
            'Gnome': 'Alliance',
            'Draenei': 'Alliance',
            # Horde races
            'Orc': 'Horde',
            'Undead': 'Horde',
            'Tauren': 'Horde',
            'Troll': 'Horde',
            'Blood Elf': 'Horde',
        }
        
        # Zone faction tendencies (for validation)
        self.zone_factions = {
            # Alliance zones
            12: 'Alliance',  # Elwynn Forest
            1519: 'Alliance',  # Stormwind
            1537: 'Alliance',  # Ironforge
            1657: 'Alliance',  # Darnassus
            # Horde zones
            14: 'Horde',  # Durotar
            1637: 'Horde',  # Orgrimmar
            1638: 'Horde',  # Thunder Bluff
            1497: 'Horde',  # Undercity
        }
    
    def check_quest_consistency(self, quest_data: Dict, all_quests: Dict = None, all_npcs: Dict = None) -> Tuple[bool, List[str], List[str]]:
        """
        Check quest data for internal consistency
        
        Args:
            quest_data: Single quest to check
            all_quests: All quests in database (for cross-reference)
            all_npcs: All NPCs in database (for validation)
            
        Returns:
            (is_consistent, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        quest_id = quest_data.get('quest_id')
        if not quest_id:
            self.errors.append("Missing quest_id")
            return False, self.errors, self.warnings
        
        # Check internal field consistency
        self._check_quest_level_consistency(quest_data)
        self._check_quest_faction_consistency(quest_data)
        self._check_quest_chain_consistency(quest_data, all_quests)
        self._check_quest_npc_consistency(quest_data, all_npcs)
        self._check_quest_objective_consistency(quest_data)
        self._check_quest_reward_consistency(quest_data)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def check_npc_consistency(self, npc_data: Dict, all_quests: Dict = None) -> Tuple[bool, List[str], List[str]]:
        """
        Check NPC data for internal consistency
        
        Returns:
            (is_consistent, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        npc_id = npc_data.get('npc_id')
        if not npc_id:
            self.errors.append("Missing npc_id")
            return False, self.errors, self.warnings
        
        # Check internal consistency
        self._check_npc_level_consistency(npc_data)
        self._check_npc_faction_consistency(npc_data)
        self._check_npc_spawn_consistency(npc_data)
        self._check_npc_quest_consistency(npc_data, all_quests)
        self._check_npc_flag_consistency(npc_data)
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _check_quest_level_consistency(self, quest_data: Dict):
        """Check quest level relationships"""
        quest_level = quest_data.get('questLevel')
        req_level = quest_data.get('requiredLevel')
        max_level = quest_data.get('requiredMaxLevel')
        
        # Required level shouldn't be much higher than quest level
        if quest_level and req_level:
            if req_level > quest_level + 10:
                self.warnings.append(
                    f"Required level {req_level} is unusually high for quest level {quest_level}"
                )
            if req_level < quest_level - 10:
                self.warnings.append(
                    f"Required level {req_level} is unusually low for quest level {quest_level}"
                )
        
        # Max level should be higher than min level
        if req_level and max_level:
            if max_level <= req_level:
                self.errors.append(
                    f"Max level {max_level} must be higher than required level {req_level}"
                )
            if max_level < req_level + 3:
                self.warnings.append(
                    f"Max level {max_level} gives very narrow level range (req: {req_level})"
                )
    
    def _check_quest_faction_consistency(self, quest_data: Dict):
        """Check faction-related consistency"""
        # Check race requirements vs faction
        req_races = quest_data.get('requiredRaces')
        faction = quest_data.get('faction')
        
        if req_races and faction:
            # Parse race bitmask if needed
            alliance_races = {'Human', 'Dwarf', 'Night Elf', 'Gnome', 'Draenei'}
            horde_races = {'Orc', 'Undead', 'Tauren', 'Troll', 'Blood Elf'}
            
            # Check for faction mismatch
            if faction == 'Alliance' and any(r in str(req_races) for r in horde_races):
                self.errors.append("Alliance quest has Horde race requirements")
            elif faction == 'Horde' and any(r in str(req_races) for r in alliance_races):
                self.errors.append("Horde quest has Alliance race requirements")
        
        # Check zone vs faction
        zone_id = quest_data.get('zoneOrSort')
        if zone_id and zone_id > 0 and zone_id in self.zone_factions:
            zone_faction = self.zone_factions[zone_id]
            if faction and faction != zone_faction and faction != 'Neutral':
                self.warnings.append(
                    f"{faction} quest in {zone_faction} zone ({zone_id})"
                )
    
    def _check_quest_chain_consistency(self, quest_data: Dict, all_quests: Optional[Dict]):
        """Check quest chain relationships"""
        quest_id = quest_data.get('quest_id')
        
        # Parent-child relationships
        parent = quest_data.get('parentQuest')
        children = quest_data.get('childQuests', [])
        
        if parent and parent == quest_id:
            self.errors.append("Quest cannot be its own parent")
        
        if quest_id in children:
            self.errors.append("Quest cannot be its own child")
        
        if parent and parent in children:
            self.errors.append("Circular dependency: parent is also a child")
        
        # Prerequisite consistency
        pre_group = quest_data.get('preQuestGroup', [])
        pre_single = quest_data.get('preQuestSingle', [])
        next_quest = quest_data.get('nextQuestInChain')
        
        # Check for self-prerequisites
        if quest_id in pre_group:
            self.errors.append("Quest cannot be its own prerequisite (group)")
        if quest_id in pre_single:
            self.errors.append("Quest cannot be its own prerequisite (single)")
        
        # Check for duplicate prerequisites
        if pre_group and pre_single:
            duplicates = set(pre_group) & set(pre_single)
            if duplicates:
                self.warnings.append(
                    f"Quests in both prerequisite groups: {duplicates}"
                )
        
        # Next quest shouldn't be a prerequisite
        if next_quest:
            if next_quest in pre_group or next_quest in pre_single:
                self.errors.append("Next quest in chain cannot be a prerequisite")
            if next_quest == quest_id:
                self.errors.append("Quest cannot be its own follow-up")
        
        # Exclusive quest checks
        exclusive = quest_data.get('exclusiveTo', [])
        if quest_id in exclusive:
            self.errors.append("Quest cannot be exclusive with itself")
        
        # Check if exclusive quests are also prerequisites
        if exclusive:
            for ex_quest in exclusive:
                if ex_quest in pre_group or ex_quest in pre_single:
                    self.errors.append(
                        f"Quest {ex_quest} is both exclusive and prerequisite"
                    )
        
        # Validate against all quests if available
        if all_quests:
            # Check that referenced quests exist
            all_refs = (
                [parent] if parent else [] +
                children +
                pre_group +
                pre_single +
                [next_quest] if next_quest else [] +
                exclusive
            )
            
            missing_refs = [q for q in all_refs if q and q not in all_quests]
            if missing_refs:
                self.warnings.append(f"References non-existent quests: {missing_refs}")
            
            # Check reverse relationships
            if parent and parent in all_quests:
                parent_data = all_quests[parent]
                parent_children = parent_data.get('childQuests', [])
                if quest_id not in parent_children:
                    self.warnings.append(
                        f"Parent quest {parent} doesn't list this as child"
                    )
    
    def _check_quest_npc_consistency(self, quest_data: Dict, all_npcs: Optional[Dict]):
        """Check quest-NPC relationships"""
        # Extract NPC references
        started_by = quest_data.get('startedBy', (None, None, None))
        finished_by = quest_data.get('finishedBy', (None, None))
        
        quest_id = quest_data.get('quest_id')
        
        # Check started_by NPCs
        if started_by and len(started_by) >= 1 and started_by[0]:
            start_npcs = started_by[0]
            if all_npcs:
                for npc_id in start_npcs:
                    if npc_id in all_npcs:
                        npc_data = all_npcs[npc_id]
                        quest_starts = npc_data.get('questStarts', [])
                        if quest_id not in quest_starts:
                            self.warnings.append(
                                f"NPC {npc_id} doesn't list quest {quest_id} in questStarts"
                            )
                    else:
                        self.warnings.append(f"Quest starter NPC {npc_id} not in database")
        
        # Check finished_by NPCs
        if finished_by and len(finished_by) >= 1 and finished_by[0]:
            finish_npcs = finished_by[0]
            if all_npcs:
                for npc_id in finish_npcs:
                    if npc_id in all_npcs:
                        npc_data = all_npcs[npc_id]
                        quest_ends = npc_data.get('questEnds', [])
                        if quest_id not in quest_ends:
                            self.warnings.append(
                                f"NPC {npc_id} doesn't list quest {quest_id} in questEnds"
                            )
                    else:
                        self.warnings.append(f"Quest finisher NPC {npc_id} not in database")
    
    def _check_quest_objective_consistency(self, quest_data: Dict):
        """Check objective consistency"""
        objectives = quest_data.get('objectives', {})
        objectives_text = quest_data.get('objectivesText', [])
        
        if objectives:
            # Check creature objectives
            creatures = objectives.get('creatures', [])
            for creature in creatures:
                if isinstance(creature, dict):
                    count = creature.get('count', 0)
                    if count <= 0:
                        self.errors.append(f"Invalid creature count: {count}")
                    if count > 100:
                        self.warnings.append(f"Unusually high creature count: {count}")
            
            # Check item objectives
            items = objectives.get('items', [])
            for item in items:
                if isinstance(item, dict):
                    count = item.get('count', 0)
                    if count <= 0:
                        self.errors.append(f"Invalid item count: {count}")
                    if count > 200:
                        self.warnings.append(f"Unusually high item count: {count}")
            
            # Check if objectives match description
            if objectives_text and isinstance(objectives_text, list):
                text_combined = ' '.join(objectives_text).lower()
                
                # If we have kill objectives but no mention in text
                if creatures and not any(word in text_combined for word in ['kill', 'slay', 'defeat', 'destroy']):
                    self.warnings.append("Kill objectives not mentioned in description")
                
                # If we have collect objectives but no mention in text
                if items and not any(word in text_combined for word in ['collect', 'gather', 'find', 'obtain', 'bring']):
                    self.warnings.append("Collection objectives not mentioned in description")
    
    def _check_quest_reward_consistency(self, quest_data: Dict):
        """Check reward consistency"""
        quest_level = quest_data.get('questLevel', 1)
        reputation_rewards = quest_data.get('reputationReward', [])
        
        # Check reputation values
        for rep_reward in reputation_rewards:
            if isinstance(rep_reward, (list, tuple)) and len(rep_reward) >= 2:
                faction_id, rep_value = rep_reward[0], rep_reward[1]
                
                # Check for reasonable reputation values
                if rep_value < 0:
                    self.warnings.append(f"Negative reputation reward: {rep_value}")
                elif rep_value > 10000:
                    self.warnings.append(f"Unusually high reputation reward: {rep_value}")
                
                # Low level quests shouldn't give huge rep
                if quest_level < 20 and rep_value > 500:
                    self.warnings.append(
                        f"High reputation ({rep_value}) for low level quest ({quest_level})"
                    )
    
    def _check_npc_level_consistency(self, npc_data: Dict):
        """Check NPC level relationships"""
        min_level = npc_data.get('minLevel')
        max_level = npc_data.get('maxLevel')
        min_health = npc_data.get('minLevelHealth')
        max_health = npc_data.get('maxLevelHealth')
        
        # Level checks
        if min_level and max_level:
            if min_level > max_level:
                self.errors.append(f"Min level {min_level} > max level {max_level}")
            elif min_level == max_level and min_health and max_health and min_health != max_health:
                self.warnings.append(
                    "Same min/max level but different health values"
                )
        
        # Health checks
        if min_health and max_health:
            if min_health > max_health:
                self.errors.append(f"Min health {min_health} > max health {max_health}")
            
            # Check health vs level ratio
            if min_level and max_level:
                min_ratio = min_health / min_level if min_level > 0 else 0
                max_ratio = max_health / max_level if max_level > 0 else 0
                
                # Health should scale somewhat with level
                if min_ratio > max_ratio * 2:
                    self.warnings.append("Health doesn't scale properly with level")
    
    def _check_npc_faction_consistency(self, npc_data: Dict):
        """Check NPC faction consistency"""
        friendly_to = npc_data.get('friendlyToFaction')
        zone_id = npc_data.get('zoneID')
        quest_starts = npc_data.get('questStarts', [])
        quest_ends = npc_data.get('questEnds', [])
        
        # Check zone faction alignment
        if zone_id and zone_id in self.zone_factions:
            zone_faction = self.zone_factions[zone_id]
            
            if friendly_to == 'A' and zone_faction == 'Horde':
                self.warnings.append(f"Alliance-only NPC in Horde zone {zone_id}")
            elif friendly_to == 'H' and zone_faction == 'Alliance':
                self.warnings.append(f"Horde-only NPC in Alliance zone {zone_id}")
        
        # Quest NPCs should have faction data
        if (quest_starts or quest_ends) and not friendly_to:
            self.warnings.append("Quest NPC missing faction data (friendlyToFaction)")
    
    def _check_npc_spawn_consistency(self, npc_data: Dict):
        """Check NPC spawn data consistency"""
        spawns = npc_data.get('spawns', {})
        zone_id = npc_data.get('zoneID')
        waypoints = npc_data.get('waypoints', {})
        
        # Check spawn coordinates
        for zone, coords in spawns.items():
            if not coords:
                self.warnings.append(f"Empty spawn list for zone {zone}")
                continue
            
            for coord in coords:
                if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                    x, y = coord[0], coord[1]
                    
                    # Check coordinate ranges
                    if not (0 <= x <= 100):
                        self.errors.append(f"Invalid X coordinate: {x}")
                    if not (0 <= y <= 100):
                        self.errors.append(f"Invalid Y coordinate: {y}")
                    
                    # Check for duplicate coordinates
                    if coords.count(coord) > 1:
                        self.warnings.append(f"Duplicate spawn point: {coord}")
        
        # Check zone consistency
        if spawns and zone_id:
            spawn_zones = set(spawns.keys())
            if zone_id not in spawn_zones:
                self.warnings.append(
                    f"Primary zone {zone_id} not in spawn zones {spawn_zones}"
                )
        
        # Check waypoints
        if waypoints:
            for zone, path in waypoints.items():
                if zone not in spawns:
                    self.warnings.append(
                        f"Waypoints for zone {zone} but no spawns there"
                    )
                
                # Check waypoint coordinates
                for coord in path:
                    if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                        x, y = coord[0], coord[1]
                        if not (0 <= x <= 100) or not (0 <= y <= 100):
                            self.errors.append(f"Invalid waypoint coordinate: {coord}")
    
    def _check_npc_quest_consistency(self, npc_data: Dict, all_quests: Optional[Dict]):
        """Check NPC-quest relationships"""
        quest_starts = npc_data.get('questStarts', [])
        quest_ends = npc_data.get('questEnds', [])
        npc_flags = npc_data.get('npcFlags', 0)
        
        # Quest giver should have questgiver flag
        if (quest_starts or quest_ends) and not (npc_flags & 2):
            self.warnings.append(
                f"NPC has quests but missing QUESTGIVER flag (2)"
            )
        
        # Check for duplicate quests
        duplicates = set(quest_starts) & set(quest_ends)
        if duplicates:
            self.warnings.append(
                f"NPC both starts and ends same quests: {duplicates}"
            )
        
        # Validate quest references
        if all_quests:
            all_quest_refs = quest_starts + quest_ends
            missing_quests = [q for q in all_quest_refs if q not in all_quests]
            if missing_quests:
                self.warnings.append(f"References non-existent quests: {missing_quests}")
    
    def _check_npc_flag_consistency(self, npc_data: Dict):
        """Check NPC flag consistency"""
        npc_flags = npc_data.get('npcFlags', 0)
        sub_name = npc_data.get('subName', '')
        
        # Check flag combinations
        if npc_flags:
            # Vendor should not be questgiver typically
            if (npc_flags & 128) and (npc_flags & 2):
                self.warnings.append("NPC is both vendor and questgiver (unusual)")
            
            # Check subname matches flags
            if sub_name:
                sub_lower = sub_name.lower()
                if 'vendor' in sub_lower and not (npc_flags & 128):
                    self.warnings.append("Has 'Vendor' in title but missing vendor flag")
                if 'trainer' in sub_lower and not (npc_flags & 16):
                    self.warnings.append("Has 'Trainer' in title but missing trainer flag")
                if 'innkeeper' in sub_lower and not (npc_flags & 8192):
                    self.warnings.append("Has 'Innkeeper' in title but missing innkeeper flag")


def main():
    """Test the consistency checker"""
    checker = ConsistencyChecker()
    
    # Test quest consistency
    test_quest = {
        'quest_id': 12345,
        'name': 'Test Quest',
        'questLevel': 10,
        'requiredLevel': 8,
        'requiredMaxLevel': 15,
        'faction': 'Alliance',
        'zoneOrSort': 12,  # Elwynn Forest
        'startedBy': ([100], None, None),
        'finishedBy': ([101], None),
        'objectives': {
            'creatures': [{'npc_id': 200, 'count': 10}]
        },
        'objectivesText': ['Kill 10 wolves in the forest'],
        'parentQuest': None,
        'childQuests': [12346],
        'preQuestSingle': [],
        'nextQuestInChain': 12346,
    }
    
    is_consistent, errors, warnings = checker.check_quest_consistency(test_quest)
    print(f"Quest Consistent: {is_consistent}")
    if errors:
        print(f"Errors: {errors}")
    if warnings:
        print(f"Warnings: {warnings}")


if __name__ == "__main__":
    main()