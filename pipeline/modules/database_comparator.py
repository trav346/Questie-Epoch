#!/usr/bin/env python3
"""
Database Comparator Module for Questie Pipeline

Compares parsed quest/NPC data against existing database entries to detect:
- New entries that need to be added
- Existing entries that need updates
- Conflicting data that requires manual review
- Data quality improvements (better coordinates, names, etc.)

Works with WoW 3.3.5 epochQuestDB.lua and epochNpcDB.lua structures.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path
import difflib

@dataclass
class ComparisonResult:
    """Result of comparing new data against existing database"""
    entry_id: int
    entry_type: str  # 'quest' or 'npc'
    action: str  # 'add_new', 'update_existing', 'conflict', 'no_change'
    confidence: float
    existing_data: Dict = None
    new_data: Dict = None
    differences: List[str] = None
    improvement_score: float = 0.0  # How much better the new data is
    
    def __post_init__(self):
        if self.differences is None:
            self.differences = []

class DatabaseComparator:
    """Compares new quest/NPC data against existing database entries"""
    
    def __init__(self, database_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.database_path = Path(database_path) if database_path else None
        
        # Cached database content
        self.quest_db = {}
        self.npc_db = {}
        self.db_loaded = False
        
        # Field importance weights for scoring improvements
        self.quest_field_weights = {
            'name': 1.0,
            'startedBy': 0.9,
            'finishedBy': 0.9, 
            'objectives': 0.8,
            'requiredLevel': 0.7,
            'questLevel': 0.7,
            'zoneOrSort': 0.6,
            'preQuestGroup': 0.5,
            'preQuestSingle': 0.5,
            'nextQuestInChain': 0.5
        }
        
        self.npc_field_weights = {
            'name': 1.0,
            'spawns': 0.9,
            'zoneID': 0.8,
            'questStarts': 0.8,
            'questEnds': 0.8,
            'minLevel': 0.6,
            'maxLevel': 0.6,
            'rank': 0.5,
            'npcFlags': 0.4
        }
        
        # Thresholds for decision making
        self.improvement_threshold = 0.3  # Minimum improvement to justify update
        self.conflict_threshold = 0.7    # Confidence difference that indicates conflict
    
    def load_databases(self, quest_db_path: str = None, npc_db_path: str = None) -> bool:
        """Load existing database files"""
        try:
            if quest_db_path:
                self.quest_db = self._parse_lua_database(quest_db_path, 'quest')
                
            if npc_db_path:
                self.npc_db = self._parse_lua_database(npc_db_path, 'npc')
                
            self.db_loaded = True
            self.logger.info(f"Loaded {len(self.quest_db)} quests and {len(self.npc_db)} NPCs from database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading databases: {e}")
            return False
    
    def compare_quest_data(self, parsed_quests: Dict) -> List[ComparisonResult]:
        """Compare parsed quest data against existing database"""
        if not self.db_loaded:
            self.logger.warning("Databases not loaded, cannot perform comparison")
            return []
        
        results = []
        
        for quest_id, quest_data in parsed_quests.items():
            try:
                quest_id = int(quest_id)
                
                if quest_id in self.quest_db:
                    # Compare against existing entry
                    result = self._compare_quest_entry(quest_id, quest_data, self.quest_db[quest_id])
                else:
                    # New quest entry
                    result = ComparisonResult(
                        entry_id=quest_id,
                        entry_type='quest',
                        action='add_new',
                        confidence=quest_data.get('parsing_confidence', 0.0),
                        new_data=quest_data,
                        improvement_score=1.0  # New data is always an improvement
                    )
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error comparing quest {quest_id}: {e}")
                continue
        
        return results
    
    def compare_npc_data(self, parsed_npcs: Dict) -> List[ComparisonResult]:
        """Compare parsed NPC data against existing database"""
        if not self.db_loaded:
            self.logger.warning("Databases not loaded, cannot perform comparison")
            return []
        
        results = []
        
        for npc_id, npc_data in parsed_npcs.items():
            try:
                npc_id = int(npc_id)
                
                if npc_id in self.npc_db:
                    # Compare against existing entry
                    result = self._compare_npc_entry(npc_id, npc_data, self.npc_db[npc_id])
                else:
                    # New NPC entry
                    result = ComparisonResult(
                        entry_id=npc_id,
                        entry_type='npc',
                        action='add_new', 
                        confidence=npc_data.get('confidence', 0.0),
                        new_data=npc_data,
                        improvement_score=1.0  # New data is always an improvement
                    )
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error comparing NPC {npc_id}: {e}")
                continue
        
        return results
    
    def generate_comparison_report(self, results: List[ComparisonResult]) -> Dict:
        """Generate summary report of comparison results"""
        report = {
            'total_entries': len(results),
            'add_new': 0,
            'update_existing': 0,
            'conflicts': 0,
            'no_changes': 0,
            'high_confidence_updates': 0,
            'low_confidence_updates': 0,
            'recommended_actions': [],
            'entries_by_action': {
                'add_new': [],
                'update_existing': [],
                'conflict': [],
                'no_change': []
            }
        }
        
        for result in results:
            report['entries_by_action'][result.action].append(result)
            
            if result.action == 'add_new':
                report['add_new'] += 1
            elif result.action == 'update_existing':
                report['update_existing'] += 1
                if result.confidence >= 0.7:
                    report['high_confidence_updates'] += 1
                else:
                    report['low_confidence_updates'] += 1
            elif result.action == 'conflict':
                report['conflicts'] += 1
            elif result.action == 'no_change':
                report['no_changes'] += 1
        
        # Generate recommendations
        if report['add_new'] > 0:
            report['recommended_actions'].append(f"Add {report['add_new']} new entries to database")
            
        if report['high_confidence_updates'] > 0:
            report['recommended_actions'].append(f"Apply {report['high_confidence_updates']} high-confidence updates")
            
        if report['conflicts'] > 0:
            report['recommended_actions'].append(f"Manually review {report['conflicts']} conflicts")
            
        if report['low_confidence_updates'] > 0:
            report['recommended_actions'].append(f"Consider {report['low_confidence_updates']} low-confidence updates for manual review")
        
        return report
    
    def _parse_lua_database(self, file_path: str, db_type: str) -> Dict:
        """Parse Lua database file into Python dict"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entries = {}
            
            # Extract individual entries using regex
            if db_type == 'quest':
                # Match quest entries like [questId] = { ... },
                pattern = r'\[(\d+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\},'
            else:  # npc
                # Match NPC entries 
                pattern = r'\[(\d+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\},'
            
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                entry_id = int(match.group(1))
                entry_content = match.group(2)
                
                # Parse the entry content into structured data
                if db_type == 'quest':
                    entries[entry_id] = self._parse_quest_entry(entry_content)
                else:
                    entries[entry_id] = self._parse_npc_entry(entry_content)
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Error parsing {db_type} database {file_path}: {e}")
            return {}
    
    def _parse_quest_entry(self, content: str) -> Dict:
        """Parse a single quest entry from Lua format"""
        # This is a simplified parser - in production you'd want more robust parsing
        quest_data = {
            'name': None,
            'startedBy': None,
            'finishedBy': None,
            'requiredLevel': None,
            'questLevel': None,
            'objectives': None,
            'zoneOrSort': None,
            'raw_content': content.strip()
        }
        
        # Extract quest name (first quoted string)
        name_match = re.search(r'"([^"]+)"', content)
        if name_match:
            quest_data['name'] = name_match.group(1)
        
        # Extract numbers (levels, IDs, etc.)
        numbers = re.findall(r'\b\d+\b', content)
        if len(numbers) >= 2:
            quest_data['requiredLevel'] = int(numbers[0]) if numbers[0] != '0' else None
            quest_data['questLevel'] = int(numbers[1])
        
        return quest_data
    
    def _parse_npc_entry(self, content: str) -> Dict:
        """Parse a single NPC entry from Lua format"""
        npc_data = {
            'name': None,
            'minLevel': None,
            'maxLevel': None,
            'rank': None,
            'spawns': None,
            'zoneID': None,
            'questStarts': None,
            'questEnds': None,
            'npcFlags': None,
            'raw_content': content.strip()
        }
        
        # Extract NPC name (first quoted string)
        name_match = re.search(r'"([^"]+)"', content)
        if name_match:
            npc_data['name'] = name_match.group(1)
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', content)
        if len(numbers) >= 3:
            npc_data['minLevel'] = int(numbers[0])
            npc_data['maxLevel'] = int(numbers[1])
            npc_data['rank'] = int(numbers[2])
        
        return npc_data
    
    def _compare_quest_entry(self, quest_id: int, new_data: Dict, existing_data: Dict) -> ComparisonResult:
        """Compare new quest data against existing database entry"""
        differences = []
        improvement_score = 0.0
        total_weight = 0.0
        
        # Compare key fields
        for field, weight in self.quest_field_weights.items():
            total_weight += weight
            
            new_value = new_data.get(field)
            existing_value = existing_data.get(field)
            
            if new_value and existing_value:
                # Both have values - check if new is better
                if self._is_better_value(new_value, existing_value, field):
                    differences.append(f"{field}: '{existing_value}' -> '{new_value}'")
                    improvement_score += weight
            elif new_value and not existing_value:
                # New data has value, existing doesn't
                differences.append(f"{field}: None -> '{new_value}'")
                improvement_score += weight
            elif not new_value and existing_value:
                # Existing has value, new doesn't (potential regression)
                differences.append(f"{field}: '{existing_value}' -> None (LOSS)")
                improvement_score -= weight * 0.5
        
        # Normalize improvement score
        improvement_score = max(0.0, improvement_score / total_weight)
        
        # Determine action based on improvement and confidence
        new_confidence = new_data.get('parsing_confidence', 0.0)
        
        if improvement_score >= self.improvement_threshold and new_confidence >= 0.5:
            action = 'update_existing'
        elif improvement_score >= self.improvement_threshold and new_confidence < 0.5:
            action = 'conflict'  # Improvement but low confidence
        elif abs(improvement_score) < 0.1:
            action = 'no_change'
        else:
            action = 'conflict'  # Significant changes but unclear benefit
        
        return ComparisonResult(
            entry_id=quest_id,
            entry_type='quest',
            action=action,
            confidence=new_confidence,
            existing_data=existing_data,
            new_data=new_data,
            differences=differences,
            improvement_score=improvement_score
        )
    
    def _compare_npc_entry(self, npc_id: int, new_data: Dict, existing_data: Dict) -> ComparisonResult:
        """Compare new NPC data against existing database entry"""
        differences = []
        improvement_score = 0.0
        total_weight = 0.0
        
        # Compare key fields
        for field, weight in self.npc_field_weights.items():
            total_weight += weight
            
            new_value = new_data.get(field)
            existing_value = existing_data.get(field)
            
            if new_value and existing_value:
                if self._is_better_value(new_value, existing_value, field):
                    differences.append(f"{field}: '{existing_value}' -> '{new_value}'")
                    improvement_score += weight
            elif new_value and not existing_value:
                differences.append(f"{field}: None -> '{new_value}'")
                improvement_score += weight
            elif not new_value and existing_value:
                differences.append(f"{field}: '{existing_value}' -> None (LOSS)")
                improvement_score -= weight * 0.5
        
        # Normalize improvement score
        improvement_score = max(0.0, improvement_score / total_weight)
        
        # Determine action
        new_confidence = new_data.get('confidence', 0.0)
        
        if improvement_score >= self.improvement_threshold and new_confidence >= 0.5:
            action = 'update_existing'
        elif improvement_score >= self.improvement_threshold and new_confidence < 0.5:
            action = 'conflict'
        elif abs(improvement_score) < 0.1:
            action = 'no_change'
        else:
            action = 'conflict'
        
        return ComparisonResult(
            entry_id=npc_id,
            entry_type='npc',
            action=action,
            confidence=new_confidence,
            existing_data=existing_data,
            new_data=new_data,
            differences=differences,
            improvement_score=improvement_score
        )
    
    def _is_better_value(self, new_value: Any, existing_value: Any, field: str) -> bool:
        """Determine if new value is better than existing value"""
        if field in ['name']:
            # For names, prefer non-placeholder values
            if isinstance(new_value, str) and isinstance(existing_value, str):
                # Check for placeholders
                if '[Epoch]' in str(existing_value) and '[Epoch]' not in str(new_value):
                    return True
                # Check for more complete names
                return len(str(new_value)) > len(str(existing_value))
        
        elif field in ['spawns', 'coordinates']:
            # For coordinates, more locations is usually better
            if isinstance(new_value, list) and isinstance(existing_value, list):
                return len(new_value) > len(existing_value)
        
        elif field in ['objectives', 'questStarts', 'questEnds']:
            # For lists, more complete data is better
            if isinstance(new_value, list) and isinstance(existing_value, list):
                return len(new_value) > len(existing_value)
        
        elif field in ['questLevel', 'minLevel', 'maxLevel']:
            # For levels, prefer realistic values over defaults
            if isinstance(new_value, int) and isinstance(existing_value, int):
                # Prefer non-default values
                if existing_value == 1 and new_value > 1:
                    return True
                # Prefer reasonable level ranges
                return 1 <= new_value <= 80 and not (1 <= existing_value <= 80)
        
        # Default: new value is better if it's not None/empty and existing is
        if new_value and not existing_value:
            return True
        
        return False
    
    def get_conflict_summary(self, results: List[ComparisonResult]) -> Dict:
        """Generate detailed summary of conflicts requiring manual review"""
        conflicts = [r for r in results if r.action == 'conflict']
        
        summary = {
            'total_conflicts': len(conflicts),
            'by_type': {'quest': 0, 'npc': 0},
            'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
            'common_issues': [],
            'detailed_conflicts': []
        }
        
        for conflict in conflicts:
            # Count by type
            summary['by_type'][conflict.entry_type] += 1
            
            # Count by confidence
            if conflict.confidence >= 0.7:
                summary['by_confidence']['high'] += 1
            elif conflict.confidence >= 0.4:
                summary['by_confidence']['medium'] += 1
            else:
                summary['by_confidence']['low'] += 1
            
            # Add to detailed list
            summary['detailed_conflicts'].append({
                'id': conflict.entry_id,
                'type': conflict.entry_type,
                'confidence': conflict.confidence,
                'improvement_score': conflict.improvement_score,
                'differences': conflict.differences[:3]  # Top 3 differences
            })
        
        return summary


def main():
    """Test the database comparator with sample data"""
    comparator = DatabaseComparator()
    
    # Test with sample data
    sample_quest = {
        12345: {
            'name': 'Test Quest',
            'questLevel': 15,
            'requiredLevel': 10,
            'parsing_confidence': 0.8
        }
    }
    
    sample_npc = {
        67890: {
            'name': 'Test NPC',
            'minLevel': 14,
            'maxLevel': 16,
            'confidence': 0.7
        }
    }
    
    # Compare (without loading actual database)
    quest_results = []  # Would call comparator.compare_quest_data(sample_quest)
    npc_results = []    # Would call comparator.compare_npc_data(sample_npc)
    
    print("Database Comparator test completed")
    print("Note: Load actual database files to perform real comparisons")


if __name__ == "__main__":
    main()