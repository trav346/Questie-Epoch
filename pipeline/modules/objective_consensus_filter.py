#!/usr/bin/env python3
"""
Objective Consensus Filter Module
Reduces collected objectives to actual quest requirements using text parsing and pattern matching.
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

class ObjectiveConsensusFilter:
    """Filter aggregated objectives down to actual quest requirements"""
    
    def __init__(self):
        """Initialize the consensus filter with patterns and thresholds"""
        self.confidence_thresholds = {
            'automated': 0.90,     # >90% goes straight through
            'review': 0.70,        # 70-90% goes with warnings  
            'manual': 0.70         # <70% needs manual review
        }
        
        # Common objective patterns in WoW quest text
        self.objective_patterns = {
            'kill': [
                r'(?:Kill|Slay|Defeat|Destroy|Eliminate)\s+(\d+)\s+(.+?)(?:\.|,|;|$)',
                r'(.+?):\s*(\d+)/\d+',  # "Rock Elemental: 0/10"
                r'(\d+)\s+(.+?)\s+(?:killed|slain|defeated)',
            ],
            'collect': [
                r'(?:Collect|Gather|Obtain|Acquire|Bring|Get|Find)\s+(\d+)\s+(.+?)(?:\.|,|;|:|\s+to\s+|$)',
                r'(.+?):\s*0/(\d+)',  # "Bracers of Rock Binding: 0/5"
                r'(\d+)\s+x\s+(.+?)(?:\.|,|;|$)',  # "5 x Bracers"
                r'(.+?):\s*(\d+)\s+needed',
            ],
            'interact': [
                r'(?:Interact with|Use|Activate|Click|Touch)\s+(?:the\s+)?(.+?)(?:\.|,|;|$)',
                r'(?:Speak with|Talk to)\s+(.+?)(?:\.|,|;|$)',
            ]
        }
        
        # Manual review folder
        self.manual_review_dir = Path("Manual Review")
        self.manual_review_dir.mkdir(exist_ok=True)
        
    def filter_objectives(self, aggregated_data: Dict) -> Dict:
        """
        Main filtering pipeline
        
        Args:
            aggregated_data: Dictionary with 'quests' containing aggregated quest data
            
        Returns:
            Filtered quest data with reduced objectives and confidence scores
        """
        filtered_quests = {}
        manual_review_quests = []
        
        total_before = 0
        total_after = 0
        
        for quest_id, quest_data in aggregated_data.get('quests', {}).items():
            # Count objectives before
            objectives_before = self._count_objectives(quest_data.get('objectives', {}))
            total_before += objectives_before
            
            # Parse objectives from text
            required_objectives = self.parse_objectives_text(
                quest_data.get('objectivesText', [])
            )
            
            # Match against collected items
            filtered_objectives, confidence = self.match_objectives(
                required_objectives,
                quest_data.get('objectives', {}),
                quest_data.get('name', f'Quest {quest_id}')
            )
            
            # Count objectives after
            objectives_after = self._count_objectives(filtered_objectives)
            total_after += objectives_after
            
            # Create filtered quest entry
            filtered_quest = dict(quest_data)
            filtered_quest['objectives'] = filtered_objectives
            filtered_quest['_filter_confidence'] = confidence
            filtered_quest['_objectives_reduced'] = f"{objectives_before} → {objectives_after}"
            
            # Route based on confidence
            if confidence >= self.confidence_thresholds['automated']:
                filtered_quests[quest_id] = filtered_quest
            elif confidence < self.confidence_thresholds['manual']:
                manual_review_quests.append((quest_id, quest_data, filtered_quest, confidence))
            else:
                # Medium confidence - pass with warnings
                filtered_quest['_warnings'] = [f'Medium confidence: {confidence:.2%}']
                filtered_quests[quest_id] = filtered_quest
        
        # Save manual review quests
        if manual_review_quests:
            self.save_manual_review(manual_review_quests)
        
        print(f"\n📊 Filtering Results:")
        print(f"   Objectives before: {total_before:,}")
        print(f"   Objectives after: {total_after:,}")
        print(f"   Reduction: {(1 - total_after/total_before)*100:.1f}%")
        print(f"   Quests processed: {len(aggregated_data.get('quests', {}))}")
        print(f"   High confidence: {len(filtered_quests)}")
        print(f"   Manual review needed: {len(manual_review_quests)}")
        
        return filtered_quests
    
    def parse_objectives_text(self, objectives_texts: List[str]) -> Dict:
        """
        Parse objectives text to extract requirements
        
        Args:
            objectives_texts: List of objectives text strings
            
        Returns:
            Dictionary of parsed objectives by type
        """
        parsed = {
            'kill': [],
            'collect': [],
            'interact': []
        }
        
        for text in objectives_texts:
            if not text:
                continue
                
            # Clean the text
            text = text.strip()
            
            # Try to parse kill objectives
            for pattern in self.objective_patterns['kill']:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 2:
                        # Handle different capture group orders
                        if groups[0].isdigit():
                            count, name = groups[0], groups[1]
                        else:
                            name, count = groups[0], groups[1]
                        
                        parsed['kill'].append({
                            'name': name.strip(),
                            'count': int(count) if count.isdigit() else 1,
                            'raw_text': match.group(0)
                        })
            
            # Try to parse collect objectives
            for pattern in self.objective_patterns['collect']:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 2:
                        # Handle different capture group orders
                        if groups[0].isdigit():
                            count, name = groups[0], groups[1]
                        else:
                            name, count = groups[0], groups[1]
                        
                        # Special case: "Item Name: 0/5" format
                        if '/' in match.group(0) and count.isdigit():
                            parsed['collect'].append({
                                'name': name.strip(),
                                'count': int(count),
                                'raw_text': match.group(0)
                            })
                        elif count.isdigit():
                            parsed['collect'].append({
                                'name': name.strip(),
                                'count': int(count),
                                'raw_text': match.group(0)
                            })
            
            # Try to parse interact objectives
            for pattern in self.objective_patterns['interact']:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    name = match.group(1) if match.groups() else match.group(0)
                    parsed['interact'].append({
                        'name': name.strip(),
                        'count': 1,
                        'raw_text': match.group(0)
                    })
        
        return parsed
    
    def match_objectives(self, required_objectives: Dict, collected_objectives: Dict, quest_name: str) -> Tuple[Dict, float]:
        """
        Match parsed requirements against collected items/creatures/objects
        
        Args:
            required_objectives: Parsed objectives from text
            collected_objectives: All collected objectives from aggregator
            quest_name: Name of quest for context
            
        Returns:
            Tuple of (filtered objectives dict, confidence score)
        """
        filtered = {
            'items': [],
            'creatures': [],
            'objects': []
        }
        
        matches_found = 0
        total_required = 0
        
        # Match collected items against required collect objectives
        for req in required_objectives.get('collect', []):
            total_required += 1
            req_name = req['name'].lower()
            req_count = req['count']
            
            # Try to find matching items
            best_match = None
            best_score = 0
            
            for item in collected_objectives.get('items', []):
                item_name = item.get('name', '').lower()
                
                # Skip items with no name
                if not item_name:
                    continue
                
                # Direct match
                if req_name in item_name or item_name in req_name:
                    best_match = item
                    best_score = 1.0
                    break
                
                # Fuzzy match
                score = self.fuzzy_match(req_name, item_name)
                if score > best_score and score > 0.6:  # Lower threshold
                    best_match = item
                    best_score = score
            
            if best_match:
                # Add to filtered with required count
                filtered_item = dict(best_match)
                filtered_item['count'] = req_count
                filtered_item['_matched_from'] = req['raw_text']
                filtered_item['_match_confidence'] = best_score
                filtered['items'].append(filtered_item)
                matches_found += 1
            elif len(collected_objectives.get('items', [])) == 1:
                # Special case: only one item collected, probably the right one
                item = collected_objectives['items'][0]
                if item.get('name'):  # Only if it has a name
                    filtered_item = dict(item)
                    filtered_item['count'] = req_count
                    filtered_item['_matched_from'] = req['raw_text']
                    filtered_item['_match_confidence'] = 0.8
                    filtered['items'].append(filtered_item)
                    matches_found += 0.8  # Partial credit
        
        # Match creatures against kill objectives
        for req in required_objectives.get('kill', []):
            total_required += 1
            req_name = req['name'].lower()
            req_count = req['count']
            
            best_match = None
            best_score = 0
            
            for creature in collected_objectives.get('creatures', []):
                creature_name = creature.get('name', '').lower()
                
                if req_name in creature_name or creature_name in req_name:
                    best_match = creature
                    best_score = 1.0
                    break
                
                score = self.fuzzy_match(req_name, creature_name)
                if score > best_score and score > 0.7:
                    best_match = creature
                    best_score = score
            
            if best_match:
                filtered_creature = dict(best_match)
                filtered_creature['count'] = req_count
                filtered_creature['_matched_from'] = req['raw_text']
                filtered_creature['_match_confidence'] = best_score
                filtered['creatures'].append(filtered_creature)
                matches_found += 1
        
        # Calculate confidence
        if total_required > 0:
            confidence = matches_found / total_required
            
            # Boost confidence if we found reasonable matches
            if confidence >= 0.5 and confidence < 0.9:
                confidence = min(0.95, confidence + 0.2)  # Boost partial matches
        elif not required_objectives.get('collect') and not required_objectives.get('kill'):
            # No clear objectives found in text - but that's OK for simple quests
            if len(collected_objectives.get('items', [])) <= 3:
                # Few items, probably simple quest
                confidence = 0.75
                # Just pass through what was collected
                filtered['items'] = collected_objectives.get('items', [])[:3]
            else:
                confidence = 0.3
        else:
            confidence = 0.5
        
        # If we didn't match anything but have objectives text, check special cases
        if matches_found == 0 and (required_objectives.get('collect') or required_objectives.get('kill')):
            # Check if items have no names
            items_without_names = sum(1 for item in collected_objectives.get('items', []) if not item.get('name'))
            if items_without_names > 0:
                # Items exist but have no names - common issue
                confidence = 0.6
                # Take first few items as likely candidates
                filtered['items'] = collected_objectives.get('items', [])[:min(3, total_required)]
            else:
                confidence = 0.2
        
        return filtered, confidence
    
    def fuzzy_match(self, str1: str, str2: str) -> float:
        """
        Calculate fuzzy match score between two strings
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Match score between 0 and 1
        """
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _count_objectives(self, objectives: Dict) -> int:
        """Count total objectives in a dictionary"""
        return (len(objectives.get('items', [])) + 
                len(objectives.get('creatures', [])) + 
                len(objectives.get('objects', [])))
    
    def save_manual_review(self, review_quests: List):
        """
        Save quests needing manual review to timestamped file
        
        Args:
            review_quests: List of (quest_id, original_data, filtered_data, confidence) tuples
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        review_file = self.manual_review_dir / f"review_{timestamp}.txt"
        
        with open(review_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write(f"MANUAL REVIEW NEEDED - Generated: {datetime.now()}\n")
            f.write("="*80 + "\n\n")
            f.write(f"Total quests for review: {len(review_quests)}\n\n")
            
            for quest_id, original, filtered, confidence in review_quests:
                f.write("-"*80 + "\n")
                f.write(f"Quest ID: {quest_id}\n")
                f.write(f"Quest Name: {original.get('name', 'Unknown')}\n")
                f.write(f"Confidence Score: {confidence:.2%}\n")
                f.write(f"Issue: Low confidence in objective matching\n\n")
                
                f.write("OBJECTIVES TEXT:\n")
                for text in original.get('objectivesText', ['No objectives text']):
                    f.write(f'  "{text}"\n')
                f.write("\n")
                
                f.write(f"COLLECTED ITEMS ({len(original.get('objectives', {}).get('items', []))} total):\n")
                for item in original.get('objectives', {}).get('items', [])[:10]:
                    f.write(f"  - {item.get('name', 'Unknown')} (ID: {item.get('id')})\n")
                if len(original.get('objectives', {}).get('items', [])) > 10:
                    f.write(f"  ... and {len(original.get('objectives', {}).get('items', [])) - 10} more\n")
                f.write("\n")
                
                f.write(f"FILTERED RESULT:\n")
                filtered_items = filtered.get('objectives', {}).get('items', [])
                if filtered_items:
                    for item in filtered_items:
                        f.write(f"  - {item.get('name')} x{item.get('count', 1)}")
                        if '_matched_from' in item:
                            f.write(f" (matched: '{item['_matched_from']}')")
                        f.write("\n")
                else:
                    f.write("  No items matched from objectives text\n")
                f.write("\n")
                
                f.write("RECOMMENDATION:\n")
                f.write("  Review objectives text and collected items.\n")
                f.write("  Determine correct objectives manually.\n\n")
        
        print(f"\n📝 Manual review file saved: {review_file}")


def test_filter():
    """Test the filter with sample data"""
    filter = ObjectiveConsensusFilter()
    
    # Test objective text parsing
    test_texts = [
        "Burning Elemental Core: 0/1",
        "Bring 5 Bracers of Rock Binding to Lotwil Veriatus",
        "Kill 10 Rock Elementals",
        "Collect 8 Basilisk Scales and 2 Pristine Yeti Horns"
    ]
    
    print("Testing objective text parsing:")
    for text in test_texts:
        parsed = filter.parse_objectives_text([text])
        print(f"\nText: '{text}'")
        print(f"Parsed: {parsed}")
    
    # Load and filter real data
    aggregated_file = Path("aggregated_data/aggregated_quests.json")
    if aggregated_file.exists():
        print("\n" + "="*60)
        print("Testing with real aggregated data...")
        
        with open(aggregated_file, 'r') as f:
            data = json.load(f)
        
        # Filter the quests
        filtered = filter.filter_objectives(data)
        
        # Show some examples
        print("\nExample filtered quests:")
        for quest_id, quest in list(filtered.items())[:3]:
            print(f"\nQuest {quest_id}: {quest.get('name')}")
            print(f"  Confidence: {quest.get('_filter_confidence', 0):.2%}")
            print(f"  Reduction: {quest.get('_objectives_reduced')}")
            if quest.get('objectives', {}).get('items'):
                print("  Filtered items:")
                for item in quest['objectives']['items'][:3]:
                    print(f"    - {item.get('name')} x{item.get('count', 1)}")


if __name__ == "__main__":
    test_filter()