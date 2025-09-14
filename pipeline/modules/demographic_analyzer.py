#!/usr/bin/env python3
"""
Demographic Analyzer - Analyze patterns across submitters
Statistical analysis of quest submissions by demographics
"""

import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime
import statistics


class DemographicAnalyzer:
    """
    Analyzes demographic patterns in quest submissions
    Provides insights into submitter patterns and data quality
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.submissions = []
        
        # Race and class mappings
        self.races = {
            # Alliance
            'Human': {'faction': 'Alliance', 'id': 1},
            'Dwarf': {'faction': 'Alliance', 'id': 2},
            'Night Elf': {'faction': 'Alliance', 'id': 4},
            'Gnome': {'faction': 'Alliance', 'id': 8},
            'Draenei': {'faction': 'Alliance', 'id': 16},
            # Horde
            'Orc': {'faction': 'Horde', 'id': 32},
            'Undead': {'faction': 'Horde', 'id': 64},
            'Tauren': {'faction': 'Horde', 'id': 128},
            'Troll': {'faction': 'Horde', 'id': 256},
            'Blood Elf': {'faction': 'Horde', 'id': 512},
        }
        
        self.classes = {
            'Warrior': {'id': 1},
            'Paladin': {'id': 2},
            'Hunter': {'id': 4},
            'Rogue': {'id': 8},
            'Priest': {'id': 16},
            'Death Knight': {'id': 32},
            'Shaman': {'id': 64},
            'Mage': {'id': 128},
            'Warlock': {'id': 256},
            'Druid': {'id': 1024},
        }
    
    def analyze(self, submissions: List[Dict]) -> Dict:
        """
        Analyze demographic patterns in submissions
        
        Args:
            submissions: List of submission data with metadata
            
        Returns:
            Analysis results
        """
        self.submissions = submissions
        
        analysis = {
            'total_submissions': len(submissions),
            'unique_submitters': self._count_unique_submitters(),
            'faction_distribution': self._analyze_faction_distribution(),
            'race_distribution': self._analyze_race_distribution(),
            'class_distribution': self._analyze_class_distribution(),
            'level_distribution': self._analyze_level_distribution(),
            'zone_distribution': self._analyze_zone_distribution(),
            'submission_patterns': self._analyze_submission_patterns(),
            'data_quality_by_demographic': self._analyze_quality_by_demographic(),
            'insights': [],
        }
        
        # Generate insights
        analysis['insights'] = self._generate_insights(analysis)
        
        return analysis
    
    def _count_unique_submitters(self) -> int:
        """Count unique submitters"""
        submitters = set()
        
        for submission in self.submissions:
            metadata = submission.get('metadata', {})
            github_user = metadata.get('github_user')
            if github_user:
                submitters.add(github_user)
            
            # Also count by character if available
            char_name = metadata.get('character_name')
            if char_name:
                submitters.add(f"char_{char_name}")
        
        return len(submitters)
    
    def _analyze_faction_distribution(self) -> Dict:
        """Analyze faction distribution"""
        faction_counts = Counter()
        faction_quests = defaultdict(list)
        
        for submission in self.submissions:
            metadata = submission.get('metadata', {})
            faction = metadata.get('faction')
            
            if not faction:
                # Try to infer from race
                race = metadata.get('race')
                if race and race in self.races:
                    faction = self.races[race]['faction']
            
            if faction:
                faction_counts[faction] += 1
                quest_id = submission.get('quest_id')
                if quest_id:
                    faction_quests[faction].append(quest_id)
        
        total = sum(faction_counts.values())
        distribution = {}
        
        for faction, count in faction_counts.items():
            distribution[faction] = {
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0,
                'unique_quests': len(set(faction_quests[faction])),
            }
        
        return distribution
    
    def _analyze_race_distribution(self) -> Dict:
        """Analyze race distribution"""
        race_counts = Counter()
        race_levels = defaultdict(list)
        
        for submission in self.submissions:
            metadata = submission.get('metadata', {})
            race = metadata.get('race')
            level = metadata.get('level')
            
            if race:
                race_counts[race] += 1
                if level:
                    race_levels[race].append(level)
        
        distribution = {}
        total = sum(race_counts.values())
        
        for race, count in race_counts.items():
            levels = race_levels[race]
            distribution[race] = {
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0,
                'average_level': statistics.mean(levels) if levels else 0,
                'level_range': (min(levels), max(levels)) if levels else (0, 0),
            }
        
        return distribution
    
    def _analyze_class_distribution(self) -> Dict:
        """Analyze class distribution"""
        class_counts = Counter()
        class_levels = defaultdict(list)
        
        for submission in self.submissions:
            metadata = submission.get('metadata', {})
            char_class = metadata.get('class')
            level = metadata.get('level')
            
            if char_class:
                class_counts[char_class] += 1
                if level:
                    class_levels[char_class].append(level)
        
        distribution = {}
        total = sum(class_counts.values())
        
        for char_class, count in class_counts.items():
            levels = class_levels[char_class]
            distribution[char_class] = {
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0,
                'average_level': statistics.mean(levels) if levels else 0,
            }
        
        return distribution
    
    def _analyze_level_distribution(self) -> Dict:
        """Analyze level distribution"""
        level_ranges = {
            '1-10': [],
            '11-20': [],
            '21-30': [],
            '31-40': [],
            '41-50': [],
            '51-60': [],
            '61-70': [],
            '71-80': [],
            '81-85': [],
        }
        
        for submission in self.submissions:
            metadata = submission.get('metadata', {})
            level = metadata.get('level')
            
            if level:
                if level <= 10:
                    level_ranges['1-10'].append(submission)
                elif level <= 20:
                    level_ranges['11-20'].append(submission)
                elif level <= 30:
                    level_ranges['21-30'].append(submission)
                elif level <= 40:
                    level_ranges['31-40'].append(submission)
                elif level <= 50:
                    level_ranges['41-50'].append(submission)
                elif level <= 60:
                    level_ranges['51-60'].append(submission)
                elif level <= 70:
                    level_ranges['61-70'].append(submission)
                elif level <= 80:
                    level_ranges['71-80'].append(submission)
                else:
                    level_ranges['81-85'].append(submission)
        
        distribution = {}
        total = len(self.submissions)
        
        for range_name, submissions in level_ranges.items():
            distribution[range_name] = {
                'count': len(submissions),
                'percentage': (len(submissions) / total * 100) if total > 0 else 0,
            }
        
        return distribution
    
    def _analyze_zone_distribution(self) -> Dict:
        """Analyze zone distribution"""
        zone_counts = Counter()
        zone_factions = defaultdict(Counter)
        
        for submission in self.submissions:
            zone = submission.get('zone')
            metadata = submission.get('metadata', {})
            faction = metadata.get('faction')
            
            if zone:
                zone_counts[zone] += 1
                if faction:
                    zone_factions[zone][faction] += 1
        
        distribution = {}
        
        for zone, count in zone_counts.most_common(10):  # Top 10 zones
            factions = zone_factions[zone]
            distribution[zone] = {
                'count': count,
                'alliance_submissions': factions.get('Alliance', 0),
                'horde_submissions': factions.get('Horde', 0),
            }
        
        return distribution
    
    def _analyze_submission_patterns(self) -> Dict:
        """Analyze submission patterns"""
        patterns = {
            'submissions_per_user': {},
            'most_active_submitters': [],
            'submission_times': [],
            'average_data_completeness': 0,
        }
        
        # Count submissions per user
        user_submissions = Counter()
        user_quality = defaultdict(list)
        
        for submission in self.submissions:
            metadata = submission.get('metadata', {})
            github_user = metadata.get('github_user')
            quality_score = submission.get('quality_score', 0)
            
            if github_user:
                user_submissions[github_user] += 1
                user_quality[github_user].append(quality_score)
        
        # Get most active submitters
        patterns['most_active_submitters'] = [
            {
                'user': user,
                'submissions': count,
                'avg_quality': statistics.mean(user_quality[user]) if user_quality[user] else 0,
            }
            for user, count in user_submissions.most_common(5)
        ]
        
        # Submission distribution
        submission_counts = list(user_submissions.values())
        if submission_counts:
            patterns['submissions_per_user'] = {
                'average': statistics.mean(submission_counts),
                'median': statistics.median(submission_counts),
                'max': max(submission_counts),
                'min': min(submission_counts),
            }
        
        return patterns
    
    def _analyze_quality_by_demographic(self) -> Dict:
        """Analyze data quality by demographic groups"""
        quality = {
            'by_faction': defaultdict(list),
            'by_level_range': defaultdict(list),
            'by_race': defaultdict(list),
            'by_class': defaultdict(list),
        }
        
        for submission in self.submissions:
            metadata = submission.get('metadata', {})
            score = submission.get('quality_score', 0)
            
            # By faction
            faction = metadata.get('faction')
            if faction:
                quality['by_faction'][faction].append(score)
            
            # By level range
            level = metadata.get('level')
            if level:
                if level <= 20:
                    quality['by_level_range']['1-20'].append(score)
                elif level <= 40:
                    quality['by_level_range']['21-40'].append(score)
                elif level <= 60:
                    quality['by_level_range']['41-60'].append(score)
                else:
                    quality['by_level_range']['61-85'].append(score)
            
            # By race
            race = metadata.get('race')
            if race:
                quality['by_race'][race].append(score)
            
            # By class
            char_class = metadata.get('class')
            if char_class:
                quality['by_class'][char_class].append(score)
        
        # Calculate averages
        results = {}
        
        for category in ['by_faction', 'by_level_range', 'by_race', 'by_class']:
            results[category] = {}
            for group, scores in quality[category].items():
                if scores:
                    results[category][group] = {
                        'average_score': statistics.mean(scores),
                        'median_score': statistics.median(scores),
                        'submission_count': len(scores),
                    }
        
        return results
    
    def _generate_insights(self, analysis: Dict) -> List[str]:
        """Generate insights from analysis"""
        insights = []
        
        # Faction balance insight
        faction_dist = analysis['faction_distribution']
        if 'Alliance' in faction_dist and 'Horde' in faction_dist:
            alliance_pct = faction_dist['Alliance']['percentage']
            horde_pct = faction_dist['Horde']['percentage']
            
            if abs(alliance_pct - horde_pct) > 20:
                dominant = 'Alliance' if alliance_pct > horde_pct else 'Horde'
                insights.append(
                    f"Significant faction imbalance: {dominant} has "
                    f"{max(alliance_pct, horde_pct):.1f}% of submissions"
                )
        
        # Level distribution insight
        level_dist = analysis['level_distribution']
        low_level = level_dist.get('1-10', {}).get('percentage', 0) + \
                   level_dist.get('11-20', {}).get('percentage', 0)
        
        if low_level > 50:
            insights.append(
                f"Majority of submissions ({low_level:.1f}%) are from "
                "low-level characters (1-20)"
            )
        
        # Active submitter insight
        patterns = analysis['submission_patterns']
        if patterns['most_active_submitters']:
            top_submitter = patterns['most_active_submitters'][0]
            insights.append(
                f"Most active submitter: {top_submitter['user']} with "
                f"{top_submitter['submissions']} submissions"
            )
        
        # Quality insight
        quality = analysis['data_quality_by_demographic']
        if quality.get('by_faction'):
            faction_quality = quality['by_faction']
            for faction, stats in faction_quality.items():
                if stats['average_score'] < 60:
                    insights.append(
                        f"{faction} submissions have low average quality "
                        f"({stats['average_score']:.1f}%)"
                    )
        
        # Zone concentration insight
        zone_dist = analysis['zone_distribution']
        if zone_dist:
            top_zone = list(zone_dist.keys())[0]
            top_count = zone_dist[top_zone]['count']
            total = analysis['total_submissions']
            
            if total > 0:
                zone_pct = (top_count / total) * 100
                if zone_pct > 15:
                    insights.append(
                        f"High concentration in {top_zone}: "
                        f"{zone_pct:.1f}% of all submissions"
                    )
        
        return insights
    
    def generate_report(self, analysis: Dict) -> str:
        """Generate human-readable demographic report"""
        lines = []
        lines.append("=" * 70)
        lines.append("DEMOGRAPHIC ANALYSIS REPORT")
        lines.append("=" * 70)
        
        # Overview
        lines.append(f"\nTotal Submissions: {analysis['total_submissions']}")
        lines.append(f"Unique Submitters: {analysis['unique_submitters']}")
        
        # Faction distribution
        lines.append("\n--- Faction Distribution ---")
        for faction, stats in analysis['faction_distribution'].items():
            lines.append(f"  {faction}: {stats['count']} ({stats['percentage']:.1f}%)")
            lines.append(f"    Unique quests: {stats['unique_quests']}")
        
        # Race distribution
        lines.append("\n--- Top Races ---")
        race_sorted = sorted(
            analysis['race_distribution'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        for race, stats in race_sorted:
            lines.append(f"  {race}: {stats['count']} ({stats['percentage']:.1f}%)")
            lines.append(f"    Avg level: {stats['average_level']:.1f}")
        
        # Class distribution
        lines.append("\n--- Top Classes ---")
        class_sorted = sorted(
            analysis['class_distribution'].items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:5]
        
        for char_class, stats in class_sorted:
            lines.append(f"  {char_class}: {stats['count']} ({stats['percentage']:.1f}%)")
        
        # Level distribution
        lines.append("\n--- Level Distribution ---")
        for range_name, stats in analysis['level_distribution'].items():
            if stats['count'] > 0:
                lines.append(f"  {range_name}: {stats['count']} ({stats['percentage']:.1f}%)")
        
        # Top submitters
        patterns = analysis['submission_patterns']
        if patterns['most_active_submitters']:
            lines.append("\n--- Most Active Submitters ---")
            for submitter in patterns['most_active_submitters']:
                lines.append(
                    f"  {submitter['user']}: {submitter['submissions']} submissions "
                    f"(avg quality: {submitter['avg_quality']:.1f}%)"
                )
        
        # Insights
        if analysis['insights']:
            lines.append("\n--- Key Insights ---")
            for insight in analysis['insights']:
                lines.append(f"  • {insight}")
        
        return '\n'.join(lines)


def main():
    """Test the demographic analyzer"""
    analyzer = DemographicAnalyzer()
    
    # Test data
    test_submissions = [
        {
            'quest_id': 12345,
            'zone': 'Elwynn Forest',
            'quality_score': 85,
            'metadata': {
                'github_user': 'player1',
                'character_name': 'TestChar',
                'race': 'Human',
                'class': 'Warrior',
                'faction': 'Alliance',
                'level': 15,
            }
        },
        {
            'quest_id': 12346,
            'zone': 'Durotar',
            'quality_score': 72,
            'metadata': {
                'github_user': 'player2',
                'character_name': 'OrcHunter',
                'race': 'Orc',
                'class': 'Hunter',
                'faction': 'Horde',
                'level': 12,
            }
        },
        {
            'quest_id': 12347,
            'zone': 'Elwynn Forest',
            'quality_score': 90,
            'metadata': {
                'github_user': 'player1',  # Same user, different submission
                'character_name': 'TestChar',
                'race': 'Human',
                'class': 'Warrior',
                'faction': 'Alliance',
                'level': 16,
            }
        },
    ]
    
    # Analyze
    analysis = analyzer.analyze(test_submissions)
    
    # Generate report
    report = analyzer.generate_report(analysis)
    print(report)


if __name__ == "__main__":
    main()