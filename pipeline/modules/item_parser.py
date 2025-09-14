#!/usr/bin/env python3
"""
Item Parser Module - Extracts item requirements, rewards, and quest items
Handles source items, required items, quest drops, and reward items
"""

import re
from typing import Dict, List, Optional, Tuple
import json

class ItemParser:
    """Parses item data from quest submissions"""
    
    def __init__(self):
        self.parsed_items = {}
        self.parse_errors = []
        
        # Item type patterns
        self.item_types = {
            'quest_item': ['quest item', 'quest', 'unique'],
            'source_item': ['provided item', 'source', 'starting'],
            'required_item': ['required', 'bring', 'need', 'must have'],
            'reward_item': ['reward', 'choose', 'receive', 'get'],
            'consumable': ['potion', 'food', 'drink', 'elixir', 'scroll'],
            'equipment': ['weapon', 'armor', 'shield', 'helm', 'boots', 'gloves'],
            'trade_good': ['ore', 'herb', 'cloth', 'leather', 'gem']
        }
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse item data from quest submission
        
        Returns:
            Dictionary with categorized item data
        """
        items_data = {
            'quest_id': quest_id,
            'quest_items': [],      # Items that drop for the quest
            'source_items': [],     # Items provided by quest giver
            'required_items': [],   # Items needed to start quest
            'reward_items': [],     # Items rewarded on completion
            'all_items': []
        }
        
        # Parse different item sections
        items_data['quest_items'] = self._parse_quest_items_section(content)
        items_data['source_items'] = self._parse_source_items(content)
        items_data['required_items'] = self._parse_required_items(content)
        items_data['reward_items'] = self._parse_reward_items(content)
        
        # Also check objectives for item collection
        items_data['quest_items'].extend(self._parse_objective_items(content))
        
        # Combine all items and deduplicate
        items_data['all_items'] = self._deduplicate_items(
            items_data['quest_items'] + 
            items_data['source_items'] + 
            items_data['required_items'] + 
            items_data['reward_items']
        )
        
        # Store parsed items by ID for later use
        for item in items_data['all_items']:
            if item.get('id'):
                self.parsed_items[item['id']] = item
        
        return items_data
    
    def _parse_quest_items_section(self, content: str) -> List[Dict]:
        """Parse QUEST ITEMS section"""
        items = []
        
        # Look for QUEST ITEMS section - handle multiline format
        item_section = re.search(r'QUEST ITEMS:?\s*\n(.*?)(?:\n\n[A-Z]|\n\n--|\Z)', content, re.DOTALL | re.IGNORECASE)
        if item_section:
            section_text = item_section.group(1)
            
            # Handle both formats:
            # Format 1: "  Item Name (ID: 12345)"
            # Format 2: "   (ID: 12345)" followed by "  Item Name (ID: 12345)"
            item_patterns = [
                r'\s*([A-Za-z][^(]*?)\s*\(ID:\s*(\d+)\)',  # "  Hatefury Horn (ID: 6247)"
                r'\s*\(ID:\s*(\d+)\)'  # "   (ID: 60669)" - ID only lines
            ]
            
            for pattern in item_patterns:
                matches = re.findall(pattern, section_text)
                for match in matches:
                    if len(match) == 2 and match[0]:  # Has name and ID
                        item = {
                            'name': match[0].strip(),
                            'id': int(match[1]),
                            'category': 'quest_item',
                            'quantity': 1,
                            'type': self._classify_item_type(match[0]),
                            'source_type': self._determine_item_source(section_text, content)
                        }
                        items.append(item)
                    # Skip ID-only lines for now
        
        return items
    
    def _parse_source_items(self, content: str) -> List[Dict]:
        """Parse items provided by quest giver"""
        items = []
        
        # Look for provided items in quest text
        patterns = [
            r'(?:provided|given|receives?):?\s*(.+?)\s*\(ID:\s*(\d+)\)',
            r'(?:take this|use this|here is):?\s*(.+?)\s*\(ID:\s*(\d+)\)',
            r'Source Item:?\s*(.+?)\s*\(ID:\s*(\d+)\)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                item = {
                    'name': match[0].strip(),
                    'id': int(match[1]),
                    'category': 'source_item',
                    'quantity': 1,
                    'required_for_start': True
                }
                items.append(item)
        
        return items
    
    def _parse_required_items(self, content: str) -> List[Dict]:
        """Parse items required to start the quest"""
        items = []
        
        # Look for required items patterns
        patterns = [
            r'(?:requires?|needs?|must have|bring):?\s*(.+?)\s*\(ID:\s*(\d+)\)',
            r'Required Items?:?\s*(.+?)\s*\(ID:\s*(\d+)\)',
            r'(?:you need|collect first):?\s*(.+?)\s*\(ID:\s*(\d+)\)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                item = {
                    'name': match[0].strip(),
                    'id': int(match[1]),
                    'category': 'required_item',
                    'quantity': self._extract_quantity(match[0]),
                    'required_for_start': True
                }
                items.append(item)
        
        return items
    
    def _parse_reward_items(self, content: str) -> List[Dict]:
        """Parse quest reward items"""
        items = []
        
        # Look for reward sections
        reward_section = re.search(r'REWARDS?:?\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if reward_section:
            reward_text = reward_section.group(1)
            
            # Parse individual reward items
            item_matches = re.findall(r'(.+?)\s*\(ID:\s*(\d+)\)(?:\s*x(\d+))?', reward_text)
            for match in item_matches:
                item = {
                    'name': match[0].strip(),
                    'id': int(match[1]),
                    'category': 'reward_item',
                    'quantity': int(match[2]) if match[2] else 1,
                    'is_reward': True
                }
                items.append(item)
        
        # Also look for "choose one" patterns
        choice_patterns = [
            r'(?:choose one|select one|pick one):?\s*\n(.*?)(?:\n\n|\Z)',
            r'(?:reward choice|one of):?\s*\n(.*?)(?:\n\n|\Z)'
        ]
        
        for pattern in choice_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                choice_text = match.group(1)
                choice_items = re.findall(r'(.+?)\s*\(ID:\s*(\d+)\)', choice_text)
                for item_match in choice_items:
                    item = {
                        'name': item_match[0].strip(),
                        'id': int(item_match[1]),
                        'category': 'reward_item',
                        'quantity': 1,
                        'is_choice_reward': True
                    }
                    items.append(item)
        
        return items
    
    def _parse_objective_items(self, content: str) -> List[Dict]:
        """Parse items from quest objectives"""
        items = []
        
        # Look for collection objectives
        obj_patterns = [
            r'(.+?):\s*(\d+)/(\d+)(?:\s*\(item\))?',  # "Item Name: 0/5 (item)"
            r'(?:collect|gather|obtain|loot)\s+(\d+)\s+(.+)',  # "Collect 5 Iron Ore"
            r'Item:\s*(.+?)\s*\(ID:\s*(\d+)\)',  # "Item: Hatefury Claw (ID: 6246)"
        ]
        
        objectives_section = re.search(r'OBJECTIVES?:?\s*\n(.*?)(?:\n\nQUEST ITEMS|\n\nTURN-?IN|\n\nGROUND|\n\nDATABASE|\Z)', 
                                      content, re.DOTALL | re.IGNORECASE)
        
        if objectives_section:
            obj_text = objectives_section.group(1)
            
            for pattern in obj_patterns:
                matches = re.findall(pattern, obj_text, re.IGNORECASE)
                for match in matches:
                    if len(match) >= 3:
                        # Format: name, current, required
                        name = match[0].strip()
                        required = int(match[2])
                        
                        # Skip if this looks like a kill objective
                        if any(word in name.lower() for word in ['slain', 'killed', 'defeated']):
                            continue
                        
                        # Try to find item ID in the full content
                        item_id = self._find_item_id(name, content)
                        
                        item = {
                            'name': name,
                            'id': item_id,
                            'category': 'quest_item',
                            'quantity': required,
                            'is_objective': True
                        }
                        items.append(item)
                    
                    elif len(match) == 2:
                        if match[0].isdigit():
                            # Format: count, name (from "collect X items")
                            required = int(match[0])
                            name = match[1].strip()
                            item_id = self._find_item_id(name, content)
                        else:
                            # Format: name, id (from "Item: Name (ID: xxx)")
                            name = match[0].strip()
                            item_id = int(match[1])
                            required = self._extract_quantity_from_objectives(name, obj_text)
                        
                        item = {
                            'name': name,
                            'id': item_id,
                            'category': 'quest_item',
                            'quantity': required,
                            'is_objective': True
                        }
                        items.append(item)
        
        return items
    
    def _parse_item_line(self, line: str) -> Optional[Dict]:
        """Parse a single line containing item information"""
        # Try different patterns for item lines
        patterns = [
            r'(.+?)\s*\(ID:\s*(\d+)\)(?:\s*x(\d+))?',  # "Item Name (ID: 12345) x5"
            r'(.+?)\s*-\s*ID:\s*(\d+)(?:\s*x(\d+))?',   # "Item Name - ID: 12345 x5"
            r'(.+?):\s*(\d+)(?:\s*x(\d+))?$',          # "Item Name: 12345 x5"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line.strip())
            if match:
                item = {
                    'name': match.group(1).strip(),
                    'id': int(match.group(2)),
                    'quantity': int(match.group(3)) if len(match.groups()) >= 3 and match.group(3) else 1
                }
                
                # Try to determine item type from name
                item['type'] = self._classify_item_type(item['name'])
                
                return item
        
        return None
    
    def _find_item_id(self, item_name: str, content: str) -> Optional[int]:
        """Try to find item ID from item name in the content"""
        patterns = [
            rf'{re.escape(item_name)}\s*\(ID:\s*(\d+)\)',
            rf'{re.escape(item_name)}\s*-\s*ID:\s*(\d+)',
            rf'Item:\s*{re.escape(item_name)}\s*\(ID:\s*(\d+)\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_quantity(self, text: str) -> int:
        """Extract quantity from text"""
        # Look for numbers in the text
        numbers = re.findall(r'\b(\d+)\b', text)
        if numbers:
            # Return the first reasonable quantity (usually < 100 for quest items)
            for num in numbers:
                quantity = int(num)
                if 1 <= quantity <= 100:
                    return quantity
        
        return 1  # Default quantity
    
    def _extract_quantity_from_objectives(self, item_name: str, objectives_text: str) -> int:
        """Extract quantity for an item from objectives section"""
        # Look for patterns like "Item Name: X/Y (item)"
        patterns = [
            rf'{re.escape(item_name)}:\s*\d+/(\d+)',
            rf'(\d+)/\d+.*{re.escape(item_name)}',
            rf'(\d+)\s+{re.escape(item_name)}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, objectives_text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return 1  # Default quantity
    
    def _determine_item_source(self, line: str, content: str) -> Optional[str]:
        """Determine where the item comes from"""
        line_lower = line.lower()
        
        # Check for drop sources
        if 'dropped from' in line_lower or 'drops from' in line_lower:
            # Try to extract the mob name
            drop_match = re.search(r'dropped?\s+from\s+(.+?)\s*(?:\(|$)', line, re.IGNORECASE)
            if drop_match:
                return f"creature:{drop_match.group(1).strip()}"
        
        # Check for object sources
        if any(word in line_lower for word in ['chest', 'container', 'barrel', 'crate', 'box']):
            obj_match = re.search(r'from\s+(.+?)\s*(?:\(|$)', line, re.IGNORECASE)
            if obj_match:
                return f"object:{obj_match.group(1).strip()}"
        
        # Check for vendor sources
        if any(word in line_lower for word in ['vendor', 'buy', 'purchase', 'sold']):
            return "vendor"
        
        # Check for quest reward
        if any(word in line_lower for word in ['reward', 'quest', 'complete']):
            return "quest_reward"
        
        return None
    
    def _classify_item_type(self, name: str) -> str:
        """Classify item type based on name"""
        name_lower = name.lower()
        
        for item_type, keywords in self.item_types.items():
            if any(keyword in name_lower for keyword in keywords):
                return item_type
        
        # Default classification
        if any(word in name_lower for word in ['ore', 'herb', 'cloth', 'leather']):
            return 'trade_good'
        elif any(word in name_lower for word in ['sword', 'axe', 'staff', 'bow']):
            return 'weapon'
        elif any(word in name_lower for word in ['armor', 'helm', 'boots', 'gloves']):
            return 'armor'
        
        return 'misc'
    
    def _deduplicate_items(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate items, keeping the most complete version"""
        items_by_id = {}
        items_by_name = {}
        
        for item in items:
            # Deduplicate by ID first (most reliable)
            if item.get('id'):
                key = item['id']
                if key not in items_by_id or len(str(item)) > len(str(items_by_id[key])):
                    items_by_id[key] = item
            else:
                # Deduplicate by name for items without IDs
                key = item.get('name', '').lower()
                if key and (key not in items_by_name or len(str(item)) > len(str(items_by_name[key]))):
                    items_by_name[key] = item
        
        # Combine results
        result = list(items_by_id.values()) + list(items_by_name.values())
        return result
    
    def generate_item_entries(self, items_data: Dict) -> Dict[str, List]:
        """Generate different categories of items for database"""
        entries = {
            'source_items': [],      # For quest field 11 (sourceItemId)
            'required_items': [],    # For quest field 21 (requiredSourceItems)
            'objective_items': [],   # For quest field 10 objectives.items
            'reward_items': []       # For future reward system
        }
        
        for item in items_data.get('all_items', []):
            if not item.get('id'):
                continue
                
            item_entry = {
                'id': item['id'],
                'name': item['name'],
                'quantity': item.get('quantity', 1),
                'type': item.get('type', 'misc')
            }
            
            # Categorize for database fields
            if item.get('category') == 'source_item' or item.get('required_for_start'):
                if item.get('quantity', 1) == 1 and not entries['source_items']:
                    # Single source item
                    entries['source_items'].append(item_entry)
                else:
                    # Multiple required items
                    entries['required_items'].append(item_entry)
            
            elif item.get('is_objective'):
                entries['objective_items'].append(item_entry)
            
            elif item.get('is_reward'):
                entries['reward_items'].append(item_entry)
        
        return entries
    
    def get_summary(self) -> Dict:
        """Get parsing summary"""
        total_items = len(self.parsed_items)
        
        categories = {}
        types = {}
        
        for item in self.parsed_items.values():
            category = item.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
            
            item_type = item.get('type', 'unknown')
            types[item_type] = types.get(item_type, 0) + 1
        
        return {
            'total_items': total_items,
            'by_category': categories,
            'by_type': types,
            'parse_errors': len(self.parse_errors)
        }

def main():
    """Test the item parser"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python item_parser.py <submission_file>")
        sys.exit(1)
    
    parser = ItemParser()
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract quest ID if present
    quest_id = None
    id_match = re.search(r'Quest ID:\s*(\d+)', content)
    if id_match:
        quest_id = int(id_match.group(1))
    
    items_data = parser.parse(content, quest_id)
    
    print(f"\nQuest {quest_id} Items:")
    
    if items_data['quest_items']:
        print(f"\nQuest Items ({len(items_data['quest_items'])}):")
        for item in items_data['quest_items']:
            print(f"  - {item['name']} (ID: {item.get('id', 'Unknown')}) x{item.get('quantity', 1)}")
    
    if items_data['source_items']:
        print(f"\nSource Items ({len(items_data['source_items'])}):")
        for item in items_data['source_items']:
            print(f"  - {item['name']} (ID: {item.get('id', 'Unknown')})")
    
    if items_data['required_items']:
        print(f"\nRequired Items ({len(items_data['required_items'])}):")
        for item in items_data['required_items']:
            print(f"  - {item['name']} (ID: {item.get('id', 'Unknown')}) x{item.get('quantity', 1)}")
    
    if items_data['reward_items']:
        print(f"\nReward Items ({len(items_data['reward_items'])}):")
        for item in items_data['reward_items']:
            print(f"  - {item['name']} (ID: {item.get('id', 'Unknown')})")
    
    print(f"\nTotal Items Found: {len(items_data['all_items'])}")
    
    # Show database entries
    entries = parser.generate_item_entries(items_data)
    print(f"\nDatabase Entries:")
    for category, items in entries.items():
        if items:
            print(f"  {category}: {[item['id'] for item in items]}")
    
    print(f"\nSummary: {json.dumps(parser.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()