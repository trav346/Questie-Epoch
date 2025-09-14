#!/usr/bin/env python3
"""
Lua Formatter Module - Generates properly formatted Lua database entries
Ensures exact 30-field structure for quests and 15-field structure for NPCs
"""

from typing import Dict, List, Optional, Any, Union

class LuaFormatter:
    """
    Formats quest and NPC data into proper Lua database entries
    Following the exact field structure required by Questie
    """
    
    def __init__(self):
        # Quest database has exactly 30 fields
        self.QUEST_FIELD_COUNT = 30
        
        # NPC database has exactly 15 fields  
        self.NPC_FIELD_COUNT = 15
        
    def format_quest_entry(self, quest_id: int, quest_data: Dict) -> str:
        """
        Format a quest into proper Lua database entry with exactly 30 fields
        
        Field order (1-based indexing in Lua):
        1. name (string)
        2. startedBy {{NPCs},{Objects},{Items}}
        3. finishedBy {{NPCs},{Objects}}
        4. requiredLevel (int or nil)
        5. questLevel (int)
        6. requiredRaces (bitmask or nil)
        7. requiredClasses (bitmask or nil)
        8. objectivesText (table of strings)
        9. triggerEnd (exploration trigger)
        10. objectives (complex structure)
        11. sourceItemId (int or nil)
        12. preQuestGroup {questIds}
        13. preQuestSingle {questIds}
        14. childQuests {questIds}
        15. inGroupWith {questIds}
        16. exclusiveTo {questIds}
        17. zoneOrSort (int)
        18. requiredSkill {skillId, value}
        19. requiredMinRep {factionId, value}
        20. requiredMaxRep {factionId, value}
        21. requiredSourceItems {itemIds}
        22. nextQuestInChain (int)
        23. questFlags (int)
        24. specialFlags (int)
        25. parentQuest (int)
        26. reputationReward {{factionId, value}}
        27. extraObjectives {{spellId, text}}
        28. requiredSpell (int)
        29. requiredSpecialization (int)
        30. requiredMaxLevel (int)
        """
        
        fields = []
        
        # Field 1: name
        name = quest_data.get('name', f'Quest {quest_id}')
        fields.append(self._format_string(name))
        
        # Field 2: startedBy {{NPCs},{Objects},{Items}}
        started_by = quest_data.get('startedBy', {})
        fields.append(self._format_started_by(started_by))
        
        # Field 3: finishedBy {{NPCs},{Objects}}
        finished_by = quest_data.get('finishedBy', {})
        fields.append(self._format_finished_by(finished_by))
        
        # Field 4: requiredLevel
        req_level = quest_data.get('requiredLevel')
        fields.append(self._format_number(req_level))
        
        # Field 5: questLevel
        quest_level = quest_data.get('questLevel') or quest_data.get('level')
        fields.append(self._format_number(quest_level, default=1))
        
        # Field 6: requiredRaces
        req_races = quest_data.get('requiredRaces')
        fields.append(self._format_number(req_races))
        
        # Field 7: requiredClasses
        req_classes = quest_data.get('requiredClasses')
        fields.append(self._format_number(req_classes))
        
        # Field 8: objectivesText
        obj_text = quest_data.get('objectivesText', [])
        fields.append(self._format_string_table(obj_text))
        
        # Field 9: triggerEnd (exploration trigger)
        trigger = quest_data.get('triggerEnd')
        fields.append(self._format_trigger_end(trigger))
        
        # Field 10: objectives
        objectives = quest_data.get('objectives', {})
        fields.append(self._format_objectives(objectives))
        
        # Field 11: sourceItemId
        source_item = quest_data.get('sourceItemId')
        fields.append(self._format_number(source_item))
        
        # Field 12: preQuestGroup
        pre_group = quest_data.get('preQuestGroup', [])
        fields.append(self._format_number_table(pre_group))
        
        # Field 13: preQuestSingle
        pre_single = quest_data.get('preQuestSingle', [])
        fields.append(self._format_number_table(pre_single))
        
        # Field 14: childQuests
        children = quest_data.get('childQuests', [])
        fields.append(self._format_number_table(children))
        
        # Field 15: inGroupWith
        group_with = quest_data.get('inGroupWith', [])
        fields.append(self._format_number_table(group_with))
        
        # Field 16: exclusiveTo
        exclusive = quest_data.get('exclusiveTo', [])
        fields.append(self._format_number_table(exclusive))
        
        # Field 17: zoneOrSort
        zone = quest_data.get('zoneOrSort') or quest_data.get('zone')
        fields.append(self._format_number(zone, default=1))
        
        # Field 18: requiredSkill
        req_skill = quest_data.get('requiredSkill')
        fields.append(self._format_skill_requirement(req_skill))
        
        # Field 19: requiredMinRep
        min_rep = quest_data.get('requiredMinRep')
        fields.append(self._format_reputation_requirement(min_rep))
        
        # Field 20: requiredMaxRep
        max_rep = quest_data.get('requiredMaxRep')
        fields.append(self._format_reputation_requirement(max_rep))
        
        # Field 21: requiredSourceItems
        source_items = quest_data.get('requiredSourceItems', [])
        fields.append(self._format_number_table(source_items))
        
        # Field 22: nextQuestInChain
        next_quest = quest_data.get('nextQuestInChain')
        fields.append(self._format_number(next_quest))
        
        # Field 23: questFlags
        flags = quest_data.get('questFlags', 0)
        fields.append(self._format_number(flags, default=0))
        
        # Field 24: specialFlags
        special = quest_data.get('specialFlags', 0)
        fields.append(self._format_number(special, default=0))
        
        # Field 25: parentQuest
        parent = quest_data.get('parentQuest')
        fields.append(self._format_number(parent))
        
        # Field 26: reputationReward
        rep_reward = quest_data.get('reputationReward')
        fields.append(self._format_reputation_rewards(rep_reward))
        
        # Field 27: extraObjectives
        extra_obj = quest_data.get('extraObjectives')
        fields.append(self._format_extra_objectives(extra_obj))
        
        # Field 28: requiredSpell
        req_spell = quest_data.get('requiredSpell')
        fields.append(self._format_number(req_spell))
        
        # Field 29: requiredSpecialization
        req_spec = quest_data.get('requiredSpecialization')
        fields.append(self._format_number(req_spec))
        
        # Field 30: requiredMaxLevel
        max_level = quest_data.get('requiredMaxLevel')
        fields.append(self._format_number(max_level))
        
        # Verify we have exactly 30 fields
        assert len(fields) == self.QUEST_FIELD_COUNT, f"Expected {self.QUEST_FIELD_COUNT} fields, got {len(fields)}"
        
        # Build the Lua entry
        return f"[{quest_id}] = {{{','.join(fields)}}}"
    
    def format_npc_entry(self, npc_id: int, npc_data: Dict) -> str:
        """
        Format an NPC into proper Lua database entry with exactly 15 fields
        
        Field order:
        1. name (string)
        2. minLevelHealth (int or nil)
        3. maxLevelHealth (int or nil)
        4. minLevel (int)
        5. maxLevel (int)
        6. rank (int: 0=normal, 1=elite, 2=rare elite, 3=boss, 4=rare)
        7. spawns {[zoneId]={{x,y},...}}
        8. waypoints {[zoneId]={{x,y},...}}
        9. zoneID (int)
        10. questStarts {questIds}
        11. questEnds {questIds}
        12. factionID (int or nil)
        13. friendlyToFaction ("A", "H", "AH", or nil)
        14. subName (string or nil)
        15. npcFlags (int)
        """
        
        fields = []
        
        # Field 1: name
        name = npc_data.get('name', f'NPC {npc_id}')
        fields.append(self._format_string(name))
        
        # Field 2-3: health
        fields.append('nil')  # minLevelHealth
        fields.append('nil')  # maxLevelHealth
        
        # Field 4-5: levels
        min_level = npc_data.get('minLevel', 1)
        max_level = npc_data.get('maxLevel', min_level)
        fields.append(str(min_level))
        fields.append(str(max_level))
        
        # Field 6: rank
        rank = npc_data.get('rank', 0)
        fields.append(str(rank))
        
        # Field 7: spawns
        spawns = npc_data.get('spawns', {})
        fields.append(self._format_spawns(spawns))
        
        # Field 8: waypoints
        fields.append('nil')  # waypoints
        
        # Field 9: zoneID
        zone_id = npc_data.get('zoneID', 1)
        fields.append(str(zone_id))
        
        # Field 10: questStarts
        quest_starts = npc_data.get('questStarts', [])
        fields.append(self._format_number_table(quest_starts))
        
        # Field 11: questEnds
        quest_ends = npc_data.get('questEnds', [])
        fields.append(self._format_number_table(quest_ends))
        
        # Field 12: factionID
        faction_id = npc_data.get('factionID')
        fields.append(self._format_number(faction_id))
        
        # Field 13: friendlyToFaction
        friendly = npc_data.get('friendlyToFaction')
        fields.append(self._format_string(friendly) if friendly else 'nil')
        
        # Field 14: subName
        sub_name = npc_data.get('subName')
        fields.append(self._format_string(sub_name) if sub_name else 'nil')
        
        # Field 15: npcFlags
        flags = npc_data.get('npcFlags', 0)
        fields.append(str(flags))
        
        # Verify we have exactly 15 fields
        assert len(fields) == self.NPC_FIELD_COUNT, f"Expected {self.NPC_FIELD_COUNT} fields, got {len(fields)}"
        
        # Build the Lua entry
        return f"[{npc_id}] = {{{','.join(fields)}}}"
    
    # Helper formatting methods
    
    def _format_string(self, value: Optional[str]) -> str:
        """Format a string value for Lua"""
        if value is None:
            return 'nil'
        # Escape quotes, special characters, and newlines
        value = value.replace('\\', '\\\\').replace('"', '\\"')
        value = value.replace('\n', '\\n').replace('\r', '\\r')
        return f'"{value}"'
    
    def _format_number(self, value: Optional[Union[int, float]], default=None) -> str:
        """Format a number value for Lua"""
        if value is None:
            return str(default) if default is not None else 'nil'
        return str(value)
    
    def _format_string_table(self, values: Optional[List[str]]) -> str:
        """Format a table of strings"""
        if not values:
            return 'nil'
        # Clean up strings before formatting
        cleaned_values = []
        for v in values:
            if v:
                # Remove newlines and excessive whitespace
                v = ' '.join(v.split())
                cleaned_values.append(v)
        if not cleaned_values:
            return 'nil'
        formatted = [self._format_string(v) for v in cleaned_values]
        return f'{{{",".join(formatted)}}}'
    
    def _format_number_table(self, values: Optional[List[int]]) -> str:
        """Format a table of numbers"""
        if not values:
            return 'nil'
        return f'{{{",".join(str(v) for v in values)}}}'
    
    def _format_started_by(self, started_by: Dict) -> str:
        """Format the startedBy structure: {{NPCs},{Objects},{Items}}"""
        if not started_by:
            return 'nil'
        
        npcs = started_by.get('npcs', [])
        objects = started_by.get('objects', [])
        items = started_by.get('items', [])
        
        npc_part = self._format_number_table(npcs) if npcs else 'nil'
        obj_part = self._format_number_table(objects) if objects else 'nil'
        item_part = self._format_number_table(items) if items else 'nil'
        
        # If all are nil, return nil instead of {nil,nil,nil}
        if npc_part == 'nil' and obj_part == 'nil' and item_part == 'nil':
            return 'nil'
        
        return f'{{{npc_part},{obj_part},{item_part}}}'
    
    def _format_finished_by(self, finished_by: Dict) -> str:
        """Format the finishedBy structure: {{NPCs},{Objects}}"""
        if not finished_by:
            return 'nil'
        
        npcs = finished_by.get('npcs', [])
        objects = finished_by.get('objects', [])
        
        npc_part = self._format_number_table(npcs) if npcs else 'nil'
        obj_part = self._format_number_table(objects) if objects else 'nil'
        
        # If both are nil, return nil instead of {nil,nil}
        if npc_part == 'nil' and obj_part == 'nil':
            return 'nil'
        
        return f'{{{npc_part},{obj_part}}}'
    
    def _format_objectives(self, objectives: Dict) -> str:
        """
        Format the objectives structure:
        {creatures, objects, items, reputation, killCredit, spells}
        """
        if not objectives:
            return 'nil'
        
        parts = []
        
        # Creatures: {{npcId, count, "text"},...}
        creatures = objectives.get('creatures', [])
        if creatures:
            creature_parts = []
            for c in creatures:
                if isinstance(c, dict):
                    npc_id = c.get('npc_id', 0)
                    count = c.get('count', 1)
                    text = c.get('text', '')
                    if text:
                        creature_parts.append(f'{{{npc_id},{count},{self._format_string(text)}}}')
                    else:
                        creature_parts.append(f'{{{npc_id},{count}}}')
            parts.append(f'{{{",".join(creature_parts)}}}' if creature_parts else 'nil')
        else:
            parts.append('nil')
        
        # Objects: {{objectId, count, "text"},...}
        objects = objectives.get('objects', [])
        if objects:
            object_parts = []
            for o in objects:
                if isinstance(o, dict):
                    obj_id = o.get('object_id', 0)
                    count = o.get('count', 1)
                    text = o.get('text', '')
                    if text:
                        object_parts.append(f'{{{obj_id},{count},{self._format_string(text)}}}')
                    else:
                        object_parts.append(f'{{{obj_id},{count}}}')
            parts.append(f'{{{",".join(object_parts)}}}' if object_parts else 'nil')
        else:
            parts.append('nil')
        
        # Items: {{itemId, count},...}
        items = objectives.get('items', [])
        if items:
            item_parts = []
            for i in items:
                if isinstance(i, dict):
                    item_id = i.get('item_id', 0)
                    count = i.get('count', 1)
                    item_parts.append(f'{{{item_id},{count}}}')
            parts.append(f'{{{",".join(item_parts)}}}' if item_parts else 'nil')
        else:
            parts.append('nil')
        
        # Reputation, killCredit, spells - simplified for now
        parts.extend(['nil', 'nil', 'nil'])
        
        # If all parts are nil, return nil
        if all(p == 'nil' for p in parts):
            return 'nil'
        
        return f'{{{",".join(parts)}}}'
    
    def _format_trigger_end(self, trigger: Any) -> str:
        """Format exploration trigger"""
        # TODO: Implement if needed
        return 'nil'
    
    def _format_skill_requirement(self, skill: Any) -> str:
        """Format skill requirement: {skillId, value}"""
        if not skill:
            return 'nil'
        if isinstance(skill, dict):
            skill_id = skill.get('id', 0)
            value = skill.get('value', 0)
            return f'{{{skill_id},{value}}}'
        return 'nil'
    
    def _format_reputation_requirement(self, rep: Any) -> str:
        """Format reputation requirement: {factionId, value}"""
        if not rep:
            return 'nil'
        if isinstance(rep, dict):
            faction_id = rep.get('faction', 0)
            value = rep.get('value', 0)
            return f'{{{faction_id},{value}}}'
        return 'nil'
    
    def _format_reputation_rewards(self, rewards: Any) -> str:
        """Format reputation rewards: {{factionId, value},...}"""
        if not rewards:
            return 'nil'
        if isinstance(rewards, list):
            parts = []
            for r in rewards:
                if isinstance(r, dict):
                    faction = r.get('faction', 0)
                    value = r.get('value', 0)
                    parts.append(f'{{{faction},{value}}}')
            return f'{{{",".join(parts)}}}' if parts else 'nil'
        return 'nil'
    
    def _format_extra_objectives(self, extra: Any) -> str:
        """Format extra objectives: {{spellId, "text"},...}"""
        # TODO: Implement if needed
        return 'nil'
    
    def _format_spawns(self, spawns: Dict) -> str:
        """Format spawn locations: {[zoneId]={{x,y},...}}"""
        if not spawns:
            return 'nil'
        
        zone_parts = []
        for zone_id, coords in spawns.items():
            if coords:
                coord_parts = []
                for coord in coords:
                    if isinstance(coord, dict):
                        x = coord.get('x', 0)
                        y = coord.get('y', 0)
                        coord_parts.append(f'{{{x},{y}}}')
                    elif isinstance(coord, (list, tuple)) and len(coord) >= 2:
                        coord_parts.append(f'{{{coord[0]},{coord[1]}}}')
                
                if coord_parts:
                    zone_parts.append(f'[{zone_id}]={{{",".join(coord_parts)}}}')
        
        return f'{{{",".join(zone_parts)}}}' if zone_parts else 'nil'


def main():
    """Test the Lua formatter"""
    formatter = LuaFormatter()
    
    # Test quest formatting
    test_quest = {
        'name': 'Test Quest',
        'startedBy': {'npcs': [12345]},
        'finishedBy': {'npcs': [67890]},
        'requiredLevel': 10,
        'questLevel': 12,
        'objectivesText': ['Kill 10 wolves', 'Collect 5 pelts'],
        'objectives': {
            'creatures': [{'npc_id': 100, 'count': 10, 'text': 'Wolf'}],
            'items': [{'item_id': 200, 'count': 5}]
        },
        'zoneOrSort': 12
    }
    
    lua_entry = formatter.format_quest_entry(99999, test_quest)
    print("Quest Entry:")
    print(lua_entry)
    
    # Count fields properly (at the top level only)
    # Remove the entry brackets and ID first
    entry_content = lua_entry.split(' = {', 1)[1].rstrip('}')
    # Count commas at depth 0
    depth = 0
    field_count = 1
    for char in entry_content:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        elif char == ',' and depth == 0:
            field_count += 1
    print(f"\nActual field count: {field_count} (expected 30)")
    
    # Test NPC formatting
    test_npc = {
        'name': 'Test NPC',
        'minLevel': 10,
        'maxLevel': 12,
        'spawns': {14: [{'x': 50.5, 'y': 60.3}]},
        'zoneID': 14,
        'questStarts': [99999],
        'questEnds': [99998],
        'friendlyToFaction': 'AH',
        'npcFlags': 2  # Quest giver
    }
    
    npc_entry = formatter.format_npc_entry(12345, test_npc)
    print("\nNPC Entry:")
    print(npc_entry)
    
    # Count NPC fields properly
    entry_content = npc_entry.split(' = {', 1)[1].rstrip('}')
    depth = 0
    field_count = 1
    for char in entry_content:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        elif char == ',' and depth == 0:
            field_count += 1
    print(f"\nActual field count: {field_count} (expected 15)")


if __name__ == "__main__":
    main()