#!/usr/bin/env python3
"""
NPC Parser Module for Questie Pipeline

Extracts and processes NPC (Non-Player Character) information from quest submissions.
Handles all 15 NPC database fields according to WoW 3.3.5 epochNpcDB.lua structure.

NPC Database Structure (15 fields):
1. name - NPC name (string)
2. minLevelHealth - Min HP (int or nil)
3. maxLevelHealth - Max HP (int or nil) 
4. minLevel - Min level (int)
5. maxLevel - Max level (int)
6. rank - Elite status (int: 0=normal, 1=elite, 2=rare elite, 3=boss, 4=rare)
7. spawns - {[zoneId]={{x,y},...}}: Spawn locations
8. waypoints - {[zoneId]={{x,y},...}} or nil: Patrol path
9. zoneID - Primary zone for this NPC (int)
10. questStarts - {questId,...}: Quests this NPC starts
11. questEnds - {questId,...}: Quests this NPC ends  
12. factionID - Faction template ID (int or nil)
13. friendlyToFaction - "A", "H", "AH", or nil: Who can interact
14. subName - Title like "Weapon Vendor" (string or nil)
15. npcFlags - Bitflags (2=questgiver, 128=vendor, etc.)
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Import local modules
from coordinate_parser import CoordinateParser
from zone_mapper import ZoneMapper

@dataclass
class NPCInfo:
    """Data structure for NPC information"""
    npc_id: int
    name: str
    level_range: Tuple[int, int] = (1, 1)
    rank: int = 0  # 0=normal, 1=elite, 2=rare elite, 3=boss, 4=rare
    coordinates: List[Tuple[float, float]] = None
    zone_id: int = None
    zone_name: str = None
    quest_starts: List[int] = None
    quest_ends: List[int] = None
    faction: str = None  # "Alliance", "Horde", "Neutral"
    sub_name: str = None  # Title/Description
    npc_flags: int = 0  # NPC flags bitmask
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.coordinates is None:
            self.coordinates = []
        if self.quest_starts is None:
            self.quest_starts = []
        if self.quest_ends is None:
            self.quest_ends = []

class NPCParser:
    """Extracts NPC data from quest submissions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.coordinate_parser = CoordinateParser()
        self.zone_mapper = ZoneMapper()
        
        # NPC rank keywords for detection
        self.rank_keywords = {
            'elite': 1,
            'rare elite': 2,
            'boss': 3,
            'rare': 4,
            'champion': 1,
            'named': 2
        }
        
        # NPC flags (WoW 3.3.5 values)
        self.npc_flags = {
            'GOSSIP': 1,
            'QUESTGIVER': 2,
            'TRAINER': 16,
            'VENDOR': 128,
            'FLIGHTMASTER': 8192,
            'INNKEEPER': 65536,
            'BANKER': 131072,
            'AUCTIONEER': 2097152,
            'STABLEMASTER': 4194304,
            'REPAIR': 4096
        }
        
        # Faction mappings
        self.faction_mappings = {
            'alliance': 'A',
            'horde': 'H', 
            'neutral': 'AH',
            'both': 'AH',
            'all': 'AH'
        }
        
        # Common NPC title patterns
        self.title_patterns = [
            r'<([^>]+)>',  # <Weapon Vendor>
            r'"([^"]+)"',  # "The Innkeeper"
            r'\(([^)]+)\)' # (Quest Giver)
        ]
    
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse NPC data from quest submission content
        
        Args:
            content: Quest submission text
            quest_id: Associated quest ID
            
        Returns:
            Dict containing extracted NPC data
        """
        npc_data = {
            'quest_id': quest_id,
            'quest_giver': None,
            'turn_in_npc': None,
            'objective_npcs': [],
            'all_npcs': [],
            'npc_database_entries': {},
            'parsing_confidence': 0.0
        }
        
        try:
            # Extract NPCs from different sections
            npc_data['quest_giver'] = self._extract_quest_giver(content, quest_id)
            npc_data['turn_in_npc'] = self._extract_turn_in_npc(content, quest_id)
            npc_data['objective_npcs'] = self._extract_objective_npcs(content, quest_id)
            
            # Compile all unique NPCs
            all_npcs = []
            if npc_data['quest_giver']:
                all_npcs.append(npc_data['quest_giver'])
            if npc_data['turn_in_npc']:
                all_npcs.append(npc_data['turn_in_npc'])
            all_npcs.extend(npc_data['objective_npcs'])
            
            # Remove duplicates based on NPC ID
            unique_npcs = {}
            for npc in all_npcs:
                if npc and npc.npc_id not in unique_npcs:
                    unique_npcs[npc.npc_id] = npc
                elif npc and npc.npc_id in unique_npcs:
                    # Merge data from duplicate entries
                    unique_npcs[npc.npc_id] = self._merge_npc_data(unique_npcs[npc.npc_id], npc)
            
            npc_data['all_npcs'] = list(unique_npcs.values())
            
            # Generate database entries
            npc_data['npc_database_entries'] = self._generate_database_entries(npc_data['all_npcs'])
            
            # Calculate overall confidence
            if npc_data['all_npcs']:
                total_confidence = sum(npc.confidence for npc in npc_data['all_npcs'])
                npc_data['parsing_confidence'] = min(total_confidence / len(npc_data['all_npcs']), 1.0)
            
            self.logger.info(f"Parsed {len(npc_data['all_npcs'])} NPCs for quest {quest_id}")
            
        except Exception as e:
            self.logger.error(f"Error parsing NPC data: {e}")
            npc_data['parsing_confidence'] = 0.0
        
        return npc_data
    
    def _extract_quest_giver(self, content: str, quest_id: int) -> Optional[NPCInfo]:
        """Extract quest giver NPC information"""
        patterns = [
            # Multiline format with brackets: QUEST GIVER:\n  NPC: Name (ID: 123)\n  Location: [x, y]\n  Zone: Zone
            r'QUEST GIVER:\s*\n\s*NPC:\s*([^(]+?)\s*\(ID:\s*(\d+)\)\s*\n\s*Location:\s*\[([0-9.]+),\s*([0-9.]+)\]\s*\n\s*Zone:\s*([^\n]+)',
            # Alternative formats
            r'Quest Giver:\s*([^(]+)\s*\((\d+)\).*?at\s*\[?([0-9.]+),\s*([0-9.]+)\]?.*?in\s*([^\n]+)',
            r'Started by NPC:\s*([^(]+)\s*\(ID:\s*(\d+)\)',
            r'Accept from:\s*([^(]+)\s*\(ID:\s*(\d+)\)',
            # Fallback patterns for partial data
            r'QUEST GIVER:\s*\n\s*NPC:\s*([^(]+?)\s*\(ID:\s*(\d+)\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    if len(match.groups()) >= 5:
                        name, npc_id, x, y, zone = match.groups()[:5]
                        coords = [(float(x), float(y))]
                    else:
                        name, npc_id = match.groups()[:2]
                        coords = []
                        zone = None
                    
                    npc = NPCInfo(
                        npc_id=int(npc_id),
                        name=name.strip(),
                        coordinates=coords,
                        zone_name=zone.strip() if zone else None,
                        quest_starts=[quest_id] if quest_id else [],
                        confidence=0.8
                    )
                    
                    # Get zone ID if we have zone name
                    if npc.zone_name:
                        # CRITICAL: Pass entity_type='npc' to ensure parent zones are used
                        npc.zone_id = self.zone_mapper.get_zone_id(npc.zone_name, {'entity_type': 'npc'})
                    
                    # Set NPC flags for quest giver
                    npc.npc_flags |= self.npc_flags['QUESTGIVER']
                    
                    return npc
                    
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error parsing quest giver: {e}")
                    continue
        
        return None
    
    def _extract_turn_in_npc(self, content: str, quest_id: int) -> Optional[NPCInfo]:
        """Extract turn-in NPC information"""
        patterns = [
            # Multiline format with brackets: TURN-IN NPC:\n  NPC: Name (ID: 123)\n  Location: [x, y]\n  Zone: Zone
            r'TURN-IN NPC:\s*\n\s*NPC:\s*([^(]+?)\s*\(ID:\s*(\d+)\)\s*\n\s*Location:\s*\[([0-9.]+),\s*([0-9.]+)\]\s*\n\s*Zone:\s*([^\n]+)',
            # Alternative formats
            r'Turn in to:\s*([^(]+)\s*\((\d+)\).*?at\s*\[?([0-9.]+),\s*([0-9.]+)\]?.*?in\s*([^\n]+)',
            r'Complete at:\s*([^(]+)\s*\(ID:\s*(\d+)\)',
            r'Return to:\s*([^(]+)\s*\(ID:\s*(\d+)\)',
            # Fallback patterns for partial data
            r'TURN-IN NPC:\s*\n\s*NPC:\s*([^(]+?)\s*\(ID:\s*(\d+)\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    if len(match.groups()) >= 5:
                        name, npc_id, x, y, zone = match.groups()[:5]
                        coords = [(float(x), float(y))]
                    else:
                        name, npc_id = match.groups()[:2]
                        coords = []
                        zone = None
                    
                    npc = NPCInfo(
                        npc_id=int(npc_id),
                        name=name.strip(),
                        coordinates=coords,
                        zone_name=zone.strip() if zone else None,
                        quest_ends=[quest_id] if quest_id else [],
                        confidence=0.8
                    )
                    
                    # Get zone ID if we have zone name
                    if npc.zone_name:
                        # CRITICAL: Pass entity_type='npc' to ensure parent zones are used
                        npc.zone_id = self.zone_mapper.get_zone_id(npc.zone_name, {'entity_type': 'npc'})
                    
                    # Set NPC flags for quest giver (many also turn in quests)
                    npc.npc_flags |= self.npc_flags['QUESTGIVER']
                    
                    return npc
                    
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error parsing turn-in NPC: {e}")
                    continue
        
        return None
    
    def _extract_objective_npcs(self, content: str, quest_id: int) -> List[NPCInfo]:
        """Extract NPCs from quest objectives"""
        objective_npcs = []
        
        # Patterns for different objective types
        patterns = [
            r'Kill\s+(\d+)\s+([^(]+)\s*\((\d+)\)',  # Kill 10 Amethyst Crabs (46835)
            r'Slay\s+(\d+)\s+([^(]+)\s*\((\d+)\)',  # Slay 5 Wolves (12345)
            r'Defeat\s+([^(]+)\s*\((\d+)\)',        # Defeat Boss Name (67890)
            r'([^(]+)\s*\((\d+)\)\s*slain:\s*(\d+)', # Crab (46835) slain: 10/10
            r'Talk to\s+([^(]+)\s*\((\d+)\)',       # Talk to NPC Name (12345)
            r'Speak with\s+([^(]+)\s*\((\d+)\)',    # Speak with NPC (12345)
            r'Find\s+([^(]+)\s*\((\d+)\)'           # Find Lost NPC (12345)
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()
                    
                    if len(groups) == 3 and groups[0].isdigit():
                        # Pattern with count: Kill 10 Crabs (46835)
                        count, name, npc_id = groups
                        name = name.strip()
                        npc_id = int(npc_id)
                    elif len(groups) == 2:
                        # Pattern without count: Talk to NPC (12345)
                        name, npc_id = groups
                        name = name.strip()
                        npc_id = int(npc_id)
                    elif len(groups) == 3:
                        # Pattern like: Crab (46835) slain: 10/10
                        name, npc_id, count = groups
                        name = name.strip()
                        npc_id = int(npc_id)
                    else:
                        continue
                    
                    # Determine rank from name keywords
                    rank = 0
                    for keyword, rank_value in self.rank_keywords.items():
                        if keyword.lower() in name.lower():
                            rank = rank_value
                            break
                    
                    npc = NPCInfo(
                        npc_id=npc_id,
                        name=name,
                        rank=rank,
                        confidence=0.7
                    )
                    
                    # Try to extract coordinates for this NPC
                    npc_coords = self._find_npc_coordinates(content, name, npc_id)
                    if npc_coords:
                        npc.coordinates = npc_coords
                        npc.confidence += 0.1
                    
                    objective_npcs.append(npc)
                    
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error parsing objective NPC: {e}")
                    continue
        
        return objective_npcs
    
    def _find_npc_coordinates(self, content: str, npc_name: str, npc_id: int) -> List[Tuple[float, float]]:
        """Find coordinates for a specific NPC"""
        coordinates = []
        
        # Look for coordinates near NPC mentions
        patterns = [
            rf'{re.escape(npc_name)}.*?([0-9.]+),\s*([0-9.]+)',
            rf'\({npc_id}\).*?([0-9.]+),\s*([0-9.]+)',
            rf'ID:\s*{npc_id}.*?([0-9.]+),\s*([0-9.]+)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    x, y = float(match.group(1)), float(match.group(2))
                    if 0 <= x <= 100 and 0 <= y <= 100:  # Valid coordinate range
                        coordinates.append((x, y))
                except (ValueError, IndexError):
                    continue
        
        return coordinates
    
    def _merge_npc_data(self, npc1: NPCInfo, npc2: NPCInfo) -> NPCInfo:
        """Merge data from two NPC instances"""
        # Start with the higher confidence NPC
        if npc1.confidence >= npc2.confidence:
            primary, secondary = npc1, npc2
        else:
            primary, secondary = npc2, npc1
        
        # Merge coordinates (remove duplicates)
        all_coords = primary.coordinates + secondary.coordinates
        unique_coords = []
        for coord in all_coords:
            if coord not in unique_coords:
                unique_coords.append(coord)
        
        # Merge quest associations
        quest_starts = list(set(primary.quest_starts + secondary.quest_starts))
        quest_ends = list(set(primary.quest_ends + secondary.quest_ends))
        
        # Take best available data for each field
        merged = NPCInfo(
            npc_id=primary.npc_id,
            name=primary.name or secondary.name,
            level_range=primary.level_range if primary.level_range != (1, 1) else secondary.level_range,
            rank=max(primary.rank, secondary.rank),
            coordinates=unique_coords,
            zone_id=primary.zone_id or secondary.zone_id,
            zone_name=primary.zone_name or secondary.zone_name,
            quest_starts=quest_starts,
            quest_ends=quest_ends,
            faction=primary.faction or secondary.faction,
            sub_name=primary.sub_name or secondary.sub_name,
            npc_flags=primary.npc_flags | secondary.npc_flags,  # Combine flags
            confidence=max(primary.confidence, secondary.confidence)
        )
        
        return merged
    
    def _generate_database_entries(self, npcs: List[NPCInfo]) -> Dict:
        """Generate Lua database entries for NPCs"""
        entries = {}
        
        for npc in npcs:
            # Generate spawns table
            spawns_data = "nil"
            if npc.coordinates and npc.zone_id:
                coords_str = ",".join([f"{{{x:.1f},{y:.1f}}}" for x, y in npc.coordinates])
                spawns_data = f"{{[{npc.zone_id}]={{{coords_str}}}}}"
            
            # Determine faction affinity
            friendly_to_faction = "nil"
            if npc.faction:
                friendly_to_faction = f'"{self.faction_mappings.get(npc.faction.lower(), "AH")}"'
            
            # Quest associations
            quest_starts_str = "nil"
            if npc.quest_starts:
                quest_starts_str = "{" + ",".join(map(str, npc.quest_starts)) + "}"
            
            quest_ends_str = "nil"  
            if npc.quest_ends:
                quest_ends_str = "{" + ",".join(map(str, npc.quest_ends)) + "}"
            
            # Sub name (title)
            sub_name_str = "nil"
            if npc.sub_name:
                sub_name_str = f'"{npc.sub_name}"'
            
            # Generate NPC entry (15 fields)
            entry = f"""    [{npc.npc_id}] = {{
        "{npc.name}",                    -- [1] name
        nil,                             -- [2] minLevelHealth
        nil,                             -- [3] maxLevelHealth  
        {npc.level_range[0]},            -- [4] minLevel
        {npc.level_range[1]},            -- [5] maxLevel
        {npc.rank},                      -- [6] rank (0=normal, 1=elite, 2=rare elite, 3=boss, 4=rare)
        {spawns_data},                   -- [7] spawns
        nil,                             -- [8] waypoints
        {npc.zone_id or "nil"},          -- [9] zoneID
        {quest_starts_str},              -- [10] questStarts
        {quest_ends_str},                -- [11] questEnds
        nil,                             -- [12] factionID
        {friendly_to_faction},           -- [13] friendlyToFaction
        {sub_name_str},                  -- [14] subName
        {npc.npc_flags}                  -- [15] npcFlags
    }},"""
            
            entries[npc.npc_id] = {
                'lua_entry': entry,
                'confidence': npc.confidence,
                'npc_info': npc
            }
        
        return entries


def main():
    """Test the NPC parser with sample data"""
    parser = NPCParser()
    
    # Test with sample quest submission
    test_content = """
    QUEST GIVER:
      NPC: Deputy Willem (ID: 823)
      Location: 48.1, 42.9
      Zone: Elwynn Forest

    OBJECTIVES:
      1. Kill 10 Amethyst Crabs (46835)
      2. Talk to Marshal Dughan (240)

    TURN-IN NPC:
      NPC: Marshal Dughan (ID: 240)
      Location: 42.1, 65.9
      Zone: Elwynn Forest
    """
    
    result = parser.parse(test_content, 12345)
    
    print(f"Parsed {len(result['all_npcs'])} NPCs:")
    for npc in result['all_npcs']:
        print(f"  - {npc.name} ({npc.npc_id}) - Confidence: {npc.confidence:.2f}")
    
    print(f"\nDatabase entries:")
    for npc_id, entry_data in result['npc_database_entries'].items():
        print(f"\nNPC {npc_id}:")
        print(entry_data['lua_entry'])


if __name__ == "__main__":
    main()