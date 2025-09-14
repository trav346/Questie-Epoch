#!/usr/bin/env python3
"""
Duplicate Detector - Find and handle duplicate entries
Identifies duplicate quests and NPCs using multiple matching strategies
"""

import logging
from typing import Dict, List, Tuple, Set, Optional
import difflib


class DuplicateDetector:
    """
    Detects duplicate entries in quest and NPC databases
    Uses fuzzy matching and multiple criteria to find duplicates
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = similarity_threshold
        self.duplicates = []
        
    def detect_duplicates(self, entities: Dict) -> List[Dict]:
        """
        Detect duplicate entities
        
        Args:
            entities: Dict of entity_id -> entity_data
            
        Returns:
            List of duplicate groups
        """
        self.duplicates = []
        entity_list = list(entities.items())
        
        # Check each pair for duplicates
        for i, (id1, data1) in enumerate(entity_list):
            duplicate_group = {
                'primary': id1,
                'duplicates': [],
                'confidence': [],
                'type': 'quest' if 'quest_id' in data1 else 'npc',
            }
            
            for j, (id2, data2) in enumerate(entity_list[i+1:], i+1):
                similarity, match_type = self._calculate_similarity(data1, data2)
                
                if similarity >= self.similarity_threshold:
                    duplicate_group['duplicates'].append(id2)
                    duplicate_group['confidence'].append({
                        'id': id2,
                        'similarity': similarity,
                        'match_type': match_type,
                    })
                    
                    self.logger.info(
                        f"Found duplicate: {id1} and {id2} "
                        f"(similarity: {similarity:.2f}, type: {match_type})"
                    )
            
            if duplicate_group['duplicates']:
                self.duplicates.append(duplicate_group)
        
        return self.duplicates
    
    def _calculate_similarity(self, data1: Dict, data2: Dict) -> Tuple[float, str]:
        """
        Calculate similarity between two entities
        
        Returns:
            (similarity_score, match_type)
        """
        # Determine entity type
        is_quest = 'quest_id' in data1 or 'name' in data1
        
        if is_quest:
            return self._calculate_quest_similarity(data1, data2)
        else:
            return self._calculate_npc_similarity(data1, data2)
    
    def _calculate_quest_similarity(self, quest1: Dict, quest2: Dict) -> Tuple[float, str]:
        """Calculate similarity between two quests"""
        scores = []
        match_types = []
        
        # Name similarity (highest weight)
        name1 = quest1.get('name', '')
        name2 = quest2.get('name', '')
        if name1 and name2:
            name_sim = self._string_similarity(name1, name2)
            scores.append(name_sim * 2.0)  # Double weight
            if name_sim > 0.9:
                match_types.append('name')
        
        # Objectives similarity
        obj1 = quest1.get('objectivesText', [])
        obj2 = quest2.get('objectivesText', [])
        if obj1 and obj2:
            obj_text1 = ' '.join(obj1) if isinstance(obj1, list) else str(obj1)
            obj_text2 = ' '.join(obj2) if isinstance(obj2, list) else str(obj2)
            obj_sim = self._string_similarity(obj_text1, obj_text2)
            scores.append(obj_sim * 1.5)  # 1.5x weight
            if obj_sim > 0.8:
                match_types.append('objectives')
        
        # NPC matching
        npc_match = self._check_npc_match(quest1, quest2)
        if npc_match > 0:
            scores.append(npc_match)
            if npc_match > 0.7:
                match_types.append('npcs')
        
        # Level matching
        level_match = self._check_level_match(quest1, quest2)
        if level_match > 0:
            scores.append(level_match * 0.5)  # Half weight
            if level_match > 0.9:
                match_types.append('levels')
        
        # Zone matching
        zone1 = quest1.get('zoneOrSort')
        zone2 = quest2.get('zoneOrSort')
        if zone1 and zone2 and zone1 == zone2:
            scores.append(0.3)
            match_types.append('zone')
        
        # Calculate weighted average
        if not scores:
            return 0.0, 'none'
        
        avg_score = sum(scores) / len(scores)
        match_type = '+'.join(match_types) if match_types else 'partial'
        
        return avg_score, match_type
    
    def _calculate_npc_similarity(self, npc1: Dict, npc2: Dict) -> Tuple[float, str]:
        """Calculate similarity between two NPCs"""
        scores = []
        match_types = []
        
        # Name similarity (highest weight)
        name1 = npc1.get('name', '')
        name2 = npc2.get('name', '')
        if name1 and name2:
            name_sim = self._string_similarity(name1, name2)
            scores.append(name_sim * 2.0)
            if name_sim > 0.9:
                match_types.append('name')
        
        # Location similarity
        loc_sim = self._check_location_match(npc1, npc2)
        if loc_sim > 0:
            scores.append(loc_sim * 1.5)
            if loc_sim > 0.8:
                match_types.append('location')
        
        # Level similarity
        level_match = self._check_npc_level_match(npc1, npc2)
        if level_match > 0:
            scores.append(level_match)
            if level_match > 0.9:
                match_types.append('levels')
        
        # Quest association
        quest_match = self._check_quest_association_match(npc1, npc2)
        if quest_match > 0:
            scores.append(quest_match)
            if quest_match > 0.7:
                match_types.append('quests')
        
        # Calculate weighted average
        if not scores:
            return 0.0, 'none'
        
        avg_score = sum(scores) / len(scores)
        match_type = '+'.join(match_types) if match_types else 'partial'
        
        return avg_score, match_type
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using difflib"""
        if not str1 or not str2:
            return 0.0
        
        # Normalize strings
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        # Exact match
        if str1 == str2:
            return 1.0
        
        # Use SequenceMatcher for fuzzy matching
        return difflib.SequenceMatcher(None, str1, str2).ratio()
    
    def _check_npc_match(self, quest1: Dict, quest2: Dict) -> float:
        """Check if quests have matching NPCs"""
        # Get quest giver NPCs
        start1 = quest1.get('startedBy', ([], [], []))
        start2 = quest2.get('startedBy', ([], [], []))
        
        if start1 and start2 and start1[0] and start2[0]:
            start_npcs1 = set(start1[0]) if start1[0] else set()
            start_npcs2 = set(start2[0]) if start2[0] else set()
            
            if start_npcs1 and start_npcs2:
                overlap = len(start_npcs1 & start_npcs2)
                total = len(start_npcs1 | start_npcs2)
                if total > 0:
                    return overlap / total
        
        # Get turn-in NPCs
        finish1 = quest1.get('finishedBy', ([], []))
        finish2 = quest2.get('finishedBy', ([], []))
        
        if finish1 and finish2 and finish1[0] and finish2[0]:
            finish_npcs1 = set(finish1[0]) if finish1[0] else set()
            finish_npcs2 = set(finish2[0]) if finish2[0] else set()
            
            if finish_npcs1 and finish_npcs2:
                overlap = len(finish_npcs1 & finish_npcs2)
                total = len(finish_npcs1 | finish_npcs2)
                if total > 0:
                    return overlap / total
        
        return 0.0
    
    def _check_level_match(self, quest1: Dict, quest2: Dict) -> float:
        """Check if quests have matching levels"""
        level1 = quest1.get('questLevel')
        level2 = quest2.get('questLevel')
        
        if level1 and level2:
            if level1 == level2:
                return 1.0
            else:
                # Partial credit for close levels
                diff = abs(level1 - level2)
                if diff <= 2:
                    return 0.8
                elif diff <= 5:
                    return 0.5
        
        req1 = quest1.get('requiredLevel')
        req2 = quest2.get('requiredLevel')
        
        if req1 and req2:
            if req1 == req2:
                return 0.8
            else:
                diff = abs(req1 - req2)
                if diff <= 2:
                    return 0.6
                elif diff <= 5:
                    return 0.3
        
        return 0.0
    
    def _check_location_match(self, npc1: Dict, npc2: Dict) -> float:
        """Check if NPCs have matching locations"""
        spawns1 = npc1.get('spawns', {})
        spawns2 = npc2.get('spawns', {})
        
        if not spawns1 or not spawns2:
            # Check zone IDs
            zone1 = npc1.get('zoneID')
            zone2 = npc2.get('zoneID')
            if zone1 and zone2 and zone1 == zone2:
                return 0.5
            return 0.0
        
        # Check for zone overlap
        zones1 = set(spawns1.keys())
        zones2 = set(spawns2.keys())
        
        zone_overlap = zones1 & zones2
        if not zone_overlap:
            return 0.0
        
        # Check coordinate proximity
        total_matches = 0
        total_coords = 0
        
        for zone in zone_overlap:
            coords1 = spawns1[zone]
            coords2 = spawns2[zone]
            
            for c1 in coords1:
                for c2 in coords2:
                    distance = self._coordinate_distance(c1, c2)
                    if distance < 5.0:  # Within 5 units
                        total_matches += 1
                    total_coords += 1
        
        if total_coords > 0:
            return total_matches / total_coords
        
        return 0.0
    
    def _coordinate_distance(self, coord1: List[float], coord2: List[float]) -> float:
        """Calculate distance between two coordinates"""
        if len(coord1) < 2 or len(coord2) < 2:
            return float('inf')
        
        dx = coord1[0] - coord2[0]
        dy = coord1[1] - coord2[1]
        return (dx * dx + dy * dy) ** 0.5
    
    def _check_npc_level_match(self, npc1: Dict, npc2: Dict) -> float:
        """Check if NPCs have matching levels"""
        min1 = npc1.get('minLevel')
        max1 = npc1.get('maxLevel')
        min2 = npc2.get('minLevel')
        max2 = npc2.get('maxLevel')
        
        if min1 and max1 and min2 and max2:
            if min1 == min2 and max1 == max2:
                return 1.0
            
            # Check for overlap
            overlap_start = max(min1, min2)
            overlap_end = min(max1, max2)
            
            if overlap_start <= overlap_end:
                overlap = overlap_end - overlap_start + 1
                range1 = max1 - min1 + 1
                range2 = max2 - min2 + 1
                max_range = max(range1, range2)
                
                return overlap / max_range
        
        return 0.0
    
    def _check_quest_association_match(self, npc1: Dict, npc2: Dict) -> float:
        """Check if NPCs are associated with same quests"""
        starts1 = set(npc1.get('questStarts', []))
        starts2 = set(npc2.get('questStarts', []))
        ends1 = set(npc1.get('questEnds', []))
        ends2 = set(npc2.get('questEnds', []))
        
        all_quests1 = starts1 | ends1
        all_quests2 = starts2 | ends2
        
        if not all_quests1 or not all_quests2:
            return 0.0
        
        overlap = len(all_quests1 & all_quests2)
        total = len(all_quests1 | all_quests2)
        
        if total > 0:
            return overlap / total
        
        return 0.0
    
    def merge_duplicates(self, duplicate_group: Dict) -> Dict:
        """
        Merge duplicate entities into single entry
        
        Args:
            duplicate_group: Group of duplicates to merge
            
        Returns:
            Merged entity data
        """
        # Start with primary entity
        primary_id = duplicate_group['primary']
        merged_data = duplicate_group['primary_data'].copy()
        
        # Merge each duplicate
        for dup_info in duplicate_group['confidence']:
            dup_id = dup_info['id']
            dup_data = duplicate_group.get(f'data_{dup_id}', {})
            
            # Merge fields
            for field, value in dup_data.items():
                if field in ['quest_id', 'npc_id']:
                    continue
                
                existing = merged_data.get(field)
                
                # Merge logic based on field type
                if existing is None:
                    merged_data[field] = value
                elif value is None:
                    continue
                elif isinstance(value, str) and isinstance(existing, str):
                    # Keep longer string
                    if len(value) > len(existing):
                        merged_data[field] = value
                elif isinstance(value, (list, set)) and isinstance(existing, (list, set)):
                    # Combine collections
                    combined = list(set(list(existing) + list(value)))
                    merged_data[field] = combined
                elif isinstance(value, dict) and isinstance(existing, dict):
                    # Merge dicts
                    merged_dict = existing.copy()
                    merged_dict.update(value)
                    merged_data[field] = merged_dict
        
        return merged_data
    
    def generate_duplicate_report(self) -> str:
        """Generate report of detected duplicates"""
        lines = []
        lines.append("=" * 60)
        lines.append("DUPLICATE DETECTION REPORT")
        lines.append("=" * 60)
        
        if not self.duplicates:
            lines.append("No duplicates detected")
            return '\n'.join(lines)
        
        lines.append(f"Total duplicate groups: {len(self.duplicates)}")
        
        for i, group in enumerate(self.duplicates, 1):
            lines.append(f"\n--- Duplicate Group {i} ---")
            lines.append(f"Type: {group['type']}")
            lines.append(f"Primary ID: {group['primary']}")
            lines.append(f"Duplicates: {', '.join(map(str, group['duplicates']))}")
            
            for conf in group['confidence']:
                lines.append(f"  - ID {conf['id']}: {conf['similarity']:.2%} "
                           f"similarity ({conf['match_type']})")
        
        # Summary statistics
        total_duplicates = sum(len(g['duplicates']) for g in self.duplicates)
        lines.append(f"\n--- Summary ---")
        lines.append(f"Total duplicate entities: {total_duplicates}")
        lines.append(f"Average duplicates per group: {total_duplicates/len(self.duplicates):.1f}")
        
        return '\n'.join(lines)


def main():
    """Test the duplicate detector"""
    detector = DuplicateDetector(similarity_threshold=0.8)
    
    # Test data with duplicates
    entities = {
        12345: {
            'quest_id': 12345,
            'name': 'Kill the Wolves',
            'questLevel': 10,
            'objectivesText': ['Kill 10 wolves in the forest'],
            'zoneOrSort': 12,
        },
        12346: {
            'quest_id': 12346,
            'name': 'Kill the Wolves',  # Same name
            'questLevel': 10,  # Same level
            'objectivesText': ['Kill 10 wolves in the woods'],  # Similar text
            'zoneOrSort': 12,  # Same zone
        },
        12347: {
            'quest_id': 12347,
            'name': 'Completely Different Quest',
            'questLevel': 25,
            'objectivesText': ['Do something else'],
            'zoneOrSort': 14,
        }
    }
    
    # Detect duplicates
    duplicates = detector.detect_duplicates(entities)
    
    # Generate report
    report = detector.generate_duplicate_report()
    print(report)


if __name__ == "__main__":
    main()