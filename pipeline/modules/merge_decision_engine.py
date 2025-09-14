#!/usr/bin/env python3
"""
Merge Decision Engine for Questie Pipeline

Makes intelligent decisions about merging new quest/NPC data with existing database entries.
Uses confidence scores, data quality analysis, and conflict resolution strategies to determine
the best way to integrate new data while preserving existing good data.

Key Functions:
- Conflict resolution between competing data sources
- Data quality scoring and improvement detection
- Merge strategy selection (replace, merge, manual review)
- Risk assessment for database changes
- Rollback point creation for safe merging
"""

import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

class MergeStrategy(Enum):
    """Different strategies for merging data"""
    REPLACE_ALL = "replace_all"           # Replace entire entry with new data
    MERGE_FIELDS = "merge_fields"         # Merge field by field, keeping best
    PRESERVE_EXISTING = "preserve_existing" # Keep existing, ignore new
    MANUAL_REVIEW = "manual_review"       # Requires human decision
    APPEND_DATA = "append_data"          # Add new data without replacing existing

class ConflictType(Enum):
    """Types of data conflicts"""
    NAME_MISMATCH = "name_mismatch"
    COORDINATE_DIFFERENCE = "coordinate_difference"
    LEVEL_DISCREPANCY = "level_discrepancy"
    QUEST_CHAIN_CONFLICT = "quest_chain_conflict"
    NPC_ASSOCIATION_CONFLICT = "npc_association_conflict"
    FLAG_MISMATCH = "flag_mismatch"
    ZONE_CONFLICT = "zone_conflict"

@dataclass
class MergeDecision:
    """Represents a decision about how to merge data"""
    entry_id: int
    entry_type: str  # 'quest' or 'npc'
    strategy: MergeStrategy
    confidence: float
    risk_level: str  # 'low', 'medium', 'high'
    reasoning: str
    conflicts: List[ConflictType] = field(default_factory=list)
    field_decisions: Dict[str, Dict] = field(default_factory=dict)
    requires_backup: bool = True
    estimated_improvement: float = 0.0
    
@dataclass
class MergeContext:
    """Context information for making merge decisions"""
    existing_data: Dict
    new_data: Dict
    submission_history: List[Dict] = field(default_factory=list)
    user_preferences: Dict = field(default_factory=dict)
    database_stats: Dict = field(default_factory=dict)

class MergeDecisionEngine:
    """Makes intelligent decisions about data merging"""
    
    def __init__(self, config: Dict = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or self._get_default_config()
        
        # Decision thresholds
        self.high_confidence_threshold = 0.8
        self.medium_confidence_threshold = 0.5
        self.major_change_threshold = 0.7
        self.conflict_tolerance = 0.3
        
        # Field criticality weights
        self.critical_fields = {
            'quest': {'name', 'questLevel', 'startedBy', 'finishedBy'},
            'npc': {'name', 'spawns', 'questStarts', 'questEnds'}
        }
        
        self.merge_history = []  # Track previous decisions for learning
    
    def decide_merge_strategy(self, entry_id: int, entry_type: str, 
                            existing_data: Dict, new_data: Dict,
                            context: MergeContext = None) -> MergeDecision:
        """
        Decide the best strategy for merging new data with existing entry
        
        Args:
            entry_id: Quest or NPC ID
            entry_type: 'quest' or 'npc'
            existing_data: Current database entry
            new_data: New parsed data
            context: Additional context for decision making
            
        Returns:
            MergeDecision with recommended strategy and reasoning
        """
        if context is None:
            context = MergeContext(existing_data, new_data)
        
        try:
            # Analyze the data quality and conflicts
            conflicts = self._detect_conflicts(existing_data, new_data, entry_type)
            quality_analysis = self._analyze_data_quality(existing_data, new_data, entry_type)
            risk_assessment = self._assess_risk(conflicts, quality_analysis, entry_type)
            
            # Determine merge strategy based on analysis
            strategy = self._select_merge_strategy(conflicts, quality_analysis, risk_assessment)
            
            # Generate field-level decisions
            field_decisions = self._generate_field_decisions(
                existing_data, new_data, entry_type, strategy
            )
            
            # Calculate confidence in this decision
            decision_confidence = self._calculate_decision_confidence(
                conflicts, quality_analysis, strategy
            )
            
            # Create reasoning explanation
            reasoning = self._generate_reasoning(
                strategy, conflicts, quality_analysis, risk_assessment
            )
            
            decision = MergeDecision(
                entry_id=entry_id,
                entry_type=entry_type,
                strategy=strategy,
                confidence=decision_confidence,
                risk_level=risk_assessment['level'],
                reasoning=reasoning,
                conflicts=conflicts,
                field_decisions=field_decisions,
                requires_backup=risk_assessment['level'] in ['medium', 'high'],
                estimated_improvement=quality_analysis.get('improvement_score', 0.0)
            )
            
            # Record this decision for learning
            self._record_decision(decision, context)
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error making merge decision for {entry_type} {entry_id}: {e}")
            
            # Fallback to safe manual review
            return MergeDecision(
                entry_id=entry_id,
                entry_type=entry_type,
                strategy=MergeStrategy.MANUAL_REVIEW,
                confidence=0.0,
                risk_level='high',
                reasoning=f"Error during analysis: {e}",
                requires_backup=True
            )
    
    def batch_decide(self, comparison_results: List[Dict]) -> List[MergeDecision]:
        """Make merge decisions for a batch of comparison results"""
        decisions = []
        
        for result in comparison_results:
            try:
                decision = self.decide_merge_strategy(
                    entry_id=result['entry_id'],
                    entry_type=result['entry_type'],
                    existing_data=result.get('existing_data', {}),
                    new_data=result.get('new_data', {})
                )
                decisions.append(decision)
                
            except Exception as e:
                self.logger.error(f"Error in batch decision for {result.get('entry_id')}: {e}")
                continue
        
        return decisions
    
    def _detect_conflicts(self, existing: Dict, new: Dict, entry_type: str) -> List[ConflictType]:
        """Detect conflicts between existing and new data"""
        conflicts = []
        
        try:
            # Name conflicts
            if (existing.get('name') and new.get('name') and 
                existing['name'].lower() != new['name'].lower()):
                # Allow for common variations
                if not self._are_name_variants(existing['name'], new['name']):
                    conflicts.append(ConflictType.NAME_MISMATCH)
            
            # Coordinate conflicts
            if entry_type == 'npc':
                existing_coords = existing.get('coordinates', [])
                new_coords = new.get('coordinates', [])
                if existing_coords and new_coords:
                    if not self._coordinates_compatible(existing_coords, new_coords):
                        conflicts.append(ConflictType.COORDINATE_DIFFERENCE)
            
            # Level conflicts
            if entry_type == 'quest':
                existing_level = existing.get('questLevel')
                new_level = new.get('questLevel')
                if (existing_level and new_level and 
                    abs(existing_level - new_level) > 5):  # Allow 5 level tolerance
                    conflicts.append(ConflictType.LEVEL_DISCREPANCY)
            
            elif entry_type == 'npc':
                existing_min = existing.get('minLevel', 1)
                existing_max = existing.get('maxLevel', 1)
                new_min = new.get('minLevel', 1)
                new_max = new.get('maxLevel', 1)
                
                # Check for reasonable overlap
                if (new_max < existing_min - 5 or new_min > existing_max + 5):
                    conflicts.append(ConflictType.LEVEL_DISCREPANCY)
            
            # Quest association conflicts for NPCs
            if entry_type == 'npc':
                existing_starts = set(existing.get('questStarts', []))
                new_starts = set(new.get('questStarts', []))
                existing_ends = set(existing.get('questEnds', []))
                new_ends = set(new.get('questEnds', []))
                
                # Check for conflicting quest associations
                if existing_starts and new_starts and not existing_starts.intersection(new_starts):
                    conflicts.append(ConflictType.NPC_ASSOCIATION_CONFLICT)
            
            # Zone conflicts
            existing_zone = existing.get('zoneID') or existing.get('zoneOrSort')
            new_zone = new.get('zoneID') or new.get('zoneOrSort')
            
            if (existing_zone and new_zone and existing_zone != new_zone and
                not self._are_compatible_zones(existing_zone, new_zone)):
                conflicts.append(ConflictType.ZONE_CONFLICT)
            
        except Exception as e:
            self.logger.error(f"Error detecting conflicts: {e}")
        
        return conflicts
    
    def _analyze_data_quality(self, existing: Dict, new: Dict, entry_type: str) -> Dict:
        """Analyze the quality of existing vs new data"""
        analysis = {
            'existing_score': 0.0,
            'new_score': 0.0,
            'improvement_score': 0.0,
            'completeness_comparison': {},
            'accuracy_indicators': {}
        }
        
        try:
            # Get field weights for this entry type
            if entry_type == 'quest':
                field_weights = {
                    'name': 1.0,
                    'questLevel': 0.8,
                    'requiredLevel': 0.7,
                    'startedBy': 0.9,
                    'finishedBy': 0.9,
                    'objectives': 0.8,
                    'zoneOrSort': 0.6,
                    'preQuestGroup': 0.5,
                    'preQuestSingle': 0.5
                }
            else:  # npc
                field_weights = {
                    'name': 1.0,
                    'spawns': 0.9,
                    'questStarts': 0.8,
                    'questEnds': 0.8,
                    'zoneID': 0.7,
                    'minLevel': 0.6,
                    'maxLevel': 0.6,
                    'rank': 0.5
                }
            
            total_weight = sum(field_weights.values())
            
            # Score existing data
            for field, weight in field_weights.items():
                existing_value = existing.get(field)
                new_value = new.get(field)
                
                # Score completeness
                if existing_value:
                    if self._is_placeholder_value(existing_value):
                        analysis['existing_score'] += weight * 0.3
                    else:
                        analysis['existing_score'] += weight
                
                if new_value:
                    if self._is_placeholder_value(new_value):
                        analysis['new_score'] += weight * 0.3
                    else:
                        analysis['new_score'] += weight
                
                # Track completeness comparison
                analysis['completeness_comparison'][field] = {
                    'existing_has_data': bool(existing_value),
                    'new_has_data': bool(new_value),
                    'existing_is_placeholder': self._is_placeholder_value(existing_value),
                    'new_is_placeholder': self._is_placeholder_value(new_value)
                }
            
            # Normalize scores
            analysis['existing_score'] /= total_weight
            analysis['new_score'] /= total_weight
            analysis['improvement_score'] = analysis['new_score'] - analysis['existing_score']
            
            # Add accuracy indicators
            analysis['accuracy_indicators'] = {
                'new_confidence': new.get('parsing_confidence', 0.0),
                'has_coordinates': bool(new.get('coordinates')),
                'has_quest_associations': bool(new.get('questStarts') or new.get('questEnds')),
                'data_source_quality': self._assess_source_quality(new)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing data quality: {e}")
        
        return analysis
    
    def _assess_risk(self, conflicts: List[ConflictType], quality_analysis: Dict, 
                    entry_type: str) -> Dict:
        """Assess risk level of making this merge"""
        risk_factors = []
        risk_score = 0.0
        
        # Conflict-based risk
        high_risk_conflicts = {
            ConflictType.NAME_MISMATCH,
            ConflictType.QUEST_CHAIN_CONFLICT,
            ConflictType.NPC_ASSOCIATION_CONFLICT
        }
        
        for conflict in conflicts:
            if conflict in high_risk_conflicts:
                risk_score += 0.3
                risk_factors.append(f"High-risk conflict: {conflict.value}")
            else:
                risk_score += 0.1
                risk_factors.append(f"Minor conflict: {conflict.value}")
        
        # Data quality based risk
        improvement = quality_analysis.get('improvement_score', 0.0)
        if improvement < -0.2:  # New data significantly worse
            risk_score += 0.4
            risk_factors.append("New data appears lower quality")
        
        # Confidence based risk
        new_confidence = quality_analysis.get('accuracy_indicators', {}).get('new_confidence', 0.0)
        if new_confidence < 0.3:
            risk_score += 0.3
            risk_factors.append("Low confidence in new data")
        
        # Critical field changes
        critical_changes = 0
        for field in self.critical_fields.get(entry_type, set()):
            if quality_analysis.get('completeness_comparison', {}).get(field, {}).get('existing_has_data'):
                if field in conflicts:
                    critical_changes += 1
        
        if critical_changes > 0:
            risk_score += critical_changes * 0.2
            risk_factors.append(f"Changes to {critical_changes} critical fields")
        
        # Determine risk level
        if risk_score >= 0.7:
            level = 'high'
        elif risk_score >= 0.4:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'level': level,
            'score': min(risk_score, 1.0),
            'factors': risk_factors
        }
    
    def _select_merge_strategy(self, conflicts: List[ConflictType], 
                              quality_analysis: Dict, risk_assessment: Dict) -> MergeStrategy:
        """Select the appropriate merge strategy based on analysis"""
        improvement = quality_analysis.get('improvement_score', 0.0)
        risk_level = risk_assessment['level']
        conflict_count = len(conflicts)
        new_confidence = quality_analysis.get('accuracy_indicators', {}).get('new_confidence', 0.0)
        
        # High-risk situations require manual review
        if risk_level == 'high' or conflict_count >= 3:
            return MergeStrategy.MANUAL_REVIEW
        
        # Low confidence new data with conflicts
        if new_confidence < 0.4 and conflict_count > 0:
            return MergeStrategy.MANUAL_REVIEW
        
        # Significant improvement with acceptable risk
        if improvement >= 0.5 and risk_level == 'low':
            return MergeStrategy.REPLACE_ALL
        
        # Moderate improvement, merge field by field
        if improvement >= 0.2 and risk_level in ['low', 'medium']:
            return MergeStrategy.MERGE_FIELDS
        
        # New data adds information without major conflicts
        if improvement > 0 and conflict_count == 0:
            return MergeStrategy.MERGE_FIELDS
        
        # New data is worse or equivalent, keep existing
        if improvement <= 0 and conflict_count == 0:
            return MergeStrategy.PRESERVE_EXISTING
        
        # Default to manual review for ambiguous cases
        return MergeStrategy.MANUAL_REVIEW
    
    def _generate_field_decisions(self, existing: Dict, new: Dict, entry_type: str, 
                                 strategy: MergeStrategy) -> Dict[str, Dict]:
        """Generate field-by-field merge decisions"""
        field_decisions = {}
        
        if strategy == MergeStrategy.REPLACE_ALL:
            # Replace all fields with new data
            for field in new:
                field_decisions[field] = {
                    'action': 'replace',
                    'old_value': existing.get(field),
                    'new_value': new[field],
                    'reasoning': 'Full replacement strategy'
                }
        
        elif strategy == MergeStrategy.MERGE_FIELDS:
            # Decide field by field
            all_fields = set(existing.keys()) | set(new.keys())
            
            for field in all_fields:
                existing_value = existing.get(field)
                new_value = new.get(field)
                
                if not existing_value and new_value:
                    # Add new field
                    action = 'add'
                    reasoning = 'Adding missing field'
                elif existing_value and not new_value:
                    # Keep existing
                    action = 'keep'
                    reasoning = 'Preserving existing data'
                elif existing_value and new_value:
                    # Choose better value
                    if self._is_better_field_value(new_value, existing_value, field, entry_type):
                        action = 'replace'
                        reasoning = 'New value is better quality'
                    else:
                        action = 'keep'
                        reasoning = 'Existing value is better or equivalent'
                else:
                    action = 'keep'
                    reasoning = 'No change needed'
                
                field_decisions[field] = {
                    'action': action,
                    'old_value': existing_value,
                    'new_value': new_value,
                    'reasoning': reasoning
                }
        
        elif strategy == MergeStrategy.PRESERVE_EXISTING:
            # Keep all existing values, only add truly new fields
            for field in new:
                if field not in existing:
                    field_decisions[field] = {
                        'action': 'add',
                        'old_value': None,
                        'new_value': new[field],
                        'reasoning': 'Adding new field to existing entry'
                    }
        
        return field_decisions
    
    def _is_better_field_value(self, new_value: Any, existing_value: Any, 
                              field: str, entry_type: str) -> bool:
        """Determine if new field value is better than existing"""
        # Handle different field types
        if field == 'name':
            # Prefer non-placeholder names
            if '[Epoch]' in str(existing_value) and '[Epoch]' not in str(new_value):
                return True
            return len(str(new_value)) > len(str(existing_value))
        
        elif field in ['coordinates', 'spawns']:
            # More coordinate data is usually better
            if isinstance(new_value, list) and isinstance(existing_value, list):
                return len(new_value) > len(existing_value)
        
        elif field in ['objectives', 'questStarts', 'questEnds']:
            # More complete quest data is better
            if isinstance(new_value, list) and isinstance(existing_value, list):
                return len(new_value) > len(existing_value)
        
        elif field in ['questLevel', 'minLevel', 'maxLevel']:
            # Prefer realistic levels over defaults
            if isinstance(new_value, int) and isinstance(existing_value, int):
                if existing_value == 1 and new_value > 1:
                    return True
                if 1 <= new_value <= 80 and not (1 <= existing_value <= 80):
                    return True
        
        # Default: new is better if existing is placeholder/empty
        return bool(new_value) and self._is_placeholder_value(existing_value)
    
    def _is_placeholder_value(self, value: Any) -> bool:
        """Check if a value is a placeholder"""
        if not value:
            return True
        
        if isinstance(value, str):
            placeholders = ['[Epoch]', 'Unknown', 'Placeholder', 'TBD', '???']
            return any(placeholder in value for placeholder in placeholders)
        
        if isinstance(value, (int, float)):
            return value in [0, 1]  # Common default values
        
        return False
    
    def _are_name_variants(self, name1: str, name2: str) -> bool:
        """Check if two names are likely variants of the same entity"""
        # Simple variant detection
        name1_clean = name1.lower().strip()
        name2_clean = name2.lower().strip()
        
        # Common variations
        variants = [
            (name1_clean.replace(' ', ''), name2_clean.replace(' ', '')),  # Space differences
            (name1_clean.replace('-', ' '), name2_clean.replace('-', ' ')),  # Hyphen differences
        ]
        
        for v1, v2 in variants:
            if v1 == v2:
                return True
        
        return False
    
    def _coordinates_compatible(self, coords1: List, coords2: List) -> bool:
        """Check if coordinate sets are compatible (nearby locations)"""
        if not coords1 or not coords2:
            return True
        
        # Check if any coordinates in the sets are within reasonable distance
        for c1 in coords1:
            for c2 in coords2:
                if isinstance(c1, (list, tuple)) and isinstance(c2, (list, tuple)):
                    if len(c1) >= 2 and len(c2) >= 2:
                        distance = ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5
                        if distance <= 10.0:  # Within 10 units
                            return True
        
        return False
    
    def _are_compatible_zones(self, zone1: int, zone2: int) -> bool:
        """Check if two zones are compatible (same general area)"""
        # This would need actual zone relationship data
        # For now, just check if they're the same
        return zone1 == zone2
    
    def _assess_source_quality(self, data: Dict) -> float:
        """Assess quality of data source"""
        quality = 0.5  # Base quality
        
        # Check for indicators of quality
        if data.get('coordinates'):
            quality += 0.2
        
        if data.get('parsing_confidence', 0) > 0.7:
            quality += 0.2
        
        if data.get('questStarts') or data.get('questEnds'):
            quality += 0.1
        
        return min(quality, 1.0)
    
    def _calculate_decision_confidence(self, conflicts: List[ConflictType], 
                                     quality_analysis: Dict, strategy: MergeStrategy) -> float:
        """Calculate confidence in the merge decision"""
        base_confidence = 0.5
        
        # Reduce confidence for conflicts
        base_confidence -= len(conflicts) * 0.1
        
        # Adjust for quality improvement
        improvement = quality_analysis.get('improvement_score', 0.0)
        base_confidence += improvement * 0.3
        
        # Adjust for strategy certainty
        strategy_confidence = {
            MergeStrategy.PRESERVE_EXISTING: 0.9,
            MergeStrategy.REPLACE_ALL: 0.8,
            MergeStrategy.MERGE_FIELDS: 0.7,
            MergeStrategy.APPEND_DATA: 0.6,
            MergeStrategy.MANUAL_REVIEW: 0.3
        }
        
        base_confidence = (base_confidence + strategy_confidence[strategy]) / 2
        
        return max(0.0, min(1.0, base_confidence))
    
    def _generate_reasoning(self, strategy: MergeStrategy, conflicts: List[ConflictType],
                          quality_analysis: Dict, risk_assessment: Dict) -> str:
        """Generate human-readable reasoning for the decision"""
        reasons = []
        
        improvement = quality_analysis.get('improvement_score', 0.0)
        conflict_count = len(conflicts)
        risk_level = risk_assessment['level']
        
        if strategy == MergeStrategy.REPLACE_ALL:
            reasons.append(f"Replacing all data due to {improvement:.1%} quality improvement")
            if risk_level == 'low':
                reasons.append("Low risk of data corruption")
        
        elif strategy == MergeStrategy.MERGE_FIELDS:
            reasons.append("Merging field-by-field to preserve good existing data")
            if improvement > 0:
                reasons.append(f"New data offers {improvement:.1%} improvement")
        
        elif strategy == MergeStrategy.PRESERVE_EXISTING:
            reasons.append("Keeping existing data as new data doesn't offer improvements")
            if conflict_count > 0:
                reasons.append(f"Avoiding {conflict_count} potential conflicts")
        
        elif strategy == MergeStrategy.MANUAL_REVIEW:
            if risk_level == 'high':
                reasons.append("High risk changes require manual review")
            if conflict_count >= 3:
                reasons.append(f"Too many conflicts ({conflict_count}) for automatic resolution")
        
        # Add conflict information
        if conflicts:
            conflict_names = [c.value.replace('_', ' ') for c in conflicts[:2]]
            reasons.append(f"Conflicts detected: {', '.join(conflict_names)}")
        
        return ". ".join(reasons)
    
    def _record_decision(self, decision: MergeDecision, context: MergeContext):
        """Record decision for learning and analysis"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'entry_id': decision.entry_id,
            'entry_type': decision.entry_type,
            'strategy': decision.strategy.value,
            'confidence': decision.confidence,
            'risk_level': decision.risk_level,
            'conflict_count': len(decision.conflicts),
            'improvement_score': decision.estimated_improvement
        }
        
        self.merge_history.append(record)
        
        # Keep only recent history (last 1000 decisions)
        if len(self.merge_history) > 1000:
            self.merge_history = self.merge_history[-1000:]
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'conservative_mode': False,
            'auto_backup': True,
            'max_batch_size': 100,
            'require_human_review_threshold': 0.3
        }
    
    def get_decision_statistics(self) -> Dict:
        """Get statistics about recent merge decisions"""
        if not self.merge_history:
            return {}
        
        recent_decisions = self.merge_history[-100:]  # Last 100 decisions
        
        strategies = {}
        risk_levels = {}
        avg_confidence = 0.0
        
        for record in recent_decisions:
            strategy = record['strategy']
            risk = record['risk_level']
            
            strategies[strategy] = strategies.get(strategy, 0) + 1
            risk_levels[risk] = risk_levels.get(risk, 0) + 1
            avg_confidence += record['confidence']
        
        return {
            'total_decisions': len(recent_decisions),
            'strategy_distribution': strategies,
            'risk_distribution': risk_levels,
            'average_confidence': avg_confidence / len(recent_decisions) if recent_decisions else 0.0,
            'manual_review_rate': strategies.get('manual_review', 0) / len(recent_decisions)
        }


def main():
    """Test the merge decision engine with sample data"""
    engine = MergeDecisionEngine()
    
    # Test with sample conflicting data
    existing_quest = {
        'name': '[Epoch] Test Quest',
        'questLevel': 15,
        'requiredLevel': 10,
        'startedBy': [[12345]],
        'zoneOrSort': 14
    }
    
    new_quest = {
        'name': 'The Lost Artifact',
        'questLevel': 16,
        'requiredLevel': 12,
        'startedBy': [[12345]],
        'finishedBy': [[67890]],
        'objectives': [{'creatures': [[46835, 10, 'Amethyst Crab']]}],
        'parsing_confidence': 0.8
    }
    
    decision = engine.decide_merge_strategy(
        entry_id=28723,
        entry_type='quest',
        existing_data=existing_quest,
        new_data=new_quest
    )
    
    print(f"Merge Decision for Quest 28723:")
    print(f"Strategy: {decision.strategy.value}")
    print(f"Confidence: {decision.confidence:.2f}")
    print(f"Risk Level: {decision.risk_level}")
    print(f"Reasoning: {decision.reasoning}")
    print(f"Conflicts: {[c.value for c in decision.conflicts]}")
    print(f"Field Decisions: {len(decision.field_decisions)} fields analyzed")


if __name__ == "__main__":
    main()