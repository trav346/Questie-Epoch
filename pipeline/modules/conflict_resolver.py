#!/usr/bin/env python3
"""
Conflict Resolver - Resolve merge conflicts intelligently
Handles conflicts when merging new data with existing database
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum


class ConflictStrategy(Enum):
    """Strategies for resolving conflicts"""
    KEEP_EXISTING = "keep_existing"
    REPLACE_ALL = "replace_all"
    MERGE_FIELDS = "merge_fields"
    PREFER_COMPLETE = "prefer_complete"
    MANUAL_REVIEW = "manual_review"


class ConflictResolver:
    """
    Resolves conflicts between new and existing database entries
    Uses intelligent strategies based on data quality and completeness
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.conflicts = []
        self.resolutions = []
        
        # Field priority for conflicts (higher = more important)
        self.field_priority = {
            # Critical fields
            'name': 10,
            'startedBy': 9,
            'finishedBy': 9,
            'objectives': 8,
            'spawns': 8,
            
            # Important fields
            'questLevel': 7,
            'requiredLevel': 7,
            'minLevel': 7,
            'maxLevel': 7,
            'objectivesText': 6,
            'zoneOrSort': 6,
            'zoneID': 6,
            
            # Moderate importance
            'requiredRaces': 5,
            'requiredClasses': 5,
            'friendlyToFaction': 5,
            'questFlags': 4,
            'npcFlags': 4,
            
            # Lower importance
            'sourceItemId': 3,
            'requiredSkill': 3,
            'requiredMinRep': 3,
            'subName': 2,
            'specialFlags': 1,
        }
    
    def resolve(self, new_data: Dict, existing_data: Dict, 
               strategy: ConflictStrategy = None) -> Tuple[Dict, Dict]:
        """
        Resolve conflicts between new and existing data
        
        Args:
            new_data: New data to merge
            existing_data: Existing database entry
            strategy: Override strategy (None for auto-detect)
            
        Returns:
            (resolved_data, conflict_report)
        """
        entity_id = new_data.get('quest_id') or new_data.get('npc_id')
        self.logger.info(f"Resolving conflicts for entity {entity_id}")
        
        # Detect conflicts
        conflicts = self._detect_conflicts(new_data, existing_data)
        
        if not conflicts:
            self.logger.info(f"No conflicts found for entity {entity_id}")
            return new_data, {'status': 'no_conflicts', 'conflicts': []}
        
        # Choose strategy if not provided
        if not strategy:
            strategy = self._choose_strategy(new_data, existing_data, conflicts)
        
        self.logger.info(f"Using strategy: {strategy.value}")
        
        # Apply strategy
        resolved_data = self._apply_strategy(
            new_data, existing_data, conflicts, strategy
        )
        
        # Generate conflict report
        report = self._generate_report(
            conflicts, strategy, new_data, existing_data, resolved_data
        )
        
        self.resolutions.append({
            'entity_id': entity_id,
            'strategy': strategy.value,
            'conflicts': len(conflicts),
        })
        
        return resolved_data, report
    
    def _detect_conflicts(self, new_data: Dict, existing_data: Dict) -> List[Dict]:
        """Detect all conflicts between new and existing data"""
        conflicts = []
        
        # Check each field
        all_fields = set(new_data.keys()) | set(existing_data.keys())
        
        for field in all_fields:
            new_value = new_data.get(field)
            existing_value = existing_data.get(field)
            
            # Skip if both are None or if field is an ID
            if new_value is None and existing_value is None:
                continue
            if field in ['quest_id', 'npc_id']:
                continue
            
            # Detect conflict
            if self._is_conflict(new_value, existing_value):
                conflict = {
                    'field': field,
                    'new_value': new_value,
                    'existing_value': existing_value,
                    'priority': self.field_priority.get(field, 0),
                    'conflict_type': self._classify_conflict(new_value, existing_value),
                }
                conflicts.append(conflict)
                
                self.logger.debug(
                    f"Conflict in {field}: new={new_value}, existing={existing_value}"
                )
        
        return conflicts
    
    def _is_conflict(self, new_value: Any, existing_value: Any) -> bool:
        """Determine if two values are in conflict"""
        # No conflict if one is None
        if new_value is None or existing_value is None:
            return False
        
        # For collections, check if they're meaningfully different
        if isinstance(new_value, (list, tuple)) and isinstance(existing_value, (list, tuple)):
            # Convert to sets for comparison
            new_set = set(new_value) if new_value else set()
            existing_set = set(existing_value) if existing_value else set()
            return new_set != existing_set
        
        if isinstance(new_value, dict) and isinstance(existing_value, dict):
            # For dicts, check if keys or values differ
            return new_value != existing_value
        
        # Direct comparison for other types
        return new_value != existing_value
    
    def _classify_conflict(self, new_value: Any, existing_value: Any) -> str:
        """Classify the type of conflict"""
        if new_value is None:
            return 'new_missing'
        if existing_value is None:
            return 'existing_missing'
        
        if isinstance(new_value, str) and isinstance(existing_value, str):
            if len(new_value) > len(existing_value):
                return 'new_longer'
            elif len(new_value) < len(existing_value):
                return 'existing_longer'
            else:
                return 'different_text'
        
        if isinstance(new_value, (list, dict)) and isinstance(existing_value, (list, dict)):
            new_len = len(new_value)
            existing_len = len(existing_value)
            if new_len > existing_len:
                return 'new_has_more'
            elif new_len < existing_len:
                return 'existing_has_more'
            else:
                return 'different_content'
        
        return 'value_mismatch'
    
    def _choose_strategy(self, new_data: Dict, existing_data: Dict, 
                        conflicts: List[Dict]) -> ConflictStrategy:
        """Choose resolution strategy based on data analysis"""
        # Count conflict priorities
        high_priority_conflicts = sum(1 for c in conflicts if c['priority'] >= 7)
        total_conflicts = len(conflicts)
        
        # Analyze data completeness
        new_completeness = self._calculate_completeness(new_data)
        existing_completeness = self._calculate_completeness(existing_data)
        
        self.logger.debug(
            f"Completeness: new={new_completeness:.1f}%, existing={existing_completeness:.1f}%"
        )
        
        # Strategy selection logic
        if high_priority_conflicts >= 3:
            # Many critical conflicts - needs review
            return ConflictStrategy.MANUAL_REVIEW
        
        if new_completeness > existing_completeness + 20:
            # New data is significantly more complete
            return ConflictStrategy.REPLACE_ALL
        
        if existing_completeness > new_completeness + 20:
            # Existing data is significantly more complete
            return ConflictStrategy.KEEP_EXISTING
        
        if total_conflicts <= 3:
            # Few conflicts - merge fields
            return ConflictStrategy.MERGE_FIELDS
        
        # Default: prefer more complete data per field
        return ConflictStrategy.PREFER_COMPLETE
    
    def _calculate_completeness(self, data: Dict) -> float:
        """Calculate data completeness percentage"""
        total_fields = 0
        filled_fields = 0
        
        for field, value in data.items():
            if field in ['quest_id', 'npc_id']:
                continue
            
            total_fields += 1
            
            if value is not None:
                # Check if value is meaningful
                if isinstance(value, str) and value.strip():
                    filled_fields += 1
                elif isinstance(value, (list, dict, tuple)) and len(value) > 0:
                    filled_fields += 1
                elif isinstance(value, (int, float)):
                    filled_fields += 1
        
        return (filled_fields / total_fields * 100) if total_fields > 0 else 0
    
    def _apply_strategy(self, new_data: Dict, existing_data: Dict, 
                       conflicts: List[Dict], strategy: ConflictStrategy) -> Dict:
        """Apply resolution strategy to create resolved data"""
        if strategy == ConflictStrategy.KEEP_EXISTING:
            # Keep existing data, only add new fields that don't exist
            resolved = existing_data.copy()
            for field, value in new_data.items():
                if field not in existing_data or existing_data[field] is None:
                    resolved[field] = value
        
        elif strategy == ConflictStrategy.REPLACE_ALL:
            # Use new data, but keep existing fields that are missing in new
            resolved = new_data.copy()
            for field, value in existing_data.items():
                if field not in new_data or new_data[field] is None:
                    resolved[field] = value
        
        elif strategy == ConflictStrategy.MERGE_FIELDS:
            # Merge on per-field basis
            resolved = existing_data.copy()
            for conflict in conflicts:
                field = conflict['field']
                resolved[field] = self._merge_field(
                    conflict['new_value'], 
                    conflict['existing_value'],
                    conflict['conflict_type']
                )
        
        elif strategy == ConflictStrategy.PREFER_COMPLETE:
            # Choose more complete value for each field
            resolved = existing_data.copy()
            for conflict in conflicts:
                field = conflict['field']
                new_val = conflict['new_value']
                existing_val = conflict['existing_value']
                
                # Choose the more complete value
                if self._is_more_complete(new_val, existing_val):
                    resolved[field] = new_val
                else:
                    resolved[field] = existing_val
        
        else:  # MANUAL_REVIEW
            # Mark for manual review, keep existing for now
            resolved = existing_data.copy()
            resolved['_needs_review'] = True
            resolved['_conflicts'] = conflicts
        
        return resolved
    
    def _merge_field(self, new_value: Any, existing_value: Any, conflict_type: str) -> Any:
        """Merge a single field value"""
        # Handle None values
        if new_value is None:
            return existing_value
        if existing_value is None:
            return new_value
        
        # Merge lists/tuples
        if isinstance(new_value, (list, tuple)) and isinstance(existing_value, (list, tuple)):
            # Combine and deduplicate
            combined = list(set(list(new_value) + list(existing_value)))
            return combined if isinstance(new_value, list) else tuple(combined)
        
        # Merge dicts
        if isinstance(new_value, dict) and isinstance(existing_value, dict):
            merged = existing_value.copy()
            for key, val in new_value.items():
                if key not in merged or merged[key] is None:
                    merged[key] = val
                elif isinstance(val, (list, tuple)) and isinstance(merged[key], (list, tuple)):
                    # Merge lists within dict
                    merged[key] = list(set(list(val) + list(merged[key])))
            return merged
        
        # For strings, prefer longer or non-placeholder
        if isinstance(new_value, str) and isinstance(existing_value, str):
            # Check for placeholders
            placeholders = ['unknown', 'todo', 'placeholder', '???']
            new_is_placeholder = any(p in new_value.lower() for p in placeholders)
            existing_is_placeholder = any(p in existing_value.lower() for p in placeholders)
            
            if existing_is_placeholder and not new_is_placeholder:
                return new_value
            if new_is_placeholder and not existing_is_placeholder:
                return existing_value
            
            # Prefer longer non-placeholder text
            return new_value if len(new_value) > len(existing_value) else existing_value
        
        # For numbers, prefer non-zero/non-negative
        if isinstance(new_value, (int, float)) and isinstance(existing_value, (int, float)):
            if existing_value <= 0 and new_value > 0:
                return new_value
            if new_value <= 0 and existing_value > 0:
                return existing_value
            # Average if both valid
            if new_value > 0 and existing_value > 0:
                return (new_value + existing_value) / 2
        
        # Default: keep existing
        return existing_value
    
    def _is_more_complete(self, new_value: Any, existing_value: Any) -> bool:
        """Determine if new value is more complete than existing"""
        if new_value is None:
            return False
        if existing_value is None:
            return True
        
        # Compare collections by size
        if isinstance(new_value, (list, dict, tuple)):
            if isinstance(existing_value, (list, dict, tuple)):
                return len(new_value) > len(existing_value)
            return True
        
        # Compare strings by length and quality
        if isinstance(new_value, str) and isinstance(existing_value, str):
            # Check for placeholders
            new_placeholder = any(p in new_value.lower() 
                                for p in ['unknown', 'todo', '???'])
            existing_placeholder = any(p in existing_value.lower() 
                                     for p in ['unknown', 'todo', '???'])
            
            if existing_placeholder and not new_placeholder:
                return True
            if new_placeholder and not existing_placeholder:
                return False
            
            return len(new_value) > len(existing_value)
        
        # Numbers: non-zero is more complete
        if isinstance(new_value, (int, float)) and isinstance(existing_value, (int, float)):
            if existing_value == 0 and new_value != 0:
                return True
        
        return False
    
    def _generate_report(self, conflicts: List[Dict], strategy: ConflictStrategy,
                        new_data: Dict, existing_data: Dict, 
                        resolved_data: Dict) -> Dict:
        """Generate detailed conflict resolution report"""
        report = {
            'status': 'resolved',
            'strategy': strategy.value,
            'total_conflicts': len(conflicts),
            'conflicts': conflicts,
            'high_priority_conflicts': [c for c in conflicts if c['priority'] >= 7],
            'completeness': {
                'new': self._calculate_completeness(new_data),
                'existing': self._calculate_completeness(existing_data),
                'resolved': self._calculate_completeness(resolved_data),
            },
            'changes_made': [],
        }
        
        # Identify changes made
        for field in resolved_data:
            if field in ['quest_id', 'npc_id', '_needs_review', '_conflicts']:
                continue
            
            resolved_val = resolved_data.get(field)
            existing_val = existing_data.get(field)
            new_val = new_data.get(field)
            
            if resolved_val != existing_val:
                change = {
                    'field': field,
                    'from': existing_val,
                    'to': resolved_val,
                    'source': 'new' if resolved_val == new_val else 'merged',
                }
                report['changes_made'].append(change)
        
        return report
    
    def batch_resolve(self, conflicts_list: List[Tuple[Dict, Dict]]) -> List[Tuple[Dict, Dict]]:
        """Resolve multiple conflicts in batch"""
        results = []
        
        for new_data, existing_data in conflicts_list:
            resolved, report = self.resolve(new_data, existing_data)
            results.append((resolved, report))
        
        return results


def main():
    """Test the conflict resolver"""
    resolver = ConflictResolver()
    
    # Test data with conflicts
    new_quest = {
        'quest_id': 12345,
        'name': 'Updated Quest Name',
        'questLevel': 15,  # Different from existing
        'objectives': ['Kill 10 wolves', 'Collect 5 pelts'],  # More objectives
        'requiredLevel': 10,
        'zoneOrSort': 12,
    }
    
    existing_quest = {
        'quest_id': 12345,
        'name': 'Old Quest Name',
        'questLevel': 10,  # Conflict
        'objectives': ['Kill 10 wolves'],  # Fewer objectives
        'requiredLevel': 10,  # Same
        'questFlags': 128,  # Only in existing
    }
    
    # Resolve conflicts
    resolved, report = resolver.resolve(new_quest, existing_quest)
    
    print(f"Strategy: {report['strategy']}")
    print(f"Conflicts: {report['total_conflicts']}")
    print(f"Changes made: {len(report['changes_made'])}")
    print("\nResolved data:")
    for field, value in resolved.items():
        if field not in ['quest_id']:
            print(f"  {field}: {value}")


if __name__ == "__main__":
    main()