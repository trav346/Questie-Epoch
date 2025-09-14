#!/usr/bin/env python3
"""
Mob Kill Coordinate Parser - Surgical module for extracting mob kill locations
Focuses on coordinates where quest mobs were killed
"""

import re
from typing import Dict, List, Set
from collections import defaultdict

class MobKillCoordinateParser:
    """
    Extracts coordinates for mobs that were killed for quest objectives.
    Fast, pattern-based extraction without complex objective parsing.
    """
    
    def __init__(self):
        self.mob_coordinates = defaultdict(list)
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Extract mob kill coordinates from quest submission.
        
        Returns:
            Dictionary with mob kill coordinate data
        """
        result = {
            'quest_id': quest_id,
            'mob_kills': defaultdict(list),
            'total_locations': 0,
            'unique_mobs': 0
        }
        
        # Pattern 1: From OBJECTIVES section - "Looted X from Y" format
        # e.g., "- [72.6, 22.5] in Desolace - Looted Hatefury Claw from Hatefury Trickster"
        loot_pattern = r'\[?([\d.]+),\s*([\d.]+)\]?\s+in\s+([^\n-]+?)\s*-\s*Looted\s+.+?\s+from\s+(.+?)$'
        
        for match in re.finditer(loot_pattern, content, re.MULTILINE):
            x = float(match.group(1))
            y = float(match.group(2))
            zone = match.group(3).strip()
            mob_name = match.group(4).strip()
            
            # Validate coordinates
            if 0 < x < 100 and 0 < y < 100:
                result['mob_kills'][mob_name].append({
                    'x': x,
                    'y': y,
                    'zone': zone
                })
                result['total_locations'] += 1
        
        # Pattern 2: From TRACKED QUEST MOBS section (if present)
        # e.g., "Hatefury Trickster (ID: 4670, Level: 28-29) at 71.3, 19.1 in Desolace"
        tracked_section = re.search(r'TRACKED QUEST MOBS:?\s*\n(.*?)(?:\n\n|\Z)', 
                                    content, re.DOTALL | re.IGNORECASE)
        
        if tracked_section:
            mob_lines = tracked_section.group(1).split('\n')
            for line in mob_lines:
                mob_match = re.search(
                    r'(.+?)\s*\(ID:\s*(\d+)[^)]*\)\s*at\s*([\d.]+),\s*([\d.]+)(?:\s+in\s+(.+))?',
                    line
                )
                if mob_match:
                    mob_name = mob_match.group(1).strip()
                    mob_id = int(mob_match.group(2))
                    x = float(mob_match.group(3))
                    y = float(mob_match.group(4))
                    zone = mob_match.group(5).strip() if mob_match.group(5) else None
                    
                    # Validate and avoid duplicates
                    if 0 < x < 100 and 0 < y < 100:
                        # Check if this coordinate already exists for this mob
                        exists = any(
                            abs(coord['x'] - x) < 0.5 and abs(coord['y'] - y) < 0.5
                            for coord in result['mob_kills'][mob_name]
                        )
                        
                        if not exists:
                            result['mob_kills'][mob_name].append({
                                'x': x,
                                'y': y,
                                'zone': zone,
                                'id': mob_id
                            })
                            result['total_locations'] += 1
        
        # Pattern 3: Kill objectives mentioned explicitly
        # e.g., "Kill 10 Hatefury Trickster"
        kill_pattern = r'(?:kill|slay|defeat|destroy)\s+(\d+)\s+(.+?)(?:\n|$)'
        kill_matches = re.findall(kill_pattern, content, re.IGNORECASE)
        
        # Store kill requirements for reference
        result['kill_requirements'] = {}
        for count, mob_name in kill_matches:
            result['kill_requirements'][mob_name.strip()] = int(count)
        
        # Update unique mob count
        result['unique_mobs'] = len(result['mob_kills'])
        
        # Convert defaultdict to regular dict for JSON serialization
        result['mob_kills'] = dict(result['mob_kills'])
        
        return result
    
    def get_summary(self) -> Dict:
        """Get summary of parsed mob coordinates."""
        total_mobs = len(self.mob_coordinates)
        total_coords = sum(len(coords) for coords in self.mob_coordinates.values())
        
        return {
            'unique_mobs': total_mobs,
            'total_coordinates': total_coords,
            'average_coords_per_mob': total_coords / total_mobs if total_mobs > 0 else 0
        }