#!/usr/bin/env python3
"""
Phantom Quest Processor - Identifies and removes quests that don't exist on server
Processes player reports of phantom quests and applies smart filtering
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from datetime import datetime

class PhantomQuestProcessor:
    """
    Processes phantom quest reports and generates removal lists
    """
    
    def __init__(self):
        self.phantom_reports = defaultdict(list)
        self.confirmed_phantoms = set()
        self.patch_data = {}  # Will be populated from Wowhead scraping
        
        # Known expansion content ranges
        self.EXPANSION_RANGES = {
            'tbc': (10000, 12999),
            'wotlk': (13000, 24999),
            'cata_prepatch': (25000, 29999)
        }
        
        # Known problem patterns
        self.PHANTOM_PATTERNS = [
            r'death\s*knight',
            r'achievement',
            r'inscription',
            r'jewelcrafting',  # Added in TBC
            r'flying\s*mount',  # TBC feature
            r'heroic',  # TBC/WotLK dungeons
            r'northrend',
            r'outland',
            r'shattrath',
            r'dalaran',
            r'wintergrasp',
            r'argent\s*tournament'
        ]
        
        # Zones that don't exist in vanilla
        self.NON_VANILLA_ZONES = {
            # TBC zones
            530: 'Outland',
            3430: 'Eversong Woods',
            3433: 'Ghostlands',
            3483: 'Hellfire Peninsula',
            3518: 'Nagrand',
            3519: 'Terokkar Forest',
            3520: 'Shadowmoon Valley',
            3521: 'Zangarmarsh',
            3522: 'Blade\'s Edge Mountains',
            3523: 'Netherstorm',
            3487: 'Silvermoon City',
            3557: 'The Exodar',
            3524: 'Azuremyst Isle',
            3525: 'Bloodmyst Isle',
            
            # WotLK zones
            571: 'Northrend',
            3537: 'Borean Tundra',
            3711: 'Sholazar Basin',
            4197: 'Wintergrasp',
            65: 'Dragonblight',
            66: 'Zul\'Drak',
            67: 'The Storm Peaks',
            210: 'Icecrown',
            394: 'Grizzly Hills',
            495: 'Howling Fjord',
            2817: 'Crystalsong Forest',
            4395: 'Dalaran'
        }
        
    def process_phantom_report(self, report_data: Dict) -> None:
        """Process a single phantom quest report from player"""
        quest_id = report_data.get('quest_id')
        if not quest_id:
            return
        
        self.phantom_reports[quest_id].append({
            'timestamp': report_data.get('timestamp', datetime.now().isoformat()),
            'player_level': report_data.get('player_level'),
            'player_class': report_data.get('player_class'),
            'player_race': report_data.get('player_race'),
            'npc_id': report_data.get('npc_id'),
            'npc_name': report_data.get('npc_name'),
            'zone': report_data.get('zone'),
            'report_type': report_data.get('report_type', 'manual')
        })
        
        # Auto-confirm if enough reports
        if len(self.phantom_reports[quest_id]) >= 3:
            self.confirmed_phantoms.add(quest_id)
    
    def analyze_quest_for_removal(self, quest_id: int, quest_data: Dict) -> Tuple[bool, str]:
        """
        Analyze if a quest should be removed
        Returns (should_remove, reason)
        """
        
        # Check if it's a confirmed phantom
        if quest_id in self.confirmed_phantoms:
            return True, "Confirmed phantom by multiple players"
        
        # Check expansion ranges
        for expansion, (min_id, max_id) in self.EXPANSION_RANGES.items():
            if min_id <= quest_id <= max_id:
                return True, f"In {expansion.upper()} ID range ({min_id}-{max_id})"
        
        # Check quest name patterns
        quest_name = quest_data.get('name', '').lower()
        for pattern in self.PHANTOM_PATTERNS:
            if re.search(pattern, quest_name):
                return True, f"Name matches non-vanilla pattern: {pattern}"
        
        # Check zone
        zone_id = quest_data.get('zone_id')
        if zone_id in self.NON_VANILLA_ZONES:
            return True, f"In non-vanilla zone: {self.NON_VANILLA_ZONES[zone_id]}"
        
        # Check level (vanilla cap was 60)
        quest_level = quest_data.get('level', 0)
        min_level = quest_data.get('min_level', 0)
        if quest_level > 60 or min_level > 60:
            return True, f"Level exceeds vanilla cap (level: {quest_level}, min: {min_level})"
        
        # Check patch data if available
        if quest_id in self.patch_data:
            patch = self.patch_data[quest_id]
            if not patch.startswith('1.'):
                return True, f"Added in patch {patch} (not vanilla)"
        
        return False, ""
    
    def scan_database_for_phantoms(self, db_path: Path) -> Dict:
        """Scan WotLK database for likely phantom quests"""
        results = {
            'definite_removals': [],  # Definitely should be removed
            'likely_removals': [],     # Probably should be removed
            'needs_verification': [],  # Needs player verification
            'statistics': {}
        }
        
        # Load WotLK quest database
        wotlk_quests = self._load_quest_database(db_path)
        
        # Analyze each quest
        for quest_id, quest_data in wotlk_quests.items():
            should_remove, reason = self.analyze_quest_for_removal(quest_id, quest_data)
            
            if should_remove:
                # Categorize by confidence
                if 'ID range' in reason or 'Confirmed phantom' in reason:
                    results['definite_removals'].append({
                        'id': quest_id,
                        'name': quest_data.get('name'),
                        'reason': reason
                    })
                elif 'non-vanilla zone' in reason or 'exceeds vanilla cap' in reason:
                    results['likely_removals'].append({
                        'id': quest_id,
                        'name': quest_data.get('name'),
                        'reason': reason
                    })
                else:
                    results['needs_verification'].append({
                        'id': quest_id,
                        'name': quest_data.get('name'),
                        'reason': reason
                    })
        
        # Calculate statistics
        results['statistics'] = {
            'total_quests': len(wotlk_quests),
            'definite_removals': len(results['definite_removals']),
            'likely_removals': len(results['likely_removals']),
            'needs_verification': len(results['needs_verification']),
            'total_removals': len(results['definite_removals']) + len(results['likely_removals'])
        }
        
        return results
    
    def _load_quest_database(self, db_path: Path) -> Dict:
        """Load and parse quest database"""
        quests = {}
        
        if not db_path.exists():
            return quests
        
        with open(db_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Parse quest entries
        pattern = r'\[(\d+)\]\s*=\s*\{([^}]+)\}'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for quest_id_str, quest_content in matches:
            quest_id = int(quest_id_str)
            
            # Extract basic info
            name_match = re.search(r'"([^"]+)"', quest_content)
            name = name_match.group(1) if name_match else f"Quest {quest_id}"
            
            # Try to extract level and zone
            level = 1
            zone_id = 0
            
            # Simple extraction (would need more sophisticated parsing)
            parts = quest_content.split(',')
            if len(parts) > 4:
                try:
                    level = int(parts[4].strip())
                except:
                    pass
            
            quests[quest_id] = {
                'id': quest_id,
                'name': name,
                'level': level,
                'zone_id': zone_id
            }
        
        return quests
    
    def generate_removal_script(self, results: Dict, output_path: str = "remove_phantom_quests.py") -> Path:
        """Generate Python script to remove phantom quests"""
        
        script_lines = []
        script_lines.append("#!/usr/bin/env python3")
        script_lines.append('"""')
        script_lines.append("Auto-generated script to remove phantom quests from WotLK database")
        script_lines.append(f"Generated: {datetime.now().isoformat()}")
        script_lines.append(f"Total removals: {results['statistics']['total_removals']}")
        script_lines.append('"""')
        script_lines.append("")
        script_lines.append("import re")
        script_lines.append("from pathlib import Path")
        script_lines.append("from datetime import datetime")
        script_lines.append("")
        
        # Add quest lists
        script_lines.append("# Definite removals (expansion content)")
        definite_ids = [q['id'] for q in results['definite_removals']]
        script_lines.append(f"DEFINITE_REMOVALS = {definite_ids}")
        script_lines.append("")
        
        script_lines.append("# Likely removals (non-vanilla indicators)")
        likely_ids = [q['id'] for q in results['likely_removals']]
        script_lines.append(f"LIKELY_REMOVALS = {likely_ids}")
        script_lines.append("")
        
        # Add the removal function
        script_lines.append("def comment_out_quest(file_path, quest_id):")
        script_lines.append('    """Comment out a quest in the database"""')
        script_lines.append("    with open(file_path, 'r', encoding='utf-8') as f:")
        script_lines.append("        content = f.read()")
        script_lines.append("    ")
        script_lines.append(r"    pattern = rf'(\[{quest_id}\]\s*=\s*\{{[^}}]*\}}[,\s]*)'")
        script_lines.append("    ")
        script_lines.append("    def replace_func(match):")
        script_lines.append("        entry = match.group(1)")
        script_lines.append("        lines = entry.split('\\n')")
        script_lines.append("        commented = []")
        script_lines.append("        for line in lines:")
        script_lines.append("            if line.strip():")
        script_lines.append("                commented.append('-- ' + line)")
        script_lines.append("            else:")
        script_lines.append("                commented.append(line)")
        script_lines.append("        return f'-- Phantom quest (not in vanilla)\\n' + '\\n'.join(commented)")
        script_lines.append("    ")
        script_lines.append("    new_content = re.sub(pattern, replace_func, content, flags=re.DOTALL)")
        script_lines.append("    ")
        script_lines.append("    if new_content == content:")
        script_lines.append("        return False")
        script_lines.append("    ")
        script_lines.append("    # Create backup")
        script_lines.append("    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')")
        script_lines.append("    backup_path = file_path.with_suffix(f'.backup_phantom_{timestamp}.lua')")
        script_lines.append("    with open(backup_path, 'w', encoding='utf-8') as f:")
        script_lines.append("        f.write(content)")
        script_lines.append("    ")
        script_lines.append("    # Write updated content")
        script_lines.append("    with open(file_path, 'w', encoding='utf-8') as f:")
        script_lines.append("        f.write(new_content)")
        script_lines.append("    ")
        script_lines.append("    return True")
        script_lines.append("")
        
        # Add main function
        script_lines.append("def main():")
        script_lines.append('    print("="*70)')
        script_lines.append('    print("PHANTOM QUEST REMOVAL")')
        script_lines.append('    print("="*70)')
        script_lines.append("    ")
        script_lines.append("    # Update this path to your Questie installation
    db_path = Path('../../Database/WotLK/wotlkQuestDB.lua')")
        script_lines.append("    ")
        script_lines.append('    print(f"\\nProcessing definite removals ({len(DEFINITE_REMOVALS)} quests)...")')
        script_lines.append("    for quest_id in DEFINITE_REMOVALS:")
        script_lines.append("        if comment_out_quest(db_path, quest_id):")
        script_lines.append("            print(f'  Removed quest {quest_id}')")
        script_lines.append("    ")
        script_lines.append('    print(f"\\nProcessing likely removals ({len(LIKELY_REMOVALS)} quests)...")')
        script_lines.append("    for quest_id in LIKELY_REMOVALS:")
        script_lines.append("        if comment_out_quest(db_path, quest_id):")
        script_lines.append("            print(f'  Removed quest {quest_id}')")
        script_lines.append("    ")
        script_lines.append('    print("\\nComplete! Restart WoW to see changes.")')
        script_lines.append("")
        script_lines.append('if __name__ == "__main__":')
        script_lines.append("    main()")
        
        # Save script
        script_path = Path(output_path)
        with open(script_path, 'w') as f:
            f.write('\n'.join(script_lines))
        
        return script_path
    
    def generate_report(self, results: Dict) -> str:
        """Generate human-readable report of phantom quests"""
        lines = []
        lines.append("="*70)
        lines.append("PHANTOM QUEST ANALYSIS REPORT")
        lines.append("="*70)
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("")
        
        # Statistics
        lines.append("SUMMARY:")
        for key, value in results['statistics'].items():
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")
        lines.append("")
        
        # Definite removals
        if results['definite_removals']:
            lines.append("DEFINITE REMOVALS (Expansion Content):")
            lines.append("-"*50)
            for i, quest in enumerate(results['definite_removals'][:20], 1):
                lines.append(f"{i}. Quest {quest['id']}: {quest['name']}")
                lines.append(f"   Reason: {quest['reason']}")
            if len(results['definite_removals']) > 20:
                lines.append(f"... and {len(results['definite_removals']) - 20} more")
            lines.append("")
        
        # Likely removals
        if results['likely_removals']:
            lines.append("LIKELY REMOVALS (Non-Vanilla Indicators):")
            lines.append("-"*50)
            for i, quest in enumerate(results['likely_removals'][:20], 1):
                lines.append(f"{i}. Quest {quest['id']}: {quest['name']}")
                lines.append(f"   Reason: {quest['reason']}")
            if len(results['likely_removals']) > 20:
                lines.append(f"... and {len(results['likely_removals']) - 20} more")
            lines.append("")
        
        # Needs verification
        if results['needs_verification']:
            lines.append("NEEDS PLAYER VERIFICATION:")
            lines.append("-"*50)
            for i, quest in enumerate(results['needs_verification'][:10], 1):
                lines.append(f"{i}. Quest {quest['id']}: {quest['name']}")
                lines.append(f"   Reason: {quest['reason']}")
            if len(results['needs_verification']) > 10:
                lines.append(f"... and {len(results['needs_verification']) - 10} more")
        
        return "\n".join(lines)


def main():
    """Test the phantom quest processor"""
    print("="*70)
    print("PHANTOM QUEST PROCESSOR TEST")
    print("="*70)
    
    processor = PhantomQuestProcessor()
    
    # Path to WotLK database
    # Update this path to your Questie installation
    db_path = Path("../../Database/WotLK/wotlkQuestDB.lua")
    
    print("\nScanning database for phantom quests...")
    results = processor.scan_database_for_phantoms(db_path)
    
    # Generate report
    report = processor.generate_report(results)
    print(report)
    
    # Save report
    report_path = Path("phantom_quest_report.txt")
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    # Generate removal script
    if results['definite_removals'] or results['likely_removals']:
        script_path = processor.generate_removal_script(results)
        print(f"Removal script generated: {script_path}")
        print("\nTo remove phantom quests, run:")
        print(f"  python3 {script_path}")
    
    print("="*70)

if __name__ == "__main__":
    main()