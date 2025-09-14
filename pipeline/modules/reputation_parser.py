#!/usr/bin/env python3
"""
Reputation Parser Module - Extracts reputation requirements and rewards
Handles faction reputation minimums, maximums, and quest rewards
"""

import re
from typing import Dict, List, Optional, Tuple
import json

class ReputationParser:
    """Parses reputation data from quest submissions"""
    
    def __init__(self):
        self.parsed_reputation = {}
        self.parse_errors = []
        
        # WoW faction IDs (WotLK 3.3.5)
        self.factions = {
            # Alliance
            'stormwind': 72,
            'ironforge': 47,
            'darnassus': 69,
            'gnomeregan exiles': 54,
            'exodar': 930,
            
            # Horde  
            'orgrimmar': 76,
            'thunder bluff': 81,
            'undercity': 68,
            'darkspear trolls': 530,
            'silvermoon city': 911,
            
            # Neutral/Shared
            'cenarion expedition': 942,
            'honor hold': 946,
            'thrallmar': 947,
            'cenarion circle': 609,
            'argent dawn': 529,
            'timbermaw hold': 576,
            'bloodsail buccaneers': 87,
            'steamwheedle cartel': 169,
            'booty bay': 21,
            'gadgetzan': 369,
            'ratchet': 470,
            'everlook': 577,
            
            # Burning Crusade
            'kurenai': 978,
            'maghar': 941,
            'sporeggar': 970,
            'consortium': 933,
            'keepers of time': 989,
            'lower city': 1011,
            'shattered sun offensive': 1077,
            'aldor': 932,
            'scryers': 934,
            'sha\'tari skyguard': 1031,
            'netherwing': 1015,
            'ogri\'la': 1038,
            
            # Wrath of the Lich King
            'knights of the ebon blade': 1098,
            'argent crusade': 1106,
            'kirin tor': 1090,
            'wyrmrest accord': 1091,
            'explorers\' league': 1068,
            'valiance expedition': 1050,
            'alliance vanguard': 1037,
            'horde expedition': 1052,
            'warsong offensive': 1085,
            'the kalu\'ak': 1073,
            'frenzyheart tribe': 1104,
            'the oracles': 1105,
            'sons of hodir': 1119,
            'ashen verdict': 1156,
            
            # Special
            'bloodsail buccaneers': 87,
            'darkmoon faire': 909,
            'zandalar tribe': 270,
            'brood of nozdormu': 910,
            'hydraxian waterlords': 749,
            'thorium brotherhood': 59,
            'wintersaber trainers': 589,
            'darnassian': 69,  # Language faction
            
            # Goblin factions
            'steamwheedle cartel': 169,
            'booty bay': 21,
            'everlook': 577,
            'gadgetzan': 369,
            'ratchet': 470,
        }
        
        # Faction aliases and common names
        self.faction_aliases = {
            'sw': 'stormwind',
            'if': 'ironforge', 
            'darn': 'darnassus',
            'gnomes': 'gnomeregan exiles',
            'draenei': 'exodar',
            'org': 'orgrimmar',
            'tb': 'thunder bluff',
            'uc': 'undercity',
            'trolls': 'darkspear trolls',
            'belves': 'silvermoon city',
            'blood elves': 'silvermoon city',
            'cenarion': 'cenarion circle',
            'ad': 'argent dawn',
            'timbermaw': 'timbermaw hold',
            'bloodsail': 'bloodsail buccaneers',
            'pirates': 'bloodsail buccaneers',
            'cartel': 'steamwheedle cartel',
            'goblins': 'steamwheedle cartel',
            'bb': 'booty bay',
            'gadget': 'gadgetzan',
            'everook': 'everlook',
            'maghar': 'mag\'har',
            'spore': 'sporeggar',
            'keepers': 'keepers of time',
            'lower': 'lower city',
            'sso': 'shattered sun offensive',
            'skyguard': 'sha\'tari skyguard',
            'nether': 'netherwing',
            'ebon blade': 'knights of the ebon blade',
            'death knights': 'knights of the ebon blade',
            'argent': 'argent crusade',
            'kirin': 'kirin tor',
            'wyrmrest': 'wyrmrest accord',
            'explorers': 'explorers\' league',
            'valiance': 'valiance expedition',
            'vanguard': 'alliance vanguard',
            'horde exp': 'horde expedition',
            'warsong': 'warsong offensive',
            'kalu\'ak': 'the kalu\'ak',
            'kaluak': 'the kalu\'ak',
            'walrus': 'the kalu\'ak',
            'frenzyheart': 'frenzyheart tribe',
            'oracles': 'the oracles',
            'hodir': 'sons of hodir',
            'ashen': 'ashen verdict',
            'dmf': 'darkmoon faire',
            'zandalar': 'zandalar tribe',
            'nozdormu': 'brood of nozdormu',
            'hydraxian': 'hydraxian waterlords',
            'thorium': 'thorium brotherhood',
            'wintersaber': 'wintersaber trainers'
        }
        
        # Reputation levels
        self.reputation_levels = {
            'hated': -42000,
            'hostile': -6000,
            'unfriendly': -3000,
            'neutral': 0,
            'friendly': 3000,
            'honored': 9000,
            'revered': 21000,
            'exalted': 42000
        }
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse reputation data from quest submission
        
        Returns:
            Dictionary with reputation requirement and reward data
        """
        rep_data = {
            'quest_id': quest_id,
            'required_min_rep': None,     # Field 19: {factionId, value}
            'required_max_rep': None,     # Field 20: {factionId, value}
            'reputation_rewards': [],     # Field 26: {{factionId, value},...}
            'detected_factions': [],      # All mentioned factions
            'reputation_hints': {}        # Faction reputation hints from text
        }
        
        # Parse explicit requirements
        rep_data.update(self._parse_explicit_requirements(content))
        
        # Parse quest text for faction mentions
        rep_data.update(self._parse_faction_hints(content))
        
        # Parse rewards section
        rep_data.update(self._parse_reputation_rewards(content))
        
        # Parse NPC affiliations
        rep_data.update(self._parse_npc_factions(content))
        
        # Consolidate and validate
        rep_data = self._consolidate_reputation(rep_data)
        
        self.parsed_reputation[quest_id] = rep_data
        return rep_data
    
    def _parse_explicit_requirements(self, content: str) -> Dict:
        """Parse explicitly stated reputation requirements"""
        requirements = {}
        
        # Look for requirements section
        req_section = re.search(r'REQUIREMENTS?:?\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if req_section:
            req_text = req_section.group(1)
            
            # Parse minimum reputation requirements
            min_patterns = [
                r'requires?\s+(.+?)\s+(?:reputation\s+)?(?:level\s+)?(?:of\s+)?(\w+)',
                r'minimum\s+(.+?)\s+(?:reputation\s+)?(?:level\s+)?(\w+)',
                r'must be\s+(\w+)\s+(?:or higher\s+)?with\s+(.+)',
                r'need\s+(\w+)\s+(?:reputation\s+)?with\s+(.+)'
            ]
            
            for pattern in min_patterns:
                matches = re.findall(pattern, req_text, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        # Determine which is faction and which is level
                        faction_name, rep_level = match
                        if rep_level.lower() in self.reputation_levels:
                            faction_name, rep_level = match[0], match[1]
                        elif faction_name.lower() in self.reputation_levels:
                            faction_name, rep_level = match[1], match[0]
                        else:
                            continue
                        
                        faction_id = self._get_faction_id(faction_name)
                        rep_value = self.reputation_levels.get(rep_level.lower())
                        
                        if faction_id and rep_value is not None:
                            requirements['required_min_rep'] = {'faction_id': faction_id, 'value': rep_value}
                            break
            
            # Parse maximum reputation requirements (rare but exists)
            max_patterns = [
                r'maximum\s+(.+?)\s+(?:reputation\s+)?(?:level\s+)?(\w+)',
                r'no higher than\s+(\w+)\s+with\s+(.+)',
                r'must not be\s+(\w+)\s+with\s+(.+)'
            ]
            
            for pattern in max_patterns:
                matches = re.findall(pattern, req_text, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        faction_name = match[0] if match[1].lower() in self.reputation_levels else match[1]
                        rep_level = match[1] if match[1].lower() in self.reputation_levels else match[0]
                        
                        faction_id = self._get_faction_id(faction_name)
                        rep_value = self.reputation_levels.get(rep_level.lower())
                        
                        if faction_id and rep_value is not None:
                            requirements['required_max_rep'] = {'faction_id': faction_id, 'value': rep_value}
                            break
        
        return requirements
    
    def _parse_faction_hints(self, content: str) -> Dict:
        """Parse quest text for faction-related hints"""
        hints = {
            'detected_factions': [],
            'reputation_hints': {}
        }
        
        # Get all text sections
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
            
            # Look for faction mentions
            for faction_name, faction_id in self.factions.items():
                if faction_name in text_lower:
                    hints['detected_factions'].append(faction_name)
                    
                    # Look for reputation context
                    context_patterns = [
                        rf'{re.escape(faction_name)}[^.]*?(friendly|honored|revered|exalted)',
                        rf'(friendly|honored|revered|exalted)[^.]*?{re.escape(faction_name)}',
                        rf'{re.escape(faction_name)}[^.]*?(reputation|standing|favor)'
                    ]
                    
                    for context_pattern in context_patterns:
                        context_match = re.search(context_pattern, text_lower)
                        if context_match:
                            rep_level = context_match.group(1).lower()
                            if rep_level in self.reputation_levels:
                                hints['reputation_hints'][faction_name] = self.reputation_levels[rep_level]
                            break
            
            # Check aliases
            for alias, faction_name in self.faction_aliases.items():
                if alias in text_lower and faction_name not in hints['detected_factions']:
                    hints['detected_factions'].append(faction_name)
        
        return hints
    
    def _parse_reputation_rewards(self, content: str) -> Dict:
        """Parse reputation rewards from quest"""
        rewards = {'reputation_rewards': []}
        
        # Look for rewards section
        reward_section = re.search(r'REWARDS?:?\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if reward_section:
            reward_text = reward_section.group(1)
            
            # Look for reputation rewards
            rep_patterns = [
                r'(\d+)\s+(.+?)\s+reputation',
                r'(.+?)\s+reputation:?\s*(\d+)',
                r'gains?\s+(\d+)\s+reputation\s+with\s+(.+)',
                r'reputation\s+with\s+(.+?):\s*(\d+)'
            ]
            
            for pattern in rep_patterns:
                matches = re.findall(pattern, reward_text, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        # Determine which is amount and which is faction
                        if match[0].isdigit():
                            rep_amount, faction_name = int(match[0]), match[1].strip()
                        elif match[1].isdigit():
                            faction_name, rep_amount = match[0].strip(), int(match[1])
                        else:
                            continue
                        
                        faction_id = self._get_faction_id(faction_name)
                        if faction_id and 0 < rep_amount <= 5000:  # Reasonable reputation range
                            rewards['reputation_rewards'].append({
                                'faction_id': faction_id,
                                'value': rep_amount
                            })
        
        # Also check for database entries with reputation rewards
        db_section = re.search(r'-- Add to epochQuestDB\.lua:(.*?)(?:-- Add to|$)', content, re.DOTALL)
        if db_section:
            db_text = db_section.group(1)
            
            # Look for field 26 (reputationReward)
            table_match = re.search(r'\[(\d+)\]\s*=\s*\{(.+?)\}', db_text, re.DOTALL)
            if table_match:
                fields = [f.strip() for f in table_match.group(2).split(',')]
                if len(fields) > 25:  # Field 26 exists
                    rep_reward_field = fields[25]
                    if rep_reward_field != 'nil':
                        # Parse reputation reward array
                        rep_rewards = self._parse_lua_reputation_array(rep_reward_field)
                        if rep_rewards:
                            rewards['reputation_rewards'].extend(rep_rewards)
        
        return rewards
    
    def _parse_npc_factions(self, content: str) -> Dict:
        """Parse NPC factions to infer quest faction alignment"""
        npc_data = {'detected_factions': []}
        
        # Look for quest giver and turn-in NPCs
        npc_sections = [
            r'QUEST GIVER:.*?\n.*?(.+?)\s*\(ID:\s*(\d+)\)',
            r'TURN-?IN NPC:.*?\n.*?(.+?)\s*\(ID:\s*(\d+)\)'
        ]
        
        for section_pattern in npc_sections:
            matches = re.findall(section_pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                npc_name = match[0].strip().lower()
                
                # Check for faction-specific NPC naming patterns
                faction_indicators = {
                    'stormwind': ['stormwind', 'human', 'alliance'],
                    'ironforge': ['ironforge', 'dwarf', 'dwarven'],
                    'darnassus': ['darnassus', 'night elf', 'elf'],
                    'exodar': ['exodar', 'draenei'],
                    'orgrimmar': ['orgrimmar', 'orc', 'horde'],
                    'thunder bluff': ['thunder bluff', 'tauren'],
                    'undercity': ['undercity', 'forsaken', 'undead'],
                    'darkspear trolls': ['darkspear', 'troll'],
                    'silvermoon city': ['silvermoon', 'blood elf', 'sin\'dorei'],
                    'cenarion circle': ['cenarion', 'druid', 'nature'],
                    'argent dawn': ['argent', 'scarlet', 'plaguelands'],
                    'timbermaw hold': ['timbermaw', 'furbolg'],
                    'thorium brotherhood': ['thorium', 'dark iron']
                }
                
                for faction_name, indicators in faction_indicators.items():
                    if any(indicator in npc_name for indicator in indicators):
                        npc_data['detected_factions'].append(faction_name)
                        break
        
        return npc_data
    
    def _parse_lua_reputation_array(self, lua_str: str) -> List[Dict]:
        """Parse Lua reputation reward array"""
        if not lua_str or lua_str.strip() == 'nil':
            return []
        
        try:
            # Remove outer braces
            cleaned = lua_str.strip().strip('{}')
            if not cleaned:
                return []
            
            # Parse nested arrays: {{factionId,value},{factionId,value}}
            nested_pattern = r'\{(\d+),(\d+)\}'
            matches = re.findall(nested_pattern, cleaned)
            
            rewards = []
            for match in matches:
                faction_id = int(match[0])
                value = int(match[1])
                rewards.append({'faction_id': faction_id, 'value': value})
            
            return rewards
        except (ValueError, IndexError):
            return []
    
    def _get_faction_id(self, faction_name: str) -> Optional[int]:
        """Get faction ID from faction name or alias"""
        faction_name = faction_name.lower().strip()
        
        # Direct lookup
        if faction_name in self.factions:
            return self.factions[faction_name]
        
        # Check aliases
        if faction_name in self.faction_aliases:
            actual_name = self.faction_aliases[faction_name]
            return self.factions.get(actual_name)
        
        # Partial matching for common variations
        for name, faction_id in self.factions.items():
            if faction_name in name or name in faction_name:
                return faction_id
        
        return None
    
    def _consolidate_reputation(self, rep_data: Dict) -> Dict:
        """Consolidate and validate reputation data"""
        # Remove duplicates
        if 'detected_factions' in rep_data:
            rep_data['detected_factions'] = list(set(rep_data['detected_factions']))
        
        # If we have detected factions but no explicit requirements, create hints
        if rep_data.get('detected_factions') and not rep_data.get('required_min_rep'):
            # If quest involves specific faction NPCs, it might require neutral standing
            primary_faction = rep_data['detected_factions'][0]
            faction_id = self._get_faction_id(primary_faction)
            
            if faction_id:
                # Only add requirement if it seems like a faction-specific quest
                if len(rep_data['detected_factions']) == 1:
                    rep_data['reputation_hints'][primary_faction] = 0  # Neutral minimum
        
        return rep_data
    
    def generate_reputation_lua(self, rep_data: Dict) -> Dict[str, str]:
        """Generate Lua values for reputation fields"""
        lua_fields = {}
        
        # Field 19: requiredMinRep {factionId, value}
        if rep_data.get('required_min_rep'):
            min_rep = rep_data['required_min_rep']
            lua_fields['requiredMinRep'] = f"{{{min_rep['faction_id']},{min_rep['value']}}}"
        else:
            lua_fields['requiredMinRep'] = "nil"
        
        # Field 20: requiredMaxRep {factionId, value}
        if rep_data.get('required_max_rep'):
            max_rep = rep_data['required_max_rep']
            lua_fields['requiredMaxRep'] = f"{{{max_rep['faction_id']},{max_rep['value']}}}"
        else:
            lua_fields['requiredMaxRep'] = "nil"
        
        # Field 26: reputationReward {{factionId,value},...}
        if rep_data.get('reputation_rewards'):
            reward_entries = []
            for reward in rep_data['reputation_rewards']:
                reward_entries.append(f"{{{reward['faction_id']},{reward['value']}}}")
            lua_fields['reputationReward'] = "{" + ",".join(reward_entries) + "}"
        else:
            lua_fields['reputationReward'] = "nil"
        
        return lua_fields
    
    def get_faction_name(self, faction_id: int) -> Optional[str]:
        """Get faction name from faction ID"""
        for name, fid in self.factions.items():
            if fid == faction_id:
                return name.title()
        return None
    
    def get_summary(self) -> Dict:
        """Get parsing summary"""
        total_parsed = len(self.parsed_reputation)
        
        with_min_req = sum(1 for rep in self.parsed_reputation.values() if rep.get('required_min_rep'))
        with_max_req = sum(1 for rep in self.parsed_reputation.values() if rep.get('required_max_rep'))
        with_rewards = sum(1 for rep in self.parsed_reputation.values() if rep.get('reputation_rewards'))
        with_detected = sum(1 for rep in self.parsed_reputation.values() if rep.get('detected_factions'))
        
        # Count by faction
        faction_counts = {}
        for rep_data in self.parsed_reputation.values():
            for faction in rep_data.get('detected_factions', []):
                faction_counts[faction] = faction_counts.get(faction, 0) + 1
        
        return {
            'total_parsed': total_parsed,
            'with_min_requirements': with_min_req,
            'with_max_requirements': with_max_req,
            'with_rewards': with_rewards,
            'with_detected_factions': with_detected,
            'faction_distribution': faction_counts,
            'parse_errors': len(self.parse_errors)
        }

def main():
    """Test the reputation parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python reputation_parser.py <submission_file>")
        sys.exit(1)
    
    parser = ReputationParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract quest ID if present
    quest_id = None
    id_match = re.search(r'Quest ID:\s*(\d+)', content)
    if id_match:
        quest_id = int(id_match.group(1))
    
    rep_data = parser.parse(content, quest_id)
    
    print(f"\nQuest {quest_id} Reputation Analysis:")
    
    if rep_data.get('required_min_rep'):
        min_rep = rep_data['required_min_rep']
        faction_name = parser.get_faction_name(min_rep['faction_id'])
        print(f"Minimum Reputation: {faction_name} ({min_rep['faction_id']}) = {min_rep['value']}")
    
    if rep_data.get('required_max_rep'):
        max_rep = rep_data['required_max_rep']
        faction_name = parser.get_faction_name(max_rep['faction_id'])
        print(f"Maximum Reputation: {faction_name} ({max_rep['faction_id']}) = {max_rep['value']}")
    
    if rep_data.get('reputation_rewards'):
        print(f"Reputation Rewards:")
        for reward in rep_data['reputation_rewards']:
            faction_name = parser.get_faction_name(reward['faction_id'])
            print(f"  {faction_name} ({reward['faction_id']}): +{reward['value']}")
    
    if rep_data.get('detected_factions'):
        print(f"Detected Factions: {', '.join(rep_data['detected_factions'])}")
    
    if rep_data.get('reputation_hints'):
        print(f"Reputation Hints:")
        for faction, value in rep_data['reputation_hints'].items():
            print(f"  {faction}: {value}")
    
    # Show Lua output
    lua_fields = parser.generate_reputation_lua(rep_data)
    print(f"\nLua Fields:")
    for field, value in lua_fields.items():
        print(f"  {field}: {value}")
    
    print(f"\nSummary: {json.dumps(parser.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()