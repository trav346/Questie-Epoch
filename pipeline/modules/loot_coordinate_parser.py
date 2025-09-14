#!/usr/bin/env python3
"""
Loot Coordinate Parser - Surgical module for item drop locations
Extracts coordinates where quest items were looted
"""

import re
from typing import Dict, List, Set
from collections import defaultdict

class LootCoordinateParser:
    """
    Extracts coordinates for locations where quest items were obtained.
    Includes both mob drops and container/object loots.
    """
    
    def __init__(self):
        self.loot_locations = defaultdict(list)
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Extract loot/item drop coordinates from quest submission.
        
        Returns:
            Dictionary with loot coordinate data
        """
        result = {
            'quest_id': quest_id,
            'item_locations': defaultdict(list),
            'container_locations': defaultdict(list),
            'total_loot_spots': 0,
            'unique_items': 0,
            'unique_containers': 0
        }
        
        # Pattern 1: Item drops from mobs
        # e.g., "- [72.6, 22.5] in Desolace - Looted Hatefury Claw from Hatefury Trickster"
        mob_loot_pattern = r'\[?([\d.]+),\s*([\d.]+)\]?\s+in\s+([^\n-]+?)\s*-\s*Looted\s+(.+?)\s+from\s+(.+?)$'
        
        for match in re.finditer(mob_loot_pattern, content, re.MULTILINE):
            x = float(match.group(1))
            y = float(match.group(2))
            zone = match.group(3).strip()
            item_name = match.group(4).strip()
            source_name = match.group(5).strip()
            
            # Validate coordinates
            if 0 < x < 100 and 0 < y < 100:
                result['item_locations'][item_name].append({
                    'x': x,
                    'y': y,
                    'zone': zone,
                    'source': source_name,
                    'source_type': 'mob'
                })
                result['total_loot_spots'] += 1
        
        # Pattern 2: Items from containers/objects
        # e.g., "- [45.2, 67.8] in Durotar - Obtained Ancient Gem from Ancient Chest"
        container_patterns = [
            r'\[?([\d.]+),\s*([\d.]+)\]?\s+in\s+([^\n-]+?)\s*-\s*(?:Obtained|Got|Received|Looted)\s+(.+?)\s+from\s+(.+?)$',
            r'\[?([\d.]+),\s*([\d.]+)\]?\s+in\s+([^\n-]+?)\s*-\s*Interacted with\s+(.+?)$'
        ]
        
        for pattern in container_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                if len(match.groups()) == 5:  # Has item and container
                    x = float(match.group(1))
                    y = float(match.group(2))
                    zone = match.group(3).strip()
                    item_name = match.group(4).strip()
                    container_name = match.group(5).strip()
                    
                    if 0 < x < 100 and 0 < y < 100:
                        result['item_locations'][item_name].append({
                            'x': x,
                            'y': y,
                            'zone': zone,
                            'source': container_name,
                            'source_type': 'container'
                        })
                        result['total_loot_spots'] += 1
                elif len(match.groups()) == 4:  # Just interaction
                    x = float(match.group(1))
                    y = float(match.group(2))
                    zone = match.group(3).strip()
                    object_name = match.group(4).strip()
                    
                    if 0 < x < 100 and 0 < y < 100:
                        result['container_locations'][object_name].append({
                            'x': x,
                            'y': y,
                            'zone': zone
                        })
        
        # Pattern 3: Ground objects/containers section
        ground_section = re.search(r'GROUND OBJECTS?(?:/CONTAINERS)?:?\s*\n(.*?)(?:\n\n|\Z)', 
                                   content, re.DOTALL | re.IGNORECASE)
        
        if ground_section:
            lines = ground_section.group(1).split('\n')
            for line in lines:
                # e.g., "Ancient Chest at [45.2, 67.8] in Durotar"
                obj_match = re.search(r'(.+?)\s+at\s+\[?([\d.]+),\s*([\d.]+)\]?(?:\s+in\s+(.+))?', line)
                if obj_match:
                    obj_name = obj_match.group(1).strip()
                    x = float(obj_match.group(2))
                    y = float(obj_match.group(3))
                    zone = obj_match.group(4).strip() if obj_match.group(4) else None
                    
                    if 0 < x < 100 and 0 < y < 100:
                        # Check if not duplicate
                        exists = any(
                            abs(loc['x'] - x) < 0.5 and abs(loc['y'] - y) < 0.5
                            for loc in result['container_locations'][obj_name]
                        )
                        
                        if not exists:
                            result['container_locations'][obj_name].append({
                                'x': x,
                                'y': y,
                                'zone': zone
                            })
        
        # Extract quest items list for reference
        items_section = re.search(r'QUEST ITEMS:?\s*\n(.*?)(?:\n\n|\Z)', 
                                  content, re.DOTALL | re.IGNORECASE)
        
        result['quest_items'] = []
        if items_section:
            lines = items_section.group(1).split('\n')
            for line in lines:
                item_match = re.search(r'(.+?)\s*\(ID:\s*(\d+)\)', line)
                if item_match:
                    result['quest_items'].append({
                        'name': item_match.group(1).strip(),
                        'id': int(item_match.group(2))
                    })
        
        # Update counts
        result['unique_items'] = len(result['item_locations'])
        result['unique_containers'] = len(result['container_locations'])
        
        # Convert defaultdicts to regular dicts for JSON
        result['item_locations'] = dict(result['item_locations'])
        result['container_locations'] = dict(result['container_locations'])
        
        return result
    
    def get_summary(self) -> Dict:
        """Get summary of parsed loot locations."""
        return {
            'total_items': len(self.loot_locations),
            'total_locations': sum(len(locs) for locs in self.loot_locations.values())
        }