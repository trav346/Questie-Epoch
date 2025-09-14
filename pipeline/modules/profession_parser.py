#!/usr/bin/env python3
"""
Profession Parser Module - Extracts profession and skill requirements
Handles required skills, spell requirements, and specialization needs
"""

import re
from typing import Dict, List, Optional, Tuple
import json

class ProfessionParser:
    """Parses profession/skill requirements from quest submissions"""
    
    def __init__(self):
        self.parsed_professions = {}
        self.parse_errors = []
        
        # WoW profession and skill mappings
        self.professions = {
            # Primary Professions
            'alchemy': 171,
            'blacksmithing': 164,
            'enchanting': 333,
            'engineering': 202,
            'herbalism': 182,
            'inscription': 773,
            'jewelcrafting': 755,
            'leatherworking': 165,
            'mining': 186,
            'skinning': 393,
            'tailoring': 197,
            
            # Secondary Professions
            'cooking': 185,
            'first aid': 129,
            'fishing': 356,
            'archaeology': 794,
            
            # Riding
            'riding': 762,
            
            # Weapon Skills
            'swords': 43,
            'axes': 44,
            'maces': 54,
            'polearms': 229,
            'staves': 136,
            'daggers': 173,
            'thrown': 176,
            'bows': 264,
            'crossbows': 5011,
            'guns': 266,
            'wands': 228,
            'fist weapons': 473,
            
            # Defense Skills
            'defense': 95,
            'shield': 433,
            'dodge': 752,
            'parry': 754,
            'block': 753,
            
            # Magic Schools
            'arcane': 166,
            'fire': 8,
            'frost': 6,
            'holy': 2,
            'nature': 3,
            'shadow': 5,
            
            # Language Skills
            'common': 98,
            'orcish': 109,
            'dwarven': 111,
            'darnassian': 113,
            'taurahe': 115,
            'gnomish': 313,
            'troll': 315,
            'gutterspeak': 673,
            'draenei': 759,
            'blood elf': 813,
        }
        
        # Common profession aliases
        self.profession_aliases = {
            'alch': 'alchemy',
            'bs': 'blacksmithing',
            'smith': 'blacksmithing',
            'ench': 'enchanting',
            'eng': 'engineering',
            'herb': 'herbalism',
            'jc': 'jewelcrafting',
            'lw': 'leatherworking',
            'leather': 'leatherworking',
            'mining': 'mining',
            'skin': 'skinning',
            'tailor': 'tailoring',
            'cook': 'cooking',
            'fa': 'first aid',
            'firstaid': 'first aid',
            'fish': 'fishing',
            'arch': 'archaeology',
            'mount': 'riding',
            'riding skill': 'riding'
        }
        
        # Spell schools and magic requirements
        self.spell_schools = {
            'arcane': ['arcane', 'mage', 'magic'],
            'fire': ['fire', 'flame', 'burn', 'ignite'],
            'frost': ['frost', 'ice', 'chill', 'freeze'],
            'holy': ['holy', 'light', 'heal', 'divine', 'priest'],
            'nature': ['nature', 'earth', 'lightning', 'shaman'],
            'shadow': ['shadow', 'dark', 'death', 'warlock']
        }
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse profession requirements from quest submission
        
        Returns:
            Dictionary with profession requirement data
        """
        prof_data = {
            'quest_id': quest_id,
            'required_skill': None,        # Field 18: {skillId, value}
            'required_spell': None,        # Field 28: spellId
            'required_specialization': None, # Field 29: specializationId
            'detected_professions': [],    # All mentioned professions
            'skill_level_hints': {},       # Skill level requirements found
            'spell_requirements': [],      # Specific spells needed
            'class_hints': []             # Classes that likely can do this quest
        }
        
        # Parse explicit requirements
        prof_data.update(self._parse_explicit_requirements(content))
        
        # Parse quest text for profession hints
        prof_data.update(self._parse_profession_hints(content))
        
        # Parse objectives for profession items/actions
        prof_data.update(self._parse_objective_professions(content))
        
        # Parse NPC interactions for trainers
        prof_data.update(self._parse_trainer_interactions(content))
        
        # Validate and consolidate requirements
        prof_data = self._consolidate_requirements(prof_data)
        
        self.parsed_professions[quest_id] = prof_data
        return prof_data
    
    def _parse_explicit_requirements(self, content: str) -> Dict:
        """Parse explicitly stated requirements"""
        requirements = {}
        
        # Look for requirements section
        req_section = re.search(r'REQUIREMENTS?:?\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if req_section:
            req_text = req_section.group(1)
            
            # Parse profession requirements
            for profession, skill_id in self.professions.items():
                pattern = rf'{re.escape(profession)}\s*(?:skill)?\s*(?:level)?\s*(\d+)'
                match = re.search(pattern, req_text, re.IGNORECASE)
                if match:
                    skill_level = int(match.group(1))
                    requirements['required_skill'] = {'skill_id': skill_id, 'level': skill_level}
                    requirements['detected_professions'] = [profession]
                    break
        
        # Look for spell requirements
        spell_patterns = [
            r'requires?\s+spell:?\s*(\d+)',
            r'must know spell:?\s*(\d+)',
            r'spell\s+(?:id|ID):?\s*(\d+)',
            r'requires?\s+(.+?)\s+spell'
        ]
        
        for pattern in spell_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if match.group(1).isdigit():
                    requirements['required_spell'] = int(match.group(1))
                else:
                    # Try to find spell by name
                    spell_name = match.group(1).strip()
                    requirements['spell_requirements'] = [spell_name]
                break
        
        # Look for class/specialization requirements
        spec_patterns = [
            r'requires?\s+(warrior|paladin|hunter|rogue|priest|shaman|mage|warlock|druid|death knight)',
            r'(?:only|must be)\s+(warrior|paladin|hunter|rogue|priest|shaman|mage|warlock|druid|death knight)',
            r'class:?\s+(warrior|paladin|hunter|rogue|priest|shaman|mage|warlock|druid|death knight)'
        ]
        
        for pattern in spec_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                class_name = match.group(1).lower()
                requirements['class_hints'] = [class_name]
                # Map class to specialization ID if needed
                break
        
        return requirements
    
    def _parse_profession_hints(self, content: str) -> Dict:
        """Parse quest text for profession-related hints"""
        hints = {
            'detected_professions': [],
            'skill_level_hints': {}
        }
        
        # Get quest text sections
        text_sections = [
            r'Quest Text:?\s*\n(.*?)(?:\n\n|\Z)',
            r'Description:?\s*\n(.*?)(?:\n\n|\Z)',
            r'Completion Text:?\s*\n(.*?)(?:\n\n|\Z)'
        ]
        
        all_text = ""
        for section_pattern in text_sections:
            match = re.search(section_pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                all_text += " " + match.group(1)
        
        if all_text:
            # Look for profession mentions
            text_lower = all_text.lower()
            
            for profession, skill_id in self.professions.items():
                if profession in text_lower:
                    hints['detected_professions'].append(profession)
                    
                    # Look for skill level hints near the profession mention
                    level_pattern = rf'{re.escape(profession)}[^.]*?(\d+)'
                    level_match = re.search(level_pattern, text_lower)
                    if level_match:
                        level = int(level_match.group(1))
                        if 1 <= level <= 450:  # Reasonable skill levels
                            hints['skill_level_hints'][profession] = level
            
            # Check aliases
            for alias, profession in self.profession_aliases.items():
                if alias in text_lower and profession not in hints['detected_professions']:
                    hints['detected_professions'].append(profession)
        
        return hints
    
    def _parse_objective_professions(self, content: str) -> Dict:
        """Parse objectives for profession-related tasks"""
        prof_data = {
            'detected_professions': [],
            'skill_level_hints': {}
        }
        
        # Get objectives section
        obj_section = re.search(r'OBJECTIVES?:?\s*\n(.*?)(?:\n\nTURN-?IN|\n\nGROUND|\n\nDATABASE|\Z)', 
                               content, re.DOTALL | re.IGNORECASE)
        
        if obj_section:
            obj_text = obj_section.group(1).lower()
            
            # Look for profession-related objectives
            prof_actions = {
                'alchemy': ['create potion', 'brew', 'transmute', 'flask', 'elixir'],
                'blacksmithing': ['forge', 'smith', 'craft weapon', 'craft armor', 'smelt'],
                'enchanting': ['enchant', 'disenchant', 'dust', 'essence', 'shard'],
                'engineering': ['craft bomb', 'create gadget', 'build', 'tinker', 'explosive'],
                'leatherworking': ['craft leather', 'skin', 'hide', 'leather armor'],
                'tailoring': ['weave', 'sew', 'craft cloth', 'embroider', 'cloth armor'],
                'jewelcrafting': ['cut gem', 'socket', 'jewelry', 'ring', 'necklace'],
                'inscription': ['inscribe', 'glyph', 'scroll', 'research', 'ink'],
                'herbalism': ['pick', 'gather herb', 'find plant', 'lotus', 'flower'],
                'mining': ['mine', 'extract ore', 'vein', 'deposit', 'quarry'],
                'skinning': ['skin beast', 'leather from', 'hide from', 'pelt'],
                'cooking': ['cook', 'recipe', 'ingredient', 'seasoning', 'prepare food'],
                'first aid': ['bandage', 'heal', 'treat wound', 'first aid'],
                'fishing': ['catch fish', 'fishing', 'bait', 'lure', 'school of']
            }
            
            for profession, actions in prof_actions.items():
                if any(action in obj_text for action in actions):
                    prof_data['detected_professions'].append(profession)
                    
                    # Try to infer skill level from objective difficulty
                    if any(word in obj_text for word in ['master', 'expert', 'artisan']):
                        prof_data['skill_level_hints'][profession] = 300
                    elif any(word in obj_text for word in ['journeyman', 'advanced']):
                        prof_data['skill_level_hints'][profession] = 150
                    elif any(word in obj_text for word in ['apprentice', 'basic']):
                        prof_data['skill_level_hints'][profession] = 75
        
        return prof_data
    
    def _parse_trainer_interactions(self, content: str) -> Dict:
        """Parse NPC interactions with profession trainers"""
        trainer_data = {
            'detected_professions': [],
            'class_hints': []
        }
        
        # Look for trainer NPCs
        npc_sections = [
            r'QUEST GIVER:.*?\n.*?(.+?)\s*\(ID:\s*\d+\)',
            r'TURN-?IN NPC:.*?\n.*?(.+?)\s*\(ID:\s*\d+\)',
            r'NPC:.*?(.+?)\s*\(ID:\s*\d+\)'
        ]
        
        for section_pattern in npc_sections:
            matches = re.findall(section_pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                npc_name = match.strip().lower()
                
                # Check for profession trainer keywords
                trainer_keywords = {
                    'alchemy': ['alchemist', 'potion', 'brew'],
                    'blacksmithing': ['blacksmith', 'smith', 'forge', 'weaponsmith', 'armorsmith'],
                    'enchanting': ['enchanter', 'magic', 'mystic'],
                    'engineering': ['engineer', 'tinker', 'gadget'],
                    'leatherworking': ['leatherworker', 'tanner', 'skinner'],
                    'tailoring': ['tailor', 'seamstress', 'weaver'],
                    'jewelcrafting': ['jeweler', 'gem', 'cutter'],
                    'inscription': ['scribe', 'inscriber', 'scholar'],
                    'herbalism': ['herbalist', 'botanist', 'gatherer'],
                    'mining': ['miner', 'prospector', 'excavator'],
                    'cooking': ['chef', 'cook', 'baker'],
                    'first aid': ['medic', 'healer', 'surgeon'],
                    'fishing': ['fisherman', 'angler']
                }
                
                for profession, keywords in trainer_keywords.items():
                    if any(keyword in npc_name for keyword in keywords):
                        trainer_data['detected_professions'].append(profession)
                        break
                
                # Check for class trainer keywords
                class_keywords = {
                    'warrior': ['warrior', 'fighter', 'guard', 'soldier'],
                    'paladin': ['paladin', 'knight', 'crusader'],
                    'hunter': ['hunter', 'ranger', 'tracker'],
                    'rogue': ['rogue', 'assassin', 'thief', 'spy'],
                    'priest': ['priest', 'cleric', 'healer'],
                    'shaman': ['shaman', 'spirit', 'elemental'],
                    'mage': ['mage', 'wizard', 'sorcerer', 'arcane'],
                    'warlock': ['warlock', 'demon', 'shadow'],
                    'druid': ['druid', 'nature', 'grove']
                }
                
                for class_name, keywords in class_keywords.items():
                    if any(keyword in npc_name for keyword in keywords):
                        trainer_data['class_hints'].append(class_name)
                        break
        
        return trainer_data
    
    def _consolidate_requirements(self, prof_data: Dict) -> Dict:
        """Consolidate and validate profession requirements"""
        # Remove duplicates
        if 'detected_professions' in prof_data:
            prof_data['detected_professions'] = list(set(prof_data['detected_professions']))
        
        if 'class_hints' in prof_data:
            prof_data['class_hints'] = list(set(prof_data['class_hints']))
        
        # If we have detected professions but no explicit requirement, create one
        if prof_data.get('detected_professions') and not prof_data.get('required_skill'):
            # Use the most mentioned profession
            primary_prof = prof_data['detected_professions'][0]
            skill_id = self.professions.get(primary_prof)
            
            if skill_id:
                # Use skill level hint or default to 1
                skill_level = prof_data.get('skill_level_hints', {}).get(primary_prof, 1)
                prof_data['required_skill'] = {'skill_id': skill_id, 'level': skill_level}
        
        return prof_data
    
    def generate_profession_lua(self, prof_data: Dict) -> Dict[str, str]:
        """Generate Lua values for profession fields"""
        lua_fields = {}
        
        # Field 18: requiredSkill {skillId, value}
        if prof_data.get('required_skill'):
            skill = prof_data['required_skill']
            lua_fields['requiredSkill'] = f"{{{skill['skill_id']},{skill['level']}}}"
        else:
            lua_fields['requiredSkill'] = "nil"
        
        # Field 28: requiredSpell
        if prof_data.get('required_spell'):
            lua_fields['requiredSpell'] = str(prof_data['required_spell'])
        else:
            lua_fields['requiredSpell'] = "nil"
        
        # Field 29: requiredSpecialization
        if prof_data.get('required_specialization'):
            lua_fields['requiredSpecialization'] = str(prof_data['required_specialization'])
        else:
            lua_fields['requiredSpecialization'] = "nil"
        
        return lua_fields
    
    def get_profession_name(self, skill_id: int) -> Optional[str]:
        """Get profession name from skill ID"""
        for name, sid in self.professions.items():
            if sid == skill_id:
                return name.title()
        return None
    
    def get_summary(self) -> Dict:
        """Get parsing summary"""
        total_parsed = len(self.parsed_professions)
        
        with_skill_req = sum(1 for prof in self.parsed_professions.values() if prof.get('required_skill'))
        with_spell_req = sum(1 for prof in self.parsed_professions.values() if prof.get('required_spell'))
        with_detected = sum(1 for prof in self.parsed_professions.values() if prof.get('detected_professions'))
        
        # Count by profession type
        profession_counts = {}
        for prof_data in self.parsed_professions.values():
            for profession in prof_data.get('detected_professions', []):
                profession_counts[profession] = profession_counts.get(profession, 0) + 1
        
        return {
            'total_parsed': total_parsed,
            'with_skill_requirements': with_skill_req,
            'with_spell_requirements': with_spell_req,
            'with_detected_professions': with_detected,
            'profession_distribution': profession_counts,
            'parse_errors': len(self.parse_errors)
        }

def main():
    """Test the profession parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python profession_parser.py <submission_file>")
        sys.exit(1)
    
    parser = ProfessionParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract quest ID if present
    quest_id = None
    id_match = re.search(r'Quest ID:\s*(\d+)', content)
    if id_match:
        quest_id = int(id_match.group(1))
    
    prof_data = parser.parse(content, quest_id)
    
    print(f"\nQuest {quest_id} Profession Analysis:")
    
    if prof_data.get('required_skill'):
        skill = prof_data['required_skill']
        skill_name = parser.get_profession_name(skill['skill_id'])
        print(f"Required Skill: {skill_name} ({skill['skill_id']}) Level {skill['level']}")
    
    if prof_data.get('required_spell'):
        print(f"Required Spell: {prof_data['required_spell']}")
    
    if prof_data.get('detected_professions'):
        print(f"Detected Professions: {', '.join(prof_data['detected_professions'])}")
    
    if prof_data.get('skill_level_hints'):
        print(f"Skill Level Hints:")
        for prof, level in prof_data['skill_level_hints'].items():
            print(f"  {prof}: {level}")
    
    if prof_data.get('class_hints'):
        print(f"Class Hints: {', '.join(prof_data['class_hints'])}")
    
    # Show Lua output
    lua_fields = parser.generate_profession_lua(prof_data)
    print(f"\nLua Fields:")
    for field, value in lua_fields.items():
        print(f"  {field}: {value}")
    
    print(f"\nSummary: {json.dumps(parser.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()