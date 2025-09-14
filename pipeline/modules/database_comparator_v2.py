#!/usr/bin/env python3
"""
Database Comparator Module V2
Compares filtered quest data against existing epochQuestDB to determine what needs updating.
Works with the complete pipeline after consensus filtering.
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime

class DatabaseComparatorV2:
    """Compare filtered quests with existing database to determine changes needed"""
    
    def __init__(self, database_path: Optional[Path] = None):
        """
        Initialize the comparator with database path
        
        Args:
            database_path: Path to epochQuestDB.lua file
        """
        if database_path is None:
            # Default path relative to pipeline - update to your Questie installation
            self.database_path = Path("../../Database/Epoch/epochQuestDB.lua")
        else:
            self.database_path = Path(database_path)
        
        # Load existing database
        self.existing_db = self.load_existing_database()
        
        # Comparison result categories
        self.categories = {
            'new_quests': [],           # Don't exist in DB at all
            'runtime_stubs': [],        # Exist as [Epoch] stubs needing data  
            'better_data': [],          # Our data is more complete
            'missing_objectives': [],   # DB missing objectives we have
            'missing_npcs': [],         # DB missing quest giver/turn-in NPCs
            'missing_coordinates': [],  # DB missing spawn coordinates
            'identical': [],            # No changes needed
            'inferior': [],             # DB has better data than us
            'conflicts': []             # Different data that needs resolution
        }
        
    def load_existing_database(self) -> Dict:
        """
        Load and parse the existing epochQuestDB.lua file
        
        Returns:
            Dictionary of quest_id -> quest_data
        """
        if not self.database_path.exists():
            print(f"⚠️ Database not found at {self.database_path}")
            return {}
        
        existing_quests = {}
        
        with open(self.database_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse Lua table entries
        # Pattern matches [questId] = {data...} including nested tables
        pattern = r'\[(\d+)\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}'
        
        for match in re.finditer(pattern, content):
            quest_id = match.group(1)
            quest_data_str = match.group(2)
            
            # Parse the quest data
            quest_data = self.parse_lua_quest(quest_id, quest_data_str)
            if quest_data:
                existing_quests[quest_id] = quest_data
        
        print(f"📚 Loaded {len(existing_quests)} existing quests from database")
        return existing_quests
    
    def parse_lua_quest(self, quest_id: str, lua_str: str) -> Optional[Dict]:
        """
        Parse a Lua quest entry into a Python dict
        
        This parser extracts key fields we need for comparison
        """
        quest = {'id': quest_id}
        
        # Extract quest name (first string in quotes)
        name_match = re.search(r'"([^"]+)"', lua_str)
        if name_match:
            quest['name'] = name_match.group(1)
        
        # Check if it's a runtime stub
        if quest.get('name', '').startswith('[Epoch]'):
            quest['is_runtime_stub'] = True
        
        # Check for objectives - look for triple-nested braces
        # Format: {{{npcId,count,"name"},...},{{objectId,count},...},{{itemId,count},...}}
        if '{{{' in lua_str or '{{' in lua_str:
            quest['has_objectives'] = True
            # Count items/creatures/objects
            quest['objective_count'] = lua_str.count('{{')
        else:
            quest['has_objectives'] = False
            quest['objective_count'] = 0
        
        # Check for quest giver NPC (startedBy field)
        # Usually second field after name: {"name",{{npcId}},...}
        parts = lua_str.split(',', 5)
        if len(parts) > 1:
            started_by = parts[1].strip()
            if '{{' in started_by and '}}' in started_by:
                npc_match = re.search(r'\{\{(\d+)', started_by)
                if npc_match:
                    quest['has_quest_giver'] = True
                    quest['quest_giver_id'] = npc_match.group(1)
                else:
                    quest['has_quest_giver'] = False
            else:
                quest['has_quest_giver'] = False
        
        # Check for turn-in NPC (finishedBy field)
        if len(parts) > 2:
            finished_by = parts[2].strip()
            if '{{' in finished_by and '}}' in finished_by:
                npc_match = re.search(r'\{\{(\d+)', finished_by)
                if npc_match:
                    quest['has_turn_in'] = True
                    quest['turn_in_id'] = npc_match.group(1)
                else:
                    quest['has_turn_in'] = False
            else:
                quest['has_turn_in'] = False
        
        # Check for coordinates (usually in spawns field)
        if re.search(r'\d+\.\d+,\s*\d+\.\d+', lua_str):
            quest['has_coordinates'] = True
        else:
            quest['has_coordinates'] = False
        
        # Extract quest level if present
        level_match = re.search(r',(\d+),(\d+),', lua_str)
        if level_match:
            try:
                quest['requiredLevel'] = int(level_match.group(1))
                quest['questLevel'] = int(level_match.group(2))
            except:
                pass
        
        return quest
    
    def compare_all_quests(self, filtered_quests: Dict) -> Dict:
        """
        Compare all filtered quests against the existing database
        
        Args:
            filtered_quests: Dictionary of quest_id -> quest_data from pipeline
            
        Returns:
            Categorized comparison results
        """
        print("\n🔍 Comparing filtered quests with existing database...")
        
        for quest_id, new_data in filtered_quests.items():
            if quest_id in self.existing_db:
                # Quest exists - determine what kind of update is needed
                self.compare_existing_quest(quest_id, new_data, self.existing_db[quest_id])
            else:
                # New quest not in database
                self.categories['new_quests'].append({
                    'id': quest_id,
                    'name': new_data.get('name', f'Quest {quest_id}'),
                    'data': new_data
                })
        
        # Generate statistics
        self.print_comparison_stats()
        
        return self.categories
    
    def compare_existing_quest(self, quest_id: str, new_data: Dict, existing_data: Dict):
        """
        Compare a single quest that exists in both datasets
        
        Determines the appropriate action based on data completeness
        """
        comparison = {
            'id': quest_id,
            'name': new_data.get('name', existing_data.get('name', f'Quest {quest_id}')),
            'changes': []
        }
        
        # Priority 1: Check if it's a runtime stub that needs enhancement
        if existing_data.get('is_runtime_stub', False):
            comparison['changes'].append('Runtime stub needs real data')
            comparison['data'] = new_data
            self.categories['runtime_stubs'].append(comparison)
            return
        
        # Priority 2: Check for missing objectives
        new_objectives = new_data.get('objectives', {})
        new_obj_count = (len(new_objectives.get('items', [])) + 
                        len(new_objectives.get('creatures', [])) + 
                        len(new_objectives.get('objects', [])))
        
        existing_obj_count = existing_data.get('objective_count', 0)
        
        if new_obj_count > 0 and existing_obj_count == 0:
            comparison['changes'].append(f'Adding {new_obj_count} missing objectives')
            comparison['data'] = new_data
            self.categories['missing_objectives'].append(comparison)
            return
        
        # Priority 3: Check for missing NPCs
        has_new_giver = bool(new_data.get('startedBy'))
        has_existing_giver = existing_data.get('has_quest_giver', False)
        
        has_new_turnin = bool(new_data.get('finishedBy'))
        has_existing_turnin = existing_data.get('has_turn_in', False)
        
        if (has_new_giver and not has_existing_giver) or (has_new_turnin and not has_existing_turnin):
            if has_new_giver and not has_existing_giver:
                comparison['changes'].append('Adding quest giver NPC')
            if has_new_turnin and not has_existing_turnin:
                comparison['changes'].append('Adding turn-in NPC')
            comparison['data'] = new_data
            self.categories['missing_npcs'].append(comparison)
            return
        
        # Priority 4: Check for missing coordinates
        if new_data.get('has_coordinates') and not existing_data.get('has_coordinates'):
            comparison['changes'].append('Adding spawn coordinates')
            comparison['data'] = new_data
            self.categories['missing_coordinates'].append(comparison)
            return
        
        # Priority 5: Calculate completeness scores
        new_score = self.calculate_completeness_score(new_data)
        existing_score = self.calculate_completeness_score(existing_data)
        
        if new_score > existing_score + 10:  # Significantly better (10% improvement)
            comparison['changes'].append(f'Better data (score: {new_score} vs {existing_score})')
            comparison['data'] = new_data
            self.categories['better_data'].append(comparison)
        elif new_score < existing_score - 10:  # Significantly worse
            comparison['changes'].append(f'Inferior data (score: {new_score} vs {existing_score})')
            self.categories['inferior'].append(comparison)
        else:
            # Similar completeness - consider identical
            self.categories['identical'].append({'id': quest_id, 'name': comparison['name']})
    
    def calculate_completeness_score(self, quest_data: Dict) -> int:
        """
        Calculate a completeness score for quest data
        
        Based on QuestCompletenessScorer.lua weights from Questie
        """
        score = 0
        weights = {
            'HAS_NAME': 10,
            'HAS_STARTER_NPC': 20,
            'HAS_FINISHER_NPC': 15,
            'HAS_OBJECTIVES': 25,
            'HAS_STARTER_SPAWNS': 15,
            'HAS_FINISHER_SPAWNS': 10,
            'HAS_PROPER_LEVEL': 5
        }
        
        # Check each component
        if quest_data.get('name') and not quest_data.get('name', '').startswith('[Epoch]'):
            score += weights['HAS_NAME']
        
        if quest_data.get('startedBy'):
            score += weights['HAS_STARTER_NPC']
            if quest_data.get('has_coordinates') or quest_data.get('_coord_data'):
                score += weights['HAS_STARTER_SPAWNS']
            
        if quest_data.get('finishedBy'):
            score += weights['HAS_FINISHER_NPC']
            # Could check for finisher spawns too
        
        objectives = quest_data.get('objectives', {})
        if (objectives.get('items') or objectives.get('creatures') or objectives.get('objects')):
            score += weights['HAS_OBJECTIVES']
        
        if quest_data.get('questLevel'):
            score += weights['HAS_PROPER_LEVEL']
        
        return score
    
    def print_comparison_stats(self):
        """Print detailed statistics about the comparison"""
        total = sum(len(cat) for cat in self.categories.values())
        
        print("\n📊 Comparison Results:")
        print("-" * 50)
        
        # Print each category with examples
        for category, items in self.categories.items():
            if items:
                percentage = (len(items) / total * 100) if total > 0 else 0
                print(f"{category.replace('_', ' ').title()}: {len(items)} ({percentage:.1f}%)")
                
                # Show examples for interesting categories
                if category not in ['identical', 'inferior'] and len(items) > 0:
                    examples = items[:2]  # Show first 2 examples
                    for ex in examples:
                        if isinstance(ex, dict):
                            name = ex.get('name', 'Unknown')
                            changes = ex.get('changes', [])
                            print(f"  - {ex['id']}: {name}")
                            for change in changes:
                                print(f"    → {change}")
                    if len(items) > 2:
                        print(f"  ... and {len(items)-2} more")
        
        # Summary of actions needed
        print("\n📋 Action Summary:")
        print(f"  ✅ New quests to add: {len(self.categories['new_quests'])}")
        print(f"  🔧 Runtime stubs to enhance: {len(self.categories['runtime_stubs'])}")
        print(f"  ➕ Quests needing objectives: {len(self.categories['missing_objectives'])}")
        print(f"  👤 Quests needing NPCs: {len(self.categories['missing_npcs'])}")
        print(f"  📍 Quests needing coordinates: {len(self.categories['missing_coordinates'])}")
        print(f"  💎 Quests with better data: {len(self.categories['better_data'])}")
        print(f"  ⚠️ Conflicts to resolve: {len(self.categories['conflicts'])}")
        print(f"  ⏭️ Quests to skip (identical/inferior): {len(self.categories['identical']) + len(self.categories['inferior'])}")
    
    def generate_merge_instructions(self) -> Dict:
        """
        Generate specific merge instructions for each category
        
        Returns:
            Dictionary of merge instructions by category
        """
        instructions = {}
        
        # New quests - simple insert
        if self.categories['new_quests']:
            instructions['new_quests'] = {
                'action': 'INSERT',
                'count': len(self.categories['new_quests']),
                'quests': self.categories['new_quests'],
                'description': 'Add new quests to database'
            }
        
        # Runtime stubs - replace with real data
        if self.categories['runtime_stubs']:
            instructions['runtime_stubs'] = {
                'action': 'REPLACE',
                'count': len(self.categories['runtime_stubs']),
                'quests': self.categories['runtime_stubs'],
                'description': 'Replace runtime stubs with real quest data'
            }
        
        # Missing objectives - additive merge
        if self.categories['missing_objectives']:
            instructions['missing_objectives'] = {
                'action': 'MERGE_OBJECTIVES',
                'count': len(self.categories['missing_objectives']),
                'quests': self.categories['missing_objectives'],
                'description': 'Add missing objectives to existing quests'
            }
        
        # Missing NPCs - additive merge
        if self.categories['missing_npcs']:
            instructions['missing_npcs'] = {
                'action': 'MERGE_NPCS',
                'count': len(self.categories['missing_npcs']),
                'quests': self.categories['missing_npcs'],
                'description': 'Add quest giver/turn-in NPCs'
            }
        
        # Missing coordinates - additive merge  
        if self.categories['missing_coordinates']:
            instructions['missing_coordinates'] = {
                'action': 'MERGE_COORDINATES',
                'count': len(self.categories['missing_coordinates']),
                'quests': self.categories['missing_coordinates'],
                'description': 'Add spawn coordinates'
            }
        
        # Better data - replace if significantly better
        if self.categories['better_data']:
            instructions['better_data'] = {
                'action': 'REPLACE',
                'count': len(self.categories['better_data']),
                'quests': self.categories['better_data'],
                'description': 'Replace with more complete data'
            }
        
        # Conflicts - need manual review or strategy
        if self.categories['conflicts']:
            instructions['conflicts'] = {
                'action': 'MANUAL_REVIEW',
                'count': len(self.categories['conflicts']),
                'quests': self.categories['conflicts'],
                'description': 'Conflicts requiring resolution strategy'
            }
        
        # Summary
        total_actions = sum(inst['count'] for inst in instructions.values())
        instructions['summary'] = {
            'total_actions': total_actions,
            'skip_count': len(self.categories['identical']) + len(self.categories['inferior'])
        }
        
        return instructions
    
    def save_comparison_report(self, output_dir: Path = None):
        """Save detailed comparison report to file"""
        if output_dir is None:
            output_dir = Path("comparison_reports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_dir / f"comparison_report_{timestamp}.json"
        
        # Create the report
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'database_path': str(self.database_path),
                'existing_quests': len(self.existing_db),
                'compared_quests': sum(len(cat) for cat in self.categories.values())
            },
            'categories': {
                cat: len(items) for cat, items in self.categories.items()
            },
            'merge_instructions': self.generate_merge_instructions(),
            'details': self.categories  # Full details for each category
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Comparison report saved to: {report_file}")
        
        # Also save a human-readable summary
        summary_file = output_dir / f"comparison_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write("DATABASE COMPARISON SUMMARY\n")
            f.write("="*60 + "\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Database: {self.database_path}\n")
            f.write(f"Existing Quests: {len(self.existing_db)}\n")
            f.write(f"Compared Quests: {sum(len(cat) for cat in self.categories.values())}\n\n")
            
            f.write("ACTIONS NEEDED:\n")
            f.write("-"*40 + "\n")
            instructions = self.generate_merge_instructions()
            for key, inst in instructions.items():
                if key != 'summary':
                    f.write(f"{inst['description']}: {inst['count']}\n")
            
            f.write(f"\nTotal Actions: {instructions['summary']['total_actions']}\n")
            f.write(f"Quests to Skip: {instructions['summary']['skip_count']}\n")
        
        print(f"💾 Summary saved to: {summary_file}")
        
        return report_file