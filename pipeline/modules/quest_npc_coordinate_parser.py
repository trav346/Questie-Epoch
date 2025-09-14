#!/usr/bin/env python3
"""
Quest NPC Coordinate Parser - Surgical module for quest giver and turn-in NPCs only
Fast, focused extraction of quest start/end NPC coordinates
"""

import re
from typing import Dict, List, Optional

class QuestNPCCoordinateParser:
    """
    Extracts ONLY quest giver and turn-in NPC coordinates.
    These are always relevant and don't need objective matching.
    """
    
    def __init__(self):
        self.parsed_npcs = []
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """Fast, line-based extraction of quest giver and turn-in NPC coords.

        This avoids expensive multi-line regex over entire content by scanning
        for labeled sections and then looking ahead a few lines for Location/Zone.
        """
        res = {
            'quest_id': quest_id,
            'quest_giver': None,
            'turn_in_npc': None,
            'success': False,
        }

        lines = content.splitlines()
        n = len(lines)

        def extract_block(start_idx: int) -> Optional[Dict]:
            name = nid = None
            x = y = zone = None
            # Within next ~8 lines, find NPC line and coords/zone
            for j in range(start_idx + 1, min(start_idx + 9, n)):
                lj = lines[j]
                m = re.search(r'NPC:\s*(.+?)\s*\(ID:\s*(\d+)\)', lj, re.IGNORECASE)
                if not m:
                    m = re.search(r'^\s*(.+?)\s*\(ID:\s*(\d+)\)', lj)
                if m and not nid:
                    name = m.group(1).strip()
                    try:
                        nid = int(m.group(2))
                    except Exception:
                        nid = None
                lm = re.search(r'Location:\s*\[?([\d.]+),\s*([\d.]+)\]?', lj, re.IGNORECASE)
                if lm:
                    try:
                        x = float(lm.group(1)); y = float(lm.group(2))
                    except Exception:
                        pass
                zm = re.search(r'Zone:\s*([^\n]+)', lj, re.IGNORECASE)
                if zm:
                    zone = zm.group(1).strip()
            if nid and x is not None and y is not None:
                return {'name': name, 'id': nid, 'x': x, 'y': y, 'zone': zone}
            return None

        for i, line in enumerate(lines):
            l = line.strip().lower()
            if res['quest_giver'] is None and l.startswith('quest giver'):
                block = extract_block(i)
                if block:
                    res['quest_giver'] = block
                    res['success'] = True
            elif res['turn_in_npc'] is None and (l.startswith('turn-in npc') or l.startswith('turn in npc')):
                block = extract_block(i)
                if block:
                    res['turn_in_npc'] = block
                    res['success'] = True
            if res['quest_giver'] and res['turn_in_npc']:
                break

        return res
    
    def get_summary(self) -> Dict:
        """Get summary of parsed NPCs."""
        return {
            'total_parsed': len(self.parsed_npcs),
            'quest_givers': sum(1 for npc in self.parsed_npcs if npc.get('type') == 'quest_giver'),
            'turn_in_npcs': sum(1 for npc in self.parsed_npcs if npc.get('type') == 'turn_in')
        }
