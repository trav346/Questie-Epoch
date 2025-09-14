#!/usr/bin/env python3
"""
Objective Consensus Filter Module V2
Enhanced version with better handling of:
- Items without names (match by ID)
- Improved text parsing patterns
- Lower fuzzy match thresholds
- Better comma-separated list handling
- Database lookups for item names
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

class ObjectiveConsensusFilterV2:
    """Enhanced filter with improved matching logic"""
    
    def __init__(self):
        """Initialize the consensus filter with patterns and thresholds"""
        self.confidence_thresholds = {
            'automated': 0.85,     # Lowered from 0.90 for more automation
            'review': 0.60,        # Lowered from 0.70 for wider middle ground
            'manual': 0.60         # <60% needs manual review
        }
        
        # Enhanced objective patterns with more variations
        self.objective_patterns = {
            'kill': [
                # Standard kill patterns
                r'(?:Kill|Slay|Defeat|Destroy|Eliminate)\s+(\d+)\s+(.+?)(?:\.|,|;|$)',
                # Progress format: "Rock Elemental: 0/10" or "10/10 Rock Elementals"
                r'(.+?):\s*\d+/(\d+)',
                r'(\d+)/\d+\s+(.+?)(?:\s+killed|\s+slain|$)',
                # Past tense variations
                r'(\d+)\s+(.+?)\s+(?:killed|slain|defeated|destroyed)',
                # Simple count format
                r'(\d+)\s+(.+?)(?:\s+to\s+kill|\s+to\s+slay|$)',
            ],
            'collect': [
                # Standard collect patterns
                r'(?:Collect|Gather|Obtain|Acquire|Bring|Get|Find|Retrieve|Fetch)\s+(\d+)\s+(.+?)(?:\.|,|;|:|\s+to\s+|\s+from\s+|$)',
                # Progress format: "Bracers of Rock Binding: 0/5"
                r'(.+?):\s*\d+/(\d+)',
                # Quantity format: "5 x Bracers" or "Bracers x5"
                r'(\d+)\s*x\s+(.+?)(?:\.|,|;|$)',
                r'(.+?)\s*x\s*(\d+)(?:\.|,|;|$)',
                # Needed/required format
                r'(.+?):\s*(\d+)\s+(?:needed|required)',
                r'(\d+)\s+(.+?)\s+(?:needed|required)',
                # Quest item format
                r'Quest\s+Item:\s*(.+?)(?:\.|,|;|$)',
                # Simple number format at start
                r'^(\d+)\s+(.+?)(?:\.|,|;|$)',
            ],
            'interact': [
                r'(?:Interact with|Use|Activate|Click|Touch|Examine)\s+(?:the\s+)?(.+?)(?:\.|,|;|$)',
                r'(?:Speak with|Talk to|Speak to|Find)\s+(.+?)(?:\.|,|;|$)',
                r'(?:Right-click|Left-click|Click on)\s+(?:the\s+)?(.+?)(?:\.|,|;|$)',
            ]
        }
        
        # Manual review folder
        self.manual_review_dir = Path("Manual Review")
        self.manual_review_dir.mkdir(exist_ok=True)
        
        # Load item database for name lookups (if available)
        self.item_database = self._load_item_database()
        
    def _load_item_database(self) -> Dict:
        """Load item database for name lookups"""
        item_db = {}
        # Try to load from epochItemDB.lua if available
        epoch_item_db = Path("../../Database/Epoch/epochItemDB.lua")
        if epoch_item_db.exists():
            try:
                with open(epoch_item_db, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple regex to extract item ID and name
                    pattern = r'\[(\d+)\]\s*=\s*\{\s*"([^"]+)"'
                    for match in re.finditer(pattern, content):
                        item_id = int(match.group(1))
                        item_name = match.group(2)
                        item_db[item_id] = item_name
            except:
                pass  # Database not available, that's OK
        return item_db
        
    def filter_objectives(self, aggregated_data: Dict) -> Dict:
        """
        Main filtering pipeline with enhanced logic
        """
        filtered_quests = {}
        manual_review_quests = []
        
        total_before = 0
        total_after = 0
        
        for quest_id, quest_data in aggregated_data.get('quests', {}).items():
            # Count objectives before
            objectives_before = self._count_objectives(quest_data.get('objectives', {}))
            total_before += objectives_before
            
            # Parse objectives from text with enhanced patterns
            required_objectives = self.parse_objectives_text_enhanced(
                quest_data.get('objectivesText', [])
            )
            
            # Match against collected items with improved logic
            filtered_objectives, confidence = self.match_objectives_enhanced(
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
            print(f"📝 Saved {len(manual_review_quests)} quests to Manual Review folder")
        
        # Print statistics
        print(f"\n📊 Filtering Results:")
        print(f"   Objectives before: {total_before}")
        print(f"   Objectives after: {total_after}")
        if total_before > 0:
            print(f"   Reduction: {(1 - total_after/total_before)*100:.1f}%")
        print(f"   High confidence: {len(filtered_quests)} quests")
        print(f"   Manual review needed: {len(manual_review_quests)} quests")
        
        return filtered_quests
    
    def parse_objectives_text_enhanced(self, objectives_texts: List[str]) -> Dict:
        """
        Enhanced parsing with better comma-separated list handling
        """
        parsed = {
            'kill': [],
            'collect': [],
            'interact': []
        }
        
        for text in objectives_texts:
            if not text:
                continue
            
            # First, handle comma-separated lists
            # Example: "Collect 5 Bracers, 3 Shards, and 2 Cores"
            comma_pattern = r'(?:Collect|Gather|Get)\s+(.+?)(?:\.|$)'
            comma_match = re.search(comma_pattern, text, re.IGNORECASE)
            if comma_match:
                items_text = comma_match.group(1)
                # Split by commas and 'and'
                items = re.split(r',\s*(?:and\s+)?|\s+and\s+', items_text)
                for item in items:
                    item = item.strip()
                    # Extract count and name
                    count_match = re.match(r'(\d+)\s+(.+)', item)
                    if count_match:
                        parsed['collect'].append({
                            'count': int(count_match.group(1)),
                            'name': count_match.group(2).strip(),
                            'raw_text': item
                        })
                continue
            
            # Try each pattern type
            for obj_type, patterns in self.objective_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        if obj_type in ['kill', 'collect']:
                            # Handle patterns with count
                            if len(match.groups()) >= 2:
                                # Determine which group is count vs name
                                group1, group2 = match.group(1), match.group(2)
                                
                                # Try to figure out which is the count
                                try:
                                    count = int(group1)
                                    name = group2
                                except:
                                    try:
                                        count = int(group2)
                                        name = group1
                                    except:
                                        # Neither is a clean number, skip
                                        continue
                                
                                # Clean up the name
                                name = name.strip()
                                # Remove trailing words like "slain", "killed", etc.
                                name = re.sub(r'\s+(slain|killed|defeated|destroyed|found|collected)$', '', name, flags=re.IGNORECASE)
                                
                                if name and count > 0:
                                    parsed[obj_type].append({
                                        'count': count,
                                        'name': name,
                                        'raw_text': match.group(0)
                                    })
                        else:
                            # Interact objectives
                            if match.group(1):
                                parsed[obj_type].append({
                                    'name': match.group(1).strip(),
                                    'raw_text': match.group(0)
                                })
        
        return parsed
    
    def match_objectives_enhanced(self, required_objectives: Dict, 
                                 collected_objectives: Dict, 
                                 quest_name: str) -> Tuple[Dict, float]:
        """
        Enhanced matching with ID-based fallback and lower thresholds
        """
        filtered = {
            'items': [],
            'creatures': [],
            'objects': []
        }
        
        matches_found = 0
        total_required = 0
        
        # Track which collected items we've already matched
        matched_item_ids = set()
        
        # Match collected items against required collect objectives
        for req in required_objectives.get('collect', []):
            total_required += 1
            req_name = req['name'].lower()
            req_count = req['count']
            
            # Try to find matching items
            best_match = None
            best_score = 0
            best_match_id = None
            
            for item in collected_objectives.get('items', []):
                item_id = item.get('id')
                if item_id in matched_item_ids:
                    continue  # Already matched this item
                    
                item_name = item.get('name', '').lower()
                
                # If item has no name, try to look it up
                if not item_name and item_id and self.item_database:
                    item_name = self.item_database.get(item_id, '').lower()
                    if item_name:
                        item['name'] = item_name  # Update the item with found name
                
                # Skip if still no name and we have other options
                if not item_name and len(collected_objectives.get('items', [])) > 3:
                    continue
                
                # If we have a name, try matching
                if item_name:
                    # Direct substring match
                    if req_name in item_name or item_name in req_name:
                        best_match = item
                        best_score = 1.0
                        best_match_id = item_id
                        break
                    
                    # Try word-level matching (any word matches)
                    req_words = set(req_name.split())
                    item_words = set(item_name.split())
                    if req_words & item_words:  # Intersection
                        score = len(req_words & item_words) / len(req_words)
                        if score > best_score:
                            best_match = item
                            best_score = score
                            best_match_id = item_id
                    
                    # Fuzzy match with lower threshold
                    score = self.fuzzy_match(req_name, item_name)
                    if score > best_score and score > 0.5:  # Lowered from 0.6
                        best_match = item
                        best_score = score
                        best_match_id = item_id
                else:
                    # No name but we have an ID - partial credit
                    if not best_match:
                        best_match = item
                        best_score = 0.4  # Low confidence but better than nothing
                        best_match_id = item_id
            
            if best_match:
                # Add to filtered with required count
                filtered_item = dict(best_match)
                filtered_item['count'] = req_count
                filtered_item['_matched_from'] = req['raw_text']
                filtered_item['_match_confidence'] = best_score
                filtered['items'].append(filtered_item)
                matches_found += best_score  # Partial credit based on confidence
                if best_match_id:
                    matched_item_ids.add(best_match_id)
        
        # If no objectives text but few items, accept them
        if not required_objectives.get('collect') and not required_objectives.get('kill'):
            items = collected_objectives.get('items', [])
            if len(items) <= 3:
                # Accept all items for simple quests
                filtered['items'] = items
                confidence = 0.80  # Good confidence for simple quests
            elif len(items) <= 5:
                # Accept with medium confidence
                filtered['items'] = items[:5]
                confidence = 0.65
            else:
                # Too many items, low confidence
                confidence = 0.30
        elif total_required > 0:
            # Calculate base confidence
            confidence = matches_found / total_required
            
            # Apply intelligent boosting
            if confidence >= 0.3 and confidence < 0.85:
                # Boost partial matches more aggressively
                confidence = min(0.90, confidence + 0.25)
            
            # Special case: single item collected for single objective
            if (total_required == 1 and len(collected_objectives.get('items', [])) == 1):
                confidence = max(confidence, 0.85)
        else:
            confidence = 0.5
        
        # Handle items without names as special case
        if matches_found == 0 and total_required > 0:
            items_without_names = [item for item in collected_objectives.get('items', []) 
                                  if not item.get('name')]
            if items_without_names:
                # Take items by ID even without names
                for i, item in enumerate(items_without_names[:total_required]):
                    filtered_item = dict(item)
                    filtered_item['_note'] = 'Matched by position (no name available)'
                    filtered['items'].append(filtered_item)
                confidence = 0.65  # Medium confidence for ID-only matches
        
        # Match creatures (similar logic but simpler)
        for req in required_objectives.get('kill', []):
            total_required += 1
            req_name = req['name'].lower()
            req_count = req['count']
            
            best_match = None
            best_score = 0
            
            for creature in collected_objectives.get('creatures', []):
                creature_name = creature.get('name', '').lower()
                if not creature_name:
                    continue
                
                # Direct match
                if req_name in creature_name or creature_name in req_name:
                    best_match = creature
                    best_score = 1.0
                    break
                
                # Word matching
                req_words = set(req_name.split())
                creature_words = set(creature_name.split())
                if req_words & creature_words:
                    score = len(req_words & creature_words) / len(req_words)
                    if score > best_score:
                        best_match = creature
                        best_score = score
                
                # Fuzzy match
                score = self.fuzzy_match(req_name, creature_name)
                if score > best_score and score > 0.5:
                    best_match = creature
                    best_score = score
            
            if best_match:
                filtered_creature = dict(best_match)
                filtered_creature['count'] = req_count
                filtered_creature['_matched_from'] = req['raw_text']
                filtered_creature['_match_confidence'] = best_score
                filtered['creatures'].append(filtered_creature)
                matches_found += best_score
        
        return filtered, confidence
    
    def fuzzy_match(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match score between two strings"""
        return SequenceMatcher(None, str1, str2).ratio()
    
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
                
                # Determine why it needs review
                if confidence < 0.3:
                    f.write("Issue: Very low confidence - likely missing objectives text or no matches\n")
                elif confidence < 0.6:
                    f.write("Issue: Low confidence - partial matches or uncertain parsing\n")
                else:
                    f.write("Issue: Medium confidence - review recommended\n")
                
                f.write(f"\nOBJECTIVES TEXT:\n")
                for text in original.get('objectivesText', []):
                    f.write(f"  {text}\n")
                if not original.get('objectivesText'):
                    f.write("  (No objectives text available)\n")
                
                # Show what was collected
                objectives = original.get('objectives', {})
                total_collected = self._count_objectives(objectives)
                f.write(f"\nCOLLECTED ITEMS ({total_collected} total):\n")
                
                for item in objectives.get('items', []):
                    name = item.get('name', f"(ID: {item.get('id')})")
                    f.write(f"  - {name}\n")
                
                for creature in objectives.get('creatures', []):
                    f.write(f"  - {creature.get('name')} (creature)\n")
                
                # Show filtered result
                filtered_obj = filtered.get('objectives', {})
                total_filtered = self._count_objectives(filtered_obj)
                f.write(f"\nFILTERED RESULT ({total_filtered} items):\n")
                
                if total_filtered == 0:
                    f.write("  No items matched from objectives text\n")
                else:
                    for item in filtered_obj.get('items', []):
                        conf = item.get('_match_confidence', 0)
                        f.write(f"  - {item.get('name', 'Unknown')} (confidence: {conf:.1%})\n")
                
                f.write("\n")
        
        print(f"Saved manual review file: {filepath}")