#!/usr/bin/env python3
"""
Submission Tracker Module - Tracks all quest submissions for redundancy analysis
Maintains a database of who submitted what, when, and with what character
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

class SubmissionTracker:
    """
    Tracks all quest submissions to identify patterns and restrictions
    Uses SQLite for persistent storage and fast queries
    """
    
    def __init__(self, db_path: str = "submission_tracker.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._init_database()
        
    def _init_database(self):
        """Initialize database tables"""
        cursor = self.conn.cursor()
        
        # Main submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quest_id INTEGER NOT NULL,
                github_user TEXT NOT NULL,
                github_issue INTEGER,
                submission_date TEXT NOT NULL,
                addon_version TEXT,
                player_name TEXT,
                player_class TEXT,
                player_race TEXT,
                player_faction TEXT,
                player_level INTEGER,
                quest_giver_npc INTEGER,
                turn_in_npc INTEGER,
                zone_id INTEGER,
                zone_name TEXT,
                quest_level INTEGER,
                min_level INTEGER,
                quest_name TEXT,
                is_complete BOOLEAN DEFAULT 0,
                has_objectives BOOLEAN DEFAULT 0,
                raw_data TEXT,
                UNIQUE(quest_id, github_user, github_issue)
            )
        ''')
        
        # NPCs encountered table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submission_npcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER,
                npc_id INTEGER NOT NULL,
                npc_name TEXT,
                npc_role TEXT,  -- 'giver', 'turnin', 'objective', 'service'
                services TEXT,  -- JSON array of services
                FOREIGN KEY(submission_id) REFERENCES submissions(id)
            )
        ''')
        
        # Quest objectives table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submission_objectives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER,
                objective_type TEXT,  -- 'kill', 'collect', 'interact', 'explore'
                target_id INTEGER,
                target_name TEXT,
                quantity INTEGER,
                FOREIGN KEY(submission_id) REFERENCES submissions(id)
            )
        ''')
        
        # Create indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_quest_id ON submissions(quest_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_class ON submissions(player_class)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_faction ON submissions(player_faction)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_race ON submissions(player_race)')
        
        self.conn.commit()
    
    def record_submission(self, data: Dict) -> int:
        """
        Record a new submission in the database
        Returns the submission ID
        """
        cursor = self.conn.cursor()
        
        # Extract player info from various formats
        player_info = self._extract_player_info(data)
        
        # Insert main submission record
        cursor.execute('''
            INSERT OR REPLACE INTO submissions (
                quest_id, github_user, github_issue, submission_date, addon_version,
                player_name, player_class, player_race, player_faction, player_level,
                quest_giver_npc, turn_in_npc, zone_id, zone_name,
                quest_level, min_level, quest_name, is_complete, has_objectives, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('quest_id'),
            data.get('github_user', 'unknown'),
            data.get('github_issue'),
            data.get('submission_date', datetime.now().isoformat()),
            data.get('addon_version'),
            player_info['name'],
            player_info['class'],
            player_info['race'],
            player_info['faction'],
            player_info['level'],
            data.get('quest_giver_npc_id'),
            data.get('turn_in_npc_id'),
            data.get('zone_id'),
            data.get('zone_name'),
            data.get('quest_level'),
            data.get('min_level'),
            data.get('quest_name'),
            1 if data.get('turn_in_npc_id') else 0,
            1 if data.get('objectives') else 0,
            json.dumps(data)
        ))
        
        submission_id = cursor.lastrowid
        
        # Record NPCs if present
        if data.get('npcs'):
            for npc_id, npc_data in data['npcs'].items():
                cursor.execute('''
                    INSERT INTO submission_npcs (submission_id, npc_id, npc_name, npc_role, services)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    submission_id,
                    npc_id,
                    npc_data.get('name'),
                    npc_data.get('role'),
                    json.dumps(list(npc_data.get('services', [])))
                ))
        
        # Record objectives if present
        if data.get('objectives'):
            for obj in data['objectives']:
                cursor.execute('''
                    INSERT INTO submission_objectives (submission_id, objective_type, target_id, target_name, quantity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    submission_id,
                    obj.get('type'),
                    obj.get('target_id'),
                    obj.get('target_name'),
                    obj.get('quantity')
                ))
        
        self.conn.commit()
        return submission_id
    
    def _extract_player_info(self, data: Dict) -> Dict:
        """Extract player info from various submission formats"""
        info = {
            'name': None,
            'class': None,
            'race': None,
            'faction': None,
            'level': None
        }
        
        # Try to parse from "Player: Troll Priest (Horde) Level 60" format
        if data.get('player_string'):
            import re
            pattern = r'Player:\s*(?:(\w+)\s+)?(\w+)\s*\((\w+)\)\s*Level\s*(\d+)'
            match = re.search(pattern, data['player_string'])
            if match:
                info['race'] = match.group(1) if match.group(1) else None
                info['class'] = match.group(2)
                info['faction'] = match.group(3)
                info['level'] = int(match.group(4))
        
        # Override with explicit fields if present
        info.update({
            'name': data.get('player_name', info['name']),
            'class': data.get('player_class', info['class']),
            'race': data.get('player_race', info['race']),
            'faction': data.get('player_faction', info['faction']),
            'level': data.get('player_level', info['level'])
        })
        
        return info
    
    def analyze_quest_restrictions(self, quest_id: int) -> Dict:
        """
        Analyze all submissions for a quest to determine restrictions
        Returns detailed analysis with confidence scores
        """
        cursor = self.conn.cursor()
        
        # Get all submissions for this quest
        cursor.execute('''
            SELECT * FROM submissions WHERE quest_id = ?
        ''', (quest_id,))
        
        submissions = cursor.fetchall()
        
        if not submissions:
            return {'error': 'No submissions found for quest'}
        
        analysis = {
            'quest_id': quest_id,
            'quest_name': submissions[0]['quest_name'],
            'total_submissions': len(submissions),
            'unique_users': len(set(s['github_user'] for s in submissions)),
            'faction_analysis': self._analyze_faction(submissions),
            'class_analysis': self._analyze_class(submissions),
            'race_analysis': self._analyze_race(submissions),
            'level_analysis': self._analyze_level(submissions),
            'npc_consensus': self._analyze_npcs(cursor, quest_id),
            'confidence_score': 0
        }
        
        # Calculate overall confidence score
        analysis['confidence_score'] = self._calculate_confidence(analysis)
        
        return analysis
    
    def _analyze_faction(self, submissions: List) -> Dict:
        """Analyze faction restrictions"""
        factions = defaultdict(int)
        for s in submissions:
            if s['player_faction']:
                factions[s['player_faction']] += 1
        
        total = sum(factions.values())
        if total == 0:
            return {'restricted': False, 'confidence': 0}
        
        # If only one faction submitted, likely restricted
        if len(factions) == 1:
            faction = list(factions.keys())[0]
            return {
                'restricted': True,
                'faction': faction,
                'confidence': min(total / 3, 1.0),  # Higher confidence with more submissions
                'distribution': dict(factions)
            }
        
        # Check if heavily skewed (>90% one faction)
        for faction, count in factions.items():
            if count / total > 0.9:
                return {
                    'restricted': True,
                    'faction': faction,
                    'confidence': 0.7,
                    'distribution': dict(factions),
                    'note': 'Heavily skewed distribution suggests faction restriction'
                }
        
        return {
            'restricted': False,
            'confidence': min(total / 5, 1.0),
            'distribution': dict(factions)
        }
    
    def _analyze_class(self, submissions: List) -> Dict:
        """Analyze class restrictions"""
        classes = defaultdict(int)
        for s in submissions:
            if s['player_class']:
                classes[s['player_class'].upper()] += 1
        
        total = sum(classes.values())
        if total < 3:
            return {'restricted': False, 'confidence': 0.2, 'note': 'Insufficient data'}
        
        # If only one class and multiple submissions, likely restricted
        if len(classes) == 1 and total >= 3:
            class_name = list(classes.keys())[0]
            return {
                'restricted': True,
                'class': class_name,
                'confidence': min(total / 5, 0.95),
                'distribution': dict(classes)
            }
        
        # If 2-3 classes with many submissions, might be multi-class restricted
        if len(classes) <= 3 and total >= 10:
            return {
                'restricted': 'possibly',
                'classes': list(classes.keys()),
                'confidence': 0.6,
                'distribution': dict(classes),
                'note': f'Only {len(classes)} classes in {total} submissions'
            }
        
        return {
            'restricted': False,
            'confidence': min(total / 10, 0.9),
            'distribution': dict(classes)
        }
    
    def _analyze_race(self, submissions: List) -> Dict:
        """Analyze race restrictions"""
        races = defaultdict(int)
        for s in submissions:
            if s['player_race']:
                races[s['player_race']] += 1
        
        total = sum(races.values())
        if total < 5:
            return {'restricted': False, 'confidence': 0.1, 'note': 'Insufficient data'}
        
        # Check for single-race restriction
        if len(races) == 1 and total >= 3:
            return {
                'restricted': True,
                'race': list(races.keys())[0],
                'confidence': min(total / 5, 0.9),
                'distribution': dict(races)
            }
        
        return {
            'restricted': False,
            'confidence': min(total / 10, 0.8),
            'distribution': dict(races)
        }
    
    def _analyze_level(self, submissions: List) -> Dict:
        """Analyze level requirements"""
        levels = [s['player_level'] for s in submissions if s['player_level']]
        quest_levels = [s['quest_level'] for s in submissions if s['quest_level']]
        min_levels = [s['min_level'] for s in submissions if s['min_level']]
        
        analysis = {}
        
        if levels:
            analysis['player_level_range'] = (min(levels), max(levels))
            analysis['avg_player_level'] = sum(levels) / len(levels)
        
        if quest_levels:
            # Use most common quest level
            from collections import Counter
            level_counts = Counter(quest_levels)
            analysis['quest_level'] = level_counts.most_common(1)[0][0]
        
        if min_levels:
            # Use most common min level
            from collections import Counter
            min_counts = Counter(min_levels)
            analysis['min_level'] = min_counts.most_common(1)[0][0]
        
        return analysis
    
    def _analyze_npcs(self, cursor, quest_id: int) -> Dict:
        """Analyze NPC consensus for quest givers and turn-ins"""
        
        # Get quest giver consensus
        cursor.execute('''
            SELECT quest_giver_npc, COUNT(*) as count
            FROM submissions
            WHERE quest_id = ? AND quest_giver_npc IS NOT NULL
            GROUP BY quest_giver_npc
            ORDER BY count DESC
        ''', (quest_id,))
        
        givers = cursor.fetchall()
        
        # Get turn-in NPC consensus
        cursor.execute('''
            SELECT turn_in_npc, COUNT(*) as count
            FROM submissions
            WHERE quest_id = ? AND turn_in_npc IS NOT NULL
            GROUP BY turn_in_npc
            ORDER BY count DESC
        ''', (quest_id,))
        
        turnins = cursor.fetchall()
        
        analysis = {}
        
        if givers:
            total_giver_submissions = sum(g['count'] for g in givers)
            analysis['quest_giver'] = {
                'consensus_npc': givers[0]['quest_giver_npc'],
                'confidence': givers[0]['count'] / total_giver_submissions,
                'all_reported': {g['quest_giver_npc']: g['count'] for g in givers}
            }
        
        if turnins:
            total_turnin_submissions = sum(t['count'] for t in turnins)
            analysis['turn_in'] = {
                'consensus_npc': turnins[0]['turn_in_npc'],
                'confidence': turnins[0]['count'] / total_turnin_submissions,
                'all_reported': {t['turn_in_npc']: t['count'] for t in turnins}
            }
        
        return analysis
    
    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calculate overall confidence score for the analysis"""
        scores = []
        
        # Weight different factors
        if analysis['unique_users'] >= 5:
            scores.append(1.0)
        elif analysis['unique_users'] >= 3:
            scores.append(0.7)
        else:
            scores.append(0.3)
        
        # Factor in restriction confidence
        if 'faction_analysis' in analysis:
            scores.append(analysis['faction_analysis'].get('confidence', 0))
        
        if 'class_analysis' in analysis:
            scores.append(analysis['class_analysis'].get('confidence', 0))
        
        return sum(scores) / len(scores) if scores else 0
    
    def generate_restriction_report(self) -> str:
        """Generate a comprehensive report of likely quest restrictions"""
        cursor = self.conn.cursor()
        
        # Get all quests with multiple submissions
        cursor.execute('''
            SELECT quest_id, quest_name, COUNT(*) as submission_count, 
                   COUNT(DISTINCT github_user) as unique_users
            FROM submissions
            GROUP BY quest_id
            HAVING submission_count >= 3
            ORDER BY submission_count DESC
        ''')
        
        quests = cursor.fetchall()
        
        report = []
        report.append("="*80)
        report.append("QUEST RESTRICTION ANALYSIS REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("="*80)
        report.append("")
        
        faction_restricted = []
        class_restricted = []
        race_restricted = []
        
        for quest in quests:
            analysis = self.analyze_quest_restrictions(quest['quest_id'])
            
            # Check for restrictions
            if analysis['faction_analysis'].get('restricted'):
                faction_restricted.append(analysis)
            
            if analysis['class_analysis'].get('restricted'):
                class_restricted.append(analysis)
            
            if analysis['race_analysis'].get('restricted'):
                race_restricted.append(analysis)
        
        # Report faction restrictions
        if faction_restricted:
            report.append("\n📍 FACTION-SPECIFIC QUESTS")
            report.append("-" * 40)
            for q in sorted(faction_restricted, key=lambda x: x['confidence_score'], reverse=True):
                faction = q['faction_analysis']['faction']
                confidence = q['faction_analysis']['confidence']
                report.append(f"  [{q['quest_id']}] {q['quest_name']}")
                report.append(f"    → {faction} only (confidence: {confidence:.1%})")
                report.append(f"    → Submissions: {q['total_submissions']} from {q['unique_users']} users")
        
        # Report class restrictions
        if class_restricted:
            report.append("\n🎯 CLASS-SPECIFIC QUESTS")
            report.append("-" * 40)
            for q in sorted(class_restricted, key=lambda x: x['confidence_score'], reverse=True):
                class_info = q['class_analysis']
                if class_info.get('class'):
                    report.append(f"  [{q['quest_id']}] {q['quest_name']}")
                    report.append(f"    → {class_info['class']} only (confidence: {class_info['confidence']:.1%})")
                    report.append(f"    → Distribution: {class_info['distribution']}")
        
        # Report race restrictions
        if race_restricted:
            report.append("\n🏃 RACE-SPECIFIC QUESTS")
            report.append("-" * 40)
            for q in sorted(race_restricted, key=lambda x: x['confidence_score'], reverse=True):
                race_info = q['race_analysis']
                report.append(f"  [{q['quest_id']}] {q['quest_name']}")
                report.append(f"    → {race_info['race']} only (confidence: {race_info['confidence']:.1%})")
        
        # Summary statistics
        report.append("\n" + "="*80)
        report.append("SUMMARY STATISTICS")
        report.append("-" * 40)
        
        cursor.execute('SELECT COUNT(DISTINCT quest_id) FROM submissions')
        total_quests = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT github_user) FROM submissions')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM submissions')
        total_submissions = cursor.fetchone()[0]
        
        report.append(f"Total unique quests: {total_quests}")
        report.append(f"Total unique contributors: {total_users}")
        report.append(f"Total submissions: {total_submissions}")
        report.append(f"Faction-restricted quests: {len(faction_restricted)}")
        report.append(f"Class-restricted quests: {len(class_restricted)}")
        report.append(f"Race-restricted quests: {len(race_restricted)}")
        
        return "\n".join(report)
    
    def close(self):
        """Close database connection"""
        self.conn.close()

def main():
    """Test the submission tracker"""
    tracker = SubmissionTracker("test_tracker.db")
    
    # Test data
    test_submissions = [
        {
            'quest_id': 12345,
            'quest_name': 'Hunter Training',
            'github_user': 'user1',
            'github_issue': 100,
            'player_class': 'HUNTER',
            'player_faction': 'Alliance',
            'quest_giver_npc_id': 456,
            'turn_in_npc_id': 789
        },
        {
            'quest_id': 12345,
            'quest_name': 'Hunter Training',
            'github_user': 'user2',
            'github_issue': 101,
            'player_class': 'HUNTER',
            'player_faction': 'Alliance',
            'quest_giver_npc_id': 456,
            'turn_in_npc_id': 789
        },
        {
            'quest_id': 12345,
            'quest_name': 'Hunter Training',
            'github_user': 'user3',
            'github_issue': 102,
            'player_class': 'HUNTER',
            'player_faction': 'Horde',
            'quest_giver_npc_id': 456,
            'turn_in_npc_id': 789
        },
        {
            'quest_id': 67890,
            'quest_name': 'Alliance Duty',
            'github_user': 'user1',
            'github_issue': 103,
            'player_class': 'WARRIOR',
            'player_faction': 'Alliance',
            'quest_giver_npc_id': 111,
            'turn_in_npc_id': 222
        },
        {
            'quest_id': 67890,
            'quest_name': 'Alliance Duty',
            'github_user': 'user4',
            'github_issue': 104,
            'player_class': 'PRIEST',
            'player_faction': 'Alliance',
            'quest_giver_npc_id': 111,
            'turn_in_npc_id': 222
        }
    ]
    
    # Record test submissions
    for sub in test_submissions:
        tracker.record_submission(sub)
    
    # Analyze restrictions
    print("\nAnalyzing Quest 12345 (Hunter Training):")
    print(json.dumps(tracker.analyze_quest_restrictions(12345), indent=2))
    
    print("\nAnalyzing Quest 67890 (Alliance Duty):")
    print(json.dumps(tracker.analyze_quest_restrictions(67890), indent=2))
    
    # Generate report
    print("\n" + tracker.generate_restriction_report())
    
    tracker.close()

if __name__ == "__main__":
    main()