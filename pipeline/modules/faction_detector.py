#!/usr/bin/env python3
"""
Faction Detector - Detect faction-specific quests from metadata
Uses submitter metadata and quest content to determine faction
"""

import re
import logging
from typing import Dict, Optional, List, Tuple


class FactionDetector:
    """
    Detects quest faction alignment using multiple signals:
    - Submitter character race/faction
    - NPC names and locations
    - Zone information
    - Quest text content
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Race to faction mapping
        self.race_factions = {
            # Alliance
            'human': 'Alliance',
            'dwarf': 'Alliance',
            'night elf': 'Alliance',
            'nightelf': 'Alliance',
            'gnome': 'Alliance',
            'draenei': 'Alliance',
            # Horde
            'orc': 'Horde',
            'undead': 'Horde',
            'forsaken': 'Horde',
            'tauren': 'Horde',
            'troll': 'Horde',
            'blood elf': 'Horde',
            'bloodelf': 'Horde',
        }
        
        # Faction-specific NPCs (lowercase for matching)
        self.faction_npcs = {
            'Alliance': [
                'king varian', 'varian wrynn', 'bolvar', 'magni bronzebeard',
                'tyrande', 'malfurion', 'jaina', 'anduin', 'marshal',
                'captain', 'guard thomas', 'deputy', 'magistrate',
                'sentinel', 'priestess', 'anchorite', 'vindicator',
                'stormwind', 'ironforge', 'darnassus', 'exodar',
            ],
            'Horde': [
                'thrall', 'sylvanas', "vol'jin", 'cairne', 'bloodhoof',
                'garrosh', 'saurfang', "lor'themar", 'baine',
                'grunt', 'peon', 'overseer', 'warchief', 'chieftain',
                'dark ranger', 'executor', 'deathguard', 'blademaster',
                'orgrimmar', 'undercity', 'thunder bluff', "silvermoon",
            ],
        }
        
        # Zone to faction mapping
        self.zone_factions = {
            # Alliance strongholds
            'elwynn forest': 'Alliance',
            'stormwind': 'Alliance',
            'westfall': 'Alliance',
            'redridge': 'Alliance',
            'duskwood': 'Alliance',
            'wetlands': 'Alliance',
            'ironforge': 'Alliance',
            'dun morogh': 'Alliance',
            'loch modan': 'Alliance',
            'teldrassil': 'Alliance',
            'darnassus': 'Alliance',
            'darkshore': 'Alliance',
            'ashenvale': 'Alliance',  # Contested but Alliance-leaning
            'azuremyst': 'Alliance',
            'bloodmyst': 'Alliance',
            'exodar': 'Alliance',
            
            # Horde strongholds
            'durotar': 'Horde',
            'orgrimmar': 'Horde',
            'the barrens': 'Horde',
            'northern barrens': 'Horde',
            'southern barrens': 'Horde',
            'mulgore': 'Horde',
            'thunder bluff': 'Horde',
            'tirisfal': 'Horde',
            'tirisfal glades': 'Horde',
            'undercity': 'Horde',
            'silverpine': 'Horde',
            'silverpine forest': 'Horde',
            'hillsbrad': 'Horde',  # Contested but Horde-leaning
            'eversong': 'Horde',
            'eversong woods': 'Horde',
            'ghostlands': 'Horde',
            'silvermoon': 'Horde',
            
            # Neutral/Contested
            'stranglethorn': 'Neutral',
            'tanaris': 'Neutral',
            'winterspring': 'Neutral',
            'un\'goro': 'Neutral',
            'silithus': 'Neutral',
            'eastern plaguelands': 'Neutral',
            'western plaguelands': 'Neutral',
        }
        
        # Faction-specific keywords in quest text
        self.faction_keywords = {
            'Alliance': [
                'for the alliance', 'alliance', 'light', 'holy light',
                'elune', 'moon goddess', 'naaru', 'honor', 'nobility',
                'justice', 'peace', 'protect the innocent', 'defenders',
                'blue and gold', 'lion', 'gryphon', 'griffin',
            ],
            'Horde': [
                'for the horde', 'horde', "lok'tar", 'victory or death',
                'blood and thunder', 'strength and honor', 'spirits',
                'ancestors', 'earthmother', 'warchief', 'dark lady',
                'forsaken', 'red and black', 'wyvern', 'wolf',
            ],
        }
    
    def detect(self, quest_data: Dict, submitter_metadata: Optional[Dict] = None) -> Tuple[str, float]:
        """
        Detect faction for a quest
        
        Args:
            quest_data: Quest information
            submitter_metadata: Metadata about who submitted the quest
            
        Returns:
            (faction, confidence) where faction is 'Alliance', 'Horde', or 'Neutral'
            and confidence is 0.0-1.0
        """
        signals = {
            'Alliance': 0,
            'Horde': 0,
            'Neutral': 0,
        }
        
        # Signal 1: Submitter's character faction (strongest signal)
        if submitter_metadata:
            submitter_faction = self._detect_from_submitter(submitter_metadata)
            if submitter_faction and submitter_faction != 'Neutral':
                signals[submitter_faction] += 3.0
                self.logger.debug(f"Submitter faction: {submitter_faction} (+3.0)")
        
        # Signal 2: NPC names
        npc_faction = self._detect_from_npcs(quest_data)
        if npc_faction and npc_faction != 'Neutral':
            signals[npc_faction] += 2.0
            self.logger.debug(f"NPC faction: {npc_faction} (+2.0)")
        
        # Signal 3: Zone information
        zone_faction = self._detect_from_zone(quest_data)
        if zone_faction and zone_faction != 'Neutral':
            signals[zone_faction] += 1.5
            self.logger.debug(f"Zone faction: {zone_faction} (+1.5)")
        
        # Signal 4: Quest text content
        text_faction = self._detect_from_text(quest_data)
        if text_faction and text_faction != 'Neutral':
            signals[text_faction] += 1.0
            self.logger.debug(f"Text faction: {text_faction} (+1.0)")
        
        # Signal 5: Race/class restrictions
        restriction_faction = self._detect_from_restrictions(quest_data)
        if restriction_faction and restriction_faction != 'Neutral':
            signals[restriction_faction] += 2.5
            self.logger.debug(f"Restriction faction: {restriction_faction} (+2.5)")
        
        # Determine faction based on signals
        faction, confidence = self._determine_faction(signals)
        
        # Log the decision
        quest_id = quest_data.get('quest_id', 'Unknown')
        quest_name = quest_data.get('name', 'Unknown')
        self.logger.info(
            f"Quest {quest_id} '{quest_name}': {faction} (confidence: {confidence:.2f})"
        )
        
        return faction, confidence
    
    def _detect_from_submitter(self, metadata: Dict) -> Optional[str]:
        """Detect faction from submitter metadata"""
        # Direct faction field
        if metadata.get('faction'):
            return metadata['faction']
        
        # From race
        race = metadata.get('race', '').lower()
        if race in self.race_factions:
            return self.race_factions[race]
        
        # From character name patterns (less reliable)
        char_name = metadata.get('character_name', '').lower()
        if any(orc in char_name for orc in ['grom', 'thrall', 'garrosh']):
            return 'Horde'
        if any(human in char_name for human in ['anduin', 'varian', 'uther']):
            return 'Alliance'
        
        return None
    
    def _detect_from_npcs(self, quest_data: Dict) -> Optional[str]:
        """Detect faction from NPC names"""
        alliance_count = 0
        horde_count = 0
        
        # Check quest giver and turn-in NPCs
        all_npc_names = []
        
        # Get NPC names from various fields
        if quest_data.get('quest_giver_name'):
            all_npc_names.append(quest_data['quest_giver_name'].lower())
        if quest_data.get('turn_in_npc_name'):
            all_npc_names.append(quest_data['turn_in_npc_name'].lower())
        if quest_data.get('npc_names'):
            all_npc_names.extend([n.lower() for n in quest_data['npc_names']])
        
        # Check against faction NPC lists
        for npc_name in all_npc_names:
            for alliance_npc in self.faction_npcs['Alliance']:
                if alliance_npc in npc_name:
                    alliance_count += 1
                    break
            
            for horde_npc in self.faction_npcs['Horde']:
                if horde_npc in npc_name:
                    horde_count += 1
                    break
        
        if alliance_count > horde_count:
            return 'Alliance'
        elif horde_count > alliance_count:
            return 'Horde'
        
        return None
    
    def _detect_from_zone(self, quest_data: Dict) -> Optional[str]:
        """Detect faction from zone information"""
        zones = []
        
        # Collect all zone references
        if quest_data.get('zone'):
            zones.append(quest_data['zone'].lower())
        if quest_data.get('quest_giver_zone'):
            zones.append(quest_data['quest_giver_zone'].lower())
        if quest_data.get('turn_in_zone'):
            zones.append(quest_data['turn_in_zone'].lower())
        if quest_data.get('zones'):
            zones.extend([z.lower() for z in quest_data['zones']])
        
        # Check zones against faction mapping
        faction_votes = {'Alliance': 0, 'Horde': 0, 'Neutral': 0}
        
        for zone in zones:
            for zone_name, faction in self.zone_factions.items():
                if zone_name in zone or zone in zone_name:
                    faction_votes[faction] += 1
        
        # Return faction with most votes
        if faction_votes['Alliance'] > faction_votes['Horde']:
            return 'Alliance'
        elif faction_votes['Horde'] > faction_votes['Alliance']:
            return 'Horde'
        elif faction_votes['Neutral'] > 0:
            return 'Neutral'
        
        return None
    
    def _detect_from_text(self, quest_data: Dict) -> Optional[str]:
        """Detect faction from quest text content"""
        # Combine all text fields
        all_text = []
        
        if quest_data.get('name'):
            all_text.append(quest_data['name'])
        if quest_data.get('objectives'):
            if isinstance(quest_data['objectives'], str):
                all_text.append(quest_data['objectives'])
            elif isinstance(quest_data['objectives'], list):
                all_text.extend(quest_data['objectives'])
        if quest_data.get('description'):
            all_text.append(quest_data['description'])
        if quest_data.get('objectivesText'):
            if isinstance(quest_data['objectivesText'], list):
                all_text.extend(quest_data['objectivesText'])
            else:
                all_text.append(str(quest_data['objectivesText']))
        
        combined_text = ' '.join(all_text).lower()
        
        # Check for faction keywords
        alliance_score = 0
        horde_score = 0
        
        for keyword in self.faction_keywords['Alliance']:
            if keyword in combined_text:
                alliance_score += 1
        
        for keyword in self.faction_keywords['Horde']:
            if keyword in combined_text:
                horde_score += 1
        
        if alliance_score > horde_score:
            return 'Alliance'
        elif horde_score > alliance_score:
            return 'Horde'
        
        return None
    
    def _detect_from_restrictions(self, quest_data: Dict) -> Optional[str]:
        """Detect faction from race/class restrictions"""
        # Check race restrictions
        race_restrictions = quest_data.get('requiredRaces', [])
        if race_restrictions:
            if isinstance(race_restrictions, str):
                race_restrictions = [race_restrictions]
            
            alliance_races = 0
            horde_races = 0
            
            for race in race_restrictions:
                race_lower = race.lower()
                if race_lower in self.race_factions:
                    faction = self.race_factions[race_lower]
                    if faction == 'Alliance':
                        alliance_races += 1
                    elif faction == 'Horde':
                        horde_races += 1
            
            if alliance_races > 0 and horde_races == 0:
                return 'Alliance'
            elif horde_races > 0 and alliance_races == 0:
                return 'Horde'
        
        # Check if explicitly marked as faction-specific
        if quest_data.get('faction'):
            return quest_data['faction']
        
        return None
    
    def _determine_faction(self, signals: Dict[str, float]) -> Tuple[str, float]:
        """
        Determine final faction based on weighted signals
        
        Returns:
            (faction, confidence)
        """
        total_signal = sum(signals.values())
        
        if total_signal == 0:
            return 'Neutral', 0.0
        
        # Calculate percentages
        alliance_pct = signals['Alliance'] / total_signal
        horde_pct = signals['Horde'] / total_signal
        
        # Determine faction
        if alliance_pct > 0.6:
            return 'Alliance', alliance_pct
        elif horde_pct > 0.6:
            return 'Horde', horde_pct
        elif abs(alliance_pct - horde_pct) < 0.2:
            # Too close to call - neutral
            return 'Neutral', 1.0 - abs(alliance_pct - horde_pct)
        elif alliance_pct > horde_pct:
            return 'Alliance', alliance_pct
        else:
            return 'Horde', horde_pct
    
    def analyze_batch(self, quests: List[Dict], metadata_map: Dict = None) -> Dict:
        """
        Analyze faction distribution in a batch of quests
        
        Args:
            quests: List of quest data
            metadata_map: Map of quest_id to submitter metadata
            
        Returns:
            Analysis results
        """
        results = {
            'total': len(quests),
            'alliance': [],
            'horde': [],
            'neutral': [],
            'confidence_stats': {
                'high': [],  # >0.8
                'medium': [],  # 0.5-0.8
                'low': [],  # <0.5
            },
        }
        
        for quest in quests:
            quest_id = quest.get('quest_id', 'Unknown')
            metadata = metadata_map.get(quest_id) if metadata_map else None
            
            faction, confidence = self.detect(quest, metadata)
            
            # Categorize by faction
            entry = {'quest_id': quest_id, 'confidence': confidence}
            if faction == 'Alliance':
                results['alliance'].append(entry)
            elif faction == 'Horde':
                results['horde'].append(entry)
            else:
                results['neutral'].append(entry)
            
            # Categorize by confidence
            if confidence > 0.8:
                results['confidence_stats']['high'].append(quest_id)
            elif confidence > 0.5:
                results['confidence_stats']['medium'].append(quest_id)
            else:
                results['confidence_stats']['low'].append(quest_id)
        
        return results


def main():
    """Test the faction detector"""
    detector = FactionDetector()
    
    # Test with Alliance quest
    alliance_quest = {
        'quest_id': 100,
        'name': 'Defend Stormwind',
        'quest_giver_name': 'Marshal Dughan',
        'zone': 'Elwynn Forest',
        'objectives': 'Protect Stormwind from the Horde invasion',
    }
    
    # Test with Horde quest
    horde_quest = {
        'quest_id': 200,
        'name': 'For the Horde!',
        'quest_giver_name': 'Thrall',
        'zone': 'Orgrimmar',
        'objectives': "Complete Thrall's mission in Durotar",
    }
    
    # Test with submitter metadata
    alliance_metadata = {
        'race': 'Human',
        'faction': 'Alliance',
        'character_name': 'Defender',
    }
    
    # Detect factions
    faction, conf = detector.detect(alliance_quest, alliance_metadata)
    print(f"Alliance Quest: {faction} (confidence: {conf:.2f})")
    
    faction, conf = detector.detect(horde_quest)
    print(f"Horde Quest: {faction} (confidence: {conf:.2f})")


if __name__ == "__main__":
    main()