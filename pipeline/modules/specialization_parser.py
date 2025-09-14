#!/usr/bin/env python3
"""
Specialization Parser - Parse talent specialization requirements
Handles Field 29: requiredSpecialization - talent spec requirements
"""

import re
import logging
from typing import Dict, Optional, List, Tuple


class SpecializationParser:
    """
    Parses talent specialization requirements for quests
    Field 29 format: int specialization ID or nil
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # WoW 3.3.5 Specialization mappings
        self.specializations = {
            # Death Knight
            'blood': 398,
            'blood death knight': 398,
            'blood dk': 398,
            'frost': 399,
            'frost death knight': 399,
            'frost dk': 399,
            'unholy': 400,
            'unholy death knight': 400,
            'unholy dk': 400,
            
            # Druid
            'balance': 283,
            'balance druid': 283,
            'moonkin': 283,
            'boomkin': 283,
            'feral': 281,
            'feral druid': 281,
            'feral combat': 281,
            'cat': 281,
            'bear': 281,
            'restoration druid': 282,
            'resto druid': 282,
            'tree': 282,
            
            # Hunter
            'beast mastery': 361,
            'beast master': 361,
            'bm hunter': 361,
            'marksmanship': 363,
            'marksman': 363,
            'mm hunter': 363,
            'survival': 362,
            'survival hunter': 362,
            'sv hunter': 362,
            
            # Mage
            'arcane': 81,
            'arcane mage': 81,
            'fire': 41,
            'fire mage': 41,
            'frost mage': 61,
            
            # Paladin
            'holy paladin': 382,
            'holy pally': 382,
            'protection paladin': 383,
            'prot paladin': 383,
            'prot pally': 383,
            'retribution': 381,
            'ret paladin': 381,
            'ret pally': 381,
            
            # Priest
            'discipline': 201,
            'disc priest': 201,
            'holy priest': 202,
            'holy': 202,
            'shadow': 203,
            'shadow priest': 203,
            'spriest': 203,
            
            # Rogue
            'assassination': 182,
            'assassination rogue': 182,
            'combat': 181,
            'combat rogue': 181,
            'subtlety': 183,
            'sub rogue': 183,
            
            # Shaman
            'elemental': 261,
            'elemental shaman': 261,
            'ele shaman': 261,
            'enhancement': 263,
            'enhance shaman': 263,
            'enh shaman': 263,
            'restoration shaman': 262,
            'resto shaman': 262,
            
            # Warlock
            'affliction': 302,
            'affliction warlock': 302,
            'aff lock': 302,
            'demonology': 303,
            'demo warlock': 303,
            'demo lock': 303,
            'destruction': 301,
            'destro warlock': 301,
            'destro lock': 301,
            
            # Warrior
            'arms': 161,
            'arms warrior': 161,
            'fury': 164,
            'fury warrior': 164,
            'protection warrior': 163,
            'prot warrior': 163,
            'tank': 163,
        }
        
        # Talent-specific abilities that indicate spec requirements
        self.spec_abilities = {
            # Death Knight
            'heart strike': 398,  # Blood
            'dancing rune weapon': 398,  # Blood
            'howling blast': 399,  # Frost
            'frost strike': 399,  # Frost
            'scourge strike': 400,  # Unholy
            'unholy presence': 400,  # Unholy
            
            # Druid
            'starfall': 283,  # Balance
            'moonkin form': 283,  # Balance
            'mangle': 281,  # Feral
            'swipe': 281,  # Feral
            'wild growth': 282,  # Restoration
            'tree of life': 282,  # Restoration
            
            # Hunter
            'bestial wrath': 361,  # Beast Mastery
            'chimera shot': 363,  # Marksmanship
            'explosive shot': 362,  # Survival
            'black arrow': 362,  # Survival
            
            # Mage
            'arcane barrage': 81,  # Arcane
            'arcane power': 81,  # Arcane
            'living bomb': 41,  # Fire
            'pyroblast': 41,  # Fire
            'deep freeze': 61,  # Frost
            'ice barrier': 61,  # Frost
            
            # Paladin
            'holy shock': 382,  # Holy
            'beacon of light': 382,  # Holy
            'avenger\'s shield': 383,  # Protection
            'hammer of the righteous': 383,  # Protection
            'crusader strike': 381,  # Retribution
            'divine storm': 381,  # Retribution
            
            # Priest
            'penance': 201,  # Discipline
            'pain suppression': 201,  # Discipline
            'circle of healing': 202,  # Holy
            'guardian spirit': 202,  # Holy
            'mind flay': 203,  # Shadow
            'shadowform': 203,  # Shadow
            
            # Rogue
            'mutilate': 182,  # Assassination
            'envenom': 182,  # Assassination
            'killing spree': 181,  # Combat
            'adrenaline rush': 181,  # Combat
            'shadowstep': 183,  # Subtlety
            'shadow dance': 183,  # Subtlety
            
            # Shaman
            'thunderstorm': 261,  # Elemental
            'lava burst': 261,  # Elemental
            'feral spirit': 263,  # Enhancement
            'spirit walk': 263,  # Enhancement
            'riptide': 262,  # Restoration
            'earth shield': 262,  # Restoration
            
            # Warlock
            'haunt': 302,  # Affliction
            'unstable affliction': 302,  # Affliction
            'metamorphosis': 303,  # Demonology
            'demonic empowerment': 303,  # Demonology
            'chaos bolt': 301,  # Destruction
            'shadowfury': 301,  # Destruction
            
            # Warrior
            'bladestorm': 161,  # Arms
            'mortal strike': 161,  # Arms
            'bloodthirst': 164,  # Fury
            'rampage': 164,  # Fury
            'shockwave': 163,  # Protection
            'vigilance': 163,  # Protection
        }
        
        # Spec requirement indicators
        self.spec_indicators = [
            'talent',
            'specialization',
            'spec',
            'tree',
            'build',
            'mastery',
            'requires.*points in',
            'deep.*tree',
            '51 point',
            'talent build',
        ]
    
    def parse(self, content: str, quest_id: int = None) -> Optional[int]:
        """
        Parse specialization requirements from quest content
        
        Args:
            content: Quest submission text
            quest_id: Quest ID for reference
            
        Returns:
            Specialization ID or None if no spec requirements
        """
        spec_id = None
        
        # Check for spec requirements
        spec_id = self._extract_spec_requirement(content)
        
        if spec_id:
            self.logger.info(f"Found spec requirement: {spec_id}")
        
        return spec_id
    
    def _extract_spec_requirement(self, content: str) -> Optional[int]:
        """Extract specialization requirement from content"""
        content_lower = content.lower()
        
        # Method 1: Direct spec mention
        for spec_name, spec_id in self.specializations.items():
            # Look for patterns like "requires Balance spec"
            patterns = [
                f'requires?\\s+{spec_name}',
                f'{spec_name}\\s+only',
                f'{spec_name}\\s+specialization',
                f'{spec_name}\\s+spec',
                f'{spec_name}\\s+talent',
                f'must be\\s+{spec_name}',
                f'only available to\\s+{spec_name}',
                f'exclusive to\\s+{spec_name}',
            ]
            
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return spec_id
        
        # Method 2: Check for spec-specific abilities
        for ability, spec_id in self.spec_abilities.items():
            patterns = [
                f'requires?\\s+{ability}',
                f'must have\\s+{ability}',
                f'need\\s+{ability}',
                f'use\\s+{ability}',
                f'cast\\s+{ability}',
            ]
            
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return spec_id
        
        # Method 3: Talent point requirements
        talent_pattern = r'requires?\s+(\d+)\s+points?\s+in\s+(\w+)'
        talent_match = re.search(talent_pattern, content_lower)
        
        if talent_match:
            points = int(talent_match.group(1))
            tree_name = talent_match.group(2)
            
            # Deep talent requirements (31+ points) indicate spec requirement
            if points >= 31:
                # Try to match tree name to spec
                for spec_name, spec_id in self.specializations.items():
                    if tree_name in spec_name:
                        return spec_id
        
        # Method 4: Check in requirements section
        req_pattern = r'REQUIREMENT[S]?:?\s*\n(.*?)(?:\n\n|OBJECTIVE|TURN-IN|$)'
        req_match = re.search(req_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if req_match:
            requirements = req_match.group(1).lower()
            
            # Check for spec indicators
            for indicator in self.spec_indicators:
                if re.search(indicator, requirements):
                    # Try to find associated spec
                    for spec_name, spec_id in self.specializations.items():
                        if spec_name in requirements:
                            return spec_id
        
        # Method 5: Check class trainer quests
        if 'class trainer' in content_lower or 'trainer quest' in content_lower:
            # Look for spec-specific trainer quests
            for spec_name, spec_id in self.specializations.items():
                if spec_name in content_lower:
                    # Verify it's a trainer quest for this spec
                    patterns = [
                        f'{spec_name}.*trainer',
                        f'trainer.*{spec_name}',
                        f'learn.*{spec_name}',
                        f'{spec_name}.*quest',
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, content_lower):
                            return spec_id
        
        return None
    
    def validate_spec_id(self, spec_id: int) -> bool:
        """Validate if a spec ID is valid"""
        valid_ids = set(self.specializations.values())
        return spec_id in valid_ids
    
    def get_spec_name(self, spec_id: int) -> Optional[str]:
        """Get spec name from ID"""
        for name, id_val in self.specializations.items():
            if id_val == spec_id:
                # Return the most common name (first match)
                return name.title()
        return None
    
    def generate_lua_entry(self, spec_id: Optional[int]) -> str:
        """Generate Lua code for requiredSpecialization field"""
        if spec_id is None:
            return "nil"
        
        return str(spec_id)
    
    def detect_class_from_spec(self, spec_id: int) -> Optional[str]:
        """Detect class from specialization ID"""
        spec_ranges = {
            (398, 400): 'Death Knight',
            (281, 283): 'Druid',
            (361, 363): 'Hunter',
            (41, 81): 'Mage',
            (381, 383): 'Paladin',
            (201, 203): 'Priest',
            (181, 183): 'Rogue',
            (261, 263): 'Shaman',
            (301, 303): 'Warlock',
            (161, 164): 'Warrior',
        }
        
        for (min_id, max_id), class_name in spec_ranges.items():
            if min_id <= spec_id <= max_id:
                return class_name
        
        return None


def main():
    """Test the specialization parser"""
    parser = SpecializationParser()
    
    # Test with spec requirement
    test_content = """
    Quest: The Balance of Power
    
    REQUIREMENTS:
    - Must be a Balance Druid
    - Requires 51 points in Balance tree
    
    OBJECTIVES:
    Use Starfall to defeat 10 enemies
    
    This quest is only available to druids who have specialized
    in the Balance talent tree.
    """
    
    spec_id = parser.parse(test_content, quest_id=50001)
    
    if spec_id:
        print(f"Spec Requirement Found: {spec_id}")
        print(f"Spec Name: {parser.get_spec_name(spec_id)}")
        print(f"Class: {parser.detect_class_from_spec(spec_id)}")
        print(f"Lua Entry: {parser.generate_lua_entry(spec_id)}")
    else:
        print("No spec requirements found")


if __name__ == "__main__":
    main()