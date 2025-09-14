#!/usr/bin/env python3
"""
Spell Parser - Parse spell requirements and spell-based objectives
Handles Fields 27-28: extraObjectives (spells) and requiredSpell
"""

import re
import logging
from typing import Dict, List, Optional, Tuple


class SpellParser:
    """
    Parses spell requirements and spell-based quest objectives
    Field 27: extraObjectives - {{spellId, "text"},...}
    Field 28: requiredSpell - int (spell ID required to start quest)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common spell-related keywords
        self.spell_keywords = [
            'cast',
            'channel',
            'use',
            'activate',
            'perform',
            'ritual',
            'enchant',
            'dispel',
            'purify',
            'cleanse',
            'bless',
            'curse',
            'hex',
            'polymorph',
            'teleport',
            'portal',
            'summon',
            'resurrect',
            'heal',
            'buff',
            'debuff',
        ]
        
        # Known spell names to IDs (would be expanded with full spell database)
        self.known_spells = {
            # Teleport spells
            'teleport to stormwind': 3561,
            'teleport to orgrimmar': 3567,
            'teleport to ironforge': 3562,
            'teleport to undercity': 3563,
            'teleport to darnassus': 3565,
            'teleport to thunder bluff': 3566,
            
            # Portal spells
            'portal to stormwind': 10059,
            'portal to orgrimmar': 11417,
            'portal to ironforge': 11416,
            'portal to undercity': 11418,
            'portal to darnassus': 11419,
            'portal to thunder bluff': 11420,
            
            # Common quest spells
            'lay on hands': 633,
            'divine shield': 642,
            'blessing of might': 19740,
            'blessing of wisdom': 19742,
            'blessing of kings': 20217,
            'mark of the wild': 1126,
            'arcane intellect': 1459,
            'power word fortitude': 1243,
            'power word shield': 17,
            'renew': 139,
            'rejuvenation': 774,
            'regrowth': 8936,
            'healing touch': 5185,
            'flash heal': 2061,
            'greater heal': 2060,
            'holy light': 635,
            'flash of light': 19750,
            
            # Resurrection spells
            'resurrection': 2006,
            'redemption': 7328,
            'ancestral spirit': 2008,
            'rebirth': 20484,
            
            # Dispel/cleanse spells
            'dispel magic': 527,
            'purify': 1152,
            'cleanse': 4987,
            'remove curse': 475,
            'remove poison': 8946,
            'abolish poison': 2893,
            'cure poison': 8946,
            'cure disease': 528,
            'abolish disease': 552,
            
            # Class-specific abilities
            'stealth': 1784,
            'vanish': 1856,
            'shadowmeld': 58984,
            'prowl': 5215,
            'track beasts': 1494,
            'track humanoids': 19883,
            'track undead': 19884,
            'find herbs': 2383,
            'find minerals': 2580,
            'detect magic': 2855,
            'detect invisibility': 132,
            'detect greater invisibility': 11743,
        }
        
        # Class spell indicators
        self.class_spell_indicators = {
            'paladin': ['lay on hands', 'divine shield', 'blessing', 'redemption', 'cleanse', 'holy light'],
            'priest': ['power word', 'renew', 'heal', 'resurrection', 'dispel magic', 'purify'],
            'mage': ['polymorph', 'teleport', 'portal', 'arcane', 'detect magic', 'conjure'],
            'warlock': ['summon', 'curse', 'fear', 'banish', 'enslave', 'ritual'],
            'druid': ['mark of the wild', 'rejuvenation', 'regrowth', 'rebirth', 'innervate'],
            'shaman': ['ancestral spirit', 'totemic', 'lightning', 'earth shock', 'purge'],
            'rogue': ['stealth', 'vanish', 'pickpocket', 'lockpicking', 'poison'],
            'warrior': ['charge', 'taunt', 'battle shout', 'rend', 'execute'],
            'hunter': ['track', 'tame', 'beast', 'aimed shot', 'hunter\'s mark'],
            'death knight': ['death grip', 'raise dead', 'death and decay', 'rune'],
        }
    
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse spell requirements and objectives from quest content
        
        Returns:
            Dictionary containing:
            - extra_objectives: List of spell objectives
            - required_spell: Spell ID required to start quest
            - class_requirement: Detected class requirement
        """
        result = {
            'extra_objectives': [],  # Field 27
            'required_spell': None,  # Field 28
            'detected_spells': [],
            'class_requirement': None,
            'confidence': 0
        }
        
        # Parse spell objectives
        result['extra_objectives'] = self._parse_spell_objectives(content)
        
        # Parse required spell
        result['required_spell'] = self._parse_required_spell(content)
        
        # Detect all spell references
        result['detected_spells'] = self._detect_spell_references(content)
        
        # Determine class requirement from spells
        result['class_requirement'] = self._determine_class_requirement(result['detected_spells'])
        
        # Calculate confidence
        result['confidence'] = self._calculate_confidence(result)
        
        return result
    
    def _parse_spell_objectives(self, content: str) -> List[Tuple[int, str]]:
        """
        Parse spell-based objectives
        Returns list of (spellId, "objective text") tuples
        """
        objectives = []
        content_lower = content.lower()
        
        # Pattern 1: Direct spell casting objectives
        cast_patterns = [
            r'cast\s+([a-z\s]+)\s+(?:on|at|to)\s+(.+?)(?:\.|,|\n|$)',
            r'use\s+([a-z\s]+)\s+(?:on|at|to)\s+(.+?)(?:\.|,|\n|$)',
            r'channel\s+([a-z\s]+)\s+(?:for|on|at)\s+(.+?)(?:\.|,|\n|$)',
            r'perform\s+(?:the\s+)?([a-z\s]+)\s+ritual',
        ]
        
        for pattern in cast_patterns:
            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                spell_name = match.group(1).strip()
                target = match.group(2).strip() if match.lastindex > 1 else ''
                
                # Try to find spell ID
                spell_id = self._get_spell_id(spell_name)
                
                if spell_id:
                    objective_text = f"Cast {spell_name.title()}"
                    if target:
                        objective_text += f" on {target}"
                    
                    objectives.append((spell_id, objective_text))
        
        # Pattern 2: Spell use in objectives section
        obj_pattern = r'OBJECTIVE[S]?:?\s*\n(.*?)(?:\n\n|TURN-IN|REWARD|$)'
        obj_match = re.search(obj_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if obj_match:
            objectives_text = obj_match.group(1)
            
            # Look for spell-related objectives
            for keyword in self.spell_keywords:
                if keyword in objectives_text.lower():
                    lines = objectives_text.split('\n')
                    for line in lines:
                        if keyword in line.lower():
                            # Extract spell name
                            spell_match = re.search(rf'{keyword}\s+([A-Za-z\s]+?)(?:\s+on|\s+to|\s+at|\.|,|$)', line, re.IGNORECASE)
                            if spell_match:
                                spell_name = spell_match.group(1).strip()
                                spell_id = self._get_spell_id(spell_name)
                                
                                if spell_id:
                                    clean_line = line.strip('- •·').strip()
                                    objectives.append((spell_id, clean_line))
        
        # Pattern 3: Item use that casts spell
        item_use_pattern = r'use\s+(?:the\s+)?(.+?)\s+(?:to\s+)?(?:cast|summon|create)\s+(.+?)(?:\.|,|\n|$)'
        item_matches = re.finditer(item_use_pattern, content_lower)
        
        for match in item_matches:
            item_name = match.group(1).strip()
            spell_effect = match.group(2).strip()
            
            # Items that cast spells would have spell IDs
            spell_id = self._get_spell_id(spell_effect)
            if spell_id:
                objective_text = f"Use {item_name.title()} to {match.group(0)}"
                objectives.append((spell_id, objective_text))
        
        return objectives
    
    def _parse_required_spell(self, content: str) -> Optional[int]:
        """
        Parse spell requirement to start quest
        Returns spell ID or None
        """
        # Pattern 1: Direct spell requirement
        patterns = [
            r'requires?:?\s+(?:knowing|learning|having)\s+([a-z\s]+)\s+spell',
            r'must\s+(?:know|have|learn)\s+([a-z\s]+)\s+(?:spell|ability)',
            r'prerequisite:?\s+([a-z\s]+)\s+(?:spell|ability)',
            r'need\s+([a-z\s]+)\s+(?:spell|ability)\s+to\s+(?:start|accept|begin)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                spell_name = match.group(1).strip()
                spell_id = self._get_spell_id(spell_name)
                
                if spell_id:
                    self.logger.info(f"Found required spell: {spell_name} (ID: {spell_id})")
                    return spell_id
        
        # Pattern 2: Class spell requirements
        class_patterns = [
            r'(?:paladin|priest|mage|warlock|druid|shaman|rogue|warrior|hunter|death knight)\s+only',
            r'requires?\s+(?:paladin|priest|mage|warlock|druid|shaman|rogue|warrior|hunter|death knight)',
        ]
        
        for pattern in class_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Class-specific quests might require a class spell
                class_name = re.findall(r'(paladin|priest|mage|warlock|druid|shaman|rogue|warrior|hunter|death knight)', 
                                       match.group(0), re.IGNORECASE)[0]
                
                # Return a class-specific spell ID as requirement
                # This would need to be mapped to actual class-defining spells
                return self._get_class_spell_requirement(class_name.lower())
        
        return None
    
    def _detect_spell_references(self, content: str) -> List[Dict]:
        """Detect all spell references in content"""
        detected = []
        content_lower = content.lower()
        
        # Check known spells
        for spell_name, spell_id in self.known_spells.items():
            if spell_name in content_lower:
                detected.append({
                    'name': spell_name,
                    'id': spell_id,
                    'context': self._get_spell_context(content, spell_name)
                })
        
        # Check spell keywords with context
        for keyword in self.spell_keywords:
            pattern = rf'{keyword}\s+([a-z\s]+?)(?:\s+on|\s+to|\s+at|\.|,|\n|$)'
            matches = re.finditer(pattern, content_lower)
            
            for match in matches:
                potential_spell = match.group(1).strip()
                if len(potential_spell) > 2:  # Filter out very short matches
                    spell_id = self._get_spell_id(potential_spell)
                    
                    if spell_id and not any(d['id'] == spell_id for d in detected):
                        detected.append({
                            'name': potential_spell,
                            'id': spell_id,
                            'context': keyword
                        })
        
        return detected
    
    def _determine_class_requirement(self, detected_spells: List[Dict]) -> Optional[str]:
        """Determine if quest requires specific class based on spells"""
        if not detected_spells:
            return None
        
        # Count class indicators
        class_scores = {}
        
        for spell in detected_spells:
            spell_name = spell['name'].lower()
            
            for class_name, indicators in self.class_spell_indicators.items():
                for indicator in indicators:
                    if indicator in spell_name:
                        class_scores[class_name] = class_scores.get(class_name, 0) + 1
        
        # Return class with highest score if significant
        if class_scores:
            best_class = max(class_scores, key=class_scores.get)
            if class_scores[best_class] >= 2:  # Need at least 2 indicators
                return best_class
        
        return None
    
    def _get_spell_id(self, spell_name: str) -> Optional[int]:
        """Get spell ID from spell name"""
        spell_name_lower = spell_name.lower().strip()
        
        # Check exact matches
        if spell_name_lower in self.known_spells:
            return self.known_spells[spell_name_lower]
        
        # Check partial matches
        for known_spell, spell_id in self.known_spells.items():
            if spell_name_lower in known_spell or known_spell in spell_name_lower:
                return spell_id
        
        # Generate placeholder ID for unknown spells (would query spell DB)
        # In production, this would look up a complete spell database
        if any(keyword in spell_name_lower for keyword in self.spell_keywords):
            # Return a high placeholder ID that indicates unknown spell
            return 900000 + hash(spell_name_lower) % 10000
        
        return None
    
    def _get_class_spell_requirement(self, class_name: str) -> Optional[int]:
        """Get a representative spell ID for class requirement"""
        # These would be actual class-defining spell IDs
        class_spells = {
            'paladin': 19750,  # Flash of Light
            'priest': 2061,    # Flash Heal
            'mage': 1459,      # Arcane Intellect
            'warlock': 697,    # Summon Voidwalker
            'druid': 5487,     # Bear Form
            'shaman': 324,     # Lightning Shield
            'rogue': 1784,     # Stealth
            'warrior': 2457,   # Battle Stance
            'hunter': 1494,    # Track Beasts
            'death knight': 48265,  # Death's Advance
        }
        
        return class_spells.get(class_name)
    
    def _get_spell_context(self, content: str, spell_name: str) -> str:
        """Get context around spell mention"""
        index = content.lower().find(spell_name.lower())
        if index == -1:
            return ""
        
        # Get 50 chars before and after
        start = max(0, index - 50)
        end = min(len(content), index + len(spell_name) + 50)
        
        context = content[start:end]
        return context.replace('\n', ' ').strip()
    
    def _calculate_confidence(self, result: Dict) -> int:
        """Calculate confidence in spell parsing"""
        confidence = 0
        
        # Points for finding spell objectives
        if result['extra_objectives']:
            confidence += 30
            # Extra points for multiple objectives
            confidence += min(len(result['extra_objectives']) * 10, 30)
        
        # Points for required spell
        if result['required_spell']:
            confidence += 20
        
        # Points for detected spells
        if result['detected_spells']:
            confidence += min(len(result['detected_spells']) * 5, 20)
        
        # Points for class requirement detection
        if result['class_requirement']:
            confidence += 10
        
        return min(confidence, 100)
    
    def generate_lua_entries(self, spell_data: Dict) -> Dict:
        """Generate Lua code for spell fields"""
        entries = {}
        
        # Field 27: extraObjectives
        if spell_data['extra_objectives']:
            objectives = []
            for spell_id, text in spell_data['extra_objectives']:
                objectives.append(f'{{{spell_id},"{text}"}}')
            entries['extraObjectives'] = '{' + ','.join(objectives) + '}'
        else:
            entries['extraObjectives'] = 'nil'
        
        # Field 28: requiredSpell
        if spell_data['required_spell']:
            entries['requiredSpell'] = str(spell_data['required_spell'])
        else:
            entries['requiredSpell'] = 'nil'
        
        return entries


def main():
    """Test the spell parser"""
    parser = SpellParser()
    
    # Test spell quest
    test_content = """
    Quest: The Cleansing Ritual
    Requirements: Must know Dispel Magic spell
    
    OBJECTIVES:
    - Cast Dispel Magic on 5 Cursed Villagers
    - Use Purify to cleanse the corrupted water
    - Channel the Cleansing Ritual at the altar
    - Cast Blessing of Kings on the village elder
    
    This quest requires a Paladin or Priest to complete.
    You must use your holy powers to save the village.
    """
    
    result = parser.parse(test_content, quest_id=12345)
    
    print("Spell Parser Results:")
    print(f"Extra Objectives: {result['extra_objectives']}")
    print(f"Required Spell: {result['required_spell']}")
    print(f"Detected Spells: {result['detected_spells']}")
    print(f"Class Requirement: {result['class_requirement']}")
    print(f"Confidence: {result['confidence']}%")
    
    lua_entries = parser.generate_lua_entries(result)
    print(f"\nLua Entries:")
    print(f"Field 27 (extraObjectives): {lua_entries['extraObjectives']}")
    print(f"Field 28 (requiredSpell): {lua_entries['requiredSpell']}")


if __name__ == "__main__":
    main()