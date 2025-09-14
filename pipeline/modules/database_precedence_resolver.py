#!/usr/bin/env python3
"""
Database Precedence Resolver - Handles conflicts between Epoch, WotLK, and Classic databases
Determines when vanilla/WotLK entries should be commented out in favor of Epoch content
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

class DatabaseSource(Enum):
    """Database precedence order (highest to lowest)"""
    EPOCH = 3      # Highest - Project Epoch custom content
    WOTLK = 2      # Middle - WotLK 3.3.5 content
    CLASSIC = 1    # Lowest - Vanilla content

@dataclass
class QuestSignature:
    """Signature for identifying quest similarity"""
    quest_id: int
    name: str
    source: DatabaseSource
    objectives_text: List[str]
    quest_giver_npcs: List[int]
    turn_in_npcs: List[int]
    zone_id: int
    quest_level: int
    
    def calculate_similarity(self, other: 'QuestSignature') -> float:
        """Calculate similarity score between two quests (0-100)"""
        score = 0.0
        weights = {
            'id_match': 30,
            'name_match': 25,
            'objectives_match': 20,
            'npcs_match': 15,
            'zone_match': 5,
            'level_match': 5
        }
        
        # ID match (critical for collision detection)
        if self.quest_id == other.quest_id:
            score += weights['id_match']
        
        # Name similarity
        if self.name and other.name:
            # Exact match
            if self.name.lower() == other.name.lower():
                score += weights['name_match']
            # Partial match (one contains the other)
            elif self.name.lower() in other.name.lower() or other.name.lower() in self.name.lower():
                score += weights['name_match'] * 0.5
            # Significant overlap
            elif self._string_similarity(self.name, other.name) > 0.7:
                score += weights['name_match'] * 0.3
        
        # Objectives similarity
        if self.objectives_text and other.objectives_text:
            obj_similarity = self._list_similarity(self.objectives_text, other.objectives_text)
            score += weights['objectives_match'] * obj_similarity
        
        # NPC similarity
        giver_sim = self._list_overlap(self.quest_giver_npcs, other.quest_giver_npcs)
        turnin_sim = self._list_overlap(self.turn_in_npcs, other.turn_in_npcs)
        npc_similarity = (giver_sim + turnin_sim) / 2
        score += weights['npcs_match'] * npc_similarity
        
        # Zone match
        if self.zone_id and other.zone_id and self.zone_id == other.zone_id:
            score += weights['zone_match']
        
        # Level similarity
        if self.quest_level and other.quest_level:
            level_diff = abs(self.quest_level - other.quest_level)
            if level_diff == 0:
                score += weights['level_match']
            elif level_diff <= 5:
                score += weights['level_match'] * 0.5
        
        return score
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using simple character overlap"""
        if not s1 or not s2:
            return 0.0
        
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        
        # Remove common prefixes that don't indicate similarity
        for prefix in ['[epoch]', '[deprecated]', '[old]', 'deprecated']:
            s1_lower = s1_lower.replace(prefix, '').strip()
            s2_lower = s2_lower.replace(prefix, '').strip()
        
        # Character set overlap
        set1 = set(s1_lower.split())
        set2 = set(s2_lower.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _list_similarity(self, list1: List[str], list2: List[str]) -> float:
        """Calculate similarity between two lists of strings"""
        if not list1 or not list2:
            return 0.0
        
        matches = 0
        for item1 in list1:
            for item2 in list2:
                if self._string_similarity(item1, item2) > 0.7:
                    matches += 1
                    break
        
        return matches / max(len(list1), len(list2))
    
    def _list_overlap(self, list1: List[int], list2: List[int]) -> float:
        """Calculate overlap between two lists of IDs"""
        if not list1 or not list2:
            return 0.0
        
        set1 = set(list1)
        set2 = set(list2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0


class DatabasePrecedenceResolver:
    """
    Resolves database precedence conflicts for Project Epoch
    Determines when vanilla/WotLK entries should be disabled
    
    Handles special case: Epoch often keeps vanilla quest NAMES but assigns NEW IDs
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Thresholds for decision making
        self.COLLISION_THRESHOLD = 30.0  # ID match = definite collision
        self.REPLACEMENT_THRESHOLD = 70.0  # High similarity = same quest modified
        self.DIFFERENT_QUEST_THRESHOLD = 40.0  # Low similarity = different quest
        self.NAME_MATCH_THRESHOLD = 85.0  # Name match = likely replacement
        
        # Known Epoch quest ID ranges (custom content)
        self.EPOCH_ID_RANGES = [
            (25000, 30000),  # Primary Epoch custom range
            (80000, 90000),  # Secondary custom range
        ]
        
        # Track decisions for reporting
        self.decisions = []
        self.name_replacements = {}  # Track name-based replacements
        
    def analyze_quest_collision(self, epoch_quest: Dict, existing_quests: Dict[DatabaseSource, Dict]) -> Dict:
        """
        Analyze if an Epoch quest collides with vanilla/WotLK content
        
        Special handling for Epoch pattern: Same name, different ID
        
        Args:
            epoch_quest: The new Epoch quest data
            existing_quests: Dict of existing quests by source database
            
        Returns:
            Decision dictionary with action to take
        """
        quest_id = epoch_quest.get('quest_id') or epoch_quest.get('id')
        quest_name = epoch_quest.get('name', f'Quest {quest_id}')
        
        # Create signature for Epoch quest
        epoch_sig = self._create_signature(epoch_quest, DatabaseSource.EPOCH)
        
        decision = {
            'quest_id': quest_id,
            'quest_name': quest_name,
            'action': 'ADD',  # Default action
            'conflicts': [],
            'comment_out': [],  # Databases to comment out
            'reasoning': [],
            'similarity_scores': {},
            'name_matches': []  # Track name-based matches
        }
        
        # Check if this is in known Epoch ID range
        is_custom_id = any(start <= quest_id <= end for start, end in self.EPOCH_ID_RANGES)
        if is_custom_id:
            decision['reasoning'].append(f"Quest ID {quest_id} is in Epoch custom range")
        
        # Check each existing database
        for source, quest_data in existing_quests.items():
            if not quest_data:
                continue
            
            existing_sig = self._create_signature(quest_data, source)
            similarity = epoch_sig.calculate_similarity(existing_sig)
            
            decision['similarity_scores'][source.name] = similarity
            
            # CRITICAL: Check for name match with different ID (Epoch's pattern)
            if epoch_sig.quest_id != existing_sig.quest_id:
                name_similarity = self._calculate_name_similarity(epoch_sig.name, existing_sig.name)
                if name_similarity >= self.NAME_MATCH_THRESHOLD:
                    # This is likely an Epoch replacement quest!
                    decision['name_matches'].append({
                        'source': source.name,
                        'existing_id': existing_sig.quest_id,
                        'existing_name': existing_sig.name,
                        'name_similarity': name_similarity * 100
                    })
                    decision['conflicts'].append({
                        'source': source.name,
                        'type': 'NAME_REPLACEMENT',
                        'similarity': name_similarity * 100,
                        'existing_name': existing_sig.name,
                        'existing_id': existing_sig.quest_id,
                        'note': 'Epoch quest with same name but different ID - likely replaces vanilla'
                    })
                    decision['comment_out'].append(source.name)
                    decision['reasoning'].append(
                        f"Epoch quest '{epoch_sig.name}' (ID: {quest_id}) replaces "
                        f"{source.name} quest '{existing_sig.name}' (ID: {existing_sig.quest_id})"
                    )
                    # Track this replacement
                    self.name_replacements[existing_sig.quest_id] = quest_id
                    continue
            
            # Analyze the similarity score for other types of conflicts
            if similarity >= self.COLLISION_THRESHOLD:
                # Definite collision - same ID or very similar quest
                decision['conflicts'].append({
                    'source': source.name,
                    'type': 'ID_COLLISION' if quest_id == existing_sig.quest_id else 'HIGH_SIMILARITY',
                    'similarity': similarity,
                    'existing_name': existing_sig.name
                })
                
                # Determine action based on similarity and source
                action = self._determine_action(epoch_sig, existing_sig, similarity)
                
                if action == 'REPLACE':
                    decision['comment_out'].append(source.name)
                    decision['reasoning'].append(
                        f"Comment out {source.name} entry - Epoch version is different content"
                    )
                elif action == 'SKIP':
                    decision['action'] = 'SKIP'
                    decision['reasoning'].append(
                        f"Skip - Identical to {source.name} version"
                    )
                elif action == 'MERGE':
                    decision['action'] = 'MERGE'
                    decision['reasoning'].append(
                        f"Merge with {source.name} version - Similar quest with enhancements"
                    )
        
        # Final decision logic
        if decision['comment_out']:
            decision['action'] = 'REPLACE'
            self.logger.info(
                f"Quest {quest_id} will replace {', '.join(decision['comment_out'])} entries"
            )
        
        self.decisions.append(decision)
        return decision
    
    def _determine_action(self, epoch_sig: QuestSignature, existing_sig: QuestSignature, 
                         similarity: float) -> str:
        """
        Determine action based on similarity analysis
        
        Returns:
            'REPLACE' - Comment out existing, use Epoch
            'SKIP' - Don't add Epoch version (identical)
            'MERGE' - Combine data from both
        """
        
        # ID collision is the strongest indicator
        if epoch_sig.quest_id == existing_sig.quest_id:
            # Same ID - check if it's actually different content
            
            # Different names = different quest using same ID
            if epoch_sig.name and existing_sig.name:
                name_sim = self._calculate_name_similarity(epoch_sig.name, existing_sig.name)
                if name_sim < 0.5:
                    return 'REPLACE'  # Completely different quest
            
            # Different NPCs = modified quest
            if epoch_sig.quest_giver_npcs != existing_sig.quest_giver_npcs:
                return 'REPLACE'
            
            # Different objectives = modified quest
            if similarity < self.REPLACEMENT_THRESHOLD:
                return 'REPLACE'
            
            # Very high similarity with same ID = same quest
            if similarity > 90:
                return 'SKIP'
        
        # Different ID but high similarity = quest was moved/renumbered
        elif similarity > self.REPLACEMENT_THRESHOLD:
            # Check if objectives are different
            if epoch_sig.objectives_text != existing_sig.objectives_text:
                return 'REPLACE'
            else:
                return 'MERGE'
        
        # Low similarity = different quests, no action needed
        return 'ADD'
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate detailed name similarity"""
        if not name1 or not name2:
            return 0.0
        
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        
        # Exact match
        if n1 == n2:
            return 1.0
        
        # Remove common modifications
        for pattern in [r'\[.*?\]', r'\(.*?\)', 'deprecated', 'old', 'new', 'test']:
            n1 = re.sub(pattern, '', n1).strip()
            n2 = re.sub(pattern, '', n2).strip()
        
        if n1 == n2:
            return 0.9
        
        # Check containment
        if n1 in n2 or n2 in n1:
            return 0.7
        
        # Word overlap
        words1 = set(n1.split())
        words2 = set(n2.split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        
        return overlap / total if total > 0 else 0.0
    
    def _create_signature(self, quest_data: Dict, source: DatabaseSource) -> QuestSignature:
        """Create a quest signature for comparison"""
        # Handle different data formats
        quest_id = quest_data.get('quest_id') or quest_data.get('id') or 0
        name = quest_data.get('name') or quest_data.get('quest_name') or ''
        
        # Extract NPCs
        quest_giver_npcs = []
        if 'startedBy' in quest_data:
            started_by = quest_data['startedBy']
            if isinstance(started_by, dict):
                quest_giver_npcs = started_by.get('npcs', [])
            elif isinstance(started_by, list):
                quest_giver_npcs = started_by
        
        turn_in_npcs = []
        if 'finishedBy' in quest_data:
            finished_by = quest_data['finishedBy']
            if isinstance(finished_by, dict):
                turn_in_npcs = finished_by.get('npcs', [])
            elif isinstance(finished_by, list):
                turn_in_npcs = finished_by
        
        # Extract objectives
        objectives_text = []
        if 'objectivesText' in quest_data:
            obj = quest_data['objectivesText']
            if isinstance(obj, list):
                objectives_text = obj
            elif isinstance(obj, str):
                objectives_text = [obj]
        
        return QuestSignature(
            quest_id=quest_id,
            name=name,
            source=source,
            objectives_text=objectives_text,
            quest_giver_npcs=quest_giver_npcs,
            turn_in_npcs=turn_in_npcs,
            zone_id=quest_data.get('zoneOrSort') or quest_data.get('zone') or 0,
            quest_level=quest_data.get('questLevel') or quest_data.get('level') or 0
        )
    
    def generate_precedence_report(self) -> str:
        """Generate a report of all precedence decisions"""
        lines = []
        lines.append("="*70)
        lines.append("DATABASE PRECEDENCE RESOLUTION REPORT")
        lines.append("="*70)
        
        replace_count = sum(1 for d in self.decisions if d['action'] == 'REPLACE')
        skip_count = sum(1 for d in self.decisions if d['action'] == 'SKIP')
        add_count = sum(1 for d in self.decisions if d['action'] == 'ADD')
        
        lines.append(f"\nTotal quests analyzed: {len(self.decisions)}")
        lines.append(f"  REPLACE (comment out existing): {replace_count}")
        lines.append(f"  SKIP (already exists): {skip_count}")
        lines.append(f"  ADD (new quest): {add_count}")
        
        # Show high-impact decisions
        if replace_count > 0:
            lines.append("\n" + "="*50)
            lines.append("QUESTS REQUIRING DATABASE CHANGES:")
            lines.append("-"*50)
            
            for decision in self.decisions:
                if decision['action'] == 'REPLACE':
                    lines.append(f"\nQuest {decision['quest_id']}: {decision['quest_name']}")
                    lines.append("  Conflicts:")
                    for conflict in decision['conflicts']:
                        lines.append(f"    - {conflict['source']}: {conflict['type']} "
                                   f"(similarity: {conflict['similarity']:.1f})")
                        lines.append(f"      Existing: {conflict['existing_name']}")
                    lines.append("  Action: Comment out in:")
                    for db in decision['comment_out']:
                        lines.append(f"    - {db} database")
                    lines.append("  Reasoning:")
                    for reason in decision['reasoning']:
                        lines.append(f"    - {reason}")
        
        # Summary of affected databases
        affected_dbs = {'WOTLK': 0, 'CLASSIC': 0}
        for decision in self.decisions:
            for db in decision.get('comment_out', []):
                if db in affected_dbs:
                    affected_dbs[db] += 1
        
        if any(affected_dbs.values()):
            lines.append("\n" + "="*50)
            lines.append("DATABASE IMPACT SUMMARY:")
            lines.append("-"*50)
            for db, count in affected_dbs.items():
                if count > 0:
                    lines.append(f"  {db}: {count} entries to comment out")
        
        lines.append("\n" + "="*70)
        return "\n".join(lines)


def main():
    """Test the database precedence resolver"""
    resolver = DatabasePrecedenceResolver()
    
    # Test case 1: Epoch quest with same ID as vanilla
    epoch_quest = {
        'quest_id': 27011,
        'name': 'Golem Gyroscope',
        'startedBy': {'npcs': [45956]},
        'finishedBy': {'npcs': [1093]},
        'objectivesText': ['Collect 10 golem parts'],
        'zone': 11
    }
    
    existing_quests = {
        DatabaseSource.WOTLK: {
            'quest_id': 27011,
            'name': 'Agamar Slain',  # Different quest with same ID
            'startedBy': {'npcs': [12345]},
            'objectivesText': ['Kill Agamar'],
            'zone': 85
        }
    }
    
    print("Test Case 1: ID Collision with different content")
    decision = resolver.analyze_quest_collision(epoch_quest, existing_quests)
    print(f"  Decision: {decision['action']}")
    print(f"  Comment out: {decision['comment_out']}")
    print(f"  Reasoning: {decision['reasoning']}")
    
    # Test case 2: Similar quest (modified version)
    epoch_quest2 = {
        'quest_id': 12345,
        'name': 'The Lost Artifact Enhanced',
        'startedBy': {'npcs': [100]},
        'objectivesText': ['Find the artifact', 'Return to questgiver'],
    }
    
    existing_quests2 = {
        DatabaseSource.CLASSIC: {
            'quest_id': 12345,
            'name': 'The Lost Artifact',
            'startedBy': {'npcs': [100]},
            'objectivesText': ['Find the artifact'],
        }
    }
    
    print("\nTest Case 2: Enhanced version of existing quest")
    decision2 = resolver.analyze_quest_collision(epoch_quest2, existing_quests2)
    print(f"  Decision: {decision2['action']}")
    print(f"  Similarity: {decision2['similarity_scores']}")
    
    # Generate report
    print("\n" + resolver.generate_precedence_report())


if __name__ == "__main__":
    main()