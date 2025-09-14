#!/usr/bin/env python3
"""
Quest Parser Module - Extracts ONLY quest-related data
Part of the modular pipeline architecture
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

class QuestParser:
    """Parses quest data from submissions, ignoring NPC/item/object details"""
    
    def __init__(self):
        self.parsed_quests = []
        self.parse_errors = []
        
    def parse(self, content: str, source_file: str = None) -> List[Dict]:
        """
        Parse quest data from submission content
        Returns a list of quest dictionaries (supports multi-quest submissions)
        """
        quests = []
        
        # Check if this is a multi-quest submission
        quest_sections = self._split_multi_quest_submission(content)
        
        for section in quest_sections:
            quest_data = self._parse_single_quest(section)
            if quest_data and quest_data.get('quest_id'):
                quest_data['source_file'] = source_file
                quests.append(quest_data)
                self.parsed_quests.append(quest_data)
            else:
                self.parse_errors.append({
                    'source': source_file,
                    'error': 'Could not parse quest data',
                    'content_preview': section[:200]
                })
        
        return quests
    
    def _split_multi_quest_submission(self, content: str) -> List[str]:
        """Split multi-quest submissions into individual quest sections"""
        
        # Look for common separator patterns (dashes or equals) followed by QUEST DATA
        # This handles the most common format in submissions
        quest_section_pattern = r'[-=]{30,}\s*\n=== QUEST DATA ==='
        if re.search(quest_section_pattern, content):
            # Split on the pattern
            parts = re.split(r'([-=]{30,}\s*\n=== QUEST DATA ===)', content)
            
            sections = []
            for i in range(1, len(parts), 2):  # Take separators + content pairs
                if i+1 < len(parts):
                    # Combine separator with its content
                    section = parts[i] + parts[i+1]
                    if 'Quest ID:' in section:
                        sections.append(section)
            
            # Also include the first quest if it exists before the first separator
            if parts and 'Quest ID:' in parts[0]:
                sections.insert(0, parts[0])
            
            return sections if sections else [content]
        
        # Fallback: Look for Quest ID: patterns with separator lines
        quest_id_pattern = r'={40,}\s*\nQuest ID:\s*\d+'
        if re.search(quest_id_pattern, content):
            # Split on the separator + Quest ID pattern
            # But keep the Quest ID in each section
            parts = re.split(r'(={50,}\s*\nQuest ID:\s*\d+)', content)
            
            sections = []
            for i in range(1, len(parts), 2):  # Skip first part, take separators + content
                if i+1 < len(parts):
                    # Combine separator+quest_id with its content
                    section = parts[i] + parts[i+1]
                    sections.append(section)
            
            # Also include the first quest if it exists before the first separator
            first_quest_match = re.search(r'Quest ID:\s*\d+', parts[0] if parts else '')
            if first_quest_match:
                sections.insert(0, parts[0])
            
            return [s for s in sections if s.strip() and 'Quest ID:' in s]
        
        # Look for multiple "QUEST DATA COLLECTION" sections
        if content.count('QUEST DATA COLLECTION') > 1:
            sections = re.split(r'={10,}\n.*?QUEST DATA COLLECTION.*?\n={10,}', content)
            return [s for s in sections if s.strip()]
        
        # Look for numbered quest patterns (e.g., "Quest 1:", "Quest 2:")
        if re.search(r'Quest \d+:', content, re.IGNORECASE):
            sections = re.split(r'Quest \d+:', content, re.IGNORECASE)
            return [s for s in sections if s.strip()]
        
        # Single quest submission
        return [content]
    
    def _parse_single_quest(self, content: str) -> Dict:
        """Parse a single quest from content"""
        
        quest_data = {
            'quest_id': None,
            'quest_name': None,
            'level': None,
            'quest_level': None,  # Some submissions have both
            'min_level': None,
            'zone': None,
            'subzone': None,
            'faction': None,
            'quest_giver_npc_id': None,  # Just the ID, not full NPC data
            'turn_in_npc_id': None,      # Just the ID, not full NPC data
            'objectives_text': None,
            'objectives_list': [],
            'quest_text': None,
            'completion_text': None,
            'quest_flags': None,
            'special_flags': None,
            'addon_version': None,
            'is_escort': False,
            'is_dungeon': False,
            'is_raid': False,
            'is_pvp': False,
            'is_daily': False,
            'is_weekly': False,
            'is_repeatable': False,
            'raw_database_entry': None
        }
        
        # Extract addon version
        version_match = re.search(r'Addon Version:\s*v?(\d+\.\d+\.\d+)', content, re.IGNORECASE)
        if version_match:
            quest_data['addon_version'] = version_match.group(1)
        
        # Extract quest ID (multiple patterns)
        quest_id_patterns = [
            r'Quest ID:\s*(\d+)',
            r'ID:\s*(\d+)',
            r'\[(\d+)\]\s*=',  # From database entries
            r'Quest\s+(\d+)\s+[:\-]'  # "Quest 12345:" or "Quest 12345 -"
        ]
        
        for pattern in quest_id_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                quest_data['quest_id'] = int(match.group(1))
                break
        
        # Extract quest name (multiple patterns)
        name_patterns = [
            r'Quest Name:\s*(.+?)(?:\n|$)',
            r'Name:\s*(.+?)(?:\n|$)',
            r'Title:\s*(.+?)(?:\n|$)',
            r'^\s*(.+?)\s*\(ID:\s*\d+\)',  # "Quest Name (ID: 12345)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = name.replace('[Epoch]', '').strip()
                if name and not name.startswith('[Quest'):
                    quest_data['quest_name'] = name
                    break
        
        # Extract level information
        level_match = re.search(r'Level:\s*(\d+)', content, re.IGNORECASE)
        if level_match:
            quest_data['level'] = int(level_match.group(1))
        
        quest_level_match = re.search(r'Quest Level:\s*(\d+)', content, re.IGNORECASE)
        if quest_level_match:
            quest_data['quest_level'] = int(quest_level_match.group(1))
        
        min_level_match = re.search(r'Min(?:imum)? Level:\s*(\d+)', content, re.IGNORECASE)
        if min_level_match:
            quest_data['min_level'] = int(min_level_match.group(1))
        
        # Extract zone information
        zone_match = re.search(r'Zone:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if zone_match:
            quest_data['zone'] = zone_match.group(1).strip()
        
        subzone_match = re.search(r'Subzone:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if subzone_match:
            quest_data['subzone'] = subzone_match.group(1).strip()
        
        # Extract faction
        faction_match = re.search(r'Faction:\s*(Alliance|Horde|Both|Neutral)', content, re.IGNORECASE)
        if faction_match:
            quest_data['faction'] = faction_match.group(1).capitalize()
        
        # Extract quest giver NPC ID only
        giver_section = re.search(r'QUEST GIVER:?\s*\n(.*?)(?:\n\n|OBJECTIVES:|TURN-IN)', content, re.DOTALL | re.IGNORECASE)
        if giver_section:
            npc_id_match = re.search(r'\(ID:\s*(\d+)\)', giver_section.group(1))
            if npc_id_match:
                quest_data['quest_giver_npc_id'] = int(npc_id_match.group(1))
        
        # Extract turn-in NPC ID only
        turnin_section = re.search(r'TURN-?IN NPC:?\s*\n(.*?)(?:\n\n|DATABASE|$)', content, re.DOTALL | re.IGNORECASE)
        if turnin_section:
            npc_id_match = re.search(r'\(ID:\s*(\d+)\)', turnin_section.group(1))
            if npc_id_match:
                quest_data['turn_in_npc_id'] = int(npc_id_match.group(1))
        
        # Extract objectives
        obj_section = re.search(r'OBJECTIVES?:?\s*\n(.*?)(?:\n\n|\nTURN-?IN|\nDATABASE)', content, re.DOTALL | re.IGNORECASE)
        if obj_section:
            objectives_text = obj_section.group(1).strip()
            quest_data['objectives_text'] = objectives_text
            
            # Parse individual objectives
            obj_lines = re.findall(r'(?:^|\n)\s*(?:\d+\.|\-|\*)\s*(.+?)(?=\n|$)', objectives_text)
            quest_data['objectives_list'] = [obj.strip() for obj in obj_lines if obj.strip()]
        
        # Check for quest types
        quest_text_lower = content.lower()
        if 'escort' in quest_text_lower:
            quest_data['is_escort'] = True
        if 'dungeon' in quest_text_lower or 'instance' in quest_text_lower:
            quest_data['is_dungeon'] = True
        if 'raid' in quest_text_lower:
            quest_data['is_raid'] = True
        if 'pvp' in quest_text_lower or 'battleground' in quest_text_lower:
            quest_data['is_pvp'] = True
        if 'daily' in quest_text_lower:
            quest_data['is_daily'] = True
        if 'weekly' in quest_text_lower:
            quest_data['is_weekly'] = True
        if 'repeatable' in quest_text_lower:
            quest_data['is_repeatable'] = True
        
        # Extract raw database entry if present
        db_section = re.search(r'-- Add to epochQuestDB\.lua:(.*?)(?:-- Add to|\Z)', content, re.DOTALL)
        if db_section:
            quest_data['raw_database_entry'] = db_section.group(1).strip()
        
        return quest_data
    
    def generate_quest_entry(self, quest_data: Dict) -> str:
        """Generate a Lua database entry for a quest"""
        
        quest_id = quest_data['quest_id']
        name = quest_data.get('quest_name', f'[Quest {quest_id}]')
        
        # Build startedBy (only NPC ID if available)
        started_by = "nil"
        if quest_data.get('quest_giver_npc_id'):
            started_by = f"{{{{{quest_data['quest_giver_npc_id']}}},nil,nil}}"
        
        # Build finishedBy (only NPC ID if available)  
        finished_by = "nil"
        if quest_data.get('turn_in_npc_id'):
            finished_by = f"{{{{{quest_data['turn_in_npc_id']}}},nil}}"
        
        # Levels
        min_level = quest_data.get('min_level') or quest_data.get('level') or 1
        quest_level = quest_data.get('quest_level') or quest_data.get('level') or 1
        
        # Faction/race restrictions
        required_races = "nil"  # Will be determined by faction detector module
        
        # Objectives
        objectives_text = quest_data.get('objectives_text', '[Needs data collection]')
        if isinstance(objectives_text, list):
            objectives_text = '", "'.join(objectives_text)
        objectives = f'{{"{objectives_text}"}}'
        
        # Zone (needs proper zone ID mapping - placeholder for now)
        zone_or_sort = 1  # Will be determined by zone mapper module
        
        # Build the quest entry
        entry = f"[{quest_id}] = {{"
        entry += f'"{name}",'                    # 1: name
        entry += f'{started_by},'                # 2: startedBy
        entry += f'{finished_by},'               # 3: finishedBy  
        entry += f'{min_level},'                 # 4: requiredLevel
        entry += f'{quest_level},'               # 5: questLevel
        entry += f'{required_races},'            # 6: requiredRaces
        entry += f'nil,'                         # 7: requiredClasses
        entry += f'{objectives},'                # 8: objectiveText
        entry += f'nil,'                         # 9: triggerEnd
        entry += f'nil,'                         # 10: objectives (detailed)
        entry += f'nil,'                         # 11: sourceItemId
        entry += f'nil,'                         # 12: preQuestGroup
        entry += f'nil,'                         # 13: preQuestSingle
        entry += f'nil,'                         # 14: childQuests
        entry += f'nil,'                         # 15: inGroupWith
        entry += f'nil,'                         # 16: exclusiveTo
        entry += f'{zone_or_sort},'              # 17: zoneOrSort
        entry += f'nil,'                         # 18: requiredSkill
        entry += f'nil,'                         # 19: requiredMinRep
        entry += f'nil,'                         # 20: requiredMaxRep
        entry += f'nil,'                         # 21: requiredSourceItems
        entry += f'nil,'                         # 22: nextQuestInChain
        entry += f'0,'                           # 23: questFlags
        entry += f'0,'                           # 24: specialFlags
        entry += f'nil,'                         # 25: parentQuest
        entry += f'nil,'                         # 26: reputationReward
        entry += f'nil,'                         # 27: extraObjectives
        entry += f'nil,'                         # 28: requiredSpell
        entry += f'nil,'                         # 29: requiredSpecialization
        entry += f'nil'                          # 30: requiredMaxLevel
        entry += "},"
        
        return entry
    
    def get_summary(self) -> Dict:
        """Get parsing summary statistics"""
        return {
            'total_parsed': len(self.parsed_quests),
            'parse_errors': len(self.parse_errors),
            'quests_by_version': self._count_by_field('addon_version'),
            'quests_by_zone': self._count_by_field('zone'),
            'quests_by_faction': self._count_by_field('faction'),
            'special_quests': {
                'escort': sum(1 for q in self.parsed_quests if q.get('is_escort')),
                'dungeon': sum(1 for q in self.parsed_quests if q.get('is_dungeon')),
                'daily': sum(1 for q in self.parsed_quests if q.get('is_daily')),
                'pvp': sum(1 for q in self.parsed_quests if q.get('is_pvp'))
            }
        }
    
    def _count_by_field(self, field: str) -> Dict:
        """Count quests by a specific field"""
        counts = {}
        for quest in self.parsed_quests:
            value = quest.get(field, 'Unknown')
            counts[value] = counts.get(value, 0) + 1
        return counts

def main():
    """Test the quest parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python quest_parser.py <submission_file>")
        sys.exit(1)
    
    parser = QuestParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    quests = parser.parse(content, sys.argv[1])
    
    print(f"\nParsed {len(quests)} quest(s)")
    for quest in quests:
        print(f"\n  Quest {quest.get('quest_id')}: {quest.get('quest_name')}")
        print(f"    Level: {quest.get('level')}")
        print(f"    Zone: {quest.get('zone')}")
        print(f"    Giver NPC: {quest.get('quest_giver_npc_id')}")
        print(f"    Turn-in NPC: {quest.get('turn_in_npc_id')}")
        if quest.get('objectives_list'):
            print(f"    Objectives: {len(quest['objectives_list'])} found")
    
    print(f"\nSummary: {json.dumps(parser.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()