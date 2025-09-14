#!/usr/bin/env python3
"""
Objective Parser Module - Extracts and structures quest objectives
Handles kill/collect/interact/explore objectives with coordinates
"""

import re
from typing import Dict, List, Optional, Tuple
import json

class ObjectiveParser:
    """Parses quest objectives from submissions into structured data"""
    
    def __init__(self):
        self.parsed_objectives = []
        self.parse_errors = []
        
        # Objective type patterns
        self.objective_types = {
            'kill': ['slain', 'killed', 'defeated', 'destroy', 'kill', 'slay'],
            'collect': ['collected', 'gather', 'obtain', 'loot', 'retrieved'],
            'interact': ['activate', 'use', 'click', 'interact', 'speak'],
            'explore': ['discover', 'explore', 'find', 'reach', 'visit'],
            'escort': ['escort', 'protect', 'defend', 'save'],
            'deliver': ['deliver', 'bring', 'return', 'give'],
        }
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse objectives from quest submission
        
        Returns:
            Dictionary with structured objective data
        """
        objectives = {
            'quest_id': quest_id,
            'objectives_text': None,
            'objectives_list': [],
            'creatures': [],
            'items': [],
            'objects': [],
            'exploration': [],
            'spells': [],
            'kill_credit': [],
            'has_complete_data': False
        }
        
        # Extract objectives section
        obj_section = self._extract_objectives_section(content)
        if obj_section:
            objectives['objectives_text'] = obj_section
            objectives['objectives_list'] = self._parse_objective_list(obj_section)
            
            # Parse specific objective types
            objectives['creatures'] = self._parse_creature_objectives(obj_section, content)
            objectives['items'] = self._parse_item_objectives(obj_section, content)
            objectives['objects'] = self._parse_object_objectives(content)
            objectives['exploration'] = self._parse_exploration_objectives(obj_section)
            
            # Check if we have complete data
            objectives['has_complete_data'] = self._validate_completeness(objectives)
        
        self.parsed_objectives.append(objectives)
        return objectives
    
    def _extract_objectives_section(self, content: str) -> Optional[str]:
        """Extract the OBJECTIVES section from submission"""
        patterns = [
            r'OBJECTIVES?:?\s*\n(.*?)(?:\n\nTURN-?IN|\n\nGROUND|\n\nDATABASE|\Z)',
            r'Quest Objectives?:?\s*\n(.*?)(?:\n\n|\Z)',
            r'Objectives?:?\s*\n(.*?)(?:\n\n|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _parse_objective_list(self, objectives_text: str) -> List[Dict]:
        """Parse individual objectives from text"""
        objectives = []
        
        # Look for numbered/bulleted objectives
        patterns = [
            r'(?:^|\n)\s*(?:\d+\.|[-*])\s*(.+?):\s*(\d+)/(\d+)',  # "1. Kill Boars: 0/10"
            r'(?:^|\n)\s*(.+?):\s*(\d+)/(\d+)',  # "Kill Boars: 0/10"
            r'(?:^|\n)\s*(?:\d+\.|[-*])\s*(.+?)(?:\n|$)',  # "1. Kill Boars"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, objectives_text, re.MULTILINE)
            for match in matches:
                if len(match) == 3:
                    # Has progress numbers
                    obj = {
                        'text': match[0].strip(),
                        'current': int(match[1]),
                        'required': int(match[2]),
                        'type': self._determine_objective_type(match[0])
                    }
                else:
                    # Just text
                    obj = {
                        'text': match[0].strip() if isinstance(match, tuple) else match.strip(),
                        'current': 0,
                        'required': 1,
                        'type': self._determine_objective_type(match[0] if isinstance(match, tuple) else match)
                    }
                
                if obj['text'] and not any(o['text'] == obj['text'] for o in objectives):
                    objectives.append(obj)
        
        return objectives
    
    def _determine_objective_type(self, text: str) -> str:
        """Determine the type of objective from its text"""
        text_lower = text.lower()
        
        for obj_type, keywords in self.objective_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return obj_type
        
        # Default detection based on common patterns
        if 'slain' in text_lower or 'killed' in text_lower:
            return 'kill'
        elif any(x in text_lower for x in ['collected', 'gather', 'obtain']):
            return 'collect'
        
        return 'unknown'
    
    def _parse_creature_objectives(self, objectives_text: str, full_content: str) -> List[Dict]:
        """Parse creature/kill objectives with IDs and coordinates"""
        creatures = []
        
        # Look for creature objectives in the objectives text
        kill_patterns = [
            r'(.+?)\s+slain:\s*(\d+)/(\d+)(?:\s*\(monster\))?',
            r'(.+?)\s+killed:\s*(\d+)/(\d+)',
            r'Kill\s+(\d+)\s+(.+)',
            r'Slay\s+(\d+)\s+(.+)',
            r'Defeat\s+(\d+)\s+(.+)',
        ]
        
        for pattern in kill_patterns:
            matches = re.findall(pattern, objectives_text, re.IGNORECASE)
            for match in matches:
                creature = self._extract_creature_data(match, full_content)
                if creature and not any(c['name'] == creature['name'] for c in creatures):
                    creatures.append(creature)
        
        # Also look in the MONSTERS KILLED section if present
        monster_section = re.search(r'MONSTERS KILLED:?\s*\n(.*?)(?:\n\n|\Z)', full_content, re.DOTALL | re.IGNORECASE)
        if monster_section:
            monster_lines = monster_section.group(1).split('\n')
            for line in monster_lines:
                # Parse lines like "Amethyst Crab (ID: 46835) at 60.1, 53.3 in Durotar"
                match = re.search(r'(.+?)\s*\(ID:\s*(\d+)\)\s*at\s*([\d.]+),\s*([\d.]+)(?:\s+in\s+(.+))?', line)
                if match:
                    creature = {
                        'name': match.group(1).strip(),
                        'id': int(match.group(2)),
                        'coordinates': [{'x': float(match.group(3)), 'y': float(match.group(4))}],
                        'zone': match.group(5).strip() if match.group(5) else None,
                        'count': 1  # Default count
                    }
                    
                    # Merge with existing or add new
                    existing = next((c for c in creatures if c.get('id') == creature['id']), None)
                    if existing:
                        # Add coordinates if new
                        coord = {'x': creature['coordinates'][0]['x'], 'y': creature['coordinates'][0]['y']}
                        if not any(abs(c['x'] - coord['x']) < 1 and abs(c['y'] - coord['y']) < 1 for c in existing['coordinates']):
                            existing['coordinates'].append(coord)
                    else:
                        creatures.append(creature)
        
        return creatures
    
    def _extract_creature_data(self, match: Tuple, full_content: str) -> Optional[Dict]:
        """Extract creature data from a match"""
        if len(match) >= 3:
            # Format: name, current, required
            name = match[0].strip()
            # Remove leading numbers and periods (e.g., "1. Baron Valimar Mordis" -> "Baron Valimar Mordis")
            name = re.sub(r'^\d+\.\s*', '', name)
            current = int(match[1]) if match[1].isdigit() else 0
            required = int(match[2]) if len(match) > 2 and match[2].isdigit() else 1
        elif len(match) == 2:
            # Format: count, name
            if match[0].isdigit():
                required = int(match[0])
                name = match[1].strip()
                name = re.sub(r'^\d+\.\s*', '', name)
                current = 0
            else:
                name = match[0].strip()
                name = re.sub(r'^\d+\.\s*', '', name)
                required = 1
                current = 0
        else:
            return None
        
        # Try to find NPC ID in the full content
        npc_id = None
        
        # First check in "Mobs tracked" section for this specific creature
        mob_tracked_pattern = rf'Mobs tracked:.*?-\s*{re.escape(name)}\s*\(ID:\s*(\d+)\)'
        mob_match = re.search(mob_tracked_pattern, full_content, re.IGNORECASE | re.DOTALL)
        if mob_match:
            npc_id = int(mob_match.group(1))
        else:
            # Fallback to other patterns
            id_patterns = [
                rf'{re.escape(name)}\s*\(ID:\s*(\d+)\)',
                rf'NPC:\s*{re.escape(name)}\s*\(ID:\s*(\d+)\)',
            ]
            
            for pattern in id_patterns:
                match = re.search(pattern, full_content, re.IGNORECASE)
                if match:
                    npc_id = int(match.group(1))
                    break
        
        return {
            'name': name,
            'id': npc_id,
            'current': current,
            'required': required,
            'coordinates': []  # Will be filled by coordinate parser
        }
    
    def _parse_item_objectives(self, objectives_text: str, full_content: str) -> List[Dict]:
        """Parse item collection objectives"""
        items = []
        
        # Look for item objectives
        item_patterns = [
            r'(.+?):\s*(\d+)/(\d+)(?:\s*\(item\))?',
            r'Collect\s+(\d+)\s+(.+)',
            r'Gather\s+(\d+)\s+(.+)',
            r'Obtain\s+(\d+)\s+(.+)',
        ]
        
        for pattern in item_patterns:
            matches = re.findall(pattern, objectives_text, re.IGNORECASE)
            for match in matches:
                item = self._extract_item_data(match, full_content)
                if item and not any(i['name'] == item['name'] for i in items):
                    items.append(item)
        
        # Also check QUEST ITEMS section
        item_section = re.search(r'QUEST ITEMS:?\s*\n(.*?)(?:\n\n|\Z)', full_content, re.DOTALL | re.IGNORECASE)
        if item_section:
            item_lines = item_section.group(1).split('\n')
            for line in item_lines:
                # Parse lines like "Sun-Ripened Banana (ID: 69876)"
                match = re.search(r'(.+?)\s*\(ID:\s*(\d+)\)', line)
                if match:
                    item = {
                        'name': match.group(1).strip(),
                        'id': int(match.group(2)),
                        'current': 0,
                        'required': 1,
                        'source_type': None,
                        'source_id': None
                    }
                    
                    # Check if item dropped from a mob
                    drop_match = re.search(rf'{re.escape(item["name"])}.*?dropped from (.+?)\s*\(ID:\s*(\d+)\)', full_content, re.IGNORECASE)
                    if drop_match:
                        item['source_type'] = 'creature'
                        item['source_id'] = int(drop_match.group(2))
                    
                    if not any(i.get('id') == item['id'] for i in items):
                        items.append(item)
        
        return items
    
    def _extract_item_data(self, match: Tuple, full_content: str) -> Optional[Dict]:
        """Extract item data from a match"""
        if len(match) >= 3:
            # Format: name, current, required
            name = match[0].strip()
            # Skip if this looks like a creature objective
            if any(word in name.lower() for word in ['slain', 'killed', 'defeated']):
                return None
            current = int(match[1]) if match[1].isdigit() else 0
            required = int(match[2]) if len(match) > 2 and match[2].isdigit() else 1
        elif len(match) == 2:
            # Format: count, name
            if match[0].isdigit():
                required = int(match[0])
                name = match[1].strip()
            else:
                return None
            current = 0
        else:
            return None
        
        # Try to find item ID
        item_id = None
        id_match = re.search(rf'{re.escape(name)}\s*\(ID:\s*(\d+)\)', full_content, re.IGNORECASE)
        if id_match:
            item_id = int(id_match.group(1))
        
        return {
            'name': name,
            'id': item_id,
            'current': current,
            'required': required,
            'source_type': None,  # creature, object, or vendor
            'source_id': None
        }
    
    def _parse_object_objectives(self, content: str) -> List[Dict]:
        """Parse ground object interaction objectives"""
        objects = []
        
        # Look for GROUND OBJECTS section
        object_section = re.search(r'GROUND OBJECTS?/CONTAINERS?:?\s*\n(.*?)(?:\n\nDATABASE|\n\n=|\Z)', 
                                  content, re.DOTALL | re.IGNORECASE)
        
        if object_section:
            lines = object_section.group(1).split('\n')
            for line in lines:
                # Skip invalid coordinates lines
                if 'Invalid coordinates' in line:
                    continue
                
                # Parse lines like "Sun-Ripened Banana at 60.1, 53.3 in Durotar"
                match = re.search(r'(.+?)\s+at\s+([\d.]+),\s*([\d.]+)(?:\s+in\s+(.+))?', line)
                if match:
                    obj = {
                        'name': match.group(1).strip(),
                        'id': None,  # Object IDs rarely provided in submissions
                        'coordinates': [{'x': float(match.group(2)), 'y': float(match.group(3))}],
                        'zone': match.group(4).strip() if match.group(4) else None
                    }
                    
                    # Check for additional locations
                    if 'Additional location:' in content:
                        additional = re.findall(rf'Additional location:.*?{re.escape(obj["name"])}.*?at\s+([\d.]+),\s*([\d.]+)', 
                                              content, re.IGNORECASE)
                        for coord in additional:
                            obj['coordinates'].append({'x': float(coord[0]), 'y': float(coord[1])})
                    
                    # Don't add duplicates
                    if not any(o['name'] == obj['name'] for o in objects):
                        objects.append(obj)
        
        return objects
    
    def _parse_exploration_objectives(self, objectives_text: str) -> List[Dict]:
        """Parse exploration/discovery objectives"""
        explorations = []
        
        # Look for exploration patterns
        explore_patterns = [
            r'(?:Discover|Explore|Find|Reach|Visit)\s+(.+?)(?:\:|$)',
            r'(.+?)\s+(?:discovered|explored|found|reached):\s*(\d+)/(\d+)',
        ]
        
        for pattern in explore_patterns:
            matches = re.findall(pattern, objectives_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 1:
                    location = match[0].strip()
                    current = int(match[1]) if len(match) > 1 and match[1].isdigit() else 0
                    required = int(match[2]) if len(match) > 2 and match[2].isdigit() else 1
                else:
                    location = match.strip() if isinstance(match, str) else str(match)
                    current = 0
                    required = 1
                
                exploration = {
                    'location': location,
                    'current': current,
                    'required': required,
                    'coordinates': []  # Will be filled by coordinate parser
                }
                
                if not any(e['location'] == location for e in explorations):
                    explorations.append(exploration)
        
        return explorations
    
    def _validate_completeness(self, objectives: Dict) -> bool:
        """Check if we have complete objective data"""
        # Must have at least the objectives text
        if not objectives.get('objectives_text'):
            return False
        
        # Should have at least one type of objective
        has_objectives = (
            len(objectives.get('objectives_list', [])) > 0 or
            len(objectives.get('creatures', [])) > 0 or
            len(objectives.get('items', [])) > 0 or
            len(objectives.get('objects', [])) > 0 or
            len(objectives.get('exploration', [])) > 0
        )
        
        return has_objectives
    
    def generate_objectives_entry(self, objectives: Dict) -> str:
        """Generate Lua objectives structure for database"""
        
        # Build creatures array
        creatures_lua = "nil"
        if objectives.get('creatures'):
            creature_entries = []
            for creature in objectives['creatures']:
                if creature.get('id'):
                    entry = f"{{{creature['id']},{creature.get('required', 1)}"
                    if creature.get('name'):
                        entry += f',"{creature["name"]}"'
                    entry += "}"
                    creature_entries.append(entry)
            if creature_entries:
                creatures_lua = "{" + ",".join(creature_entries) + "}"
        
        # Build items array
        items_lua = "nil"
        if objectives.get('items'):
            item_entries = []
            for item in objectives['items']:
                if item.get('id'):
                    entry = f"{{{item['id']},{item.get('required', 1)}}}"
                    item_entries.append(entry)
            if item_entries:
                items_lua = "{" + ",".join(item_entries) + "}"
        
        # Build objects array  
        objects_lua = "nil"
        if objectives.get('objects'):
            object_entries = []
            for obj in objectives['objects']:
                # Objects need IDs which we rarely have from submissions
                # This would need to be filled by database lookup
                pass
        
        # Build the objectives structure
        if creatures_lua != "nil" or items_lua != "nil" or objects_lua != "nil":
            return f"{{{creatures_lua},{objects_lua},{items_lua},nil,nil,nil}}"
        
        return "nil"
    
    def get_summary(self) -> Dict:
        """Get parsing summary"""
        return {
            'total_parsed': len(self.parsed_objectives),
            'with_creatures': sum(1 for o in self.parsed_objectives if o.get('creatures')),
            'with_items': sum(1 for o in self.parsed_objectives if o.get('items')),
            'with_objects': sum(1 for o in self.parsed_objectives if o.get('objects')),
            'with_exploration': sum(1 for o in self.parsed_objectives if o.get('exploration')),
            'complete_data': sum(1 for o in self.parsed_objectives if o.get('has_complete_data')),
            'parse_errors': len(self.parse_errors)
        }

def main():
    """Test the objective parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python objective_parser.py <submission_file>")
        sys.exit(1)
    
    parser = ObjectiveParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract quest ID if present
    quest_id = None
    id_match = re.search(r'Quest ID:\s*(\d+)', content)
    if id_match:
        quest_id = int(id_match.group(1))
    
    objectives = parser.parse(content, quest_id)
    
    print(f"\nQuest {quest_id} Objectives:")
    print(f"Objectives Text: {objectives.get('objectives_text', 'None')[:100]}...")
    print(f"\nParsed Objectives: {len(objectives.get('objectives_list', []))}")
    for obj in objectives.get('objectives_list', []):
        print(f"  - {obj['text']} [{obj['type']}] ({obj['current']}/{obj['required']})")
    
    if objectives.get('creatures'):
        print(f"\nCreature Objectives: {len(objectives['creatures'])}")
        for creature in objectives['creatures']:
            print(f"  - {creature['name']} (ID: {creature.get('id', 'Unknown')}) x{creature['required']}")
    
    if objectives.get('items'):
        print(f"\nItem Objectives: {len(objectives['items'])}")
        for item in objectives['items']:
            print(f"  - {item['name']} (ID: {item.get('id', 'Unknown')}) x{item['required']}")
    
    if objectives.get('objects'):
        print(f"\nObject Interactions: {len(objectives['objects'])}")
        for obj in objectives['objects']:
            print(f"  - {obj['name']} at {len(obj['coordinates'])} location(s)")
    
    print(f"\nComplete Data: {objectives['has_complete_data']}")
    print(f"\nLua Entry:\n{parser.generate_objectives_entry(objectives)}")

if __name__ == "__main__":
    main()