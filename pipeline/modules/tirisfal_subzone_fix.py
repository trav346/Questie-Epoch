"""
Tirisfal Glades Subzone Detection
Based on coordinate analysis from existing NPCs

CRITICAL: Questie requires subzone IDs, not parent zones
"""

# Tirisfal Glades subzones with coordinate boundaries
TIRISFAL_SUBZONES = {
    'Deathknell': {
        'zone_id': 154,
        'center': (29.5, 71.0),
        'radius': 5,  # Small starting area
        'description': 'Undead starting area'
    },
    'Brill': {
        'zone_id': 159,
        'center': (60.5, 51.5),
        'radius': 8,  # Town and immediate surroundings
        'description': 'Main Horde town in Tirisfal'
    },
    'The Bulwark': {
        'zone_id': 85,  # Uses parent zone
        'center': (83.0, 72.0),
        'radius': 5,
        'description': 'Eastern fortification'
    },
    'Scarlet Monastery': {
        'zone_id': 85,  # Uses parent zone
        'center': (85.0, 30.0),
        'radius': 10,
        'description': 'Dungeon entrance area'
    }
}

def get_tirisfal_subzone(x: float, y: float) -> int:
    """
    Determine the correct subzone ID for coordinates in Tirisfal Glades
    
    Args:
        x: X coordinate (0-100)
        y: Y coordinate (0-100)
    
    Returns:
        Zone ID (154 for Deathknell, 159 for Brill, 85 for rest)
    """
    # Check each subzone
    for subzone_name, data in TIRISFAL_SUBZONES.items():
        center_x, center_y = data['center']
        radius = data['radius']
        
        # Calculate distance from center
        distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
        
        if distance <= radius:
            return data['zone_id']
    
    # Default to parent zone
    return 85

def fix_zone_for_tirisfal(zone_id: int, coordinates: list) -> int:
    """
    Fix zone ID for Tirisfal Glades based on coordinates
    
    Args:
        zone_id: Current zone ID (probably 85)
        coordinates: List of (x, y) tuples
    
    Returns:
        Corrected zone ID
    """
    if zone_id != 85 or not coordinates:
        return zone_id
    
    # Use first coordinate to determine subzone
    if isinstance(coordinates[0], (list, tuple)) and len(coordinates[0]) >= 2:
        x, y = coordinates[0][0], coordinates[0][1]
        return get_tirisfal_subzone(x, y)
    
    return zone_id

# Known NPCs in each subzone for reference
KNOWN_NPCS = {
    154: {  # Deathknell
        'Undertaker Mordo': (30.2, 71.7),
        'Shadow Priest Sarvis': (30.8, 66.2),
        'Novice Elreth': (29.9, 71.5)
    },
    159: {  # Brill
        'Innkeeper Renee': (61.7, 52.1),
        'Historian Todd Page': (60.6, 51.0),
        'Jasper Greene': (38.9, 52.8),
        'Magistrate Sevren': (61.2, 50.8),
        'Deathguard Burgess': (65.5, 60.2)
    }
}

if __name__ == "__main__":
    # Test with known coordinates
    test_cases = [
        ((60.6, 51.0), "Historian Todd Page in Brill"),
        ((61.7, 52.1), "Innkeeper Renee in Brill"),
        ((30.2, 71.7), "Undertaker Mordo in Deathknell"),
        ((50.0, 50.0), "Random point in Tirisfal"),
        ((83.0, 72.0), "The Bulwark")
    ]
    
    for (x, y), description in test_cases:
        zone = get_tirisfal_subzone(x, y)
        print(f"[{x}, {y}] - {description}: zone {zone}")