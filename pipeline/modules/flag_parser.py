#!/usr/bin/env python3
"""
Flag Parser Module - Determines quest type flags and special properties
Handles questFlags, specialFlags, race/class restrictions, and quest types
"""

import re
from typing import Dict, List, Optional, Set, Tuple
import json

class FlagParser:
    """Parses quest flags and restrictions from submissions"""
    
    def __init__(self):
        self.parsed_flags = {}
        self.parse_errors = []
        
        # WoW quest flag values (WotLK 3.3.5)
        self.quest_flags = {
            'NONE': 0,
            'STAY_ALIVE': 1,
            'PARTY_ACCEPT': 2,
            'EXPLORATION': 4,
            'SHARABLE': 8,
            'HAS_CONDITION': 16,
            'HIDE_REWARD_POI': 32,
            'RAID': 64,
            'TBC': 128,  # Burning Crusade
            'NO_MONEY_FROM_XP': 256,
            'HIDDEN_REWARDS': 512,
            'TRACKING': 1024,
            'DEPRECATE_REPUTATION': 2048,
            'DAILY': 4096,
            'FLAGS_PVP': 8192,
            'UNAVAILABLE': 16384,
            'WEEKLY': 32768,
            'AUTOCOMPLETE': 65536,
            'DISPLAY_SPELL': 131072,
            'AUTO_ACCEPT': 262144,
            'UNK19': 524288,
            'AUTO_TAKE': 1048576,
        }
        
        # Special quest flags
        self.special_flags = {
            'NONE': 0,
            'DELIVER_MORE': 1,
            'UNKNOWN1': 2,  
            'UNKNOWN2': 4,
            'UNKNOWN3': 8,
            'UNKNOWN4': 16,
            'UNKNOWN5': 32,
            'UNKNOWN6': 64,
            'UNKNOWN7': 128,
        }
        
        # Race restrictions (bitmask)
        self.races = {
            'human': 1,
            'orc': 2,
            'dwarf': 4,
            'night elf': 8,
            'undead': 16,
            'tauren': 32,
            'gnome': 64,
            'troll': 128,
            'goblin': 256,
            'blood elf': 512,
            'draenei': 1024,
        }
        
        # Class restrictions (bitmask) 
        self.classes = {
            'warrior': 1,
            'paladin': 2,
            'hunter': 4,
            'rogue': 8,
            'priest': 16,
            'death knight': 32,
            'shaman': 64,
            'mage': 128,
            'warlock': 256,
            'druid': 1024,
        }
        
        # Quest type indicators
        self.quest_types = {
            'elite': ['elite', 'group quest', 'group', 'difficult', '(elite)', '[elite]'],
            'raid': ['raid', 'raid quest', '(raid)', '[raid]', 'instance'],
            'dungeon': ['dungeon', 'instance', 'heroic', '(dungeon)', '[dungeon]'],
            'daily': ['daily', 'daily quest', '(daily)', '[daily]', 'repeatable daily'],
            'weekly': ['weekly', 'weekly quest', '(weekly)', '[weekly]'],
            'pvp': ['pvp', 'battleground', 'arena', 'player vs player', '(pvp)', '[pvp]'],
            'escort': ['escort', 'protect', 'defend', 'accompany', 'follow'],
            'delivery': ['deliver', 'bring', 'take', 'courier', 'message'],
            'collection': ['collect', 'gather', 'retrieve', 'find', 'obtain'],
            'kill': ['kill', 'slay', 'defeat', 'eliminate', 'destroy'],
            'exploration': ['explore', 'discover', 'find location', 'visit'],
            'seasonal': ['seasonal', 'holiday', 'event', 'limited time'],
            'auto_accept': ['auto', 'automatic', 'starts automatically'],
            'shareable': ['shareable', 'party quest', 'can share']
        }
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse quest flags and restrictions from submission
        
        Returns:
            Dictionary with flag and restriction data
        """
        flag_data = {
            'quest_id': quest_id,
            'quest_flags': 0,           # Field 23: questFlags
            'special_flags': 0,         # Field 24: specialFlags  
            'required_races': None,     # Field 6: requiredRaces
            'required_classes': None,   # Field 7: requiredClasses
            'detected_types': [],       # Quest types detected
            'faction_restriction': None, # 'Alliance', 'Horde', or None
            'level_restrictions': {},   # Min/max level hints
            'special_properties': []    # Special quest properties
        }
        
        # Parse quest type indicators
        flag_data.update(self._parse_quest_types(content))
        
        # Parse explicit restrictions
        flag_data.update(self._parse_explicit_restrictions(content))
        
        # Parse quest text for hints
        flag_data.update(self._parse_flag_hints(content))
        
        # Parse level and difficulty
        flag_data.update(self._parse_level_flags(content))
        
        # Parse database flags if present
        flag_data.update(self._parse_database_flags(content))
        
        # Calculate final flag values
        flag_data = self._calculate_flags(flag_data)
        
        self.parsed_flags[quest_id] = flag_data
        return flag_data
    
    def _parse_quest_types(self, content: str) -> Dict:
        """Parse quest type from various indicators"""
        types = {'detected_types': [], 'special_properties': []}
        
        # Check quest name and description
        quest_name_match = re.search(r'Quest Name:\s*(.+)', content, re.IGNORECASE)
        quest_name = quest_name_match.group(1).lower() if quest_name_match else ""
        
        # Get full content in lowercase for easier matching
        content_lower = content.lower()
        
        # Check each quest type
        for quest_type, indicators in self.quest_types.items():
            for indicator in indicators:
                if indicator in content_lower or indicator in quest_name:
                    types['detected_types'].append(quest_type)
                    break
        
        # Special case detection
        if any(word in content_lower for word in ['wanted:', 'wanted poster', 'bounty']):
            types['detected_types'].append('bounty')
            types['special_properties'].append('wanted_poster')
        
        if any(word in content_lower for word in ['timed', 'time limit', 'timer']):
            types['special_properties'].append('timed')
        
        if any(word in content_lower for word in ['breadcrumb', 'leads to', 'unlocks']):
            types['special_properties'].append('breadcrumb')
        
        # Remove duplicates
        types['detected_types'] = list(set(types['detected_types']))
        types['special_properties'] = list(set(types['special_properties']))
        
        return types
    
    def _parse_explicit_restrictions(self, content: str) -> Dict:
        """Parse explicitly stated race/class/faction restrictions"""
        restrictions = {}
        
        # Look for requirements section
        req_section = re.search(r'REQUIREMENTS?:?\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if req_section:
            req_text = req_section.group(1).lower()
            
            # Parse class restrictions
            class_patterns = [
                r'(?:class|classes):?\s*(.+)',
                r'(?:only|restricted to)\s+(.+?)\s*(?:class|classes)',
                r'(?:must be|requires?)\s+(.+?)\s*(?:class|$)'
            ]
            
            for pattern in class_patterns:
                match = re.search(pattern, req_text)
                if match:
                    class_text = match.group(1)
                    detected_classes = []
                    
                    for class_name in self.classes.keys():
                        if class_name in class_text:
                            detected_classes.append(class_name)
                    
                    if detected_classes:
                        class_mask = 0
                        for class_name in detected_classes:
                            class_mask |= self.classes[class_name]
                        restrictions['required_classes'] = class_mask
                        break
            
            # Parse race restrictions
            race_patterns = [
                r'(?:race|races):?\s*(.+)',
                r'(?:only|restricted to)\s+(.+?)\s*(?:race|races)',
                r'(?:alliance|horde)\s+(?:only|exclusive)'
            ]
            
            for pattern in race_patterns:
                match = re.search(pattern, req_text)
                if match:
                    race_text = match.group(1)
                    detected_races = []
                    
                    for race_name in self.races.keys():
                        if race_name in race_text:
                            detected_races.append(race_name)
                    
                    if detected_races:
                        race_mask = 0
                        for race_name in detected_races:
                            race_mask |= self.races[race_name]
                        restrictions['required_races'] = race_mask
                        break
            
            # Parse faction restrictions
            if any(word in req_text for word in ['alliance only', 'alliance exclusive']):
                restrictions['faction_restriction'] = 'Alliance'
                # Alliance races: human, dwarf, night elf, gnome, draenei
                restrictions['required_races'] = 1 + 4 + 8 + 64 + 1024
            elif any(word in req_text for word in ['horde only', 'horde exclusive']):
                restrictions['faction_restriction'] = 'Horde'
                # Horde races: orc, undead, tauren, troll, blood elf
                restrictions['required_races'] = 2 + 16 + 32 + 128 + 512
        
        return restrictions
    
    def _parse_flag_hints(self, content: str) -> Dict:
        """Parse quest text for flag-related hints"""
        hints = {'special_properties': []}
        
        # Get all text content
        text_sections = [
            r'Quest Text:?\s*\n(.*?)(?:\n\n|\Z)',
            r'Description:?\s*\n(.*?)(?:\n\n|\Z)',
            r'Completion Text:?\s*\n(.*?)(?:\n\n|\Z)',
            r'OBJECTIVES?:?\s*\n(.*?)(?:\n\nTURN-?IN|\n\nGROUND|\n\nDATABASE|\Z)'
        ]
        
        all_text = ""
        for section_pattern in text_sections:
            match = re.search(section_pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                all_text += " " + match.group(1)
        
        if all_text:
            text_lower = all_text.lower()
            
            # Check for auto-accept indicators
            if any(phrase in text_lower for phrase in ['automatically accepted', 'starts when', 'begins automatically']):
                hints['special_properties'].append('auto_accept')
            
            # Check for party/sharing requirements
            if any(phrase in text_lower for phrase in ['bring friends', 'group recommended', 'party suggested', 'share this']):
                hints['special_properties'].append('party_suggested')
            
            # Check for stay-alive requirements
            if any(phrase in text_lower for phrase in ['don\'t die', 'stay alive', 'survive', 'without dying']):
                hints['special_properties'].append('stay_alive')
            
            # Check for exploration quests
            if any(phrase in text_lower for phrase in ['discover', 'explore', 'find the location', 'locate']):
                hints['special_properties'].append('exploration')
            
            # Check for PvP content
            if any(phrase in text_lower for phrase in ['battleground', 'arena', 'honor points', 'enemy players']):
                hints['special_properties'].append('pvp')
        
        return hints
    
    def _parse_level_flags(self, content: str) -> Dict:
        """Parse level restrictions and elite status"""
        level_data = {'level_restrictions': {}}
        
        # Extract quest level
        level_match = re.search(r'(?:Quest )?Level:\s*(\d+)', content, re.IGNORECASE)
        if level_match:
            quest_level = int(level_match.group(1))
            level_data['level_restrictions']['quest_level'] = quest_level
            
            # High level quests are more likely to be elite/group
            if quest_level >= 60:
                level_data['level_restrictions']['likely_elite'] = True
        
        # Extract minimum level
        min_level_match = re.search(r'Min(?:imum)? Level:\s*(\d+)', content, re.IGNORECASE)
        if min_level_match:
            min_level = int(min_level_match.group(1))
            level_data['level_restrictions']['min_level'] = min_level
        
        # Check for elite indicators by level and context
        content_lower = content.lower()
        if any(word in content_lower for word in ['elite', 'group', 'difficult', 'challenging']):
            level_data['level_restrictions']['is_elite'] = True
        
        return level_data
    
    def _parse_database_flags(self, content: str) -> Dict:
        """Parse flags from existing database entries"""
        db_flags = {}
        
        # Look for database entry
        db_section = re.search(r'-- Add to epochQuestDB\.lua:(.*?)(?:-- Add to|$)', content, re.DOTALL)
        if db_section:
            db_text = db_section.group(1)
            
            # Extract quest entry
            table_match = re.search(r'\[(\d+)\]\s*=\s*\{(.+?)\}', db_text, re.DOTALL)
            if table_match:
                fields = [f.strip() for f in table_match.group(2).split(',')]
                
                if len(fields) > 23:
                    # Field 23: questFlags
                    try:
                        quest_flags = int(fields[22]) if fields[22] != 'nil' else 0
                        db_flags['quest_flags'] = quest_flags
                    except ValueError:
                        pass
                
                if len(fields) > 24:
                    # Field 24: specialFlags
                    try:
                        special_flags = int(fields[23]) if fields[23] != 'nil' else 0
                        db_flags['special_flags'] = special_flags
                    except ValueError:
                        pass
                
                if len(fields) > 5:
                    # Field 6: requiredRaces
                    if fields[5] != 'nil':
                        try:
                            required_races = int(fields[5])
                            db_flags['required_races'] = required_races
                        except ValueError:
                            pass
                
                if len(fields) > 6:
                    # Field 7: requiredClasses
                    if fields[6] != 'nil':
                        try:
                            required_classes = int(fields[6])
                            db_flags['required_classes'] = required_classes
                        except ValueError:
                            pass
        
        return db_flags
    
    def _calculate_flags(self, flag_data: Dict) -> Dict:
        """Calculate final quest flags based on detected types and properties"""
        quest_flags = flag_data.get('quest_flags', 0)
        special_flags = flag_data.get('special_flags', 0)
        
        detected_types = flag_data.get('detected_types', [])
        special_props = flag_data.get('special_properties', [])
        
        # Apply flags based on detected quest types
        if 'daily' in detected_types:
            quest_flags |= self.quest_flags['DAILY']
        
        if 'weekly' in detected_types:
            quest_flags |= self.quest_flags['WEEKLY']
        
        if 'raid' in detected_types:
            quest_flags |= self.quest_flags['RAID']
        
        if 'pvp' in detected_types:
            quest_flags |= self.quest_flags['FLAGS_PVP']
        
        if 'shareable' in detected_types or 'party_suggested' in special_props:
            quest_flags |= self.quest_flags['SHARABLE']
        
        if 'exploration' in detected_types or 'exploration' in special_props:
            quest_flags |= self.quest_flags['EXPLORATION']
        
        if 'auto_accept' in special_props:
            quest_flags |= self.quest_flags['AUTO_ACCEPT']
        
        if 'stay_alive' in special_props:
            quest_flags |= self.quest_flags['STAY_ALIVE']
        
        if 'party_suggested' in special_props:
            quest_flags |= self.quest_flags['PARTY_ACCEPT']
        
        # Update the flag data
        flag_data['quest_flags'] = quest_flags
        flag_data['special_flags'] = special_flags
        
        return flag_data
    
    def generate_flag_lua(self, flag_data: Dict) -> Dict[str, str]:
        """Generate Lua values for flag fields"""
        lua_fields = {}
        
        # Field 6: requiredRaces
        if flag_data.get('required_races'):
            lua_fields['requiredRaces'] = str(flag_data['required_races'])
        else:
            lua_fields['requiredRaces'] = "nil"
        
        # Field 7: requiredClasses
        if flag_data.get('required_classes'):
            lua_fields['requiredClasses'] = str(flag_data['required_classes'])
        else:
            lua_fields['requiredClasses'] = "nil"
        
        # Field 23: questFlags
        lua_fields['questFlags'] = str(flag_data.get('quest_flags', 0))
        
        # Field 24: specialFlags
        lua_fields['specialFlags'] = str(flag_data.get('special_flags', 0))
        
        return lua_fields
    
    def get_race_names(self, race_mask: int) -> List[str]:
        """Get race names from race bitmask"""
        races = []
        for race_name, mask in self.races.items():
            if race_mask & mask:
                races.append(race_name.title())
        return races
    
    def get_class_names(self, class_mask: int) -> List[str]:
        """Get class names from class bitmask"""
        classes = []
        for class_name, mask in self.classes.items():
            if class_mask & mask:
                classes.append(class_name.title())
        return classes
    
    def get_flag_names(self, flag_value: int) -> List[str]:
        """Get quest flag names from flag value"""
        flags = []
        for flag_name, mask in self.quest_flags.items():
            if flag_value & mask and flag_name != 'NONE':
                flags.append(flag_name)
        return flags
    
    def get_summary(self) -> Dict:
        """Get parsing summary"""
        total_parsed = len(self.parsed_flags)
        
        with_quest_flags = sum(1 for flag in self.parsed_flags.values() if flag.get('quest_flags', 0) > 0)
        with_race_restrictions = sum(1 for flag in self.parsed_flags.values() if flag.get('required_races'))
        with_class_restrictions = sum(1 for flag in self.parsed_flags.values() if flag.get('required_classes'))
        
        # Count quest types
        type_counts = {}
        for flag_data in self.parsed_flags.values():
            for quest_type in flag_data.get('detected_types', []):
                type_counts[quest_type] = type_counts.get(quest_type, 0) + 1
        
        return {
            'total_parsed': total_parsed,
            'with_quest_flags': with_quest_flags,
            'with_race_restrictions': with_race_restrictions,
            'with_class_restrictions': with_class_restrictions,
            'quest_type_distribution': type_counts,
            'parse_errors': len(self.parse_errors)
        }

def main():
    """Test the flag parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python flag_parser.py <submission_file>")
        sys.exit(1)
    
    parser = FlagParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract quest ID if present
    quest_id = None
    id_match = re.search(r'Quest ID:\s*(\d+)', content)
    if id_match:
        quest_id = int(id_match.group(1))
    
    flag_data = parser.parse(content, quest_id)
    
    print(f"\nQuest {quest_id} Flag Analysis:")
    
    if flag_data.get('detected_types'):
        print(f"Quest Types: {', '.join(flag_data['detected_types'])}")
    
    if flag_data.get('quest_flags', 0) > 0:
        flag_names = parser.get_flag_names(flag_data['quest_flags'])
        print(f"Quest Flags: {flag_data['quest_flags']} ({', '.join(flag_names)})")
    
    if flag_data.get('required_races'):
        race_names = parser.get_race_names(flag_data['required_races'])
        print(f"Race Restrictions: {flag_data['required_races']} ({', '.join(race_names)})")
    
    if flag_data.get('required_classes'):
        class_names = parser.get_class_names(flag_data['required_classes'])
        print(f"Class Restrictions: {flag_data['required_classes']} ({', '.join(class_names)})")
    
    if flag_data.get('faction_restriction'):
        print(f"Faction Restriction: {flag_data['faction_restriction']}")
    
    if flag_data.get('special_properties'):
        print(f"Special Properties: {', '.join(flag_data['special_properties'])}")
    
    # Show Lua output
    lua_fields = parser.generate_flag_lua(flag_data)
    print(f"\nLua Fields:")
    for field, value in lua_fields.items():
        print(f"  {field}: {value}")
    
    print(f"\nSummary: {json.dumps(parser.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()