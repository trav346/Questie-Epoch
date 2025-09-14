#!/usr/bin/env python3
"""
Restriction Analyzer Module - Advanced detection of class/race/faction restrictions
Analyzes submission patterns to detect implicit restrictions and quest targeting
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import json

class RestrictionAnalyzer:
    """Analyzes quest restrictions based on submission patterns and content"""
    
    def __init__(self):
        self.analyzed_restrictions = {}
        self.submission_patterns = defaultdict(list)
        
        # Race/Class/Faction mappings
        self.race_ids = {
            'human': 1, 'orc': 2, 'dwarf': 4, 'night elf': 8, 'undead': 16,
            'tauren': 32, 'gnome': 64, 'troll': 128, 'goblin': 256,
            'blood elf': 512, 'draenei': 1024
        }
        
        self.class_ids = {
            'warrior': 1, 'paladin': 2, 'hunter': 4, 'rogue': 8, 'priest': 16,
            'death knight': 32, 'shaman': 64, 'mage': 128, 'warlock': 256, 'druid': 1024
        }
        
        # Faction groupings
        self.alliance_races = {'human', 'dwarf', 'night elf', 'gnome', 'draenei'}
        self.horde_races = {'orc', 'undead', 'tauren', 'troll', 'blood elf'}
        
        # Class availability by race (WotLK)
        self.class_race_matrix = {
            'human': {'warrior', 'paladin', 'hunter', 'rogue', 'priest', 'mage', 'warlock'},
            'orc': {'warrior', 'hunter', 'rogue', 'shaman', 'mage', 'warlock'},
            'dwarf': {'warrior', 'paladin', 'hunter', 'rogue', 'priest'},
            'night elf': {'warrior', 'hunter', 'rogue', 'priest', 'druid'},
            'undead': {'warrior', 'rogue', 'priest', 'mage', 'warlock'},
            'tauren': {'warrior', 'hunter', 'shaman', 'druid'},
            'gnome': {'warrior', 'rogue', 'mage', 'warlock'},
            'troll': {'warrior', 'hunter', 'rogue', 'priest', 'shaman', 'mage'},
            'blood elf': {'warrior', 'paladin', 'hunter', 'rogue', 'priest', 'mage', 'warlock'},
            'draenei': {'warrior', 'paladin', 'hunter', 'priest', 'shaman', 'mage'}
        }
        
        # Starting zone restrictions
        self.racial_starting_zones = {
            'human': [12, 40, 1519],  # Elwynn, Westfall, Stormwind
            'dwarf': [1, 38, 1537],   # Dun Morogh, Loch Modan, Ironforge
            'gnome': [1, 38, 1537],   # Same as dwarf
            'night elf': [141, 148, 1657],  # Teldrassil, Darkshore, Darnassus
            'draenei': [3524, 3525, 3557],  # Azuremyst, Bloodmyst, Exodar
            'orc': [14, 17, 1637],    # Durotar, Barrens, Orgrimmar
            'troll': [14, 17, 1637],  # Same as orc
            'undead': [85, 130, 1497], # Tirisfal, Silverpine, Undercity
            'tauren': [215, 17, 1638], # Mulgore, Barrens, Thunder Bluff
            'blood elf': [3430, 3433, 3487]  # Eversong, Ghostlands, Silvermoon
        }
        
    def analyze(self, quest_data: Dict, submission_history: List[Dict] = None) -> Dict:
        """
        Analyze quest restrictions based on content and submission patterns
        
        Args:
            quest_data: Parsed quest data
            submission_history: Historical submissions for this quest
            
        Returns:
            Dictionary with detected restrictions and confidence levels
        """
        quest_id = quest_data.get('id')
        
        analysis = {
            'quest_id': quest_id,
            'detected_restrictions': {
                'race': None,
                'class': None,
                'faction': None,
                'level': None
            },
            'confidence_scores': {
                'race': 0.0,
                'class': 0.0,
                'faction': 0.0,
                'level': 0.0
            },
            'evidence': {
                'content_based': [],
                'pattern_based': [],
                'zone_based': [],
                'npc_based': [],
                'submission_based': []
            },
            'recommendations': [],
            'alternative_explanations': []
        }
        
        # Analyze quest content for restriction hints
        self._analyze_content_restrictions(quest_data, analysis)
        
        # Analyze zone-based restrictions
        self._analyze_zone_restrictions(quest_data, analysis)
        
        # Analyze NPC-based restrictions
        self._analyze_npc_restrictions(quest_data, analysis)
        
        # Analyze submission patterns if available
        if submission_history:
            self._analyze_submission_patterns(submission_history, analysis)
        
        # Calculate final confidence and make recommendations
        self._finalize_analysis(analysis)
        
        self.analyzed_restrictions[quest_id] = analysis
        return analysis
    
    def _analyze_content_restrictions(self, quest_data: Dict, analysis: Dict):
        """Analyze quest text content for restriction hints"""
        
        # Get all text content
        all_text = self._extract_all_text(quest_data)
        text_lower = all_text.lower()
        
        # Class-specific content analysis
        class_indicators = {
            'warrior': ['warrior', 'fighter', 'weapon master', 'combat training', 'strength'],
            'paladin': ['paladin', 'holy warrior', 'light', 'divine', 'righteousness'],
            'hunter': ['hunter', 'track', 'beast', 'ranged', 'pet', 'trap'],
            'rogue': ['rogue', 'stealth', 'lockpicking', 'poison', 'backstab', 'thief'],
            'priest': ['priest', 'heal', 'holy', 'shadow', 'divine', 'blessing'],
            'shaman': ['shaman', 'spirit', 'elemental', 'totem', 'earth', 'ancestors'],
            'mage': ['mage', 'magic', 'spell', 'arcane', 'frost', 'fire', 'wizard'],
            'warlock': ['warlock', 'demon', 'fel', 'shadow', 'curse', 'soul'],
            'druid': ['druid', 'nature', 'shapeshif', 'wild', 'grove', 'balance'],
            'death knight': ['death knight', 'undeath', 'plague', 'unholy', 'frost']
        }
        
        class_scores = {}
        for class_name, indicators in class_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score > 0:
                class_scores[class_name] = score
                analysis['evidence']['content_based'].append(f"Class indicator '{class_name}': {score} matches")
        
        if class_scores:
            best_class = max(class_scores, key=class_scores.get)
            analysis['detected_restrictions']['class'] = best_class
            analysis['confidence_scores']['class'] = min(class_scores[best_class] * 0.2, 1.0)
        
        # Race-specific content analysis
        race_indicators = {
            'human': ['human', 'stormwind', 'alliance', 'kingdom'],
            'orc': ['orc', 'horde', 'orgrimmar', 'lok\'tar'],
            'dwarf': ['dwarf', 'dwarven', 'ironforge', 'mountain', 'beard'],
            'night elf': ['night elf', 'kaldorei', 'darnassus', 'ancient'],
            'undead': ['undead', 'forsaken', 'undercity', 'scourge', 'plague'],
            'tauren': ['tauren', 'thunder bluff', 'great spirit', 'earth mother'],
            'gnome': ['gnome', 'tinker', 'mechanic', 'invention'],
            'troll': ['troll', 'darkspear', 'voodoo', 'spirits', 'mon'],
            'blood elf': ['blood elf', 'sin\'dorei', 'silvermoon', 'magic addiction'],
            'draenei': ['draenei', 'exodar', 'naaru', 'light']
        }
        
        race_scores = {}
        for race_name, indicators in race_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score > 0:
                race_scores[race_name] = score
                analysis['evidence']['content_based'].append(f"Race indicator '{race_name}': {score} matches")
        
        if race_scores:
            best_race = max(race_scores, key=race_scores.get)
            analysis['detected_restrictions']['race'] = best_race
            analysis['confidence_scores']['race'] = min(race_scores[best_race] * 0.3, 1.0)
        
        # Faction analysis
        alliance_indicators = ['alliance', 'stormwind', 'ironforge', 'darnassus', 'exodar']
        horde_indicators = ['horde', 'orgrimmar', 'undercity', 'thunder bluff', 'silvermoon']
        
        alliance_score = sum(1 for indicator in alliance_indicators if indicator in text_lower)
        horde_score = sum(1 for indicator in horde_indicators if indicator in text_lower)
        
        if alliance_score > horde_score and alliance_score > 0:
            analysis['detected_restrictions']['faction'] = 'Alliance'
            analysis['confidence_scores']['faction'] = min(alliance_score * 0.3, 1.0)
            analysis['evidence']['content_based'].append(f"Alliance indicators: {alliance_score}")
        elif horde_score > alliance_score and horde_score > 0:
            analysis['detected_restrictions']['faction'] = 'Horde'
            analysis['confidence_scores']['faction'] = min(horde_score * 0.3, 1.0)
            analysis['evidence']['content_based'].append(f"Horde indicators: {horde_score}")
    
    def _analyze_zone_restrictions(self, quest_data: Dict, analysis: Dict):
        """Analyze zone-based restrictions"""
        
        zone_id = quest_data.get('zoneOrSort')
        if not zone_id or zone_id <= 0:
            return
        
        # Check if zone is racial starting area
        for race_name, zones in self.racial_starting_zones.items():
            if zone_id in zones:
                # Starting zone suggests racial restriction
                if race_name in self.alliance_races:
                    faction = 'Alliance'
                else:
                    faction = 'Horde'
                
                analysis['evidence']['zone_based'].append(f"Zone {zone_id} is {race_name} starting area")
                
                # Update faction restriction
                if not analysis['detected_restrictions']['faction']:
                    analysis['detected_restrictions']['faction'] = faction
                    analysis['confidence_scores']['faction'] = 0.7
                
                # Update race restriction if not already detected
                if not analysis['detected_restrictions']['race']:
                    analysis['detected_restrictions']['race'] = race_name
                    analysis['confidence_scores']['race'] = 0.6
                
                break
        
        # Level restrictions based on zone
        zone_level_hints = {
            # Alliance starting zones
            12: (1, 10),    # Elwynn Forest
            40: (10, 20),   # Westfall
            44: (20, 30),   # Redridge Mountains
            
            # Horde starting zones
            14: (1, 10),    # Durotar
            17: (10, 25),   # The Barrens
            130: (10, 20),  # Silverpine Forest
            
            # High level zones
            139: (50, 60),  # Eastern Plaguelands
            28: (50, 60),   # Western Plaguelands
            4: (40, 50),    # Blasted Lands
        }
        
        if zone_id in zone_level_hints:
            min_level, max_level = zone_level_hints[zone_id]
            analysis['evidence']['zone_based'].append(f"Zone {zone_id} suggests levels {min_level}-{max_level}")
            
            quest_level = quest_data.get('questLevel', 0)
            if min_level <= quest_level <= max_level:
                analysis['confidence_scores']['level'] = 0.8
    
    def _analyze_npc_restrictions(self, quest_data: Dict, analysis: Dict):
        """Analyze NPC-based restrictions"""
        
        # Check quest giver and turn-in NPCs
        quest_giver_id = quest_data.get('quest_giver_npc_id')
        turn_in_id = quest_data.get('turn_in_npc_id')
        
        # NPC faction affiliations (would normally come from NPC database)
        # For now, we can infer from NPC names in the content
        all_text = self._extract_all_text(quest_data)
        
        # Faction-specific NPC name patterns
        alliance_npc_patterns = [
            r'captain\s+\w+',
            r'marshal\s+\w+',
            r'knight\s+\w+',
            r'guard\s+\w+',
            r'stormwind\s+\w+',
            r'ironforge\s+\w+'
        ]
        
        horde_npc_patterns = [
            r'warchief\s+\w+',
            r'grunt\s+\w+',
            r'overseer\s+\w+',
            r'orgrimmar\s+\w+',
            r'undercity\s+\w+'
        ]
        
        alliance_matches = sum(1 for pattern in alliance_npc_patterns 
                             if re.search(pattern, all_text, re.IGNORECASE))
        horde_matches = sum(1 for pattern in horde_npc_patterns 
                          if re.search(pattern, all_text, re.IGNORECASE))
        
        if alliance_matches > horde_matches and alliance_matches > 0:
            analysis['evidence']['npc_based'].append(f"Alliance NPC patterns: {alliance_matches}")
            if not analysis['detected_restrictions']['faction']:
                analysis['detected_restrictions']['faction'] = 'Alliance'
                analysis['confidence_scores']['faction'] = 0.6
        elif horde_matches > alliance_matches and horde_matches > 0:
            analysis['evidence']['npc_based'].append(f"Horde NPC patterns: {horde_matches}")
            if not analysis['detected_restrictions']['faction']:
                analysis['detected_restrictions']['faction'] = 'Horde'
                analysis['confidence_scores']['faction'] = 0.6
    
    def _analyze_submission_patterns(self, submission_history: List[Dict], analysis: Dict):
        """Analyze patterns from multiple submissions"""
        
        if len(submission_history) < 2:
            return
        
        # Analyze submitter demographics
        submitter_races = defaultdict(int)
        submitter_classes = defaultdict(int)
        submitter_factions = defaultdict(int)
        
        for submission in submission_history:
            race = submission.get('race', '').lower()
            class_name = submission.get('class', '').lower()
            faction = submission.get('faction', '').lower()
            
            if race:
                submitter_races[race] += 1
            if class_name:
                submitter_classes[class_name] += 1
            if faction:
                submitter_factions[faction] += 1
        
        total_submissions = len(submission_history)
        
        # If >80% of submissions are from one faction, likely restricted
        for faction, count in submitter_factions.items():
            if count / total_submissions > 0.8:
                analysis['detected_restrictions']['faction'] = faction.title()
                analysis['confidence_scores']['faction'] = count / total_submissions
                analysis['evidence']['submission_based'].append(
                    f"{count}/{total_submissions} submissions from {faction}")
        
        # If >70% of submissions are from one race, possibly restricted
        for race, count in submitter_races.items():
            if count / total_submissions > 0.7:
                if not analysis['detected_restrictions']['race']:
                    analysis['detected_restrictions']['race'] = race
                    analysis['confidence_scores']['race'] = count / total_submissions
                    analysis['evidence']['submission_based'].append(
                        f"{count}/{total_submissions} submissions from {race}")
        
        # If >60% of submissions are from one class, possibly restricted
        for class_name, count in submitter_classes.items():
            if count / total_submissions > 0.6:
                if not analysis['detected_restrictions']['class']:
                    analysis['detected_restrictions']['class'] = class_name
                    analysis['confidence_scores']['class'] = count / total_submissions
                    analysis['evidence']['submission_based'].append(
                        f"{count}/{total_submissions} submissions from {class_name}")
    
    def _finalize_analysis(self, analysis: Dict):
        """Finalize analysis and generate recommendations"""
        
        detected = analysis['detected_restrictions']
        confidence = analysis['confidence_scores']
        
        # Cross-validate race and faction restrictions
        if detected['race'] and detected['faction']:
            race = detected['race']
            faction = detected['faction']
            
            expected_faction = 'Alliance' if race in self.alliance_races else 'Horde'
            
            if faction != expected_faction:
                analysis['alternative_explanations'].append(
                    f"Race {race} is {expected_faction} but detected faction is {faction}")
                # Reduce confidence in one or both
                if confidence['race'] > confidence['faction']:
                    confidence['faction'] *= 0.5
                else:
                    confidence['race'] *= 0.5
        
        # Cross-validate class and race restrictions
        if detected['class'] and detected['race']:
            class_name = detected['class']
            race = detected['race']
            
            if race in self.class_race_matrix:
                available_classes = self.class_race_matrix[race]
                if class_name not in available_classes:
                    analysis['alternative_explanations'].append(
                        f"Class {class_name} not available to {race}")
                    confidence['class'] *= 0.3
        
        # Generate recommendations based on confidence levels
        for restriction_type, conf in confidence.items():
            if conf > 0.8:
                analysis['recommendations'].append(
                    f"High confidence {restriction_type} restriction: {detected[restriction_type]}")
            elif conf > 0.6:
                analysis['recommendations'].append(
                    f"Likely {restriction_type} restriction: {detected[restriction_type]} (verify)")
            elif conf > 0.4:
                analysis['recommendations'].append(
                    f"Possible {restriction_type} restriction: {detected[restriction_type]} (investigate)")
    
    def _extract_all_text(self, quest_data: Dict) -> str:
        """Extract all text content from quest data"""
        text_parts = []
        
        # Quest name and basic info
        if quest_data.get('name'):
            text_parts.append(quest_data['name'])
        
        # Objectives
        if quest_data.get('objectives_text'):
            text_parts.append(quest_data['objectives_text'])
        
        if quest_data.get('objectives_list'):
            text_parts.extend(quest_data['objectives_list'])
        
        # Additional text fields
        for field in ['quest_text', 'completion_text', 'zone', 'subzone']:
            if quest_data.get(field):
                text_parts.append(quest_data[field])
        
        return ' '.join(str(part) for part in text_parts).lower()
    
    def generate_restriction_masks(self, analysis: Dict) -> Dict:
        """Generate bitmask values for detected restrictions"""
        masks = {
            'race_mask': None,
            'class_mask': None
        }
        
        detected = analysis['detected_restrictions']
        confidence = analysis['confidence_scores']
        
        # Only generate masks for high-confidence restrictions
        if detected['race'] and confidence['race'] > 0.6:
            race = detected['race']
            if race in self.race_ids:
                masks['race_mask'] = self.race_ids[race]
        
        if detected['class'] and confidence['class'] > 0.6:
            class_name = detected['class']
            if class_name in self.class_ids:
                masks['class_mask'] = self.class_ids[class_name]
        
        # Faction-based race mask
        if detected['faction'] and confidence['faction'] > 0.7 and not masks['race_mask']:
            faction = detected['faction']
            if faction == 'Alliance':
                masks['race_mask'] = sum(self.race_ids[race] for race in self.alliance_races)
            elif faction == 'Horde':
                masks['race_mask'] = sum(self.race_ids[race] for race in self.horde_races)
        
        return masks
    
    def get_summary(self) -> Dict:
        """Get analysis summary"""
        if not self.analyzed_restrictions:
            return {'message': 'No restrictions analyzed yet'}
        
        total_analyzed = len(self.analyzed_restrictions)
        
        restriction_counts = {
            'race': 0,
            'class': 0,
            'faction': 0
        }
        
        confidence_levels = {
            'high': 0,    # >0.8
            'medium': 0,  # 0.6-0.8
            'low': 0      # 0.4-0.6
        }
        
        for analysis in self.analyzed_restrictions.values():
            detected = analysis['detected_restrictions']
            confidence = analysis['confidence_scores']
            
            for restriction_type in restriction_counts:
                if detected[restriction_type]:
                    restriction_counts[restriction_type] += 1
                    
                    conf = confidence[restriction_type]
                    if conf > 0.8:
                        confidence_levels['high'] += 1
                    elif conf > 0.6:
                        confidence_levels['medium'] += 1
                    elif conf > 0.4:
                        confidence_levels['low'] += 1
        
        return {
            'total_analyzed': total_analyzed,
            'restrictions_detected': restriction_counts,
            'confidence_distribution': confidence_levels
        }

def main():
    """Test the restriction analyzer"""
    import sys
    
    # Test with sample data
    sample_quest = {
        'id': 12345,
        'name': 'Warrior Training',
        'quest_text': 'The warrior trainer needs you to prove your strength in combat.',
        'objectives_text': 'Defeat 5 enemies using warrior abilities',
        'zone': 'Elwynn Forest',
        'quest_giver_npc_id': 1234,
        'questLevel': 5
    }
    
    # Sample submission history
    sample_history = [
        {'race': 'human', 'class': 'warrior', 'faction': 'alliance'},
        {'race': 'dwarf', 'class': 'warrior', 'faction': 'alliance'},
        {'race': 'night elf', 'class': 'warrior', 'faction': 'alliance'},
    ]
    
    analyzer = RestrictionAnalyzer()
    analysis = analyzer.analyze(sample_quest, sample_history)
    
    print(f"\nRestriction Analysis:")
    print(f"Detected Restrictions:")
    for restriction_type, value in analysis['detected_restrictions'].items():
        if value:
            confidence = analysis['confidence_scores'][restriction_type]
            print(f"  {restriction_type}: {value} (confidence: {confidence:.2f})")
    
    print(f"\nEvidence:")
    for evidence_type, evidence_list in analysis['evidence'].items():
        if evidence_list:
            print(f"  {evidence_type}:")
            for evidence in evidence_list:
                print(f"    - {evidence}")
    
    if analysis['recommendations']:
        print(f"\nRecommendations:")
        for rec in analysis['recommendations']:
            print(f"  - {rec}")
    
    masks = analyzer.generate_restriction_masks(analysis)
    print(f"\nGenerated Masks:")
    for mask_type, value in masks.items():
        if value:
            print(f"  {mask_type}: {value}")
    
    print(f"\nSummary: {json.dumps(analyzer.get_summary(), indent=2)}")

if __name__ == "__main__":
    main()