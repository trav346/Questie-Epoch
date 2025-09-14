#!/usr/bin/env python3
"""
Trigger Parser - Parse exploration triggers for quests
Handles Field 9: triggerEnd - exploration objectives
"""

import re
import logging
from typing import Dict, List, Optional, Tuple


class TriggerParser:
    """
    Parses exploration triggers and area discovery objectives
    Field 9 format: {text, {[zoneID]={{x,y}}}}
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common exploration trigger keywords
        self.exploration_keywords = [
            'explore',
            'discover',
            'find',
            'locate',
            'reach',
            'visit',
            'scout',
            'investigate',
            'survey',
            'search',
            'uncover',
            'reveal',
            'travel to',
            'go to',
            'journey to',
        ]
        
        # Location type indicators
        self.location_types = [
            'area',
            'region',
            'zone',
            'cave',
            'ruins',
            'camp',
            'outpost',
            'tower',
            'fortress',
            'temple',
            'shrine',
            'graveyard',
            'tomb',
            'lake',
            'river',
            'mountain',
            'valley',
            'forest',
            'desert',
            'beach',
            'island',
        ]
    
    def parse(self, content: str, quest_id: int = None) -> Optional[Dict]:
        """
        Parse exploration triggers from quest content
        
        Args:
            content: Quest submission text
            quest_id: Quest ID for reference
            
        Returns:
            Trigger data in format: {text, {[zoneID]={{x,y}}}}
            or None if no exploration objectives
        """
        trigger_data = None
        
        # Check if this is an exploration quest
        if not self._is_exploration_quest(content):
            return None
        
        # Extract exploration text
        exploration_text = self._extract_exploration_text(content)
        
        if exploration_text:
            # Extract locations and coordinates
            locations = self._extract_exploration_locations(content)
            
            if locations:
                trigger_data = {
                    'text': exploration_text,
                    'locations': locations,
                    'formatted': self._format_trigger_data(exploration_text, locations)
                }
                
                self.logger.info(f"Found exploration trigger: {exploration_text}")
        
        return trigger_data
    
    def _is_exploration_quest(self, content: str) -> bool:
        """Determine if quest has exploration objectives"""
        content_lower = content.lower()
        
        # Check for exploration keywords
        for keyword in self.exploration_keywords:
            if keyword in content_lower:
                # Verify it's in objective context
                patterns = [
                    f'objective[s]?.*{keyword}',
                    f'{keyword}.*area',
                    f'{keyword}.*location',
                    f'{keyword}.*place',
                    f'you must {keyword}',
                    f'quest.*{keyword}',
                ]
                
                for pattern in patterns:
                    if re.search(pattern, content_lower, re.DOTALL):
                        return True
        
        return False
    
    def _extract_exploration_text(self, content: str) -> Optional[str]:
        """Extract the exploration objective text"""
        exploration_texts = []
        
        # Pattern 1: Direct exploration objectives
        patterns = [
            r'(?:explore|discover|find|locate|scout)\s+([A-Z][^.!?\n]+)',
            r'(?:travel|journey|go)\s+to\s+([A-Z][^.!?\n]+)',
            r'(?:investigate|survey|search)\s+(?:the\s+)?([A-Z][^.!?\n]+)',
            r'(?:reach|visit)\s+(?:the\s+)?([A-Z][^.!?\n]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                text = match.group(0).strip()
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)
                text = text.rstrip('.,;:')
                exploration_texts.append(text)
        
        # Pattern 2: Exploration in objectives section
        obj_pattern = r'OBJECTIVE[S]?:?\s*\n(.*?)(?:\n\n|TURN-IN|REWARD|$)'
        obj_match = re.search(obj_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if obj_match:
            objectives = obj_match.group(1)
            for keyword in self.exploration_keywords:
                if keyword in objectives.lower():
                    # Extract the specific line
                    lines = objectives.split('\n')
                    for line in lines:
                        if keyword in line.lower():
                            clean_line = line.strip('- •·').strip()
                            if clean_line and clean_line not in exploration_texts:
                                exploration_texts.append(clean_line)
        
        # Return the most complete exploration text
        if exploration_texts:
            # Sort by length and return longest (likely most complete)
            exploration_texts.sort(key=len, reverse=True)
            return exploration_texts[0]
        
        return None
    
    def _extract_exploration_locations(self, content: str) -> Dict:
        """Extract location names and coordinates for exploration"""
        locations = {}
        
        # Pattern for location with coordinates
        coord_pattern = r'(?:at|near|around)?\s*\[?(\d{1,2}(?:\.\d)?),\s*(\d{1,2}(?:\.\d)?)\]?'
        
        # Extract named locations
        for location_type in self.location_types:
            pattern = rf'(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)\s+{location_type}'
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                location_name = match.group(1).strip()
                
                # Look for coordinates near this location mention
                # Search within 100 characters after the location
                search_area = content[match.end():match.end()+100]
                coord_match = re.search(coord_pattern, search_area)
                
                if coord_match:
                    x = float(coord_match.group(1))
                    y = float(coord_match.group(2))
                    
                    # Get zone ID (would integrate with zone_mapper)
                    zone_id = self._get_zone_id_for_location(location_name, content)
                    
                    if zone_id not in locations:
                        locations[zone_id] = []
                    
                    locations[zone_id].append({
                        'name': location_name,
                        'x': x,
                        'y': y
                    })
        
        # Also check for direct coordinate mentions
        direct_pattern = r'(?:explore|discover|reach|visit)\s+(?:the\s+)?(?:area\s+)?(?:at|near)?\s*' + coord_pattern
        direct_matches = re.finditer(direct_pattern, content, re.IGNORECASE)
        
        for match in direct_matches:
            x = float(match.group(1))
            y = float(match.group(2))
            
            # Try to determine zone from context
            zone_id = self._extract_zone_from_context(content, match.start())
            
            if zone_id not in locations:
                locations[zone_id] = []
            
            locations[zone_id].append({
                'name': 'Exploration Point',
                'x': x,
                'y': y
            })
        
        return locations
    
    def _get_zone_id_for_location(self, location_name: str, content: str) -> int:
        """Get zone ID for a location (placeholder - would use zone_mapper)"""
        # This would integrate with zone_mapper.py
        # For now, return a default zone ID
        
        # Check if zone is mentioned nearby
        zone_pattern = r'(?:in|at|near)\s+([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)'
        zone_matches = re.finditer(zone_pattern, content, re.IGNORECASE)
        
        for match in zone_matches:
            potential_zone = match.group(1)
            # Would call zone_mapper here
            # For testing, use some known zones
            zone_map = {
                'Durotar': 14,
                'Elwynn Forest': 12,
                'The Barrens': 17,
                'Stormwind': 1519,
                'Orgrimmar': 1637,
            }
            
            if potential_zone in zone_map:
                return zone_map[potential_zone]
        
        # Default to zone -1 (unknown)
        return -1
    
    def _extract_zone_from_context(self, content: str, position: int) -> int:
        """Extract zone ID from context around a position"""
        # Look within 200 characters before and after
        start = max(0, position - 200)
        end = min(len(content), position + 200)
        context = content[start:end]
        
        return self._get_zone_id_for_location('', context)
    
    def _format_trigger_data(self, text: str, locations: Dict) -> Tuple:
        """
        Format trigger data for database entry
        
        Format: {text, {[zoneID]={{x,y},...}}}
        """
        if not locations:
            return (text, {})
        
        # Convert location data to database format
        zone_coords = {}
        
        for zone_id, coords in locations.items():
            if zone_id not in zone_coords:
                zone_coords[zone_id] = []
            
            for coord in coords:
                zone_coords[zone_id].append([coord['x'], coord['y']])
        
        return (text, zone_coords)
    
    def generate_lua_entry(self, trigger_data: Dict) -> str:
        """Generate Lua code for triggerEnd field"""
        if not trigger_data:
            return "nil"
        
        text = trigger_data['text']
        locations = trigger_data.get('locations', {})
        
        if not locations:
            return f'{{"{text}", {{}}}}'
        
        # Build coordinate structure
        coord_parts = []
        for zone_id, coords in locations.items():
            coord_list = ','.join([f'{{{c["x"]},{c["y"]}}}' for c in coords])
            coord_parts.append(f'[{zone_id}]={{{coord_list}}}')
        
        coord_str = '{' + ','.join(coord_parts) + '}'
        
        return f'{{"{text}", {coord_str}}}'


def main():
    """Test the trigger parser"""
    parser = TriggerParser()
    
    # Test exploration quest
    test_content = """
    Quest: Scout the Area
    
    OBJECTIVES:
    - Explore the Hidden Cave at 45.2, 67.8
    - Discover the Ancient Ruins
    - Scout the enemy camp near 52.1, 73.4
    
    You must explore three key locations in Durotar to complete this quest.
    
    The Hidden Cave is located in the northern hills.
    The Ancient Ruins can be found in the eastern valley.
    """
    
    result = parser.parse(test_content, quest_id=12345)
    
    if result:
        print("Exploration Trigger Found!")
        print(f"Text: {result['text']}")
        print(f"Locations: {result['locations']}")
        print(f"Lua Entry: {parser.generate_lua_entry(result)}")
    else:
        print("No exploration triggers found")


if __name__ == "__main__":
    main()