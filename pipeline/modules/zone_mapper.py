#!/usr/bin/env python3
"""
Zone Mapper Module - Maps zone names to WoW zone IDs
Critical for quest and NPC location data
"""

class ZoneMapper:
    """Maps zone names (from submissions) to zone IDs (for database)"""
    
    def __init__(self):
        # Comprehensive zone mapping including common variations
        self.zone_map = {
            # Eastern Kingdoms
            'elwynn forest': 12,
            'westfall': 40,
            'redridge mountains': 44,
            'stranglethorn vale': 33,
            'duskwood': 10,
            'deadwind pass': 41,
            'swamp of sorrows': 8,
            'blasted lands': 4,
            'burning steppes': 46,
            'searing gorge': 51,
            'badlands': 3,
            'loch modan': 38,
            'dun morogh': 1,
            'wetlands': 11,
            'arathi highlands': 45,
            'hillsbrad foothills': 267,
            'alterac mountains': 36,
            'silverpine forest': 130,
            'tirisfal glades': 85,
            'western plaguelands': 28,
            'eastern plaguelands': 139,
            'the hinterlands': 47,
            'eversong woods': 3430,
            'ghostlands': 3433,
            'isle of quel\'danas': 4080,
            'sunwell plateau': 4075,
            
            # Kalimdor
            'durotar': 14,
            'the barrens': 17,
            'northern barrens': 17,  # Split in later versions but same ID in 3.3.5
            'southern barrens': 17,
            'mulgore': 215,
            'thunder bluff': 1638,
            'stonetalon mountains': 406,
            'ashenvale': 331,
            'thousand needles': 400,
            'desolace': 405,
            'dustwallow marsh': 15,
            'tanaris': 440,
            'un\'goro crater': 490,
            'azshara': 16,
            'felwood': 361,
            'winterspring': 618,
            'moonglade': 493,
            'darkshore': 148,
            'teldrassil': 141,
            'the exodar': 3557,
            'azuremyst isle': 3524,
            'bloodmyst isle': 3525,
            'feralas': 357,
            'silithus': 1377,
            
            # Cities
            'stormwind': 1519,
            'stormwind city': 1519,
            'ironforge': 1537,
            'darnassus': 1657,
            'orgrimmar': 1637,
            'undercity': 1497,
            'thunder bluff': 1638,
            'silvermoon': 3487,
            'silvermoon city': 3487,
            'shattrath': 3703,
            'shattrath city': 3703,
            'dalaran': 4395,
            
            # Outland (Burning Crusade)
            'hellfire peninsula': 3483,
            'zangarmarsh': 3521,
            'terokkar forest': 3519,
            'nagrand': 3518,
            'blade\'s edge mountains': 3522,
            'netherstorm': 3523,
            'shadowmoon valley': 3520,
            
            # Northrend (Wrath of the Lich King)
            'borean tundra': 3537,
            'dragonblight': 65,
            'grizzly hills': 394,
            'howling fjord': 495,
            'icecrown': 210,
            'sholazar basin': 3711,
            'storm peaks': 67,
            'wintergrasp': 4197,
            'zul\'drak': 66,
            'crystalsong forest': 2817,
            
            # Dungeons/Raids (commonly referenced)
            'deadmines': 1581,
            'wailing caverns': 718,
            'shadowfang keep': 209,
            'blackfathom deeps': 719,
            'gnomeregan': 721,
            'razorfen kraul': 1717,
            'razorfen downs': 722,
            'scarlet monastery': 796,
            'uldaman': 1337,
            'zul\'farrak': 1176,
            'maraudon': 2100,
            'sunken temple': 1417,
            'blackrock depths': 1584,
            'blackrock spire': 1583,
            'dire maul': 2557,
            'stratholme': 2017,
            'scholomance': 2057,
            
            # Special/Common incorrect mappings
            '85': 85,  # Often incorrectly used, needs context-based correction
            '440': 440,  # Tanaris (when given as number)
            '14': 14,   # Durotar (when given as number)
            '12': 12,   # Elwynn Forest (when given as number)
            
            # Subzones (these are VALID zone IDs too!)
            '154': 154,  # Deathknell (subzone of Tirisfal Glades)
            'deathknell': 154,
            '159': 159,  # Brill (subzone of Tirisfal Glades)
            'brill': 159
        }
        
        # Subzone to parent zone mapping
        # CRITICAL: NPCs must use parent zones, not subzones!
        self.subzone_to_parent = {
            154: 85,  # Deathknell -> Tirisfal Glades
            155: 85,  # Night Web's Hollow -> Tirisfal Glades
            156: 85,  # Solliden Farmstead -> Tirisfal Glades
            157: 85,  # Agamand Mills -> Tirisfal Glades
            158: 85,  # Agamand Family Crypt -> Tirisfal Glades
            159: 85,  # Brill -> Tirisfal Glades
            160: 85,  # Whispering Gardens -> Tirisfal Glades
            161: 85,  # Terrace of Repose -> Tirisfal Glades
            162: 85,  # Brightwater Lake -> Tirisfal Glades
            163: 85,  # Gunther's Retreat -> Tirisfal Glades
            164: 85,  # Garren's Haunt -> Tirisfal Glades
            165: 85,  # Crusader Outpost -> Tirisfal Glades
            166: 85,  # Scarlet Watch Post -> Tirisfal Glades
            167: 85,  # Venomweb Vale -> Tirisfal Glades
            2117: 85, # Shadow Grave -> Tirisfal Glades
            2118: 85, # Brill Town Hall -> Tirisfal Glades
            2119: 85, # Gallows' End Tavern -> Tirisfal Glades
            # Add more subzone mappings as needed
        }
        
        # Common aliases and misspellings
        self.aliases = {
            'stv': 'stranglethorn vale',
            'swamp': 'swamp of sorrows',
            'org': 'orgrimmar',
            'sw': 'stormwind',
            'if': 'ironforge',
            'uc': 'undercity',
            'tb': 'thunder bluff',
            'darn': 'darnassus',
            'shat': 'shattrath',
            'dal': 'dalaran',
            'wpl': 'western plaguelands',
            'epl': 'eastern plaguelands',
            'brm': 'blackrock mountain',
            'brd': 'blackrock depths',
            'ubrs': 'blackrock spire',
            'lbrs': 'blackrock spire',
            'dm': 'dire maul',
            'strat': 'stratholme',
            'scholo': 'scholomance',
            'sm': 'scarlet monastery',
            'wc': 'wailing caverns',
            'sfk': 'shadowfang keep',
            'bfd': 'blackfathom deeps',
            'stocks': 'the stockade',
            'gnomer': 'gnomeregan',
            'ulda': 'uldaman',
            'zf': 'zul\'farrak',
            'mara': 'maraudon',
            'st': 'sunken temple',
            'barrens': 'the barrens',
            'hinterlands': 'the hinterlands',
            'plaguelands': 'eastern plaguelands',
            'exodar': 'the exodar',
            'ungoro': 'un\'goro crater',
        }
        
        # Zone 85 context-based corrections
        self.zone_85_corrections = {
            'tirisfal': 85,  # Zone 85 IS Tirisfal Glades
            'undead': 85,    # Undead starting zone
            'deathknell': 85, # Starting subzone in Tirisfal
        }
    
    def get_zone_id(self, zone_name: str, context: dict = None) -> int:
        """
        Get zone ID from zone name
        
        Args:
            zone_name: Zone name from submission
            context: Additional context (faction, coordinates, etc)
                    Can include 'entity_type': 'npc' or 'quest'
            
        Returns:
            Zone ID or None if not found
        """
        if not zone_name:
            return None
        
        # Handle "Unknown" zone - return None so aggregator can try other methods
        if zone_name.lower() == "unknown":
            return None
        
        # Handle numeric zone IDs
        if isinstance(zone_name, int):
            return zone_name
        
        if isinstance(zone_name, str) and zone_name.isdigit():
            return int(zone_name)
        
        # Normalize zone name
        normalized = zone_name.lower().strip()
        
        # Check for alias first
        if normalized in self.aliases:
            normalized = self.aliases[normalized]
        
        # Direct lookup
        if normalized in self.zone_map:
            zone_id = self.zone_map[normalized]
            
            # CRITICAL: NPCs must use parent zones, not subzones!
            if context and context.get('entity_type') == 'npc':
                # If this is a subzone, convert to parent zone
                if zone_id in self.subzone_to_parent:
                    return self.subzone_to_parent[zone_id]
            
            return zone_id
        
        # Try removing common prefixes/suffixes
        for prefix in ['the ', 'zone ', 'area ']:
            if normalized.startswith(prefix):
                clean = normalized[len(prefix):]
                if clean in self.zone_map:
                    return self.zone_map[clean]
        
        # Handle zone 85 special cases with context
        if normalized == '85' and context:
            if context.get('faction') == 'Horde' or context.get('race') in ['Undead', 'Forsaken']:
                return 85  # Tirisfal Glades is correct
            else:
                # Need more context to determine correct zone
                return None
        
        # Fuzzy matching for common typos
        for zone, zone_id in self.zone_map.items():
            if self._fuzzy_match(normalized, zone):
                return zone_id
        
        return None
    
    def _fuzzy_match(self, input_str: str, target: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching for typos"""
        if len(input_str) < 3 or len(target) < 3:
            return False
        
        # Check if one contains the other
        if input_str in target or target in input_str:
            return True
        
        # Simple character match ratio
        matches = sum(1 for a, b in zip(input_str, target) if a == b)
        ratio = matches / max(len(input_str), len(target))
        
        return ratio >= threshold
    
    def get_zone_name(self, zone_id: int) -> str:
        """Reverse lookup: get zone name from ID"""
        for name, id in self.zone_map.items():
            if id == zone_id:
                return name.title()
        return f"Unknown Zone {zone_id}"
    
    def validate_coordinates(self, x: float, y: float, zone_id: int = None) -> bool:
        """
        Validate if coordinates are reasonable for WoW
        
        Args:
            x, y: Coordinates (should be 0-100)
            zone_id: Optional zone ID for zone-specific validation
            
        Returns:
            True if coordinates seem valid
        """
        # Basic range check
        if not (0 <= x <= 100 and 0 <= y <= 100):
            return False
        
        # Coordinates exactly at 0,0 or 100,100 are suspicious
        if (x == 0 and y == 0) or (x == 100 and y == 100):
            return False
        
        # Zone-specific validation could go here
        # For example, some zones have water/void areas
        
        return True
    
    def correct_zone_85(self, quest_data: dict) -> int:
        """
        Correct zone 85 based on quest context
        
        Zone 85 (Tirisfal Glades) is often incorrectly used for other zones
        in legacy data. This function attempts to correct it.
        """
        # If we have NPC or player faction info
        if quest_data.get('faction') == 'Alliance':
            # Alliance doesn't typically quest in Tirisfal
            # Might be Elwynn Forest (12) or Dun Morogh (1)
            if quest_data.get('race') in ['Human']:
                return 12  # Elwynn Forest
            elif quest_data.get('race') in ['Dwarf', 'Gnome']:
                return 1  # Dun Morogh
            elif quest_data.get('race') in ['Night Elf']:
                return 141  # Teldrassil
        
        # Check quest level for hints
        level = quest_data.get('level', 0)
        if level > 15:
            # Tirisfal is levels 1-10, so probably not correct
            return None
        
        # Default to keeping 85 if it seems appropriate
        return 85
    
    def get_common_zones(self) -> list:
        """Get list of most common quest zones for validation"""
        common = [
            'durotar', 'the barrens', 'elwynn forest', 'westfall',
            'tirisfal glades', 'silverpine forest', 'dun morogh',
            'teldrassil', 'darkshore', 'ashenvale', 'stonetalon mountains',
            'thousand needles', 'hillsbrad foothills', 'stranglethorn vale',
            'tanaris', 'un\'goro crater', 'winterspring', 'eastern plaguelands'
        ]
        return [(name, self.zone_map.get(name)) for name in common]
    
    def parse(self, content: str, quest_id: int = None) -> dict:
        """
        Parse zone data from quest submission
        
        CRITICAL: v1.0.68 and older had a bug where ALL zones were recorded as 85.
        We must detect and handle this bad data.
        
        Args:
            content: Full submission content
            quest_id: Optional quest ID
            
        Returns:
            Dictionary with zone mapping data
        """
        import re
        
        result = {
            'quest_id': quest_id,
            'addon_version': None,
            'has_legacy_bug': False,
            'zones_found': [],
            'zone_mappings': {},
            'invalid_zones': [],
            'corrected_zones': []
        }
        
        # Extract addon version
        version_match = re.search(r'Addon Version:\s*v?([\d.]+)', content, re.IGNORECASE)
        if version_match:
            result['addon_version'] = version_match.group(1)
            
            # Check if this is a legacy version with the zone 85 bug
            try:
                version_parts = result['addon_version'].split('.')
                major = int(version_parts[0]) if version_parts else 1
                minor = int(version_parts[1]) if len(version_parts) > 1 else 0
                patch = int(version_parts[2]) if len(version_parts) > 2 else 0
                
                # v1.0.68 and older have the zone 85 bug
                if major == 1 and minor == 0 and patch <= 68:
                    result['has_legacy_bug'] = True
            except:
                pass
        
        # Find all zone references
        zone_patterns = [
            r'Zone:\s*([^\n]+)',
            r'Location:.*?in\s+([^\n,]+)',
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*)',  # "in Durotar"
            r'zone_id"?\s*:\s*(\d+)',
            r'zoneID"?\s*:\s*(\d+)',
        ]
        
        for pattern in zone_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                zone = match.strip()
                if zone and zone not in result['zones_found']:
                    result['zones_found'].append(zone)
        
        # Process each zone found
        for zone_ref in result['zones_found']:
            # Check if it's the problematic zone 85
            if zone_ref == '85' or zone_ref == 85:
                if result['has_legacy_bug']:
                    # This is bad data from v1.0.68 or older
                    result['invalid_zones'].append({
                        'original': zone_ref,
                        'reason': 'v1.0.68 bug - all zones recorded as 85',
                        'actual_zone': 'UNKNOWN'
                    })
                    result['zone_mappings'][zone_ref] = None  # Mark as invalid
                else:
                    # Modern version, 85 might be legitimate (Tirisfal Glades)
                    # But still check context
                    if self._is_zone_85_valid(content):
                        result['zone_mappings'][zone_ref] = 85
                    else:
                        result['invalid_zones'].append({
                            'original': zone_ref,
                            'reason': 'Zone 85 seems incorrect based on context',
                            'actual_zone': 'UNKNOWN'
                        })
                        result['zone_mappings'][zone_ref] = None
            else:
                # Normal zone processing
                zone_id = self.get_zone_id(zone_ref)
                if zone_id:
                    result['zone_mappings'][zone_ref] = zone_id
                else:
                    result['invalid_zones'].append({
                        'original': zone_ref,
                        'reason': 'Unknown zone name',
                        'actual_zone': None
                    })
        
        # Try to correct invalid zones based on context
        if result['invalid_zones']:
            result['corrected_zones'] = self._attempt_zone_corrections(content, result['invalid_zones'])
        
        return result
    
    def _is_zone_85_valid(self, content: str) -> bool:
        """
        Check if zone 85 (Tirisfal Glades) makes sense in this context
        """
        import re
        
        # Look for indicators this is actually Tirisfal Glades
        tirisfal_indicators = [
            r'undead',
            r'forsaken',
            r'deathknell',
            r'brill',
            r'undercity',
            r'tirisfal',
            r'scarlet',
            r'agamand'
        ]
        
        content_lower = content.lower()
        for indicator in tirisfal_indicators:
            if re.search(indicator, content_lower):
                return True
        
        # Look for indicators it's NOT Tirisfal
        non_tirisfal = [
            r'alliance',
            r'stormwind',
            r'ironforge',
            r'darnassus',
            r'elwynn',
            r'westfall',
            r'durotar',
            r'orgrimmar',
            r'barrens'
        ]
        
        for indicator in non_tirisfal:
            if re.search(indicator, content_lower):
                return False
        
        # Default to invalid if we can't determine
        return False
    
    def _attempt_zone_corrections(self, content: str, invalid_zones: list) -> list:
        """
        Try to determine correct zones based on NPCs, quests, and other context
        """
        import re
        corrected = []
        
        # Extract additional context
        faction_match = re.search(r'Faction:\s*(Alliance|Horde)', content, re.IGNORECASE)
        faction = faction_match.group(1) if faction_match else None
        
        race_match = re.search(r'Race:\s*([^\n]+)', content, re.IGNORECASE)
        race = race_match.group(1).strip() if race_match else None
        
        level_match = re.search(r'Level:\s*(\d+)', content, re.IGNORECASE)
        level = int(level_match.group(1)) if level_match else None
        
        # Look for NPC names that indicate zones
        npc_zone_hints = {
            'marshal mcbride': 12,  # Elwynn Forest
            'deputy willem': 12,     # Elwynn Forest  
            'grull hawkwind': 215,   # Mulgore
            'sen\'jin': 14,          # Durotar
            'razor hill': 14,        # Durotar
            'goldshire': 12,         # Elwynn Forest
            'kharanos': 1,           # Dun Morogh
            'dolanaar': 141,         # Teldrassil
            'brill': 85,             # Tirisfal (legitimate)
            'crossroads': 17,        # The Barrens
        }
        
        content_lower = content.lower()
        for npc_hint, zone_id in npc_zone_hints.items():
            if npc_hint in content_lower:
                corrected.append({
                    'detected_zone_id': zone_id,
                    'detected_zone_name': self.get_zone_name(zone_id),
                    'confidence': 'high',
                    'reason': f'NPC/location "{npc_hint}" found in content'
                })
                break
        
        # Starting zone detection based on race
        if not corrected and race and level and level <= 10:
            race_zones = {
                'human': 12,      # Elwynn Forest
                'dwarf': 1,       # Dun Morogh
                'gnome': 1,       # Dun Morogh
                'night elf': 141, # Teldrassil
                'draenei': 3524,  # Azuremyst Isle
                'orc': 14,        # Durotar
                'troll': 14,      # Durotar  
                'tauren': 215,    # Mulgore
                'undead': 85,     # Tirisfal Glades (legitimate)
                'blood elf': 3430,# Eversong Woods
            }
            
            race_lower = race.lower()
            for race_name, zone_id in race_zones.items():
                if race_name in race_lower:
                    corrected.append({
                        'detected_zone_id': zone_id,
                        'detected_zone_name': self.get_zone_name(zone_id),
                        'confidence': 'medium',
                        'reason': f'{race} starting zone for level {level} quest'
                    })
                    break
        
        return corrected

def main():
    """Test the zone mapper"""
    mapper = ZoneMapper()
    
    # Test the parse method with legacy data
    print("\nTesting Legacy Zone 85 Bug Detection:\n" + "="*50)
    
    # Simulate v1.0.68 submission with zone 85
    legacy_content = """Addon Version: v1.0.68
Quest ID: 12345
Zone: 85
NPC: Grull Hawkwind
Location: 44.5, 77.2 in 85
"""
    
    result = mapper.parse(legacy_content, 12345)
    print(f"Version: {result['addon_version']}")
    print(f"Has Legacy Bug: {result['has_legacy_bug']}")
    print(f"Invalid Zones: {result['invalid_zones']}")
    print(f"Corrected Zones: {result['corrected_zones']}")
    print()
    
    # Simulate modern submission with zone 85 (should be valid if Tirisfal)
    modern_content = """Addon Version: v1.1.0
Quest ID: 98765  
Zone: 85
NPC: Deathguard Simmer
Location: Brill, Tirisfal Glades
"""
    
    result2 = mapper.parse(modern_content, 98765)
    print(f"Version: {result2['addon_version']}")
    print(f"Has Legacy Bug: {result2['has_legacy_bug']}") 
    print(f"Zone Mappings: {result2['zone_mappings']}")
    print()
    
    # Test cases
    test_zones = [
        ('Durotar', None),
        ('the barrens', None),
        ('The Barrens', None),
        ('barrens', None),
        ('85', {'faction': 'Horde'}),
        ('85', {'faction': 'Alliance'}),
        ('440', None),
        ('stv', None),
        ('Stranglethorn Vale', None),
        ('orgrimmar', None),
        ('Org', None),
        ('Invalid Zone Name', None),
    ]
    
    print("Zone Mapping Tests:\n" + "="*50)
    for zone_name, context in test_zones:
        zone_id = mapper.get_zone_id(zone_name, context)
        if zone_id:
            zone_name_back = mapper.get_zone_name(zone_id)
            print(f"✓ '{zone_name}' → Zone {zone_id} ({zone_name_back})")
        else:
            print(f"✗ '{zone_name}' → Not found")
    
    # Test coordinate validation
    print("\nCoordinate Validation Tests:\n" + "="*50)
    test_coords = [
        (50.5, 60.3, True),
        (0, 0, False),
        (100, 100, False),
        (-5, 50, False),
        (50, 101, False),
        (25.5, 75.8, True),
    ]
    
    for x, y, expected in test_coords:
        valid = mapper.validate_coordinates(x, y)
        status = "✓" if valid == expected else "✗"
        print(f"{status} ({x}, {y}) → {'Valid' if valid else 'Invalid'}")
    
    # Show common zones
    print("\nCommon Quest Zones:\n" + "="*50)
    for name, zone_id in mapper.get_common_zones()[:10]:
        print(f"  {name.title()}: {zone_id}")

if __name__ == "__main__":
    main()