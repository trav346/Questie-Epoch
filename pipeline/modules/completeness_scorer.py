#!/usr/bin/env python3
"""
Completeness Scorer - Score data completeness 0-100%
Evaluates how complete quest and NPC data is
"""

import logging
from typing import Dict, List, Tuple, Any


class CompletenessScorer:
    """
    Scores the completeness of quest and NPC data
    Provides detailed breakdown of missing/incomplete fields
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Field importance weights for quests (total: 100)
        self.quest_field_weights = {
            'name': 10,  # Critical
            'startedBy': 10,  # Critical
            'finishedBy': 10,  # Critical
            'questLevel': 5,  # Important
            'requiredLevel': 3,  # Important
            'objectivesText': 8,  # Very Important
            'objectives': 10,  # Critical
            'zoneOrSort': 5,  # Important
            'requiredRaces': 3,  # Moderate
            'requiredClasses': 3,  # Moderate
            'questFlags': 2,  # Moderate
            'sourceItemId': 2,  # Optional
            'preQuestSingle': 3,  # Important for chains
            'preQuestGroup': 3,  # Important for chains
            'nextQuestInChain': 3,  # Important for chains
            'childQuests': 2,  # Optional
            'exclusiveTo': 2,  # Optional
            'requiredSkill': 2,  # Optional
            'requiredMinRep': 2,  # Optional
            'requiredMaxRep': 1,  # Optional
            'requiredSourceItems': 2,  # Optional
            'specialFlags': 1,  # Optional
            'parentQuest': 2,  # Optional
            'reputationReward': 2,  # Optional
            'extraObjectives': 2,  # Optional
            'requiredSpell': 1,  # Optional
            'requiredSpecialization': 1,  # Optional
            'requiredMaxLevel': 1,  # Optional
            'triggerEnd': 2,  # Optional
            'inGroupWith': 1,  # Optional
        }
        
        # Field importance weights for NPCs (total: 100)
        self.npc_field_weights = {
            'name': 20,  # Critical
            'minLevel': 10,  # Important
            'maxLevel': 10,  # Important
            'spawns': 15,  # Critical for location
            'zoneID': 10,  # Important
            'questStarts': 8,  # Important
            'questEnds': 8,  # Important
            'friendlyToFaction': 5,  # Important
            'npcFlags': 5,  # Important
            'rank': 2,  # Optional
            'minLevelHealth': 2,  # Optional
            'maxLevelHealth': 2,  # Optional
            'factionID': 1,  # Optional
            'subName': 1,  # Optional
            'waypoints': 1,  # Optional
        }
        
        # Completeness thresholds
        self.thresholds = {
            'excellent': 90,
            'good': 75,
            'acceptable': 60,
            'poor': 40,
            'incomplete': 0,
        }
    
    def score_quest(self, quest_data: Dict) -> Tuple[float, Dict]:
        """
        Score quest data completeness
        
        Returns:
            (score, breakdown) where score is 0-100
        """
        total_weight = sum(self.quest_field_weights.values())
        earned_score = 0
        missing_fields = []
        incomplete_fields = []
        present_fields = []
        
        breakdown = {
            'score': 0,
            'grade': '',
            'missing_critical': [],
            'missing_important': [],
            'missing_optional': [],
            'incomplete': [],
            'suggestions': [],
        }
        
        # Check each field
        for field_name, weight in self.quest_field_weights.items():
            value = quest_data.get(field_name)
            
            if value is None:
                missing_fields.append(field_name)
                # Categorize by importance
                if weight >= 8:
                    breakdown['missing_critical'].append(field_name)
                elif weight >= 3:
                    breakdown['missing_important'].append(field_name)
                else:
                    breakdown['missing_optional'].append(field_name)
            else:
                # Check completeness of the value
                field_score = self._score_field_completeness(field_name, value)
                earned_score += weight * field_score
                
                if field_score < 1.0:
                    incomplete_fields.append(f"{field_name} ({int(field_score*100)}% complete)")
                    breakdown['incomplete'].append({
                        'field': field_name,
                        'completeness': field_score,
                        'issue': self._get_field_issue(field_name, value)
                    })
                else:
                    present_fields.append(field_name)
        
        # Calculate final score
        score = (earned_score / total_weight) * 100
        breakdown['score'] = round(score, 1)
        breakdown['grade'] = self._get_grade(score)
        
        # Generate suggestions
        breakdown['suggestions'] = self._generate_quest_suggestions(
            missing_fields, incomplete_fields, score
        )
        
        self.logger.info(f"Quest completeness: {score:.1f}% ({breakdown['grade']})")
        
        return score, breakdown
    
    def score_npc(self, npc_data: Dict) -> Tuple[float, Dict]:
        """
        Score NPC data completeness
        
        Returns:
            (score, breakdown) where score is 0-100
        """
        total_weight = sum(self.npc_field_weights.values())
        earned_score = 0
        missing_fields = []
        incomplete_fields = []
        
        breakdown = {
            'score': 0,
            'grade': '',
            'missing_critical': [],
            'missing_important': [],
            'missing_optional': [],
            'incomplete': [],
            'suggestions': [],
        }
        
        # Check each field
        for field_name, weight in self.npc_field_weights.items():
            value = npc_data.get(field_name)
            
            if value is None:
                missing_fields.append(field_name)
                # Categorize by importance
                if weight >= 10:
                    breakdown['missing_critical'].append(field_name)
                elif weight >= 5:
                    breakdown['missing_important'].append(field_name)
                else:
                    breakdown['missing_optional'].append(field_name)
            else:
                # Check completeness of the value
                field_score = self._score_field_completeness(field_name, value)
                earned_score += weight * field_score
                
                if field_score < 1.0:
                    incomplete_fields.append(f"{field_name} ({int(field_score*100)}% complete)")
                    breakdown['incomplete'].append({
                        'field': field_name,
                        'completeness': field_score,
                        'issue': self._get_field_issue(field_name, value)
                    })
        
        # Calculate final score
        score = (earned_score / total_weight) * 100
        breakdown['score'] = round(score, 1)
        breakdown['grade'] = self._get_grade(score)
        
        # Generate suggestions
        breakdown['suggestions'] = self._generate_npc_suggestions(
            missing_fields, incomplete_fields, score
        )
        
        self.logger.info(f"NPC completeness: {score:.1f}% ({breakdown['grade']})")
        
        return score, breakdown
    
    def _score_field_completeness(self, field_name: str, value: Any) -> float:
        """
        Score how complete a field value is (0.0 to 1.0)
        """
        # Empty collections
        if isinstance(value, (list, dict, tuple)):
            if len(value) == 0:
                # Some fields are okay to be empty
                optional_empty = ['childQuests', 'exclusiveTo', 'waypoints', 'reputationReward']
                if field_name in optional_empty:
                    return 1.0
                return 0.5  # Present but empty
            
            # Check for placeholder values in collections
            if isinstance(value, dict):
                # Check spawn coordinates
                if field_name == 'spawns':
                    for zone_id, coords in value.items():
                        if not coords or len(coords) == 0:
                            return 0.7  # Has zones but missing coords
                        for coord in coords:
                            if coord == [0, 0] or coord == [-1, -1]:
                                return 0.8  # Has placeholder coords
                return 1.0
            
            # Check for nil/None in arrays
            if isinstance(value, (list, tuple)):
                none_count = sum(1 for v in value if v is None)
                if none_count > 0:
                    return (len(value) - none_count) / len(value)
            
            return 1.0
        
        # String fields
        if isinstance(value, str):
            # Check for placeholder text
            placeholders = [
                'unknown', 'todo', 'fixme', 'placeholder', 
                'temp', 'test', '???', 'n/a', 'none'
            ]
            value_lower = value.lower()
            for placeholder in placeholders:
                if placeholder in value_lower:
                    return 0.5
            
            # Check for truncated text
            if value.endswith('...') and len(value) < 20:
                return 0.7
            
            # Check minimum meaningful length
            if field_name == 'name' and len(value) < 3:
                return 0.5
            if field_name == 'objectivesText' and len(value) < 10:
                return 0.7
            
            return 1.0
        
        # Numeric fields
        if isinstance(value, (int, float)):
            # Check for obvious placeholder values
            if value in [-1, 0, 999, 9999]:
                suspicious_fields = ['questLevel', 'requiredLevel', 'npc_id', 'quest_id']
                if field_name in suspicious_fields and value in [-1, 0]:
                    return 0.5
            
            return 1.0
        
        # Default: field is present
        return 1.0
    
    def _get_field_issue(self, field_name: str, value: Any) -> str:
        """Get description of field completeness issue"""
        if isinstance(value, (list, dict, tuple)) and len(value) == 0:
            return "Empty collection"
        
        if isinstance(value, str):
            if any(p in value.lower() for p in ['unknown', 'todo', 'placeholder']):
                return "Contains placeholder text"
            if len(value) < 3:
                return "Too short to be meaningful"
        
        if isinstance(value, (int, float)) and value in [-1, 0]:
            return "Suspicious placeholder value"
        
        return "Incomplete data"
    
    def _get_grade(self, score: float) -> str:
        """Get letter grade for score"""
        if score >= self.thresholds['excellent']:
            return 'Excellent'
        elif score >= self.thresholds['good']:
            return 'Good'
        elif score >= self.thresholds['acceptable']:
            return 'Acceptable'
        elif score >= self.thresholds['poor']:
            return 'Poor'
        else:
            return 'Incomplete'
    
    def _generate_quest_suggestions(self, missing: List[str], incomplete: List[str], score: float) -> List[str]:
        """Generate improvement suggestions for quest data"""
        suggestions = []
        
        # Critical missing fields
        critical = ['name', 'startedBy', 'finishedBy', 'objectives']
        critical_missing = [f for f in critical if f in missing]
        if critical_missing:
            suggestions.append(f"CRITICAL: Add missing fields: {', '.join(critical_missing)}")
        
        # Important missing fields
        important = ['questLevel', 'requiredLevel', 'objectivesText', 'zoneOrSort']
        important_missing = [f for f in important if f in missing]
        if important_missing:
            suggestions.append(f"Important: Add missing fields: {', '.join(important_missing)}")
        
        # Quest chain fields
        chain_fields = ['preQuestSingle', 'preQuestGroup', 'nextQuestInChain']
        chain_missing = [f for f in chain_fields if f in missing]
        if len(chain_missing) == len(chain_fields):
            suggestions.append("Consider: Check if quest is part of a chain")
        
        # Incomplete fields
        if incomplete:
            suggestions.append(f"Complete partial fields: {', '.join(incomplete[:3])}")
        
        # Score-based suggestions
        if score < 40:
            suggestions.append("This quest needs significant data collection")
        elif score < 60:
            suggestions.append("Quest data needs moderate improvement")
        elif score < 75:
            suggestions.append("Quest data is good but could be more complete")
        
        return suggestions
    
    def _generate_npc_suggestions(self, missing: List[str], incomplete: List[str], score: float) -> List[str]:
        """Generate improvement suggestions for NPC data"""
        suggestions = []
        
        # Critical missing fields
        critical = ['name', 'spawns', 'minLevel', 'maxLevel']
        critical_missing = [f for f in critical if f in missing]
        if critical_missing:
            suggestions.append(f"CRITICAL: Add missing fields: {', '.join(critical_missing)}")
        
        # Location data
        if 'spawns' in missing and 'zoneID' in missing:
            suggestions.append("CRITICAL: No location data - add spawns or zoneID")
        elif 'spawns' in missing:
            suggestions.append("Important: Add spawn coordinates")
        
        # Quest NPC fields
        if 'questStarts' in missing and 'questEnds' in missing:
            suggestions.append("Check: Is this NPC a quest giver?")
        
        # Faction data
        if 'friendlyToFaction' in missing:
            suggestions.append("Add faction accessibility (A/H/AH)")
        
        # Score-based suggestions
        if score < 50:
            suggestions.append("This NPC needs significant data collection")
        elif score < 75:
            suggestions.append("NPC data needs improvement in key areas")
        
        return suggestions
    
    def generate_report(self, quest_scores: List[Tuple[int, float]], 
                       npc_scores: List[Tuple[int, float]]) -> str:
        """Generate completeness report for multiple entries"""
        report = []
        report.append("=" * 60)
        report.append("DATA COMPLETENESS REPORT")
        report.append("=" * 60)
        
        # Quest statistics
        if quest_scores:
            report.append("\nQUEST DATA:")
            avg_quest_score = sum(s for _, s in quest_scores) / len(quest_scores)
            report.append(f"  Total Quests: {len(quest_scores)}")
            report.append(f"  Average Score: {avg_quest_score:.1f}%")
            
            # Grade distribution
            grades = {'Excellent': 0, 'Good': 0, 'Acceptable': 0, 'Poor': 0, 'Incomplete': 0}
            for _, score in quest_scores:
                grades[self._get_grade(score)] += 1
            
            report.append("  Grade Distribution:")
            for grade, count in grades.items():
                pct = (count / len(quest_scores)) * 100
                report.append(f"    {grade}: {count} ({pct:.1f}%)")
            
            # Worst quests
            worst_quests = sorted(quest_scores, key=lambda x: x[1])[:5]
            if worst_quests:
                report.append("  Needs Attention (Lowest Scores):")
                for quest_id, score in worst_quests:
                    report.append(f"    Quest {quest_id}: {score:.1f}%")
        
        # NPC statistics
        if npc_scores:
            report.append("\nNPC DATA:")
            avg_npc_score = sum(s for _, s in npc_scores) / len(npc_scores)
            report.append(f"  Total NPCs: {len(npc_scores)}")
            report.append(f"  Average Score: {avg_npc_score:.1f}%")
            
            # Grade distribution
            grades = {'Excellent': 0, 'Good': 0, 'Acceptable': 0, 'Poor': 0, 'Incomplete': 0}
            for _, score in npc_scores:
                grades[self._get_grade(score)] += 1
            
            report.append("  Grade Distribution:")
            for grade, count in grades.items():
                pct = (count / len(npc_scores)) * 100
                report.append(f"    {grade}: {count} ({pct:.1f}%)")
            
            # Worst NPCs
            worst_npcs = sorted(npc_scores, key=lambda x: x[1])[:5]
            if worst_npcs:
                report.append("  Needs Attention (Lowest Scores):")
                for npc_id, score in worst_npcs:
                    report.append(f"    NPC {npc_id}: {score:.1f}%")
        
        # Overall summary
        report.append("\n" + "=" * 60)
        total_entries = len(quest_scores) + len(npc_scores)
        if total_entries > 0:
            overall_avg = (
                (sum(s for _, s in quest_scores) if quest_scores else 0) +
                (sum(s for _, s in npc_scores) if npc_scores else 0)
            ) / total_entries
            
            report.append(f"OVERALL COMPLETENESS: {overall_avg:.1f}% ({self._get_grade(overall_avg)})")
        
        return "\n".join(report)


def main():
    """Test the completeness scorer"""
    scorer = CompletenessScorer()
    
    # Test quest scoring
    test_quest = {
        'quest_id': 12345,
        'name': 'Test Quest',
        'startedBy': ([46834], None, None),
        'finishedBy': ([46718], None),
        'questLevel': 10,
        'requiredLevel': 8,
        'objectives': {
            'creatures': [{'npc_id': 100, 'count': 10}]
        },
        'objectivesText': ['Complete this test quest'],
        'zoneOrSort': 14,
    }
    
    score, breakdown = scorer.score_quest(test_quest)
    print(f"Quest Score: {score:.1f}%")
    print(f"Grade: {breakdown['grade']}")
    print(f"Suggestions: {breakdown['suggestions']}")
    
    # Test NPC scoring
    test_npc = {
        'npc_id': 46718,
        'name': 'Test NPC',
        'minLevel': 10,
        'maxLevel': 10,
        'spawns': {14: [[70.9, 45.9]]},
        'zoneID': 14,
        'friendlyToFaction': 'AH',
    }
    
    score, breakdown = scorer.score_npc(test_npc)
    print(f"\nNPC Score: {score:.1f}%")
    print(f"Grade: {breakdown['grade']}")
    print(f"Suggestions: {breakdown['suggestions']}")


if __name__ == "__main__":
    main()