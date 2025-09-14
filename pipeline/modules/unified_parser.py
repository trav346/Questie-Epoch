#!/usr/bin/env python3
"""
Unified Parser Module - Handles both old (v1.0.68) and new (v1.1.0+) submission formats
Normalizes different formats into a consistent structure for processing
"""

import re
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

class UnifiedParser:
    """Parses and normalizes both old and new quest submission formats"""
    
    def __init__(self):
        self.parsed_submissions = []
        self.format_detection_results = {}
        self.conversion_stats = {'old_format': 0, 'new_format': 0, 'unknown_format': 0}
        
        # Format detection patterns
        self.format_indicators = {
            'v1_0_68': [
                r'Version:\s*v?1\.0\.[0-6][0-8]',
                r'Addon Version:\s*v?1\.0\.[0-6][0-8]',
                r'QuestHelper',  # Old addon integration
                r'Basic quest data:',  # Old format section header
                r'Quest giver:\s*\w+\s*\((?!ID:)',  # Old NPC format without ID
            ],
            'v1_1_plus': [
                r'Version:\s*v?1\.1\.\d+',
                r'Addon Version:\s*v?1\.1\.\d+',
                r'Collection Mode:\s*(?:NORMAL|ADVANCED)',  # New collection modes
                r'Service NPCs:\s*\d+',  # New service NPC tracking
                r'QUEST GIVER:\s*\n.*?\(ID:\s*\d+\)',  # New NPC format with ID
                r'DATABASE ENTRIES:',  # New database section
            ],
            'legacy_variants': [
                r'Version:\s*v?0\.\d+',
                r'QUEST DATA COLLECTION',  # Very old format
                r'Manual submission',
                r'No addon version',
            ]
        }
        
        # Field mapping between old and new formats
        self.field_mappings = {
            'old_to_new': {
                'Quest giver': 'quest_giver_npc_id',
                'Turn in': 'turn_in_npc_id',
                'Turn-in': 'turn_in_npc_id',
                'Quest level': 'quest_level',
                'Min level': 'min_level',
                'Minimum level': 'min_level',
                'Required level': 'required_level',
                'Zone': 'zone',
                'Sub-zone': 'subzone',
                'Subzone': 'subzone',
                'Faction': 'faction',
                'Objective': 'objectives_text',
                'Objectives': 'objectives_text',
                'Description': 'quest_text',
                'Completion': 'completion_text'
            }
        }
        
    def parse(self, content: str, source_file: str = None) -> Dict:
        """
        Parse submission content, auto-detecting format and normalizing
        
        Returns:
            Dictionary with normalized submission data
        """
        submission = {
            'source_file': source_file,
            'detected_format': None,
            'format_confidence': 0.0,
            'addon_version': None,
            'submission_date': None,
            'player_info': {},
            'quests': [],
            'service_npcs': [],
            'conversion_notes': [],
            'quality_score': 0
        }
        
        # Detect submission format
        format_info = self._detect_format(content)
        submission.update(format_info)
        
        # Parse based on detected format
        if submission['detected_format'] == 'v1_0_68':
            self._parse_old_format(content, submission)
            self.conversion_stats['old_format'] += 1
        elif submission['detected_format'] == 'v1_1_plus':
            self._parse_new_format(content, submission)
            self.conversion_stats['new_format'] += 1
        elif submission['detected_format'] == 'legacy_variants':
            self._parse_legacy_format(content, submission)
            self.conversion_stats['old_format'] += 1
        else:
            self._parse_unknown_format(content, submission)
            self.conversion_stats['unknown_format'] += 1
        
        # Normalize and validate parsed data
        submission = self._normalize_submission(submission)
        
        # Calculate quality score
        submission['quality_score'] = self._calculate_quality_score(submission)
        
        self.parsed_submissions.append(submission)
        return submission
    
    def _detect_format(self, content: str) -> Dict:
        """Detect submission format based on content patterns"""
        format_scores = {'v1_0_68': 0, 'v1_1_plus': 0, 'legacy_variants': 0}
        
        # Score each format based on indicator matches
        for format_name, indicators in self.format_indicators.items():
            for indicator in indicators:
                if re.search(indicator, content, re.IGNORECASE):
                    format_scores[format_name] += 1
        
        # Determine best match
        best_format = max(format_scores, key=format_scores.get)
        best_score = format_scores[best_format]
        
        # Confidence calculation
        total_indicators = sum(len(indicators) for indicators in self.format_indicators.values())
        confidence = best_score / len(self.format_indicators[best_format])
        
        # Fallback detection if no clear match
        if best_score == 0:
            # Check for version numbers
            version_match = re.search(r'Version:\s*v?(\d+\.\d+\.\d+)', content, re.IGNORECASE)
            if version_match:
                version = version_match.group(1)
                if version.startswith('1.0.'):
                    best_format = 'v1_0_68'
                    confidence = 0.7
                elif version.startswith('1.1.'):
                    best_format = 'v1_1_plus'
                    confidence = 0.7
                else:
                    best_format = 'legacy_variants'
                    confidence = 0.5
            else:
                # Use heuristics
                if 'SERVICE NPCs' in content and 'DATABASE ENTRIES' in content:
                    best_format = 'v1_1_plus'
                    confidence = 0.6
                elif 'Quest giver:' in content or 'Turn in:' in content:
                    best_format = 'v1_0_68'
                    confidence = 0.5
                else:
                    best_format = 'unknown'
                    confidence = 0.0
        
        return {
            'detected_format': best_format,
            'format_confidence': confidence,
            'format_scores': format_scores
        }
    
    def _parse_old_format(self, content: str, submission: Dict):
        """Parse old format (v1.0.68 and similar)"""
        submission['conversion_notes'].append("Processing old format submission")
        
        # Extract addon version
        version_match = re.search(r'(?:Addon )?Version:\s*v?(\d+\.\d+\.\d+)', content, re.IGNORECASE)
        if version_match:
            submission['addon_version'] = version_match.group(1)
        
        # Extract player information (often limited in old format)
        player_match = re.search(r'Player:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if player_match:
            player_text = player_match.group(1)
            submission['player_info'] = self._parse_player_info(player_text)
        
        # Parse quest data (old format often has different structure)
        quests = self._parse_old_quest_format(content)
        submission['quests'] = quests
        
        # Old format usually doesn't have service NPCs
        submission['conversion_notes'].append("Old format: service NPCs not available")
        
    def _parse_new_format(self, content: str, submission: Dict):
        """Parse new format (v1.1.0+)"""
        submission['conversion_notes'].append("Processing new format submission")
        
        # Extract addon version
        version_match = re.search(r'Version:\s*(\d+\.\d+\.\d+)', content)
        if version_match:
            submission['addon_version'] = version_match.group(1)
        
        # Extract submission date
        date_match = re.search(r'Date:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', content)
        if date_match:
            try:
                submission['submission_date'] = datetime.strptime(date_match.group(1), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        # Extract player information
        player_match = re.search(r'Player:\s*(.+?)(?:\n|$)', content)
        if player_match:
            player_text = player_match.group(1)
            submission['player_info'] = self._parse_player_info(player_text)
        
        # Extract collection mode info
        mode_match = re.search(r'Collection Mode:\s*(.+?)(?:\n|$)', content)
        if mode_match:
            submission['collection_mode'] = mode_match.group(1)
        
        # Parse quest data (new format has standardized structure)
        quests = self._parse_new_quest_format(content)
        submission['quests'] = quests
        
        # Parse service NPCs
        service_npcs = self._parse_service_npcs(content)
        submission['service_npcs'] = service_npcs
        
    def _parse_legacy_format(self, content: str, submission: Dict):
        """Parse very old/legacy formats"""
        submission['conversion_notes'].append("Processing legacy format submission")
        
        # Legacy formats are highly variable, use flexible parsing
        quests = self._parse_flexible_quest_format(content)
        submission['quests'] = quests
        
        submission['conversion_notes'].append("Legacy format: limited data extraction capability")
        
    def _parse_unknown_format(self, content: str, submission: Dict):
        """Attempt to parse unknown format using heuristics"""
        submission['conversion_notes'].append("Processing unknown format - using heuristic parsing")
        
        # Try to extract any recognizable quest data
        quests = self._parse_flexible_quest_format(content)
        submission['quests'] = quests
        
        submission['conversion_notes'].append("Unknown format: data quality may be limited")
    
    def _parse_old_quest_format(self, content: str) -> List[Dict]:
        """Parse quest data from old format submissions"""
        quests = []
        
        # Old format patterns
        quest_sections = self._split_old_quest_sections(content)
        
        for section in quest_sections:
            quest = {
                'quest_id': None,
                'quest_name': None,
                'level': None,
                'zone': None,
                'faction': None,
                'quest_giver_npc_id': None,
                'turn_in_npc_id': None,
                'objectives_text': None,
                'format_notes': ['Converted from old format']
            }
            
            # Parse quest ID (old format variations)
            id_patterns = [
                r'Quest:\s*(\d+)',
                r'ID:\s*(\d+)',
                r'Quest ID:\s*(\d+)',
                r'#(\d+)'
            ]
            
            for pattern in id_patterns:
                match = re.search(pattern, section, re.IGNORECASE)
                if match:
                    quest['quest_id'] = int(match.group(1))
                    break
            
            # Parse quest name (old format variations)
            name_patterns = [
                r'Quest:\s*(.+?)(?:\s*\(|$)',
                r'Name:\s*(.+?)(?:\n|$)',
                r'Title:\s*(.+?)(?:\n|$)',
                r'^(.+?)(?:\s*-\s*Quest|\s*\(ID:)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, section, re.IGNORECASE | re.MULTILINE)
                if match:
                    name = match.group(1).strip()
                    if name and len(name) > 3 and not name.isdigit():
                        quest['quest_name'] = name
                        break
            
            # Parse other fields using old field names
            for old_field, new_field in self.field_mappings['old_to_new'].items():
                pattern = rf'{re.escape(old_field)}:\s*(.+?)(?:\n|$)'
                match = re.search(pattern, section, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    
                    # Convert values based on field type
                    if new_field in ['quest_level', 'min_level', 'required_level']:
                        try:
                            quest[new_field] = int(value)
                        except ValueError:
                            quest['format_notes'].append(f"Could not parse {new_field}: {value}")
                    elif new_field in ['quest_giver_npc_id', 'turn_in_npc_id']:
                        # Try to extract NPC ID from old format
                        npc_id = self._extract_npc_id_from_old_format(value)
                        if npc_id:
                            quest[new_field] = npc_id
                        else:
                            quest['format_notes'].append(f"Could not extract NPC ID from: {value}")
                    else:
                        quest[new_field] = value
            
            if quest['quest_id']:  # Only add if we found a quest ID
                quests.append(quest)
        
        return quests
    
    def _parse_new_quest_format(self, content: str) -> List[Dict]:
        """Parse quest data from new format submissions"""
        quests = []
        
        # New format uses standardized separators
        quest_sections = re.split(r'={50,}', content)
        
        for section in quest_sections:
            if 'Quest ID:' not in section:
                continue
            
            quest = {
                'quest_id': None,
                'quest_name': None,
                'level': None,
                'status': None,
                'quest_giver_npc_id': None,
                'turn_in_npc_id': None,
                'objectives_list': [],
                'ground_objects': [],
                'database_entry': None,
                'format_notes': ['New format submission']
            }
            
            # Parse quest ID
            id_match = re.search(r'Quest ID:\s*(\d+)', section)
            if id_match:
                quest['quest_id'] = int(id_match.group(1))
            
            # Parse quest name
            name_match = re.search(r'Quest Name:\s*(.+?)(?:\n|$)', section)
            if name_match:
                quest['quest_name'] = name_match.group(1).strip()
            
            # Parse level
            level_match = re.search(r'Level:\s*(\d+)', section)
            if level_match:
                quest['level'] = int(level_match.group(1))
            
            # Parse status
            status_match = re.search(r'Status:\s*(.+?)(?:\n|$)', section)
            if status_match:
                quest['status'] = status_match.group(1).strip()
            
            # Parse quest giver
            giver_section = re.search(r'QUEST GIVER:.*?\n.*?(.+?)\s*\(ID:\s*(\d+)\)', section, re.DOTALL)
            if giver_section:
                quest['quest_giver_npc_id'] = int(giver_section.group(2))
            
            # Parse turn-in NPC
            turnin_section = re.search(r'TURN-?IN NPC:.*?\n.*?(.+?)\s*\(ID:\s*(\d+)\)', section, re.DOTALL)
            if turnin_section:
                quest['turn_in_npc_id'] = int(turnin_section.group(2))
            
            # Parse objectives
            obj_section = re.search(r'OBJECTIVES?:?\s*\n(.*?)(?:\n\nGROUND|\n\nTURN-?IN|\n\nDATABASE|\Z)', 
                                   section, re.DOTALL | re.IGNORECASE)
            if obj_section:
                objectives_text = obj_section.group(1).strip()
                quest['objectives_list'] = [line.strip() for line in objectives_text.split('\n') 
                                           if line.strip()]
            
            # Parse ground objects
            ground_section = re.search(r'GROUND OBJECTS?/CONTAINERS?:?\s*\n(.*?)(?:\n\nDATABASE|\n\n=|\Z)', 
                                      section, re.DOTALL | re.IGNORECASE)
            if ground_section:
                ground_text = ground_section.group(1).strip()
                quest['ground_objects'] = [line.strip() for line in ground_text.split('\n') 
                                         if line.strip() and 'Invalid coordinates' not in line]
            
            # Parse database entry
            db_section = re.search(r'-- Add to epochQuestDB\.lua:(.*?)(?:-- Add to|$)', section, re.DOTALL)
            if db_section:
                quest['database_entry'] = db_section.group(1).strip()
            
            if quest['quest_id']:
                quests.append(quest)
        
        return quests
    
    def _parse_flexible_quest_format(self, content: str) -> List[Dict]:
        """Parse quest data using flexible heuristics for unknown formats"""
        quests = []
        
        # Try to find quest IDs anywhere in the content
        quest_id_matches = re.findall(r'(?:Quest|ID|#)\s*:?\s*(\d{4,6})', content, re.IGNORECASE)
        
        for quest_id_str in quest_id_matches:
            quest_id = int(quest_id_str)
            
            # Extract context around the quest ID
            id_context = self._extract_context_around_id(content, quest_id)
            
            quest = {
                'quest_id': quest_id,
                'quest_name': None,
                'level': None,
                'format_notes': ['Extracted using flexible parsing']
            }
            
            # Try to find quest name near the ID
            name_patterns = [
                rf'(?:{quest_id})\s*[:\-]\s*(.+?)(?:\n|$)',
                rf'(.+?)\s*(?:ID|#)?\s*:?\s*{quest_id}',
                rf'{quest_id}\s*(.+?)(?:\n|Level|\(|$)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, id_context, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if name and len(name) > 3 and not name.isdigit():
                        quest['quest_name'] = name
                        break
            
            # Try to find level near the ID
            level_match = re.search(rf'(?:Level|Lvl)\s*:?\s*(\d+)', id_context, re.IGNORECASE)
            if level_match:
                quest['level'] = int(level_match.group(1))
            
            quests.append(quest)
        
        # Remove duplicates by quest ID
        seen_ids = set()
        unique_quests = []
        for quest in quests:
            if quest['quest_id'] not in seen_ids:
                seen_ids.add(quest['quest_id'])
                unique_quests.append(quest)
        
        return unique_quests
    
    def _split_old_quest_sections(self, content: str) -> List[str]:
        """Split old format content into quest sections"""
        # Old format separation patterns
        separators = [
            r'-{10,}',  # Dashes
            r'={10,}',  # Equals
            r'Quest \d+:',  # Quest numbers
            r'\n\n\n+',  # Multiple newlines
            r'QUEST DATA COLLECTION'  # Section headers
        ]
        
        sections = [content]  # Start with full content
        
        for separator in separators:
            new_sections = []
            for section in sections:
                parts = re.split(separator, section)
                new_sections.extend(parts)
            sections = new_sections
        
        # Filter out empty sections
        return [section.strip() for section in sections if section.strip() and len(section.strip()) > 50]
    
    def _extract_npc_id_from_old_format(self, npc_text: str) -> Optional[int]:
        """Try to extract NPC ID from old format NPC description"""
        # Old format might have ID in parentheses or after name
        id_patterns = [
            r'\((\d+)\)',
            r'ID:\s*(\d+)',
            r'#(\d+)',
            r'(\d{4,6})'  # Fallback for bare numbers
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, npc_text)
            if match:
                npc_id = int(match.group(1))
                if 1 <= npc_id <= 100000:  # Reasonable NPC ID range
                    return npc_id
        
        return None
    
    def _extract_context_around_id(self, content: str, quest_id: int) -> str:
        """Extract text context around a quest ID"""
        # Find the position of the quest ID
        pattern = rf'\b{quest_id}\b'
        match = re.search(pattern, content)
        
        if match:
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 200)
            return content[start:end]
        
        return ""
    
    def _parse_player_info(self, player_text: str) -> Dict:
        """Parse player information from text"""
        player_info = {}
        
        # Common patterns
        patterns = {
            'race': r'(Human|Orc|Dwarf|Night Elf|Undead|Tauren|Gnome|Troll|Blood Elf|Draenei)',
            'class': r'(Warrior|Paladin|Hunter|Rogue|Priest|Death Knight|Shaman|Mage|Warlock|Druid)',
            'faction': r'(Alliance|Horde)',
            'level': r'Level\s*(\d+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, player_text, re.IGNORECASE)
            if match:
                player_info[key] = match.group(1).lower()
        
        return player_info
    
    def _parse_service_npcs(self, content: str) -> List[Dict]:
        """Parse service NPC data from new format"""
        service_npcs = []
        
        # Look for service NPCs section
        service_section = re.search(r'SERVICE NPCs ENCOUNTERED:?\s*\n(.*?)(?:\n\n=|\Z)', 
                                   content, re.DOTALL | re.IGNORECASE)
        
        if service_section:
            npc_blocks = re.split(r'\n\n(?=NPC:)', service_section.group(1))
            
            for block in npc_blocks:
                if 'NPC:' in block:
                    npc = self._parse_service_npc_block(block)
                    if npc:
                        service_npcs.append(npc)
        
        return service_npcs
    
    def _parse_service_npc_block(self, block: str) -> Optional[Dict]:
        """Parse a single service NPC block"""
        npc = {}
        
        # Parse NPC name and ID
        npc_match = re.search(r'NPC:\s*(.+?)\s*\(ID:\s*(\d+)\)', block)
        if npc_match:
            npc['name'] = npc_match.group(1).strip()
            npc['id'] = int(npc_match.group(2))
        else:
            return None
        
        # Parse services
        service_match = re.search(r'Services?:\s*(.+)', block, re.IGNORECASE)
        if service_match:
            services_text = service_match.group(1)
            npc['services'] = [s.strip() for s in services_text.split(',')]
        
        # Parse locations
        locations = []
        location_patterns = r'\*?\s*(.+?)\s+at\s+([\d.]+),\s*([\d.]+)'
        for match in re.findall(location_patterns, block):
            locations.append({
                'zone': match[0].strip(),
                'x': float(match[1]),
                'y': float(match[2])
            })
        
        if locations:
            npc['locations'] = locations
        
        return npc
    
    def _normalize_submission(self, submission: Dict) -> Dict:
        """Normalize parsed submission to consistent format"""
        
        # Ensure all quests have consistent field names
        for quest in submission.get('quests', []):
            # Normalize level fields
            if 'level' in quest and 'quest_level' not in quest:
                quest['quest_level'] = quest['level']
            
            # Ensure objectives is a list
            if 'objectives_text' in quest and isinstance(quest['objectives_text'], str):
                quest['objectives_list'] = [quest['objectives_text']]
            elif 'objectives_list' not in quest:
                quest['objectives_list'] = []
            
            # Add format metadata
            if 'format_notes' not in quest:
                quest['format_notes'] = []
            
            # Ensure required fields exist
            required_fields = ['quest_id', 'quest_name', 'quest_level']
            for field in required_fields:
                if field not in quest:
                    quest[field] = None
        
        return submission
    
    def _calculate_quality_score(self, submission: Dict) -> int:
        """Calculate overall quality score for the submission (0-100)"""
        score = 0
        max_score = 100
        
        # Format detection confidence (20 points)
        score += submission.get('format_confidence', 0) * 20
        
        # Quest data quality (60 points)
        quest_count = len(submission.get('quests', []))
        if quest_count > 0:
            quest_scores = []
            for quest in submission['quests']:
                quest_score = 0
                
                # Essential fields (40 points)
                if quest.get('quest_id'):
                    quest_score += 15
                if quest.get('quest_name'):
                    quest_score += 15
                if quest.get('quest_level') or quest.get('level'):
                    quest_score += 10
                
                # Additional fields (20 points)
                if quest.get('quest_giver_npc_id'):
                    quest_score += 5
                if quest.get('turn_in_npc_id'):
                    quest_score += 5
                if quest.get('objectives_list'):
                    quest_score += 5
                if quest.get('zone'):
                    quest_score += 5
                
                quest_scores.append(quest_score)
            
            avg_quest_score = sum(quest_scores) / len(quest_scores) if quest_scores else 0
            score += (avg_quest_score / 60) * 60  # Scale to 60 points
        
        # Additional data (20 points)
        if submission.get('player_info'):
            score += 5
        if submission.get('addon_version'):
            score += 5
        if submission.get('service_npcs'):
            score += 5
        if submission.get('submission_date'):
            score += 5
        
        return min(int(score), max_score)
    
    def get_conversion_stats(self) -> Dict:
        """Get statistics about format conversion"""
        total = sum(self.conversion_stats.values())
        
        if total == 0:
            return {'message': 'No submissions processed yet'}
        
        stats = {
            'total_submissions': total,
            'format_distribution': self.conversion_stats.copy(),
            'format_percentages': {
                fmt: (count / total) * 100 
                for fmt, count in self.conversion_stats.items()
            }
        }
        
        if self.parsed_submissions:
            avg_quality = sum(s.get('quality_score', 0) for s in self.parsed_submissions) / len(self.parsed_submissions)
            stats['average_quality_score'] = avg_quality
            
            # Quality distribution
            quality_levels = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
            for submission in self.parsed_submissions:
                score = submission.get('quality_score', 0)
                if score >= 90:
                    quality_levels['excellent'] += 1
                elif score >= 75:
                    quality_levels['good'] += 1
                elif score >= 50:
                    quality_levels['fair'] += 1
                else:
                    quality_levels['poor'] += 1
            
            stats['quality_distribution'] = quality_levels
        
        return stats

def main():
    """Test the unified parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python unified_parser.py <submission_file>")
        sys.exit(1)
    
    parser = UnifiedParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    submission = parser.parse(content, sys.argv[1])
    
    print(f"\nUnified Parser Results:")
    print(f"Detected Format: {submission['detected_format']} (confidence: {submission['format_confidence']:.2f})")
    print(f"Addon Version: {submission.get('addon_version', 'Unknown')}")
    print(f"Quality Score: {submission['quality_score']}/100")
    
    if submission.get('player_info'):
        print(f"Player Info: {submission['player_info']}")
    
    print(f"\nQuests Found: {len(submission.get('quests', []))}")
    for i, quest in enumerate(submission.get('quests', [])[:3]):  # Show first 3
        print(f"  {i+1}. Quest {quest.get('quest_id')}: {quest.get('quest_name')}")
        if quest.get('format_notes'):
            print(f"     Notes: {', '.join(quest['format_notes'])}")
    
    if submission.get('service_npcs'):
        print(f"\nService NPCs: {len(submission['service_npcs'])}")
        for npc in submission['service_npcs'][:3]:  # Show first 3
            print(f"  - {npc.get('name')} (ID: {npc.get('id')})")
    
    if submission.get('conversion_notes'):
        print(f"\nConversion Notes:")
        for note in submission['conversion_notes']:
            print(f"  - {note}")
    
    print(f"\nConversion Stats: {json.dumps(parser.get_conversion_stats(), indent=2)}")

if __name__ == "__main__":
    main()