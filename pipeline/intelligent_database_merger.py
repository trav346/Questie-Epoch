#!/usr/bin/env python3
"""
Intelligent Database Merger
Handles deduplication, scoring, and smart merging of quest data
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import shutil

class QuestScorer:
    """Scores quest completeness for comparison"""
    
    @staticmethod
    def score_quest(quest_data: Dict) -> Tuple[int, Dict]:
        """
        Score a quest's completeness from 0-100
        Returns (score, breakdown)
        """
        score = 0
        breakdown = {
            'name_quality': 0,
            'npc_data': 0,
            'objectives': 0,
            'zone_data': 0,
            'level_data': 0,
            'details': []
        }
        
        # Name quality (20 points)
        name = quest_data.get('name', '')
        if name and not name.startswith('[Epoch]'):
            score += 10
            breakdown['name_quality'] += 10
            breakdown['details'].append("Has proper name")
        
        if name and '[Needs data collection]' not in name and 'PLACEHOLDER' not in name.upper():
            score += 10
            breakdown['name_quality'] += 10
            breakdown['details'].append("Name is not placeholder")
        
        # NPC data (20 points)
        started_by = quest_data.get('startedBy', {})
        if started_by and (started_by.get('npcs') or started_by.get('items') or started_by.get('objects')):
            score += 10
            breakdown['npc_data'] += 10
            breakdown['details'].append("Has quest giver")
        
        finished_by = quest_data.get('finishedBy', {})
        if finished_by and (finished_by.get('npcs') or finished_by.get('objects')):
            score += 10
            breakdown['npc_data'] += 10
            breakdown['details'].append("Has turn-in NPC")
        
        # Objectives (30 points)
        objectives = quest_data.get('objectives', {})
        objectives_text = quest_data.get('objectivesText', [])
        
        if objectives:
            has_real_objectives = False
            
            # Check for actual objective data
            if objectives.get('items') or objectives.get('creatures') or objectives.get('objects'):
                has_real_objectives = True
                score += 20
                breakdown['objectives'] += 20
                breakdown['details'].append("Has objective items/creatures/objects")
            
            # Bonus for objectives text
            if objectives_text and objectives_text != ["[Needs data collection]"]:
                score += 10
                breakdown['objectives'] += 10
                breakdown['details'].append("Has objectives text")
        elif objectives_text and objectives_text != ["[Needs data collection]"]:
            # Has text but no objectives data
            score += 10
            breakdown['objectives'] += 10
            breakdown['details'].append("Has objectives text only")
        
        # Zone data (15 points)
        zone = quest_data.get('zoneOrSort')
        if zone and zone != 85 and zone != 0:  # 85 was the buggy zone
            score += 15
            breakdown['zone_data'] = 15
            breakdown['details'].append(f"Has valid zone: {zone}")
        elif zone == 85:
            breakdown['details'].append("Has buggy zone 85")
        
        # Level data (15 points)
        quest_level = quest_data.get('questLevel')
        if quest_level and quest_level > 0:
            score += 10
            breakdown['level_data'] += 10
            breakdown['details'].append(f"Has quest level: {quest_level}")
        
        required_level = quest_data.get('requiredLevel')
        if required_level and required_level > 0:
            score += 5
            breakdown['level_data'] += 5
            breakdown['details'].append(f"Has required level: {required_level}")
        
        return score, breakdown


class IntelligentDatabaseMerger:
    """Handles deduplication and intelligent merging of quest database"""
    
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.scorer = QuestScorer()
        self.existing_quests = {}
        self.duplicates = {}
        
    def load_database(self) -> Dict:
        """Load and parse existing database, tracking duplicates"""
        if not self.database_path.exists():
            print(f"❌ Database not found: {self.database_path}")
            return {}
        
        with open(self.database_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        quests = {}
        duplicates = {}
        
        for line_num, line in enumerate(lines, 1):
            # Match quest entries
            match = re.match(r'^\[(\d+)\]\s*=\s*\{(.*)\},?\s*(?:--.*)?$', line.strip())
            if match:
                quest_id = match.group(1)
                quest_data_str = match.group(2)
                
                # Parse quest data
                quest_data = self.parse_lua_quest_line(quest_id, quest_data_str)
                quest_data['_line_num'] = line_num
                quest_data['_raw_line'] = line
                
                if quest_id in quests:
                    # Track duplicate
                    if quest_id not in duplicates:
                        duplicates[quest_id] = [quests[quest_id]]
                    duplicates[quest_id].append(quest_data)
                else:
                    quests[quest_id] = quest_data
        
        self.existing_quests = quests
        self.duplicates = duplicates
        
        print(f"📚 Loaded {len(quests)} unique quests")
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} quest IDs with duplicates")
            total_dups = sum(len(dups) for dups in duplicates.values())
            print(f"    Total duplicate entries: {total_dups}")
        
        return quests
    
    def parse_lua_quest_line(self, quest_id: str, lua_str: str) -> Dict:
        """Parse a single-line Lua quest entry"""
        quest = {'id': quest_id}
        
        # Extract name (first quoted string)
        name_match = re.search(r'"([^"\\]*(?:\\.[^"\\]*)*)"', lua_str)
        if name_match:
            quest['name'] = name_match.group(1).replace('\\"', '"')
        
        # Check for placeholder indicators
        if '[Needs data collection]' in lua_str:
            quest['has_placeholder'] = True
        
        # Extract startedBy (simplified check)
        if '{{' in lua_str[:lua_str.find(',') * 3] if ',' in lua_str else lua_str:
            quest['startedBy'] = {'npcs': ['parsed']}  # Simplified for scoring
        
        # Extract zone (field 17)
        fields = self.split_lua_fields(lua_str)
        if len(fields) > 16:
            try:
                zone = int(fields[16]) if fields[16] != 'nil' else None
                if zone:
                    quest['zoneOrSort'] = zone
            except:
                pass
        
        # Extract levels (fields 4 and 5)
        if len(fields) > 4:
            try:
                quest_level = int(fields[4]) if fields[4] != 'nil' else None
                if quest_level:
                    quest['questLevel'] = quest_level
            except:
                pass
        
        return quest
    
    def split_lua_fields(self, lua_str: str) -> List[str]:
        """Split Lua fields respecting nested structures"""
        fields = []
        current = []
        depth = 0
        in_string = False
        escape_next = False
        
        for char in lua_str:
            if escape_next:
                current.append(char)
                escape_next = False
                continue
                
            if char == '\\' and in_string:
                escape_next = True
                current.append(char)
            elif char == '"' and not escape_next:
                in_string = not in_string
                current.append(char)
            elif char == '{' and not in_string:
                depth += 1
                current.append(char)
            elif char == '}' and not in_string:
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0 and not in_string:
                fields.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        
        if current:
            fields.append(''.join(current).strip())
        
        return fields
    
    def deduplicate_database(self) -> List[str]:
        """Remove duplicates, keeping the best version"""
        if not self.duplicates:
            print("✅ No duplicates to remove")
            return []
        
        print(f"\n🔧 Deduplicating {len(self.duplicates)} quest IDs...")
        
        lines_to_remove = []
        decisions = []
        
        for quest_id, duplicate_entries in self.duplicates.items():
            # Score each duplicate
            scores = []
            for entry in duplicate_entries:
                score, breakdown = self.scorer.score_quest(entry)
                scores.append((score, entry, breakdown))
            
            # Also score the original
            if quest_id in self.existing_quests:
                original = self.existing_quests[quest_id]
                score, breakdown = self.scorer.score_quest(original)
                scores.append((score, original, breakdown))
            
            # Sort by score (highest first)
            scores.sort(key=lambda x: x[0], reverse=True)
            
            # Keep the best, mark others for removal
            best_score, best_entry, best_breakdown = scores[0]
            
            decision = {
                'quest_id': quest_id,
                'name': best_entry.get('name', 'Unknown'),
                'kept_score': best_score,
                'kept_line': best_entry.get('_line_num'),
                'removed_lines': []
            }
            
            for score, entry, breakdown in scores[1:]:
                lines_to_remove.append(entry.get('_line_num'))
                decision['removed_lines'].append({
                    'line': entry.get('_line_num'),
                    'score': score
                })
            
            decisions.append(decision)
            
            # Update the main dict with the best version
            self.existing_quests[quest_id] = best_entry
        
        # Report
        print(f"\n📊 Deduplication Decisions:")
        for decision in decisions[:5]:  # Show first 5
            print(f"  Quest {decision['quest_id']}: {decision['name']}")
            print(f"    Kept line {decision['kept_line']} (score: {decision['kept_score']})")
            for removed in decision['removed_lines']:
                print(f"    Removed line {removed['line']} (score: {removed['score']})")
        
        if len(decisions) > 5:
            print(f"  ... and {len(decisions) - 5} more")
        
        return lines_to_remove
    
    def merge_with_pipeline_data(self, pipeline_data: Dict) -> Dict:
        """Intelligently merge pipeline data with existing database"""
        merge_plan = {
            'replace': [],      # Pipeline version is better
            'skip': [],         # Database version is better
            'add_new': [],      # Doesn't exist in database
            'merge_fields': []  # Combine best of both
        }
        
        pipeline_quests = pipeline_data.get('quests', {})
        
        print(f"\n🔍 Comparing {len(pipeline_quests)} pipeline quests with database...")
        
        for quest_id, pipeline_quest in pipeline_quests.items():
            if quest_id in self.existing_quests:
                # Quest exists - compare and decide
                db_quest = self.existing_quests[quest_id]
                
                db_score, db_breakdown = self.scorer.score_quest(db_quest)
                pipeline_score, pipeline_breakdown = self.scorer.score_quest(pipeline_quest)
                
                # Decision logic
                if db_quest.get('has_placeholder') or db_quest.get('name', '').startswith('[Epoch]'):
                    # Always replace placeholders
                    merge_plan['replace'].append({
                        'id': quest_id,
                        'reason': 'Database has placeholder',
                        'db_score': db_score,
                        'pipeline_score': pipeline_score
                    })
                elif pipeline_score > db_score + 10:  # Significantly better
                    merge_plan['replace'].append({
                        'id': quest_id,
                        'reason': f'Pipeline better ({pipeline_score} vs {db_score})',
                        'db_score': db_score,
                        'pipeline_score': pipeline_score
                    })
                elif db_score > pipeline_score + 10:  # Database significantly better
                    merge_plan['skip'].append({
                        'id': quest_id,
                        'reason': f'Database better ({db_score} vs {pipeline_score})',
                        'db_score': db_score,
                        'pipeline_score': pipeline_score
                    })
                else:
                    # Similar scores - merge best fields
                    merge_plan['merge_fields'].append({
                        'id': quest_id,
                        'reason': f'Similar scores ({pipeline_score} vs {db_score})',
                        'db_score': db_score,
                        'pipeline_score': pipeline_score,
                        'merge_strategy': self.determine_merge_strategy(db_quest, pipeline_quest, 
                                                                       db_breakdown, pipeline_breakdown)
                    })
            else:
                # New quest
                merge_plan['add_new'].append({
                    'id': quest_id,
                    'name': pipeline_quest.get('name', 'Unknown')
                })
        
        # Report
        print(f"\n📊 Merge Plan Summary:")
        print(f"  ➕ Add new: {len(merge_plan['add_new'])} quests")
        print(f"  🔄 Replace: {len(merge_plan['replace'])} quests") 
        print(f"  🔀 Merge fields: {len(merge_plan['merge_fields'])} quests")
        print(f"  ⏭️  Skip: {len(merge_plan['skip'])} quests")
        
        return merge_plan
    
    def determine_merge_strategy(self, db_quest: Dict, pipeline_quest: Dict, 
                                db_breakdown: Dict, pipeline_breakdown: Dict) -> Dict:
        """Determine how to merge two quests with similar scores"""
        strategy = {
            'use_name_from': 'pipeline' if pipeline_breakdown['name_quality'] >= db_breakdown['name_quality'] else 'database',
            'use_npcs_from': 'merge',  # Usually merge NPCs
            'use_objectives_from': 'pipeline' if pipeline_breakdown['objectives'] > db_breakdown['objectives'] else 'database',
            'use_zone_from': 'pipeline' if pipeline_breakdown['zone_data'] > db_breakdown['zone_data'] else 'database',
            'use_levels_from': 'pipeline' if pipeline_breakdown['level_data'] >= db_breakdown['level_data'] else 'database'
        }
        return strategy


def main():
    """Test the intelligent merger"""
    print("="*60)
    print("INTELLIGENT DATABASE MERGER")
    print("="*60)
    
    # Update this path to your Questie installation
    db_path = Path("../Database/Epoch/epochQuestDB.lua")
    
    merger = IntelligentDatabaseMerger(db_path)
    
    # Load and analyze database
    merger.load_database()
    
    # If duplicates exist, plan deduplication
    if merger.duplicates:
        lines_to_remove = merger.deduplicate_database()
        print(f"\n💡 Would remove {len(lines_to_remove)} duplicate lines")
    
    # Load pipeline data for comparison
    pipeline_file = Path("aggregated_data/complete_pipeline_results.json")
    if pipeline_file.exists():
        with open(pipeline_file, 'r') as f:
            pipeline_data = json.load(f)
        
        merge_plan = merger.merge_with_pipeline_data(pipeline_data)
        
        # Save merge plan
        with open('merge_plan.json', 'w') as f:
            json.dump(merge_plan, f, indent=2)
        
        print(f"\n📄 Merge plan saved to merge_plan.json")
    else:
        print(f"\n⚠️ Pipeline data not found")

if __name__ == "__main__":
    main()