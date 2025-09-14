#!/usr/bin/env python3
"""
Interact Coordinate Parser - Surgical module for object interaction locations
Extracts coordinates for clickable objects, books, levers, etc.
"""

import re
from typing import Dict, List
from collections import defaultdict

class InteractCoordinateParser:
    """
    Extracts coordinates for interactive objects that need to be clicked/used.
    Fast extraction of interaction points without complex logic.
    """
    
    def __init__(self):
        self.interaction_points = defaultdict(list)
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Extract interaction coordinates from quest submission.
        
        Returns:
            Dictionary with interaction coordinate data
        """
        result = {
            'quest_id': quest_id,
            'interactions': defaultdict(list),
            'total_interactions': 0,
            'unique_objects': 0
        }
        
        # Pattern 1: Direct interaction mentions
        # e.g., "- [45.2, 67.8] in Durotar - Interacted with Ancient Tome"
        # e.g., "- [45.2, 67.8] in Durotar - Clicked on Mysterious Lever"
        # e.g., "- [45.2, 67.8] in Durotar - Used Control Panel"
        interaction_patterns = [
            r'\[?([\d.]+),\s*([\d.]+)\]?\s+in\s+([^\n-]+?)\s*-\s*(?:Interacted with|Clicked on|Used|Activated|Examined|Read)\s+(.+?)$',
            r'(?:Interacted with|Clicked on|Used|Activated|Examined|Read)\s+(.+?)\s+at\s+\[?([\d.]+),\s*([\d.]+)\]?(?:\s+in\s+(.+))?'
        ]
        
        for pattern in interaction_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                if len(match.groups()) == 4 and match.group(1):  # First pattern
                    try:
                        x = float(match.group(1))
                        y = float(match.group(2))
                        zone = match.group(3).strip()
                        object_name = match.group(4).strip()
                    except:
                        continue
                else:  # Second pattern
                    try:
                        object_name = match.group(1).strip()
                        x = float(match.group(2))
                        y = float(match.group(3))
                        zone = match.group(4).strip() if match.group(4) else None
                    except:
                        continue
                
                # Validate coordinates
                if 0 < x < 100 and 0 < y < 100:
                    # Remove common suffixes/prefixes
                    object_name = self._clean_object_name(object_name)
                    
                    result['interactions'][object_name].append({
                        'x': x,
                        'y': y,
                        'zone': zone,
                        'type': 'interact'
                    })
                    result['total_interactions'] += 1
        
        # Pattern 2: Ground objects that are typically interacted with
        ground_section = re.search(
            r'GROUND OBJECTS?(?:/CONTAINERS)?:?\s*\n(.*?)(?:\n\n|\Z)', 
            content, re.DOTALL | re.IGNORECASE
        )
        
        if ground_section:
            lines = ground_section.group(1).split('\n')
            for line in lines:
                # Skip item containers (handled by loot parser)
                if any(word in line.lower() for word in ['chest', 'cache', 'crate', 'barrel']):
                    continue
                
                # Look for interactive objects
                # e.g., "Control Panel at [45.2, 67.8] in Durotar"
                obj_match = re.search(r'(.+?)\s+at\s+\[?([\d.]+),\s*([\d.]+)\]?(?:\s+in\s+(.+))?', line)
                if obj_match:
                    obj_name = self._clean_object_name(obj_match.group(1).strip())
                    
                    # Check if it's an interactive object type
                    if self._is_interactive_object(obj_name):
                        x = float(obj_match.group(2))
                        y = float(obj_match.group(3))
                        zone = obj_match.group(4).strip() if obj_match.group(4) else None
                        
                        if 0 < x < 100 and 0 < y < 100:
                            # Avoid duplicates
                            exists = any(
                                abs(loc['x'] - x) < 0.5 and abs(loc['y'] - y) < 0.5
                                for loc in result['interactions'][obj_name]
                            )
                            
                            if not exists:
                                result['interactions'][obj_name].append({
                                    'x': x,
                                    'y': y,
                                    'zone': zone,
                                    'type': 'ground_object'
                                })
                                result['total_interactions'] += 1
        
        # Pattern 3: Quest objectives mentioning interactions
        # e.g., "Activate 5 Power Crystals"
        # e.g., "Use the Ancient Altar"
        objective_patterns = [
            r'(?:Activate|Use|Click|Interact with|Examine|Read)\s+(?:the\s+)?(.+?)(?:\s+\d+\s+times?|\s+x\d+)?$',
            r'(.+?)\s+(?:activated|used|clicked|interacted|examined|read)(?:\s+\d+/\d+)?$'
        ]
        
        result['interaction_objectives'] = []
        for pattern in objective_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                obj_name = self._clean_object_name(match.group(1).strip())
                if obj_name and len(obj_name) > 2:  # Avoid single letters/numbers
                    result['interaction_objectives'].append(obj_name)
        
        # Update unique object count
        result['unique_objects'] = len(result['interactions'])
        
        # Convert defaultdict to regular dict for JSON
        result['interactions'] = dict(result['interactions'])
        
        return result
    
    def _clean_object_name(self, name: str) -> str:
        """Clean up object name by removing common affixes."""
        # Remove trailing IDs or numbers
        name = re.sub(r'\s*\((?:ID:|Object\s*ID:)?\s*\d+\)$', '', name)
        
        # Remove leading "the"
        if name.lower().startswith('the '):
            name = name[4:]
        
        return name.strip()
    
    def _is_interactive_object(self, name: str) -> bool:
        """Check if an object name suggests it's interactive."""
        interactive_keywords = [
            'altar', 'shrine', 'panel', 'console', 'lever', 'button',
            'switch', 'tome', 'book', 'scroll', 'tablet', 'crystal',
            'orb', 'rune', 'glyph', 'pedestal', 'brazier', 'beacon',
            'portal', 'gate', 'door', 'statue', 'monument', 'device',
            'machine', 'terminal', 'interface', 'relay', 'pylon'
        ]
        
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in interactive_keywords)
    
    def get_summary(self) -> Dict:
        """Get summary of parsed interaction points."""
        return {
            'total_objects': len(self.interaction_points),
            'total_interactions': sum(len(locs) for locs in self.interaction_points.values())
        }