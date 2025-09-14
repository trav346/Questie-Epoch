#!/usr/bin/env python3
"""
Partial Data Processor Module
Handles quests with incomplete/missing data that should still contribute to the database.
These quests bypass manual review and go directly to database merge with whatever data they have.
"""

import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime

class PartialDataProcessor:
    """Process quests with partial/incomplete data for database contribution"""
    
    def __init__(self):
        """Initialize the processor with categorization rules"""
        
        # Categories of partial data quests
        self.categories = {
            'missing_objectives_text': {
                'description': 'No objectives text but has items/NPCs',
                'min_confidence': 0.60,
                'strategy': 'accept_collected_data'
            },
            'no_items_collected': {
                'description': 'Kill/exploration quest with no items',
                'min_confidence': 0.70,
                'strategy': 'accept_as_is'
            },
            'unnamed_entities': {
                'description': 'Items/creatures with no names (but have IDs)',
                'min_confidence': 0.65,
                'strategy': 'accept_by_id'
            },
            'partial_match': {
                'description': 'Some objectives matched, some missing',
                'min_confidence': 0.55,
                'strategy': 'accept_matched_only'
            },
            'epoch_runtime_stub': {
                'description': 'High-ID Epoch quest needing any data',
                'min_confidence': 0.40,  # Very low threshold for runtime stubs
                'strategy': 'accept_anything'
            }
        }
        
        # Output directory for processed partial data
        self.output_dir = Path("partial_data_processed")
        self.output_dir.mkdir(exist_ok=True)
        
    def process_partial_data_quests(self, low_confidence_quests: List[Tuple], 
                                   aggregated_data: Dict) -> Dict:
        """
        Process quests that failed the main filter but have valuable partial data
        
        Args:
            low_confidence_quests: List of (quest_id, quest_data, filtered_data, confidence) tuples
            aggregated_data: Original aggregated data for reference
            
        Returns:
            Dictionary of processed quests ready for database merge
        """
        processed = {}
        categorized = {
            'missing_objectives_text': [],
            'no_items_collected': [],
            'unnamed_entities': [],
            'partial_match': [],
            'epoch_runtime_stub': [],
            'truly_incomplete': []  # Actually need manual review
        }
        
        for quest_id, quest_data, filtered_data, confidence in low_confidence_quests:
            category = self.categorize_quest(quest_id, quest_data, confidence)
            
            if category == 'truly_incomplete':
                # This one actually needs manual review
                categorized['truly_incomplete'].append((quest_id, quest_data))
                continue
            
            # Process based on category
            processed_quest = self.process_by_category(
                quest_id, quest_data, filtered_data, category, confidence
            )
            
            if processed_quest:
                processed[quest_id] = processed_quest
                categorized[category].append((quest_id, quest_data.get('name', f'Quest {quest_id}')))
        
        # Generate report
        self.generate_report(categorized, processed)
        
        return processed
    
    def categorize_quest(self, quest_id: str, quest_data: Dict, confidence: float) -> str:
        """
        Categorize a quest based on its data characteristics
        
        Returns:
            Category name or 'truly_incomplete' if it needs manual review
        """
        objectives = quest_data.get('objectives', {})
        objectives_text = quest_data.get('objectivesText', [])
        
        # Check if it's an Epoch quest (high ID)
        try:
            if int(quest_id) >= 25000:
                return 'epoch_runtime_stub'
        except:
            pass
        
        # No objectives text but has collected data
        if (not objectives_text or 
            all(not text or text == '(No objectives text available)' or text == ': 0/1' 
                for text in objectives_text)):
            if self._has_any_data(objectives):
                return 'missing_objectives_text'
        
        # No items collected (kill/exploration quest)
        items = objectives.get('items', [])
        creatures = objectives.get('creatures', [])
        if not items and (creatures or not self._has_any_data(objectives)):
            return 'no_items_collected'
        
        # Has unnamed entities but they have IDs
        if self._has_unnamed_entities(objectives):
            return 'unnamed_entities'
        
        # Partial match (confidence between 30-50%)
        if 0.30 <= confidence < 0.50 and self._has_any_data(objectives):
            return 'partial_match'
        
        # If we get here and confidence is very low with no clear category
        if confidence < 0.20 and not self._has_any_data(objectives):
            return 'truly_incomplete'
        
        # Default to partial match for anything else with data
        if self._has_any_data(objectives):
            return 'partial_match'
        
        return 'truly_incomplete'
    
    def process_by_category(self, quest_id: str, quest_data: Dict, 
                           filtered_data: Dict, category: str, 
                           original_confidence: float) -> Optional[Dict]:
        """
        Process a quest based on its category
        
        Returns:
            Processed quest data ready for database merge, or None if unable to process
        """
        strategy = self.categories[category]['strategy']
        min_confidence = self.categories[category]['min_confidence']
        
        # Create base processed quest
        processed = {
            'id': quest_id,
            'name': quest_data.get('name', f'[Epoch] Quest {quest_id}'),
            '_processing_category': category,
            '_original_confidence': original_confidence,
            '_adjusted_confidence': max(original_confidence, min_confidence),
            '_partial_data': True
        }
        
        # Apply strategy
        if strategy == 'accept_collected_data':
            # Accept whatever was collected
            processed['objectives'] = quest_data.get('objectives', {})
            processed['_note'] = 'Accepted all collected data (no objectives text)'
            
        elif strategy == 'accept_as_is':
            # Accept as kill/exploration quest
            processed['objectives'] = quest_data.get('objectives', {})
            processed['_note'] = 'Kill/exploration quest (no items expected)'
            
        elif strategy == 'accept_by_id':
            # Accept entities even without names (use IDs)
            objectives = quest_data.get('objectives', {})
            processed['objectives'] = self._clean_unnamed_entities(objectives)
            processed['_note'] = 'Accepted with ID-only entities'
            
        elif strategy == 'accept_matched_only':
            # Use whatever the filter managed to match
            processed['objectives'] = filtered_data.get('objectives', {})
            if not processed['objectives'] or self._is_empty_objectives(processed['objectives']):
                # Fall back to raw collected data
                processed['objectives'] = quest_data.get('objectives', {})
            processed['_note'] = 'Partial match - accepted what could be matched'
            
        elif strategy == 'accept_anything':
            # Epoch quest - accept ANY data to help runtime stubs
            processed['objectives'] = quest_data.get('objectives', {})
            processed['_note'] = 'Epoch quest - accepted all available data for runtime stub'
            # Mark as Epoch quest if not already
            if not processed['name'].startswith('[Epoch]'):
                processed['name'] = f"[Epoch] {processed['name']}"
        
        # Add any other valuable data
        if quest_data.get('startedBy'):
            processed['startedBy'] = quest_data['startedBy']
        if quest_data.get('finishedBy'):
            processed['finishedBy'] = quest_data['finishedBy']
        if quest_data.get('requiredLevel'):
            processed['requiredLevel'] = quest_data['requiredLevel']
        if quest_data.get('questLevel'):
            processed['questLevel'] = quest_data['questLevel']
        if quest_data.get('objectivesText'):
            processed['objectivesText'] = quest_data['objectivesText']
        
        # Add coordinates if available
        for coord_type in ['questGiverCoords', 'turnInCoords', 'objectiveCoords']:
            if quest_data.get(coord_type):
                processed[coord_type] = quest_data[coord_type]
        
        return processed
    
    def _has_any_data(self, objectives: Dict) -> bool:
        """Check if objectives dict has any actual data"""
        return (len(objectives.get('items', [])) > 0 or
                len(objectives.get('creatures', [])) > 0 or
                len(objectives.get('objects', [])) > 0)
    
    def _has_unnamed_entities(self, objectives: Dict) -> bool:
        """Check if there are entities without names but with IDs"""
        for item in objectives.get('items', []):
            if not item.get('name') and item.get('id'):
                return True
        for creature in objectives.get('creatures', []):
            if not creature.get('name') and creature.get('id'):
                return True
        return False
    
    def _clean_unnamed_entities(self, objectives: Dict) -> Dict:
        """Clean up unnamed entities, keeping those with IDs"""
        cleaned = {
            'items': [],
            'creatures': [],
            'objects': objectives.get('objects', [])
        }
        
        # Keep items with IDs even without names
        for item in objectives.get('items', []):
            if item.get('id'):
                cleaned['items'].append(item)
            elif item.get('name'):  # Keep named items even without IDs
                cleaned['items'].append(item)
        
        # Same for creatures
        for creature in objectives.get('creatures', []):
            if creature.get('id') or creature.get('name'):
                cleaned['creatures'].append(creature)
        
        return cleaned
    
    def _is_empty_objectives(self, objectives: Dict) -> bool:
        """Check if objectives dict is effectively empty"""
        return not self._has_any_data(objectives)
    
    def generate_report(self, categorized: Dict, processed: Dict):
        """Generate a report of processed partial data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"partial_data_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("PARTIAL DATA PROCESSING REPORT\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Total Processed: {len(processed)} quests\n")
            f.write(f"Actually Incomplete: {len(categorized['truly_incomplete'])} quests\n\n")
            
            f.write("CATEGORY BREAKDOWN:\n")
            f.write("-"*40 + "\n")
            
            for category, quests in categorized.items():
                if category == 'truly_incomplete':
                    continue
                if quests:
                    f.write(f"\n{category.upper().replace('_', ' ')} ({len(quests)} quests):\n")
                    f.write(f"Description: {self.categories[category]['description']}\n")
                    f.write(f"Strategy: {self.categories[category]['strategy']}\n")
                    f.write(f"Min Confidence: {self.categories[category]['min_confidence']:.0%}\n")
                    f.write("Sample quests:\n")
                    for quest_id, quest_name in quests[:5]:
                        f.write(f"  - {quest_id}: {quest_name}\n")
                    if len(quests) > 5:
                        f.write(f"  ... and {len(quests)-5} more\n")
            
            if categorized['truly_incomplete']:
                f.write("\n" + "="*40 + "\n")
                f.write(f"TRULY INCOMPLETE ({len(categorized['truly_incomplete'])} quests)\n")
                f.write("These quests have insufficient data and need manual review:\n")
                for quest_id, quest_data in categorized['truly_incomplete'][:10]:
                    f.write(f"  - {quest_id}: {quest_data.get('name', 'Unknown')}\n")
                if len(categorized['truly_incomplete']) > 10:
                    f.write(f"  ... and {len(categorized['truly_incomplete'])-10} more\n")
            
            f.write("\n" + "="*40 + "\n")
            f.write("SUMMARY:\n")
            f.write(f"• {len(processed)} quests processed with partial data\n")
            f.write(f"• {len(categorized['epoch_runtime_stub'])} Epoch quests for runtime stubs\n")
            f.write(f"• {len(categorized['no_items_collected'])} kill/exploration quests\n")
            f.write(f"• {len(categorized['missing_objectives_text'])} quests with missing text\n")
            f.write(f"• {len(categorized['truly_incomplete'])} quests need manual review\n")
        
        # Save processed quests to JSON
        json_file = self.output_dir / f"partial_data_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'total_processed': len(processed),
                    'categories': {k: len(v) for k, v in categorized.items()}
                },
                'quests': processed
            }, f, indent=2)
        
        print(f"📁 Report saved to: {report_file}")
        print(f"📁 Processed data saved to: {json_file}")
        
    def merge_with_database(self, processed_quests: Dict, existing_db: Dict) -> Dict:
        """
        Merge partial data with existing database entries
        
        This implements the additive merge strategy - adding data without removing anything
        """
        merged = {}
        stats = {
            'new_quests': 0,
            'enhanced_stubs': 0,
            'data_added': 0,
            'unchanged': 0
        }
        
        for quest_id, partial_data in processed_quests.items():
            if quest_id in existing_db:
                existing = existing_db[quest_id]
                
                # Check if it's a runtime stub
                if existing.get('name', '').startswith('[Epoch]'):
                    # Enhance the stub with partial data
                    merged[quest_id] = self._enhance_stub(existing, partial_data)
                    stats['enhanced_stubs'] += 1
                else:
                    # Add missing data to existing quest
                    merged[quest_id] = self._additive_merge(existing, partial_data)
                    if merged[quest_id] != existing:
                        stats['data_added'] += 1
                    else:
                        stats['unchanged'] += 1
            else:
                # New quest - add even with partial data
                merged[quest_id] = partial_data
                stats['new_quests'] += 1
        
        print(f"\n📊 Merge Statistics:")
        print(f"   New quests added: {stats['new_quests']}")
        print(f"   Runtime stubs enhanced: {stats['enhanced_stubs']}")
        print(f"   Existing quests improved: {stats['data_added']}")
        print(f"   Unchanged: {stats['unchanged']}")
        
        return merged
    
    def _enhance_stub(self, stub: Dict, partial_data: Dict) -> Dict:
        """Enhance a runtime stub with partial data"""
        enhanced = dict(stub)
        
        # Replace stub name if we have a real one
        if not partial_data.get('name', '').startswith('[Epoch]'):
            enhanced['name'] = partial_data['name']
        
        # Add any objectives we found
        if partial_data.get('objectives'):
            enhanced['objectives'] = partial_data['objectives']
        
        # Add any other data
        for key in ['startedBy', 'finishedBy', 'requiredLevel', 'questLevel', 
                    'objectivesText', 'questGiverCoords', 'turnInCoords']:
            if partial_data.get(key) and not enhanced.get(key):
                enhanced[key] = partial_data[key]
        
        enhanced['_enhanced_from_partial'] = True
        return enhanced
    
    def _additive_merge(self, existing: Dict, partial: Dict) -> Dict:
        """Additively merge partial data into existing quest"""
        merged = dict(existing)
        
        # Add objectives additively
        if partial.get('objectives'):
            if not merged.get('objectives'):
                merged['objectives'] = {'items': [], 'creatures': [], 'objects': []}
            
            # Merge items (avoid duplicates by ID)
            existing_item_ids = {item.get('id') for item in merged['objectives'].get('items', []) if item.get('id')}
            for item in partial['objectives'].get('items', []):
                if item.get('id') and item['id'] not in existing_item_ids:
                    merged['objectives']['items'].append(item)
            
            # Merge creatures
            existing_creature_ids = {c.get('id') for c in merged['objectives'].get('creatures', []) if c.get('id')}
            for creature in partial['objectives'].get('creatures', []):
                if creature.get('id') and creature['id'] not in existing_creature_ids:
                    merged['objectives']['creatures'].append(creature)
        
        # Add missing scalar fields
        for key in ['requiredLevel', 'questLevel']:
            if partial.get(key) and not merged.get(key):
                merged[key] = partial[key]
        
        # Merge coordinate lists
        for coord_key in ['questGiverCoords', 'turnInCoords']:
            if partial.get(coord_key):
                if not merged.get(coord_key):
                    merged[coord_key] = []
                # Add new coordinates (with deduplication)
                for coord in partial[coord_key]:
                    if coord not in merged[coord_key]:
                        merged[coord_key].append(coord)
        
        return merged