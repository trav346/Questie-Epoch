#!/usr/bin/env python3
"""
Submitter Metadata Parser - Extract and analyze submitter information
Critical for determining faction/race/class restrictions on quests
"""

import re
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path


class SubmitterMetadataParser:
    """
    Extracts metadata about quest submitters to determine restrictions
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Race mappings (bitmask values)
        self.races = {
            # Alliance races
            'human': 1,
            'dwarf': 4, 
            'night elf': 8,
            'nightelf': 8,
            'gnome': 64,
            'draenei': 1024,
            
            # Horde races
            'orc': 2,
            'undead': 16,
            'forsaken': 16,
            'tauren': 32,
            'troll': 128,
            'blood elf': 512,
            'bloodelf': 512,
        }
        
        # Class mappings (bitmask values)
        self.classes = {
            'warrior': 1,
            'paladin': 2,
            'hunter': 4,
            'rogue': 8,
            'priest': 16,
            'death knight': 32,
            'deathknight': 32,
            'dk': 32,
            'shaman': 64,
            'mage': 128,
            'warlock': 256,
            'druid': 1024,
        }
        
        # Faction detection
        self.alliance_races = {1, 4, 8, 64, 1024}  # Human, Dwarf, Night Elf, Gnome, Draenei
        self.horde_races = {2, 16, 32, 128, 512}  # Orc, Undead, Tauren, Troll, Blood Elf
        
        # Profession mappings
        self.professions = {
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
            'fishing': 356,
            'cooking': 185,
            'first aid': 129,
            'firstaid': 129,
        }
        
        # Track metadata across submissions
        self.submission_metadata = {}
        
    def parse(self, content: str, source_file: str = None) -> Dict:
        """
        Extract all submitter metadata from a submission
        
        Args:
            content: The submission text
            source_file: Path to the submission file (may contain metadata)
            
        Returns:
            Dictionary containing all extracted metadata
        """
        metadata = {
            'github_user': None,
            'character_name': None,
            'race': None,
            'race_id': None,
            'class': None,
            'class_id': None,
            'faction': None,
            'level': None,
            'professions': [],
            'profession_ids': [],
            'addon_version': None,
            'submission_date': None,
            'server': None,
            'zone': None,
            'language': 'enUS',  # Default
            'issue_number': None,
            'completion_status': None,  # partial/complete
            'confidence': 0  # 0-100 confidence in metadata
        }
        
        # Extract from filename if available
        if source_file:
            metadata.update(self._parse_filename_metadata(source_file))
        
        # Extract GitHub user
        metadata['github_user'] = self._extract_github_user(content)
        
        # Extract character info
        metadata['character_name'] = self._extract_character_name(content)
        metadata['race'], metadata['race_id'] = self._extract_race(content)
        metadata['class'], metadata['class_id'] = self._extract_class(content)
        metadata['level'] = self._extract_level(content)
        
        # Determine faction from race
        if metadata['race_id']:
            metadata['faction'] = self._determine_faction(metadata['race_id'])
        
        # Extract professions
        metadata['professions'], metadata['profession_ids'] = self._extract_professions(content)
        
        # Extract addon version
        metadata['addon_version'] = self._extract_addon_version(content)
        
        # Extract submission date
        metadata['submission_date'] = self._extract_submission_date(content)
        
        # Extract server/realm
        metadata['server'] = self._extract_server(content)
        
        # Extract zone
        metadata['zone'] = self._extract_zone(content)
        
        # Determine completion status
        metadata['completion_status'] = self._determine_completion_status(content)
        
        # Calculate confidence score
        metadata['confidence'] = self._calculate_confidence(metadata)
        
        # Store for cross-reference
        if metadata['github_user']:
            self._store_metadata(metadata)
        
        return metadata
    
    def _parse_filename_metadata(self, filepath: str) -> Dict:
        """Extract metadata from filename"""
        metadata = {}
        path = Path(filepath)
        filename = path.stem
        
        # Common format: issue_####_username_questname.txt
        if 'issue_' in filename:
            parts = filename.split('_')
            if len(parts) >= 2:
                try:
                    metadata['issue_number'] = int(parts[1])
                except:
                    pass
                
                # Username might be third part
                if len(parts) >= 3:
                    metadata['github_user'] = parts[2]
        
        return metadata
    
    def _extract_github_user(self, content: str) -> Optional[str]:
        """Extract GitHub username from submission"""
        patterns = [
            r'(?:submitted by|from|by):?\s*@?([a-zA-Z0-9\-_]+)',
            r'github\.com/([a-zA-Z0-9\-_]+)',
            r'@([a-zA-Z0-9\-_]+)',  # GitHub mention
            r'user:?\s*([a-zA-Z0-9\-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_character_name(self, content: str) -> Optional[str]:
        """Extract character name from submission"""
        patterns = [
            r'character:?\s*([A-Z][a-z]+(?:[A-Z][a-z]+)?)',  # CamelCase names
            r'player:?\s*([A-Z][a-z]+)',
            r'submitted by:?\s*([A-Z][a-z]+)\s*\(',  # "Submitted by Thrall (Orc Shaman)"
            r'name:?\s*([A-Z][a-z]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_race(self, content: str) -> tuple[Optional[str], Optional[int]]:
        """Extract character race"""
        content_lower = content.lower()
        
        for race_name, race_id in self.races.items():
            # Look for race mentions
            if race_name in content_lower:
                # Verify it's actually referring to player race
                patterns = [
                    f'\\b{race_name}\\s+(?:warrior|paladin|hunter|rogue|priest|death knight|shaman|mage|warlock|druid)',
                    f'\\bmy\\s+{race_name}\\b',
                    f'\\b(?:level|lvl|lv)\\s*\\d+\\s+{race_name}\\b',
                    f'\\b{race_name}\\s+(?:character|player)\\b',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, content_lower):
                        return race_name.replace(' ', '').title(), race_id
        
        return None, None
    
    def _extract_class(self, content: str) -> tuple[Optional[str], Optional[int]]:
        """Extract character class"""
        content_lower = content.lower()
        
        for class_name, class_id in self.classes.items():
            if class_name in content_lower:
                # Verify it's referring to player class
                patterns = [
                    f'\\b(?:human|orc|dwarf|night elf|undead|tauren|gnome|troll|blood elf|draenei)\\s+{class_name}\\b',
                    f'\\bmy\\s+{class_name}\\b',
                    f'\\b(?:level|lvl|lv)\\s*\\d+\\s+{class_name}\\b',
                    f'\\b{class_name}\\s+(?:character|player)\\b',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, content_lower):
                        return class_name.replace(' ', '').title(), class_id
        
        return None, None
    
    def _extract_level(self, content: str) -> Optional[int]:
        """Extract character level"""
        patterns = [
            r'(?:level|lvl|lv)[\s:]*(\d{1,2})',
            r'(\d{1,2})[\s]*(?:level|lvl)',
            r'\bl(?:evel|vl)?(\d{1,2})\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                level = int(match.group(1))
                if 1 <= level <= 80:  # Valid WoW level range
                    return level
        
        return None
    
    def _determine_faction(self, race_id: int) -> Optional[str]:
        """Determine faction from race ID"""
        if race_id in self.alliance_races:
            return 'Alliance'
        elif race_id in self.horde_races:
            return 'Horde'
        
        return None
    
    def _extract_professions(self, content: str) -> tuple[List[str], List[int]]:
        """Extract character professions"""
        found_profs = []
        found_ids = []
        content_lower = content.lower()
        
        for prof_name, prof_id in self.professions.items():
            if prof_name in content_lower:
                # Look for skill levels or mentions
                patterns = [
                    f'{prof_name}\\s*(?:\\(?(\\d{{1,3}})\\)?)?',
                    f'\\d{{1,3}}\\s+{prof_name}',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, content_lower):
                        found_profs.append(prof_name.title())
                        found_ids.append(prof_id)
                        break
        
        return found_profs, found_ids
    
    def _extract_addon_version(self, content: str) -> Optional[str]:
        """Extract Questie addon version"""
        patterns = [
            r'(?:addon |questie )?v(?:ersion)?:?\s*(v?[\d.]+)',
            r'v([\d.]+(?:\.\d+)?)',
            r'version\s*([\d.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_submission_date(self, content: str) -> Optional[str]:
        """Extract submission date"""
        # Look for date patterns
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Default to today if not found
        return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_server(self, content: str) -> Optional[str]:
        """Extract server/realm name"""
        patterns = [
            r'(?:server|realm):?\s*([A-Za-z\s]+)',
            r'on\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:server|realm)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Default to Epoch if not specified
        return "Project Epoch"
    
    def _extract_zone(self, content: str) -> Optional[str]:
        """Extract zone where quest was done"""
        # This would integrate with zone_mapper.py
        # For now, look for zone mentions
        zone_pattern = r'(?:zone|area|in):?\s*([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)'
        match = re.search(zone_pattern, content)
        if match:
            return match.group(1)
        
        return None
    
    def _determine_completion_status(self, content: str) -> str:
        """Determine if submission is partial or complete"""
        # Look for indicators of incomplete data
        incomplete_indicators = [
            'partial',
            'incomplete', 
            'in progress',
            'not finished',
            'couldn\'t complete',
            'unable to turn in',
            'missing',
            'unknown',
            '???',
        ]
        
        content_lower = content.lower()
        for indicator in incomplete_indicators:
            if indicator in content_lower:
                return 'partial'
        
        # Look for completion indicators
        complete_indicators = [
            'completed',
            'turned in',
            'finished',
            'quest complete',
            'reward received',
        ]
        
        for indicator in complete_indicators:
            if indicator in content_lower:
                return 'complete'
        
        # Default to unknown
        return 'unknown'
    
    def _calculate_confidence(self, metadata: Dict) -> int:
        """Calculate confidence score in metadata accuracy"""
        confidence = 0
        max_points = 100
        
        # Critical fields (50 points total)
        if metadata['github_user']:
            confidence += 10
        if metadata['race_id']:
            confidence += 15
        if metadata['class_id']:
            confidence += 15
        if metadata['faction']:
            confidence += 10
            
        # Important fields (30 points total)
        if metadata['character_name']:
            confidence += 10
        if metadata['level']:
            confidence += 10
        if metadata['addon_version']:
            confidence += 10
            
        # Nice to have (20 points total)
        if metadata['professions']:
            confidence += 5
        if metadata['server']:
            confidence += 5
        if metadata['zone']:
            confidence += 5
        if metadata['completion_status'] != 'unknown':
            confidence += 5
        
        return min(confidence, max_points)
    
    def _store_metadata(self, metadata: Dict):
        """Store metadata for cross-reference analysis"""
        user = metadata['github_user']
        if user not in self.submission_metadata:
            self.submission_metadata[user] = []
        
        self.submission_metadata[user].append({
            'race': metadata['race'],
            'class': metadata['class'],
            'faction': metadata['faction'],
            'level': metadata['level'],
            'professions': metadata['professions'],
            'server': metadata['server'],
            'date': metadata['submission_date'],
        })
    
    def analyze_submitter_patterns(self, quest_id: int = None) -> Dict:
        """
        Analyze patterns across all submitters for a quest
        
        Returns faction/race/class restrictions based on who submitted
        """
        analysis = {
            'total_submitters': len(self.submission_metadata),
            'factions': {'Alliance': 0, 'Horde': 0},
            'races': {},
            'classes': {},
            'likely_faction_specific': False,
            'likely_race_specific': False,
            'likely_class_specific': False,
            'confidence': 0
        }
        
        # Count factions, races, classes
        for user, submissions in self.submission_metadata.items():
            for sub in submissions:
                if sub['faction']:
                    analysis['factions'][sub['faction']] += 1
                if sub['race']:
                    analysis['races'][sub['race']] = analysis['races'].get(sub['race'], 0) + 1
                if sub['class']:
                    analysis['classes'][sub['class']] = analysis['classes'].get(sub['class'], 0) + 1
        
        # Determine restrictions
        total = analysis['total_submitters']
        if total >= 3:  # Need at least 3 submissions to analyze
            # Check faction specific
            if analysis['factions']['Alliance'] > 0 and analysis['factions']['Horde'] == 0:
                analysis['likely_faction_specific'] = 'Alliance'
                analysis['confidence'] = min(analysis['factions']['Alliance'] * 20, 100)
            elif analysis['factions']['Horde'] > 0 and analysis['factions']['Alliance'] == 0:
                analysis['likely_faction_specific'] = 'Horde'
                analysis['confidence'] = min(analysis['factions']['Horde'] * 20, 100)
            
            # Check race specific (if all same race)
            if len(analysis['races']) == 1:
                analysis['likely_race_specific'] = list(analysis['races'].keys())[0]
                analysis['confidence'] = min(total * 25, 100)
            
            # Check class specific (if all same class)
            if len(analysis['classes']) == 1:
                analysis['likely_class_specific'] = list(analysis['classes'].keys())[0]
                analysis['confidence'] = min(total * 25, 100)
        
        return analysis
    
    def get_restriction_bitmasks(self) -> Dict:
        """
        Get race and class restriction bitmasks based on submitter analysis
        """
        analysis = self.analyze_submitter_patterns()
        
        restrictions = {
            'requiredRaces': None,
            'requiredClasses': None,
            'friendlyToFaction': None,
        }
        
        # Set faction restriction
        if analysis['likely_faction_specific'] == 'Alliance':
            restrictions['requiredRaces'] = 77  # Alliance races: 1+4+8+64 = 77
            restrictions['friendlyToFaction'] = 'A'
        elif analysis['likely_faction_specific'] == 'Horde':
            restrictions['requiredRaces'] = 178  # Horde races: 2+16+32+128 = 178
            restrictions['friendlyToFaction'] = 'H'
        
        # Set race restriction if more specific
        if analysis['likely_race_specific']:
            race_id = self.races.get(analysis['likely_race_specific'].lower())
            if race_id:
                restrictions['requiredRaces'] = race_id
        
        # Set class restriction
        if analysis['likely_class_specific']:
            class_id = self.classes.get(analysis['likely_class_specific'].lower())
            if class_id:
                restrictions['requiredClasses'] = class_id
        
        return restrictions


def main():
    """Test the submitter metadata parser"""
    parser = SubmitterMetadataParser()
    
    # Test submission
    test_content = """
    Submitted by: @PlayerOne
    Character: Thrall (Level 60 Orc Shaman)
    Server: Project Epoch
    Addon Version: v1.1.0
    
    Quest: The Test Quest
    Zone: Durotar
    
    This quest was completed on my orc shaman with 300 herbalism.
    """
    
    metadata = parser.parse(test_content)
    print(json.dumps(metadata, indent=2))
    
    # Test restriction detection
    restrictions = parser.get_restriction_bitmasks()
    print("\nRestrictions detected:")
    print(json.dumps(restrictions, indent=2))


if __name__ == "__main__":
    main()