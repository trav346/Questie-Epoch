#!/usr/bin/env python3
"""
Coordinate Parser Module - Objective-aware coordinate extraction with quality filtering
Only extracts coordinates that are RELEVANT to quest objectives
Acts as a critical quality filter to prevent incorrect map markers
"""

import re
from typing import Dict, List, Optional, Tuple, Set
import math
from collections import defaultdict

class CoordinateParser:
    """
    Parses and validates coordinate data based on quest objectives.
    Only extracts coordinates for entities that are actually quest targets.
    """
    
    def __init__(self):
        self.parsed_coords = []
        self.dedup_radius = 2.0  # Deduplication radius
        self.coordinate_database = defaultdict(lambda: {
            'entity_type': None,
            'entity_name': None,
            'sightings': [],
            'zones': set(),
            'centroid': None,
            'frequency': 0,
            'quest_associations': set()
        })
        
    def parse(self, content: str, quest_id: int = None) -> Dict:
        """
        Parse coordinate data that matches quest objectives.
        
        Returns:
            Dictionary with objective-matched coordinate data
        """
        result = {
            'quest_id': quest_id,
            'addon_version': self._extract_version(content),
            'objectives': self._extract_objectives(content),
            'valid_entries': [],
            'rejected_entries': [],
            'manual_review_needed': [],
            'npcs_with_coords': {},
            'objects_with_coords': {},
            'summary': {
                'total_found': 0,
                'total_valid': 0,
                'total_rejected': 0,
                'completeness_score': 0,
                'objectives_matched': 0,
                'objectives_total': 0
            }
        }
        
        # First, extract quest objectives to know what we're looking for
        objectives = result['objectives']
        if not objectives or not any(objectives.values()):
            # No objectives found - flag for manual review
            result['manual_review_needed'].append({
                'reason': 'no_objectives_found',
                'message': 'Cannot extract quest objectives - manual review needed'
            })
        
        # Extract quest giver and turn-in NPCs (always relevant)
        quest_npcs = self._extract_quest_npcs(content)
        
        # Extract objective-relevant coordinates
        objective_coords = self._extract_objective_coordinates(content, objectives)
        
        # Combine all entries
        all_entries = quest_npcs + objective_coords
        
        # Process and validate each entry
        for entry in all_entries:
            result['summary']['total_found'] += 1
            
            # Validate entry has complete data
            validation_result = self._validate_entry(entry)
            if validation_result['valid']:
                result['valid_entries'].append(entry)
                result['summary']['total_valid'] += 1
                
                # Categorize by type
                if entry['entity_type'] == 'npc':
                    npc_id = entry.get('entity_id')
                    # Use ID if available, otherwise use name as key
                    npc_key = npc_id if npc_id else f"name_{entry['entity_name']}"
                    
                    if npc_key not in result['npcs_with_coords']:
                        result['npcs_with_coords'][npc_key] = {
                            'name': entry['entity_name'],
                            'id': npc_id,  # May be None
                            'coordinates': [],
                            'zones': set(),
                            'purpose': entry.get('purpose', 'unknown'),
                            'objective_link': entry.get('objective_link')
                        }
                    
                    result['npcs_with_coords'][npc_key]['coordinates'].append({
                        'x': entry['x'], 'y': entry['y']
                    })
                    if entry.get('zone'):
                        result['npcs_with_coords'][npc_key]['zones'].add(entry['zone'])
                        
                elif entry['entity_type'] == 'object':
                    obj_name = entry['entity_name']
                    if obj_name not in result['objects_with_coords']:
                        result['objects_with_coords'][obj_name] = {
                            'name': obj_name,
                            'coordinates': [],
                            'zones': set(),
                            'interaction_type': entry.get('interaction_type', 'interact'),
                            'objective_link': entry.get('objective_link')
                        }
                    result['objects_with_coords'][obj_name]['coordinates'].append({
                        'x': entry['x'], 'y': entry['y']
                    })
                    if entry.get('zone'):
                        result['objects_with_coords'][obj_name]['zones'].add(entry['zone'])
                
                # Add to global database
                self._add_to_database(entry, quest_id)
            else:
                # Add rejection reason
                entry['rejection_reason'] = validation_result['reason']
                result['rejected_entries'].append(entry)
                result['summary']['total_rejected'] += 1
                
                # Check if needs manual review
                if validation_result.get('needs_review'):
                    result['manual_review_needed'].append({
                        'reason': validation_result['reason'],
                        'entry': entry
                    })
        
        # Calculate completeness score based on objectives
        result['summary'] = self._calculate_completeness(result, objectives)
        
        # Clean up zone sets for JSON serialization
        for npc_data in result['npcs_with_coords'].values():
            npc_data['zones'] = list(npc_data['zones'])
        for obj_data in result['objects_with_coords'].values():
            obj_data['zones'] = list(obj_data['zones'])
        
        return result
    
    def _extract_objectives(self, content: str) -> Dict:
        """Extract quest objectives to understand what coordinates we need."""
        objectives = {
            'kill': [],      # NPCs to kill
            'collect': [],   # Items to collect (and their sources)
            'interact': [],  # Objects to interact with
            'deliver': [],   # Items to deliver
            'explore': []    # Locations to explore
        }
        
        # Find OBJECTIVES section
        obj_section = re.search(r'OBJECTIVES:?\s*\n(.*?)(?:\n\n|\nQUEST|\nTURN|\nGROUND|\Z)', 
                                content, re.DOTALL | re.IGNORECASE)
        if not obj_section:
            return objectives
        
        obj_text = obj_section.group(1)
        
        # Parse each objective line
        lines = obj_text.split('\n')
        current_objective = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for numbered objectives (e.g., "1. Hatefury Claw: 10/10 (item)")
            obj_match = re.match(r'\d+\.\s+(.+?):\s*(\d+)/(\d+)\s*\((\w+)\)', line)
            if obj_match:
                obj_name = obj_match.group(1)
                obj_count = obj_match.group(2)
                obj_total = obj_match.group(3)
                obj_type = obj_match.group(4).lower()
                
                current_objective = {
                    'name': obj_name,
                    'count': int(obj_total),
                    'type': obj_type,
                    'sources': []
                }
                
                if obj_type == 'item':
                    objectives['collect'].append(current_objective)
                elif obj_type in ['creature', 'monster', 'npc']:
                    objectives['kill'].append(current_objective)
                elif obj_type == 'object':
                    objectives['interact'].append(current_objective)
            
            # Parse item sources from progress locations
            elif current_objective and 'Looted' in line:
                # e.g., "- [72.6, 22.5] in Desolace - Looted Hatefury Claw from Hatefury Trickster"
                loot_match = re.search(r'Looted\s+.+?\s+from\s+(.+?)$', line)
                if loot_match:
                    mob_name = loot_match.group(1).strip()
                    if mob_name not in current_objective['sources']:
                        current_objective['sources'].append(mob_name)
            
            # Check for kill objectives in other formats
            elif 'kill' in line.lower() or 'slay' in line.lower() or 'defeat' in line.lower():
                kill_match = re.search(r'(?:kill|slay|defeat)\s+(\d+)\s+(.+?)(?:\s|$)', line, re.IGNORECASE)
                if kill_match:
                    objectives['kill'].append({
                        'name': kill_match.group(2).strip(),
                        'count': int(kill_match.group(1)),
                        'type': 'creature',
                        'sources': []
                    })
        
        return objectives
    
    def _extract_quest_npcs(self, content: str) -> List[Dict]:
        """Extract quest giver and turn-in NPC coordinates (always relevant)."""
        entries = []
        
        # Quest giver
        giver_match = re.search(
            r'QUEST GIVER:?\s*\n\s*(?:NPC:)?\s*(.+?)\s*\(ID:\s*(\d+)\).*?\n.*?Location:\s*\[?([\d.]+),\s*([\d.]+)\]?(?:\s*\n\s*Zone:\s*([^\n]+))?',
            content, re.DOTALL | re.IGNORECASE
        )
        if giver_match:
            entries.append({
                'entity_type': 'npc',
                'entity_name': giver_match.group(1).strip(),
                'entity_id': int(giver_match.group(2)),
                'x': float(giver_match.group(3)),
                'y': float(giver_match.group(4)),
                'zone': giver_match.group(5).strip() if giver_match.group(5) else None,
                'purpose': 'quest_giver',
                'always_relevant': True
            })
        
        # Turn-in NPC
        turnin_match = re.search(
            r'TURN-?IN NPC:?\s*\n\s*(?:NPC:)?\s*(.+?)\s*\(ID:\s*(\d+)\).*?\n.*?Location:\s*\[?([\d.]+),\s*([\d.]+)\]?',
            content, re.DOTALL | re.IGNORECASE
        )
        if turnin_match:
            entries.append({
                'entity_type': 'npc',
                'entity_name': turnin_match.group(1).strip(),
                'entity_id': int(turnin_match.group(2)),
                'x': float(turnin_match.group(3)),
                'y': float(turnin_match.group(4)),
                'zone': None,  # Will try to extract zone from context
                'purpose': 'quest_turnin',
                'always_relevant': True
            })
        
        return entries
    
    def _extract_objective_coordinates(self, content: str, objectives: Dict) -> List[Dict]:
        """Extract coordinates only for entities mentioned in objectives."""
        entries = []
        
        # Build list of all relevant entity names from objectives
        relevant_entities = set()
        
        # Add kill targets
        for kill_obj in objectives.get('kill', []):
            relevant_entities.add(kill_obj['name'].lower())
        
        # Add item sources (mobs that drop quest items)
        for collect_obj in objectives.get('collect', []):
            for source in collect_obj.get('sources', []):
                relevant_entities.add(source.lower())
        
        # Add interact objects
        for interact_obj in objectives.get('interact', []):
            relevant_entities.add(interact_obj['name'].lower())
        
        if not relevant_entities:
            # No specific entities identified - might need manual review
            return entries
        
        # Now extract coordinates from progress locations in OBJECTIVES section
        obj_section = re.search(r'OBJECTIVES:?\s*\n(.*?)(?:\n\n|\nQUEST|\nTURN|\nGROUND|\Z)', 
                                content, re.DOTALL | re.IGNORECASE)
        if obj_section:
            obj_text = obj_section.group(1)
            
            # Parse progress locations
            # Format: "- [72.6, 22.5] in Desolace - Looted Hatefury Claw from Hatefury Trickster"
            progress_pattern = r'\[?([\d.]+),\s*([\d.]+)\]?\s+in\s+([^\n-]+?)(?:\s*-\s*(.+))?$'
            
            for match in re.finditer(progress_pattern, obj_text, re.MULTILINE):
                x = float(match.group(1))
                y = float(match.group(2))
                zone = match.group(3).strip()
                action = match.group(4).strip() if match.group(4) else ""
                
                # Extract entity from action
                entity_name = None
                entity_type = 'npc'  # Default
                purpose = 'objective'
                objective_link = None
                
                if 'from' in action:
                    # e.g., "Looted Hatefury Claw from Hatefury Trickster"
                    from_match = re.search(r'from\s+(.+?)$', action)
                    if from_match:
                        entity_name = from_match.group(1).strip()
                        purpose = 'kill_target'
                        
                        # Link to objective
                        item_match = re.search(r'Looted\s+(.+?)\s+from', action)
                        if item_match:
                            objective_link = item_match.group(1).strip()
                
                elif 'at' in action:
                    # e.g., "Interacted with Ancient Gem at"
                    at_match = re.search(r'(?:with|at)\s+(.+?)(?:\s+at)?$', action)
                    if at_match:
                        entity_name = at_match.group(1).strip()
                        entity_type = 'object'
                        purpose = 'interact'
                
                # Check if this entity is relevant to objectives
                if entity_name and entity_name.lower() in relevant_entities:
                    entries.append({
                        'entity_type': entity_type,
                        'entity_name': entity_name,
                        'entity_id': None,  # Will need to get from mob data if available
                        'x': x,
                        'y': y,
                        'zone': zone,
                        'purpose': purpose,
                        'objective_link': objective_link,
                        'from_objectives': True
                    })
        
        # Also check for mob IDs in tracked mobs section if it exists
        tracked_section = re.search(r'TRACKED QUEST MOBS:?\s*\n(.*?)(?:\n\n|\Z)', 
                                    content, re.DOTALL | re.IGNORECASE)
        if tracked_section:
            mob_lines = tracked_section.group(1).split('\n')
            for line in mob_lines:
                # Format: "Hatefury Trickster (ID: 4670, Level: 28-29) at 71.3, 19.1 in Desolace"
                mob_match = re.search(r'(.+?)\s*\(ID:\s*(\d+)[^)]*\)\s*at\s*([\d.]+),\s*([\d.]+)(?:\s+in\s+(.+))?', line)
                if mob_match:
                    mob_name = mob_match.group(1).strip()
                    if mob_name.lower() in relevant_entities:
                        # Update entries with missing IDs
                        mob_id = int(mob_match.group(2))
                        for entry in entries:
                            if entry['entity_name'] == mob_name and entry['entity_id'] is None:
                                entry['entity_id'] = mob_id
                        
                        # Also add this as a new entry if coordinates don't match existing
                        x = float(mob_match.group(3))
                        y = float(mob_match.group(4))
                        zone = mob_match.group(5).strip() if mob_match.group(5) else None
                        
                        # Check if we already have this coordinate
                        coord_exists = any(
                            abs(e['x'] - x) < 0.5 and abs(e['y'] - y) < 0.5 and e['entity_name'] == mob_name
                            for e in entries
                        )
                        
                        if not coord_exists:
                            entries.append({
                                'entity_type': 'npc',
                                'entity_name': mob_name,
                                'entity_id': mob_id,
                                'x': x,
                                'y': y,
                                'zone': zone,
                                'purpose': 'kill_target',
                                'from_tracked_mobs': True
                            })
        
        return entries
    
    def _validate_entry(self, entry: Dict) -> Dict:
        """
        Validate entry has all required data.
        Returns validation result with reason if invalid.
        """
        # Always valid if it's a quest NPC
        if entry.get('always_relevant'):
            if entry.get('entity_id') and entry.get('x') and entry.get('y'):
                return {'valid': True}
        
        # Must have entity name
        if not entry.get('entity_name') or entry['entity_name'] == 'Unknown':
            return {
                'valid': False,
                'reason': 'missing_entity_name',
                'needs_review': False
            }
        
        # Coordinates validation
        x = entry.get('x')
        y = entry.get('y')
        if x is None or y is None:
            return {
                'valid': False,
                'reason': 'missing_coordinates',
                'needs_review': True
            }
        
        # Check coordinate range
        if not (0 < x < 100 and 0 < y < 100):
            return {
                'valid': False,
                'reason': 'invalid_coordinate_range',
                'needs_review': False
            }
        
        # For NPCs, we prefer to have IDs but it's not absolutely required if from objectives
        if entry.get('entity_type') == 'npc' and not entry.get('entity_id'):
            if entry.get('from_objectives'):
                # Accept it but flag for review
                return {
                    'valid': True,
                    'warning': 'missing_npc_id'
                }
            else:
                return {
                    'valid': False,
                    'reason': 'missing_entity_id',
                    'needs_review': True
                }
        
        # Check for legacy zone 85 bug
        if entry.get('zone') in ['85', 85]:
            version = entry.get('addon_version', '')
            if version and version.startswith('v1.0.'):
                try:
                    parts = version.replace('v', '').split('.')
                    if len(parts) >= 3 and int(parts[2]) <= 68:
                        return {
                            'valid': False,
                            'reason': 'legacy_zone_85_bug',
                            'needs_review': False
                        }
                except:
                    pass
        
        return {'valid': True}
    
    def _calculate_completeness(self, result: Dict, objectives: Dict) -> Dict:
        """Calculate completeness score based on objective coverage."""
        summary = result['summary']
        
        # Count total objectives
        total_objectives = (
            len(objectives.get('kill', [])) +
            len(objectives.get('collect', [])) +
            len(objectives.get('interact', []))
        )
        summary['objectives_total'] = total_objectives
        
        # Count matched objectives
        matched = 0
        
        # Check kill objectives
        for kill_obj in objectives.get('kill', []):
            # Check if we have coordinates for this target
            for npc_data in result['npcs_with_coords'].values():
                if npc_data['name'].lower() == kill_obj['name'].lower():
                    matched += 1
                    break
        
        # Check collect objectives (via their sources)
        for collect_obj in objectives.get('collect', []):
            for source in collect_obj.get('sources', []):
                for npc_data in result['npcs_with_coords'].values():
                    if npc_data['name'].lower() == source.lower():
                        matched += 1
                        break
                    break
        
        # Check interact objectives
        for interact_obj in objectives.get('interact', []):
            for obj_data in result['objects_with_coords'].values():
                if obj_data['name'].lower() == interact_obj['name'].lower():
                    matched += 1
                    break
        
        summary['objectives_matched'] = matched
        
        # Calculate completeness score
        if total_objectives > 0:
            objective_coverage = (matched / total_objectives) * 100
        else:
            objective_coverage = 0
        
        # Factor in coordinate quality
        if summary['total_found'] > 0:
            quality_rate = (summary['total_valid'] / summary['total_found']) * 100
        else:
            quality_rate = 0
        
        # Weighted score: 70% objective coverage, 30% quality
        summary['completeness_score'] = (objective_coverage * 0.7) + (quality_rate * 0.3)
        
        return summary
    
    def _add_to_database(self, entry: Dict, quest_id: int):
        """Add validated entry to global coordinate database."""
        if entry.get('entity_type') == 'npc' and entry.get('entity_id'):
            entity_key = f"npc_{entry['entity_id']}"
        elif entry.get('entity_type') == 'object':
            entity_key = f"object_{entry['entity_name']}"
        else:
            return  # Skip entries without proper identification
        
        db_entry = self.coordinate_database[entity_key]
        db_entry['entity_type'] = entry['entity_type']
        db_entry['entity_name'] = entry['entity_name']
        
        # Add sighting
        sighting = {
            'x': entry['x'],
            'y': entry['y'],
            'zone': entry.get('zone'),
            'quest_id': quest_id,
            'purpose': entry.get('purpose')
        }
        
        # Check for duplicate coordinates
        is_duplicate = any(
            abs(s['x'] - sighting['x']) < self.dedup_radius and
            abs(s['y'] - sighting['y']) < self.dedup_radius
            for s in db_entry['sightings']
        )
        
        if not is_duplicate:
            db_entry['sightings'].append(sighting)
            db_entry['frequency'] += 1
            
            if entry.get('zone'):
                db_entry['zones'].add(entry['zone'])
            
            if quest_id:
                db_entry['quest_associations'].add(quest_id)
            
            # Recalculate centroid
            if len(db_entry['sightings']) > 1:
                avg_x = sum(s['x'] for s in db_entry['sightings']) / len(db_entry['sightings'])
                avg_y = sum(s['y'] for s in db_entry['sightings']) / len(db_entry['sightings'])
                db_entry['centroid'] = {'x': round(avg_x, 1), 'y': round(avg_y, 1)}
    
    def _extract_version(self, content: str) -> str:
        """Extract addon version from content."""
        version_match = re.search(r'Addon Version:\s*([^\n]+)', content, re.IGNORECASE)
        if version_match:
            return version_match.group(1).strip()
        return 'Unknown'
    
    def get_database_summary(self) -> Dict:
        """Get summary of accumulated coordinate database."""
        npcs = sum(1 for k in self.coordinate_database if k.startswith('npc_'))
        objects = sum(1 for k in self.coordinate_database if k.startswith('object_'))
        
        total_sightings = sum(
            len(entry['sightings']) 
            for entry in self.coordinate_database.values()
        )
        
        multi_sighting = sum(
            1 for entry in self.coordinate_database.values()
            if len(entry['sightings']) > 1
        )
        
        patrol_paths = sum(
            1 for entry in self.coordinate_database.values()
            if len(entry['sightings']) > 3
        )
        
        return {
            'total_entities': len(self.coordinate_database),
            'npcs': npcs,
            'objects': objects,
            'total_sightings': total_sightings,
            'entities_with_multiple_sightings': multi_sighting,
            'entities_with_patrol_paths': patrol_paths
        }