#!/usr/bin/env python3
"""
Objective Consensus Filter Module V3
Handles quest progress format text like "Item Name: 0/5" and "Monster slain: 0/10 (monster)"
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

class ObjectiveConsensusFilterV3:
    """Filter with quest progress format handling"""
    
    def __init__(self):
        """Initialize the consensus filter with patterns and thresholds"""
        self.confidence_thresholds = {
            'automated': 0.80,
            'review': 0.50,
            'manual': 0.50
        }
        
        self.progress_patterns = {
            'item': [
                r'^(.+?):\s*\d+/(\d+)$',
                r'^(.+?):\s*(\d+)\s*needed$',
            ],
            'kill': [
                r'^(.+?)\s+slain:\s*\d+/(\d+)\s*\(monster\)$',
                r'^(.+?)\s+killed:\s*\d+/(\d+)\s*\(monster\)$',
                r'^(.+?)\s+slain:\s*\d+/(\d+)$',
                r'^(.+?)\s+killed:\s*\d+/(\d+)$',
            ],
            'event': [
                r'^(.+?)\s+(?:assisted|rescued|freed|saved|helped):\s*\d+/(\d+)$',
                r'^.*?\(event\)$',
            ]
        }
        
        self.objective_patterns = {
            'kill': [
                r'(?:Kill|Slay|Defeat|Destroy|Eliminate)\s+(\d+)\s+(.+?)(?:\.|,|;|$)',
                r'(\d+)\s+(.+?)\s+(?:killed|slain|defeated|destroyed)',
            ],
            'collect': [
                r'(?:Collect|Gather|Obtain|Acquire|Bring|Get|Find|Retrieve)\s+(\d+)\s+(.+?)(?:\.|,|;|:|\s+to\s+|$)',
                r'(\d+)\s*x\s+(.+?)(?:\.|,|;|$)',
                r'(.+?)\s*x\s*(\d+)(?:\.|,|;|$)',
            ]
        }
        
        self.manual_review_dir = Path("Manual Review")
        self.manual_review_dir.mkdir(exist_ok=True)
        
    def filter_objectives(self, aggregated_data: Dict) -> Dict:
        """Main filtering pipeline"""
        filtered_quests = {}
        manual_review_quests = []
        
        for quest_id, quest_data in aggregated_data.get('quests', {}).items():
            filtered_objectives, confidence = self.match_objectives_smart(
                quest_data,
                quest_id
            )
            
            filtered_quest = dict(quest_data)
            filtered_quest['objectives'] = filtered_objectives
            filtered_quest['_filter_confidence'] = confidence
            
            if confidence >= self.confidence_thresholds['automated']:
                filtered_quests[quest_id] = filtered_quest
            else:
                manual_review_quests.append((quest_id, quest_data, filtered_quest, confidence))
        
        if manual_review_quests:
            self.save_manual_review(manual_review_quests)
            print(f"\ud83d\udcce Saved {len(manual_review_quests)} quests to Manual Review folder")
        
        return filtered_quests

    def match_objectives_smart(self, quest_data: Dict, quest_id: str) -> Tuple[Dict, float]:
        """Smart matching with fallback logic"""
        
        filtered = {
            'items': [],
            'creatures': [],
            'objects': []
        }
        
        is_epoch_quest = False
        try:
            if int(quest_id) >= 25000:
                is_epoch_quest = True
        except:
            pass

        # First, try to parse the structured OBJECTIVES field
        required_from_objectives = self.parse_progress_text(quest_data.get('objectivesText', []))
        
        # Second, parse the free-text OBJECTIVES TEXT field as a fallback
        required_from_text = self._parse_objectives_from_text(quest_data.get('objectives_text', ''))

        collected_objectives = quest_data.get('objectives', {})
        matches_found = 0

        # Combine requirements from both sources, giving priority to the structured field
        all_required_kills = required_from_objectives.get('kills', []) + required_from_text.get('kills', [])
        all_required_items = required_from_objectives.get('items', []) + required_from_text.get('items', [])

        # Deduplicate requirements
        unique_kills = {req['name'].lower(): req for req in all_required_kills}
        unique_items = {req['name'].lower(): req for req in all_required_items}

        total_required = len(unique_kills) + len(unique_items)

        # Match Kills
        for req_name_lower, req in unique_kills.items():
            best_match, best_score = self._find_best_match(req_name_lower, collected_objectives.get('creatures', []))
            if best_match:
                filtered_creature = dict(best_match)
                filtered_creature['count'] = req.get('count', 1)
                filtered['creatures'].append(filtered_creature)
                matches_found += best_score

        # Match Items
        for req_name_lower, req in unique_items.items():
            best_match, best_score = self._find_best_match(req_name_lower, collected_objectives.get('items', []))
            if best_match:
                filtered_item = dict(best_match)
                filtered_item['count'] = req.get('count', 1)
                filtered['items'].append(filtered_item)
                matches_found += best_score

        if total_required > 0:
            confidence = matches_found / total_required
        elif self._has_any_data(collected_objectives):
            # No requirements found, but data was collected. Low confidence.
            confidence = 0.4
        else:
            # No requirements and no collected data. Likely a talk/exploration quest.
            confidence = 0.9 # High confidence for these simple quests

        return filtered, confidence

    def _find_best_match(self, req_name: str, collected_list: List[Dict]) -> Tuple[Optional[Dict], float]:
        """Find the best match for a required item/creature in a list of collected entities."""
        best_match = None
        best_score = 0

        for entity in collected_list:
            entity_name = (entity.get('name', '') or '').lower()
            if not entity_name:
                continue

            # Check for exact and substring matches first
            if req_name == entity_name or req_name in entity_name or entity_name in req_name:
                return entity, 1.0

            # Fuzzy matching as a fallback
            score = self.fuzzy_match(req_name, entity_name)
            if score > best_score:
                best_score = score
                best_match = entity

        if best_score > 0.7: # Confidence threshold for fuzzy match
            return best_match, best_score
        
        return None, 0
    
    def parse_progress_text(self, objectives_texts: List[str]) -> Dict:
        """Parse quest progress format text"""
        parsed = {
            'items': [],
            'kills': [],
            'events': []
        }
        
        for text in objectives_texts:
            if not text or text == '(No objectives text available)':
                continue
            
            text = text.strip()
            
            if not text or text.startswith(':'):
                continue
            
            matched = False
            for pattern in self.progress_patterns['kill']:
                match = re.match(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    count = int(match.group(2)) if len(match.groups()) > 1 else 1
                    parsed['kills'].append({'name': name, 'count': count, 'raw_text': text})
                    matched = True
                    break
            if matched: continue

            for pattern in self.progress_patterns['item']:
                match = re.match(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    count = int(match.group(2)) if len(match.groups()) > 1 else 1
                    if 'slain' not in name.lower() and 'killed' not in name.lower():
                        parsed['items'].append({'name': name, 'count': count, 'raw_text': text})
                        matched = True
                        break
        return parsed

    def _parse_objectives_from_text(self, objectives_text: str) -> Dict:
        """Parse objectives from the main quest description text"""
        parsed = {
            'items': [],
            'kills': []
        }
        if not objectives_text:
            return parsed

        if isinstance(objectives_text, list):
            objectives_text = ' '.join(objectives_text)

        for pattern in self.objective_patterns['kill']:
            matches = re.findall(pattern, objectives_text, re.IGNORECASE)
            for match in matches:
                count, name = match
                parsed['kills'].append({'name': name.strip(), 'count': int(count)})

        for pattern in self.objective_patterns['collect']:
            matches = re.findall(pattern, objectives_text, re.IGNORECASE)
            for match in matches:
                if match[0].isdigit():
                    count, name = match
                else:
                    name, count = match
                parsed['items'].append({'name': name.strip(), 'count': int(count)})
        
        return parsed
    
    def fuzzy_match(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match score between two strings"""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _has_any_data(self, objectives: Dict) -> bool:
        """Check if objectives dict has any actual data"""
        return (len(objectives.get('items', [])) > 0 or
                len(objectives.get('creatures', [])) > 0 or
                len(objectives.get('objects', [])) > 0)

    def _is_empty_objectives(self, objectives: Dict) -> bool:
        """Check if objectives dict is effectively empty"""
        return not self._has_any_data(objectives)
    
    def _count_objectives(self, objectives: Dict) -> int:
        """Count total objectives in a dictionary"""
        return (len(objectives.get('items', [])) + 
                len(objectives.get('creatures', [])) + 
                len(objectives.get('objects', [])))
    
    def save_manual_review(self, review_quests: List):
        """Save quests needing manual review to timestamped file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_{timestamp}.txt"
        filepath = self.manual_review_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"MANUAL REVIEW REQUIRED - {len(review_quests)} Quests\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            
            for quest_id, original, filtered, confidence in review_quests:
                f.write("-" * 80 + "\n")
                f.write(f"Quest ID: {quest_id}\n")
                f.write(f"Quest Name: {original.get('name', 'Unknown')}\n")
                f.write(f"Confidence Score: {confidence:.1%}\n")
                
                if confidence < 0.3:
                    f.write("Issue: Very low confidence\n")
                elif confidence < 0.5:
                    f.write("Issue: Low confidence\n")
                else:
                    f.write("Issue: Medium confidence - review recommended\n")
                
                f.write(f"\nOBJECTIVES TEXT:\n")
                for text in original.get('objectivesText', []):
                    f.write(f"  {text}\n")
                if not original.get('objectivesText'):
                    f.write("  (No objectives text available)\n")
                
                objectives = original.get('objectives', {})
                total_collected = self._count_objectives(objectives)
                f.write(f"\nCOLLECTED ({total_collected} total):\n")
                
                for item in objectives.get('items', []):
                    name = item.get('name', f"(ID: {item.get('id')})")
                    f.write(f"  - {name} (item)\n")
                
                for creature in objectives.get('creatures', []):
                    f.write(f"  - {creature.get('name', 'Unknown')} (creature)\n")
                
                filtered_obj = filtered.get('objectives', {})
                total_filtered = self._count_objectives(filtered_obj)
                f.write(f"\nFILTERED RESULT ({total_filtered} items):\n")
                
                if total_filtered == 0:
                    f.write("  No matches found\n")
                else:
                    for item in filtered_obj.get('items', []):
                        conf = item.get('_match_confidence', 0)
                        f.write(f"  - {item.get('name', 'Unknown')} (confidence: {conf:.1%})\n")
                    for creature in filtered_obj.get('creatures', []):
                        conf = creature.get('_match_confidence', 0)
                        f.write(f"  - {creature.get('name', 'Unknown')} creature (confidence: {conf:.1%})\n")
                
                f.write("\n")
        
        print(f"Saved manual review file: {filepath}")