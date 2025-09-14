#!/usr/bin/env python3
"""
Object Parser Module - Extracts ground objects and containers from quest submissions
Handles interactive world objects, containers, and clickable quest objects
"""

import re
from typing import Dict, List, Optional, Tuple
import json

class ObjectParser:
    """Parses ground objects and containers from quest submissions"""
    
    def __init__(self):
        self.parsed_objects = []
        self.parse_errors = []
        
        # Object type patterns
        self.object_keywords = {
            'container': ['chest', 'crate', 'box', 'barrel', 'sack', 'bag', 'cache', 'stash'],
            'book': ['book', 'tome', 'scroll', 'manuscript', 'journal', 'ledger', 'notes'],
            'interactive': ['lever', 'switch', 'button', 'valve', 'console', 'panel', 'device'],
            'resource': ['vein', 'deposit', 'node', 'herb', 'flower', 'plant', 'bush'],
            'quest': ['banner', 'flag', 'altar', 'shrine', 'stone', 'crystal', 'orb', 'rune'],
            'misc': ['corpse', 'remains', 'bones', 'pile', 'mound', 'debris']
        }
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse ground objects from quest submission
        
        Returns:
            Dictionary with structured object data
        """
        objects = {
            'quest_id': quest_id,
            'ground_objects': [],
            'containers': [],
            'interactive_objects': [],
            'quest_objects': [],
            'total_objects': 0,
            'has_object_ids': False,
            'has_coordinates': False
        }
        
        # Parse different sections for objects
        objects['ground_objects'] = self._parse_ground_objects_section(content)
        objects['containers'] = self._parse_containers(content)
        objects['interactive_objects'] = self._parse_interactive_objects(content)
        objects['quest_objects'] = self._parse_quest_objects(content)
        
        # Deduplicate and merge objects
        all_objects = self._merge_and_deduplicate(objects)
        
        # Count totals and check for IDs/coordinates
        objects['total_objects'] = len(all_objects)
        objects['has_object_ids'] = any(obj.get('id') for obj in all_objects)
        objects['has_coordinates'] = any(obj.get('coordinates') for obj in all_objects)
        
        self.parsed_objects.append(objects)
        return objects
    
    def _parse_ground_objects_section(self, content: str) -> List[Dict]:
        """Parse GROUND OBJECTS section"""
        objects = []
        
        # Look for GROUND OBJECTS section
        patterns = [
            r'GROUND OBJECTS?:?\s*\n(.*?)(?:\n\n[A-Z]|\Z)',
            r'OBJECTS? INTERACTED:?\s*\n(.*?)(?:\n\n[A-Z]|\Z)',
            r'CONTAINERS?:?\s*\n(.*?)(?:\n\n[A-Z]|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                objects.extend(self._extract_objects_from_section(section))
        
        return objects
    
    def _extract_objects_from_section(self, section: str) -> List[Dict]:
        """Extract object data from a text section"""
        objects = []
        
        # Parse lines like:
        # "Ancient Tome (Object ID: 185000) at 45.2, 67.3 in Durotar"
        # "Sun-Ripened Banana at [25.3, 67.2]"
        # "Sealed Chest (ID: 2843) - Location: 60.1, 53.3"
        
        patterns = [
            # With object ID and coordinates
            r'(.+?)\s*\((?:Object\s*)?ID:\s*(\d+)\)\s*(?:at|@|-\s*Location:)\s*\[?([\d.]+),\s*([\d.]+)\]?(?:\s+in\s+(.+?))?(?:\n|$)',
            # With just object ID
            r'(.+?)\s*\((?:Object\s*)?ID:\s*(\d+)\)',
            # With just coordinates
            r'(.+?)\s+(?:at|@)\s*\[?([\d.]+),\s*([\d.]+)\]?(?:\s+in\s+(.+?))?(?:\n|$)',
            # Simple name only
            r'^[-*]?\s*(.+?)(?:\s*-\s*(.+?))?$'
        ]
        
        lines = section.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            matched = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    obj = self._create_object_from_match(match)
                    if obj and not self._is_duplicate(obj, objects):
                        objects.append(obj)
                        matched = True
                        break
            
            # If no pattern matched but line has content, try to extract object name
            if not matched and line and not line.startswith('--'):
                # Clean up the line
                clean_name = re.sub(r'^[-*•]\s*', '', line)
                clean_name = re.sub(r'\s*\(.*?\)\s*', '', clean_name)
                clean_name = re.sub(r'\s+at\s+.*', '', clean_name)
                clean_name = re.sub(r'\s*:\s*\d+/\d+', '', clean_name)
                
                if clean_name and len(clean_name) > 2:
                    obj = {
                        'name': clean_name.strip(),
                        'id': None,
                        'type': self._determine_object_type(clean_name),
                        'coordinates': []
                    }
                    if not self._is_duplicate(obj, objects):
                        objects.append(obj)
        
        return objects
    
    def _create_object_from_match(self, match: Tuple) -> Optional[Dict]:
        """Create object dictionary from regex match"""
        groups = match.groups()
        
        if len(groups) >= 5:  # Full match with ID and coords
            return {
                'name': groups[0].strip(),
                'id': int(groups[1]) if groups[1] else None,
                'coordinates': [{'x': float(groups[2]), 'y': float(groups[3])}] if groups[2] and groups[3] else [],
                'zone': groups[4].strip() if len(groups) > 4 and groups[4] else None,
                'type': self._determine_object_type(groups[0])
            }
        elif len(groups) == 4:  # Name with coords
            if groups[1] and groups[1].isdigit():  # Has ID
                return {
                    'name': groups[0].strip(),
                    'id': int(groups[1]),
                    'type': self._determine_object_type(groups[0]),
                    'coordinates': []
                }
            else:  # Has coordinates
                return {
                    'name': groups[0].strip(),
                    'id': None,
                    'coordinates': [{'x': float(groups[1]), 'y': float(groups[2])}] if groups[1] and groups[2] else [],
                    'zone': groups[3].strip() if groups[3] else None,
                    'type': self._determine_object_type(groups[0])
                }
        elif len(groups) >= 2:  # Name with ID
            return {
                'name': groups[0].strip(),
                'id': int(groups[1]) if groups[1] and groups[1].isdigit() else None,
                'type': self._determine_object_type(groups[0]),
                'coordinates': []
            }
        elif len(groups) >= 1 and groups[0]:  # Just name
            return {
                'name': groups[0].strip(),
                'id': None,
                'type': self._determine_object_type(groups[0]),
                'coordinates': []
            }
        
        return None
    
    def _determine_object_type(self, name: str) -> str:
        """Determine the type of object from its name"""
        name_lower = name.lower()
        
        for obj_type, keywords in self.object_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                return obj_type
        
        # Default categorization
        if 'quest' in name_lower:
            return 'quest'
        elif any(x in name_lower for x in ['loot', 'supply', 'cache']):
            return 'container'
        
        return 'misc'
    
    def _parse_containers(self, content: str) -> List[Dict]:
        """Parse container objects specifically"""
        containers = []
        
        # Look for container mentions
        container_patterns = [
            r'(?:opened?|loot(?:ed)?|found?)\s+(?:a\s+)?(.+?(?:chest|crate|box|barrel|cache|stash))',
            r'(.+?(?:chest|crate|box|barrel|cache|stash))\s+(?:at|@|located)',
            r'Container:\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in container_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                name = match.strip() if isinstance(match, str) else match[0].strip()
                
                # Try to find ID and coordinates
                obj = {
                    'name': name,
                    'id': self._find_object_id(name, content),
                    'type': 'container',
                    'coordinates': self._find_coordinates_near_text(name, content)
                }
                
                if not self._is_duplicate(obj, containers):
                    containers.append(obj)
        
        return containers
    
    def _parse_interactive_objects(self, content: str) -> List[Dict]:
        """Parse interactive objects like levers, switches, etc."""
        interactive = []
        
        # Look for interaction mentions
        interaction_patterns = [
            r'(?:activate|use|click|interact\s+with|pull|push)\s+(?:the\s+)?(.+?)(?:\n|$|\.)',
            r'(.+?)\s+(?:activated|used|clicked|interacted)',
        ]
        
        for pattern in interaction_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                name = match.strip() if isinstance(match, str) else match[0].strip()
                
                # Filter out non-objects (NPCs, items, etc.)
                if any(skip in name.lower() for skip in ['npc', 'quest', 'talk', 'speak', 'kill', 'slay']):
                    continue
                
                obj = {
                    'name': name,
                    'id': self._find_object_id(name, content),
                    'type': 'interactive',
                    'coordinates': self._find_coordinates_near_text(name, content)
                }
                
                if not self._is_duplicate(obj, interactive):
                    interactive.append(obj)
        
        return interactive
    
    def _parse_quest_objects(self, content: str) -> List[Dict]:
        """Parse quest-specific objects"""
        quest_objects = []
        
        # Look in objectives for object interactions
        obj_section = re.search(r'OBJECTIVES?:?\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if obj_section:
            objectives_text = obj_section.group(1)
            
            # Look for object-related objectives
            object_patterns = [
                r'(?:find|locate|discover|examine|investigate|read|activate|use)\s+(?:the\s+)?(.+?)(?:\n|$|:)',
                r'(.+?)\s+(?:found|located|discovered|examined|read|activated):\s*\d+/\d+',
            ]
            
            for pattern in object_patterns:
                matches = re.findall(pattern, objectives_text, re.IGNORECASE)
                for match in matches:
                    name = match.strip() if isinstance(match, str) else match[0].strip()
                    
                    # Filter out creatures and NPCs
                    if any(skip in name.lower() for skip in ['npc', 'kill', 'slay', 'defeat', 'slain']):
                        continue
                    
                    obj = {
                        'name': name,
                        'id': self._find_object_id(name, content),
                        'type': 'quest',
                        'coordinates': self._find_coordinates_near_text(name, content)
                    }
                    
                    if not self._is_duplicate(obj, quest_objects):
                        quest_objects.append(obj)
        
        return quest_objects
    
    def _find_object_id(self, name: str, content: str) -> Optional[int]:
        """Try to find object ID for a given object name"""
        # Escape special regex characters in name
        escaped_name = re.escape(name)
        
        patterns = [
            rf'{escaped_name}\s*\((?:Object\s*)?ID:\s*(\d+)\)',
            rf'Object ID:\s*(\d+).*?{escaped_name}',
            rf'{escaped_name}.*?Object ID:\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _find_coordinates_near_text(self, text: str, content: str) -> List[Dict]:
        """Find coordinates mentioned near the given text"""
        coords = []
        escaped_text = re.escape(text)
        
        # Look for coordinates within 50 characters of the text
        patterns = [
            rf'{escaped_text}.{{0,50}}?\[?([\d.]+),\s*([\d.]+)\]?',
            rf'\[?([\d.]+),\s*([\d.]+)\]?.{{0,50}}?{escaped_text}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    coord = {'x': float(match[0]), 'y': float(match[1])}
                    if 0 <= coord['x'] <= 100 and 0 <= coord['y'] <= 100:
                        if not any(abs(c['x'] - coord['x']) < 1 and abs(c['y'] - coord['y']) < 1 for c in coords):
                            coords.append(coord)
                except (ValueError, IndexError):
                    continue
        
        return coords
    
    def _merge_and_deduplicate(self, objects: Dict) -> List[Dict]:
        """Merge all object lists and remove duplicates"""
        all_objects = []
        
        for category in ['ground_objects', 'containers', 'interactive_objects', 'quest_objects']:
            for obj in objects.get(category, []):
                if not self._is_duplicate(obj, all_objects):
                    all_objects.append(obj)
        
        return all_objects
    
    def _is_duplicate(self, obj: Dict, object_list: List[Dict]) -> bool:
        """Check if object is already in the list"""
        for existing in object_list:
            # Check by ID if both have IDs
            if obj.get('id') and existing.get('id'):
                if obj['id'] == existing['id']:
                    # Merge coordinates if different
                    for coord in obj.get('coordinates', []):
                        if not any(abs(c['x'] - coord['x']) < 1 and abs(c['y'] - coord['y']) < 1 
                                  for c in existing.get('coordinates', [])):
                            existing.setdefault('coordinates', []).append(coord)
                    return True
            
            # Check by name similarity
            if obj.get('name') and existing.get('name'):
                if obj['name'].lower() == existing['name'].lower():
                    # Merge data if one has ID and other doesn't
                    if obj.get('id') and not existing.get('id'):
                        existing['id'] = obj['id']
                    # Merge coordinates
                    for coord in obj.get('coordinates', []):
                        if not any(abs(c['x'] - coord['x']) < 1 and abs(c['y'] - coord['y']) < 1 
                                  for c in existing.get('coordinates', [])):
                            existing.setdefault('coordinates', []).append(coord)
                    return True
        
        return False
    
    def get_validation_stats(self) -> Dict:
        """Get statistics about parsed objects"""
        total_parsed = len(self.parsed_objects)
        total_objects = sum(p['total_objects'] for p in self.parsed_objects)
        with_ids = sum(1 for p in self.parsed_objects if p['has_object_ids'])
        with_coords = sum(1 for p in self.parsed_objects if p['has_coordinates'])
        
        return {
            'total_submissions': total_parsed,
            'total_objects': total_objects,
            'submissions_with_ids': with_ids,
            'submissions_with_coords': with_coords,
            'average_objects': total_objects / total_parsed if total_parsed > 0 else 0
        }