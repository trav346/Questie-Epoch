#!/usr/bin/env python3
"""
Quest Chain Parser Module - Detects quest prerequisites, chains, and dependencies
Handles prequest groups, single prereqs, child quests, and quest series
"""

import re
from typing import Dict, List, Optional, Set, Tuple
import json

class QuestChainParser:
    """Parses quest chain and dependency data from submissions"""
    
    def __init__(self):
        self.parsed_chains = {}
        self.parse_errors = []
        
        # Chain relationship patterns
        self.chain_keywords = {
            'prerequisite': ['prerequisite', 'requires', 'need', 'must complete', 'after', 'following'],
            'followup': ['leads to', 'unlocks', 'opens', 'next', 'continue', 'follow-up', 'sequel'],
            'group': ['all of', 'both', 'either', 'any of', 'group'],
            'chain': ['chain', 'series', 'sequence', 'part of', 'step'],
            'exclusive': ['or', 'instead', 'alternative', 'choose', 'either'],
            'daily': ['daily', 'repeatable', 'reset'],
            'elite': ['elite', 'group', 'raid', 'dungeon']
        }
        
        # Common quest naming patterns that indicate chains
        self.chain_patterns = {
            'numbered': r'(.+?)\s+(?:Part|Chapter|Step)\s+(\d+)',
            'roman': r'(.+?)\s+([IVX]+)$',
            'continuation': r'(.+?)\s+(?:Continued|Redux|Returns?|Again)$',
            'prequel': r'(.+?)\s+(?:Prelude|Beginning|Start)$'
        }
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse quest chain data from submission
        
        Returns:
            Dictionary with quest chain relationships
        """
        chain_data = {
            'quest_id': quest_id,
            'prerequisites_single': [],    # Any one must be done (preQuestSingle)
            'prerequisites_group': [],     # All must be done (preQuestGroup)
            'next_quest': None,           # Direct follow-up (nextQuestInChain)
            'child_quests': [],           # Unlocked by this quest (childQuests)
            'parent_quest': None,         # Parent quest (parentQuest)
            'in_group_with': [],          # Same quest group (inGroupWith)
            'exclusive_to': [],           # Mutually exclusive (exclusiveTo)
            'chain_info': {
                'chain_name': None,
                'chain_position': None,
                'is_chain_start': False,
                'is_chain_end': False,
                'is_daily': False,
                'is_elite_chain': False
            }
        }
        
        # Parse explicit chain information from submission
        chain_data.update(self._parse_explicit_chains(content))
        
        # Parse database entries for chain info
        chain_data.update(self._parse_database_chains(content))
        
        # Infer chains from quest name patterns
        quest_name = self._extract_quest_name(content)
        if quest_name:
            chain_data.update(self._infer_chain_from_name(quest_name))
        
        # Parse quest text for chain references
        chain_data.update(self._parse_quest_text_chains(content))
        
        # Parse level and difficulty hints
        chain_data.update(self._parse_difficulty_chains(content))
        
        self.parsed_chains[quest_id] = chain_data
        return chain_data
    
    def _parse_explicit_chains(self, content: str) -> Dict:
        """Parse explicitly mentioned chain information"""
        chains = {}
        
        # Look for prerequisite sections
        prereq_section = re.search(r'PREREQUISITES?:?\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if prereq_section:
            prereq_text = prereq_section.group(1)
            
            # Parse prerequisite quest IDs
            quest_ids = re.findall(r'(?:Quest|ID)\s*:?\s*(\d+)', prereq_text, re.IGNORECASE)
            if quest_ids:
                # Determine if it's AND or OR logic
                if any(word in prereq_text.lower() for word in ['all', 'both', 'and', 'plus']):
                    chains['prerequisites_group'] = [int(qid) for qid in quest_ids]
                elif any(word in prereq_text.lower() for word in ['any', 'either', 'or', 'one of']):
                    chains['prerequisites_single'] = [int(qid) for qid in quest_ids]
                else:
                    # Default to single if unclear
                    chains['prerequisites_single'] = [int(qid) for qid in quest_ids]
        
        # Look for followup/next quest information
        followup_patterns = [
            r'(?:next quest|follow-?up|leads to|unlocks|continues):?\s*(?:Quest\s*)?(\d+)',
            r'(?:after completing|upon completion):?\s*(?:Quest\s*)?(\d+)',
            r'(?:this quest unlocks|opens up):?\s*(?:Quest\s*)?(\d+)'
        ]
        
        for pattern in followup_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                chains['child_quests'] = [int(qid) for qid in matches]
                # If there's only one child, it's the direct next quest
                if len(matches) == 1:
                    chains['next_quest'] = int(matches[0])
                break
        
        # Look for parent quest information
        parent_patterns = [
            r'(?:part of|belongs to|child of):?\s*(?:Quest\s*)?(\d+)',
            r'(?:parent quest|main quest):?\s*(?:Quest\s*)?(\d+)'
        ]
        
        for pattern in parent_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                chains['parent_quest'] = int(match.group(1))
                break
        
        return chains
    
    def _parse_database_chains(self, content: str) -> Dict:
        """Parse chain info from database entries"""
        chains = {}
        
        # Look for database entry with chain information
        db_section = re.search(r'-- Add to epochQuestDB\.lua:(.*?)(?:-- Add to|$)', content, re.DOTALL)
        if db_section:
            db_text = db_section.group(1)
            
            # Parse the Lua table structure to extract chain fields
            # Field positions: 12=preQuestGroup, 13=preQuestSingle, 14=childQuests, etc.
            
            # Extract the array values (simplified Lua parsing)
            table_match = re.search(r'\[(\d+)\]\s*=\s*\{(.+?)\}', db_text, re.DOTALL)
            if table_match:
                quest_id = int(table_match.group(1))
                fields = [f.strip() for f in table_match.group(2).split(',')]
                
                # Map fields to chain data (assuming standard 30-field structure)
                if len(fields) >= 22:
                    # Field 12: preQuestGroup
                    if fields[11] != 'nil' and fields[11].strip():
                        prereq_group = self._parse_lua_array(fields[11])
                        if prereq_group:
                            chains['prerequisites_group'] = prereq_group
                    
                    # Field 13: preQuestSingle
                    if fields[12] != 'nil' and fields[12].strip():
                        prereq_single = self._parse_lua_array(fields[12])
                        if prereq_single:
                            chains['prerequisites_single'] = prereq_single
                    
                    # Field 14: childQuests
                    if fields[13] != 'nil' and fields[13].strip():
                        children = self._parse_lua_array(fields[13])
                        if children:
                            chains['child_quests'] = children
                    
                    # Field 22: nextQuestInChain
                    if len(fields) > 21 and fields[21] != 'nil' and fields[21].strip():
                        try:
                            chains['next_quest'] = int(fields[21])
                        except ValueError:
                            pass
        
        return chains
    
    def _parse_lua_array(self, lua_str: str) -> List[int]:
        """Parse a Lua array string like {1,2,3} into Python list"""
        if not lua_str or lua_str.strip() == 'nil':
            return []
        
        # Remove braces and split by comma
        cleaned = lua_str.strip().strip('{}')
        if not cleaned:
            return []
        
        try:
            return [int(x.strip()) for x in cleaned.split(',') if x.strip().isdigit()]
        except ValueError:
            return []
    
    def _extract_quest_name(self, content: str) -> Optional[str]:
        """Extract quest name from content"""
        patterns = [
            r'Quest Name:\s*(.+?)(?:\n|$)',
            r'Name:\s*(.+?)(?:\n|$)',
            r'Title:\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = name.replace('[Epoch]', '').strip()
                if name and not name.startswith('[Quest'):
                    return name
        
        return None
    
    def _infer_chain_from_name(self, quest_name: str) -> Dict:
        """Infer chain information from quest name patterns"""
        chains = {'chain_info': {}}
        
        # Check for numbered sequences
        for pattern_name, pattern in self.chain_patterns.items():
            match = re.search(pattern, quest_name, re.IGNORECASE)
            if match:
                if pattern_name == 'numbered':
                    chain_name = match.group(1).strip()
                    position = int(match.group(2))
                    chains['chain_info']['chain_name'] = chain_name
                    chains['chain_info']['chain_position'] = position
                    chains['chain_info']['is_chain_start'] = (position == 1)
                    
                elif pattern_name == 'roman':
                    chain_name = match.group(1).strip()
                    roman = match.group(2)
                    position = self._roman_to_int(roman)
                    chains['chain_info']['chain_name'] = chain_name
                    chains['chain_info']['chain_position'] = position
                    chains['chain_info']['is_chain_start'] = (position == 1)
                    
                elif pattern_name == 'continuation':
                    chains['chain_info']['chain_name'] = match.group(1).strip()
                    chains['chain_info']['is_chain_start'] = False
                    
                elif pattern_name == 'prequel':
                    chains['chain_info']['chain_name'] = match.group(1).strip()
                    chains['chain_info']['is_chain_start'] = True
                
                break
        
        # Check for common chain indicators in name
        name_lower = quest_name.lower()
        if any(word in name_lower for word in ['daily', 'weekly']):
            chains['chain_info']['is_daily'] = True
        
        if any(word in name_lower for word in ['elite', 'dungeon', 'raid', 'group']):
            chains['chain_info']['is_elite_chain'] = True
        
        return chains
    
    def _roman_to_int(self, roman: str) -> int:
        """Convert roman numeral to integer"""
        roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        result = 0
        prev_value = 0
        
        for char in reversed(roman.upper()):
            value = roman_map.get(char, 0)
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value
        
        return max(1, result)  # Ensure at least 1
    
    def _parse_quest_text_chains(self, content: str) -> Dict:
        """Parse quest text and completion text for chain references"""
        chains = {}
        
        # Look for quest text sections
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
            # Look for quest references in text
            quest_refs = re.findall(r'(?:quest|mission|task)\s+(\d+)', all_text, re.IGNORECASE)
            
            # Look for chain indicators in text
            text_lower = all_text.lower()
            
            if any(word in text_lower for word in ['before you can', 'first you must', 'after completing']):
                # Likely has prerequisites
                if quest_refs:
                    chains['prerequisites_single'] = [int(qid) for qid in quest_refs[:3]]  # Limit to 3
            
            if any(word in text_lower for word in ['next', 'continue', 'return when', 'come back']):
                # Likely has follow-up
                chains['chain_info'] = chains.get('chain_info', {})
                chains['chain_info']['is_chain_end'] = False
            
            if any(word in text_lower for word in ['final', 'last', 'end', 'complete']):
                chains['chain_info'] = chains.get('chain_info', {})
                chains['chain_info']['is_chain_end'] = True
        
        return chains
    
    def _parse_difficulty_chains(self, content: str) -> Dict:
        """Parse difficulty and level hints for chain classification"""
        chains = {'chain_info': {}}
        
        # Extract quest level
        level_match = re.search(r'(?:Quest )?Level:\s*(\d+)', content, re.IGNORECASE)
        if level_match:
            level = int(level_match.group(1))
            
            # High level quests are more likely to be part of chains
            if level >= 15:
                chains['chain_info']['likely_chained'] = True
            
            # Elite quests often have chains
            if level >= 20:
                chains['chain_info']['is_elite_chain'] = True
        
        # Check for elite/group/dungeon indicators
        content_lower = content.lower()
        if any(word in content_lower for word in ['elite', 'group', 'dungeon', 'raid', 'instance']):
            chains['chain_info']['is_elite_chain'] = True
        
        if any(word in content_lower for word in ['daily', 'repeatable', 'weekly']):
            chains['chain_info']['is_daily'] = True
        
        return chains
    
    def validate_chain_logic(self, chain_data: Dict) -> List[str]:
        """Validate chain data for logical consistency"""
        warnings = []
        
        # Check for conflicting prerequisites
        if chain_data.get('prerequisites_single') and chain_data.get('prerequisites_group'):
            warnings.append("Quest has both single and group prerequisites - this may be incorrect")
        
        # Check for circular references
        quest_id = chain_data.get('quest_id')
        if quest_id:
            if quest_id in chain_data.get('prerequisites_single', []):
                warnings.append("Quest cannot be prerequisite to itself")
            if quest_id in chain_data.get('prerequisites_group', []):
                warnings.append("Quest cannot be prerequisite to itself")
            if quest_id == chain_data.get('next_quest'):
                warnings.append("Quest cannot be its own next quest")
        
        # Check chain position logic
        chain_info = chain_data.get('chain_info', {})
        if chain_info.get('is_chain_start') and chain_data.get('prerequisites_single'):
            warnings.append("Chain start quest should not have prerequisites")
        
        if chain_info.get('is_chain_end') and chain_data.get('next_quest'):
            warnings.append("Chain end quest should not have next quest")
        
        return warnings
    
    def generate_chain_lua(self, chain_data: Dict) -> Dict[str, str]:
        """Generate Lua values for chain fields"""
        lua_fields = {}
        
        # Field 12: preQuestGroup
        if chain_data.get('prerequisites_group'):
            prereqs = ",".join(str(qid) for qid in chain_data['prerequisites_group'])
            lua_fields['preQuestGroup'] = f"{{{prereqs}}}"
        else:
            lua_fields['preQuestGroup'] = "nil"
        
        # Field 13: preQuestSingle
        if chain_data.get('prerequisites_single'):
            prereqs = ",".join(str(qid) for qid in chain_data['prerequisites_single'])
            lua_fields['preQuestSingle'] = f"{{{prereqs}}}"
        else:
            lua_fields['preQuestSingle'] = "nil"
        
        # Field 14: childQuests
        if chain_data.get('child_quests'):
            children = ",".join(str(qid) for qid in chain_data['child_quests'])
            lua_fields['childQuests'] = f"{{{children}}}"
        else:
            lua_fields['childQuests'] = "nil"
        
        # Field 15: inGroupWith
        if chain_data.get('in_group_with'):
            group = ",".join(str(qid) for qid in chain_data['in_group_with'])
            lua_fields['inGroupWith'] = f"{{{group}}}"
        else:
            lua_fields['inGroupWith'] = "nil"
        
        # Field 16: exclusiveTo
        if chain_data.get('exclusive_to'):
            exclusive = ",".join(str(qid) for qid in chain_data['exclusive_to'])
            lua_fields['exclusiveTo'] = f"{{{exclusive}}}"
        else:
            lua_fields['exclusiveTo'] = "nil"
        
        # Field 22: nextQuestInChain
        if chain_data.get('next_quest'):
            lua_fields['nextQuestInChain'] = str(chain_data['next_quest'])
        else:
            lua_fields['nextQuestInChain'] = "nil"
        
        # Field 25: parentQuest
        if chain_data.get('parent_quest'):
            lua_fields['parentQuest'] = str(chain_data['parent_quest'])
        else:
            lua_fields['parentQuest'] = "nil"
        
        return lua_fields
    
    def get_summary(self) -> Dict:
        """Get parsing summary"""
        total_chains = len(self.parsed_chains)
        
        with_prereqs = sum(1 for chain in self.parsed_chains.values() 
                          if chain.get('prerequisites_single') or chain.get('prerequisites_group'))
        with_next = sum(1 for chain in self.parsed_chains.values() if chain.get('next_quest'))
        with_children = sum(1 for chain in self.parsed_chains.values() if chain.get('child_quests'))
        
        chain_starts = sum(1 for chain in self.parsed_chains.values() 
                          if chain.get('chain_info', {}).get('is_chain_start'))
        chain_ends = sum(1 for chain in self.parsed_chains.values() 
                        if chain.get('chain_info', {}).get('is_chain_end'))
        
        return {
            'total_parsed': total_chains,
            'with_prerequisites': with_prereqs,
            'with_next_quest': with_next,
            'with_children': with_children,
            'chain_starts': chain_starts,
            'chain_ends': chain_ends,
            'parse_errors': len(self.parse_errors)
        }

def main():
    """Test the quest chain parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python quest_chain_parser.py <submission_file>")
        sys.exit(1)
    
    parser = QuestChainParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract quest ID if present
    quest_id = None
    id_match = re.search(r'Quest ID:\s*(\d+)', content)
    if id_match:
        quest_id = int(id_match.group(1))
    
    chain_data = parser.parse(content, quest_id)
    
    print(f"\nQuest {quest_id} Chain Analysis:")
    
    if chain_data.get('prerequisites_single'):
        print(f"Prerequisites (any): {chain_data['prerequisites_single']}")
    
    if chain_data.get('prerequisites_group'):
        print(f"Prerequisites (all): {chain_data['prerequisites_group']}")
    
    if chain_data.get('next_quest'):
        print(f"Next Quest: {chain_data['next_quest']}")
    
    if chain_data.get('child_quests'):
        print(f"Child Quests: {chain_data['child_quests']}")
    
    if chain_data.get('parent_quest'):
        print(f"Parent Quest: {chain_data['parent_quest']}")
    
    chain_info = chain_data.get('chain_info', {})
    if chain_info:
        print(f"\nChain Info:")
        for key, value in chain_info.items():
            if value:
                print(f"  {key}: {value}")
    
    # Validate chain logic
    warnings = parser.validate_chain_logic(chain_data)
    if warnings:
        print(f"\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Show Lua output
    lua_fields = parser.generate_chain_lua(chain_data)
    print(f"\nLua Fields:")
    for field, value in lua_fields.items():
        print(f"  {field}: {value}")
    
    print(f"\nSummary: {json.dumps(parser.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()