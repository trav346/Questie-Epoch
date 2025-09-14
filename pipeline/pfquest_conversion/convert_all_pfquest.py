#!/usr/bin/env python3

import re
import os
from datetime import datetime

def parse_pfquest_quests(filepath):
    """Parse pfQuest quest data with complete extraction"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    quests = {}
    
    # Split by quest entries and parse each
    quest_blocks = re.split(r'\n\s*\[(\d+)\]\s*=\s*', content)
    
    for i in range(1, len(quest_blocks), 2):
        quest_id = int(quest_blocks[i])
        quest_data = quest_blocks[i+1]
        
        # Skip removed quests
        if quest_data.strip() == '"_",' or quest_data.strip().startswith('"_"'):
            continue
        
        # Extract the full quest block
        block_end = quest_data.find('\n  [')
        if block_end == -1:
            block = quest_data
        else:
            block = quest_data[:block_end]
        
        quest_info = {
            'id': quest_id,
            'level': None,
            'min_level': None,
            'start_npcs': [],
            'end_npcs': [],
            'race': None,
            'pre': None,
            'next': None,
            'objectives': {}
        }
        
        # Extract level
        level_match = re.search(r'\["lvl"\]\s*=\s*(\d+)', block)
        if level_match:
            quest_info['level'] = int(level_match.group(1))
        
        # Extract min level
        min_match = re.search(r'\["min"\]\s*=\s*(\d+)', block)
        if min_match:
            quest_info['min_level'] = int(min_match.group(1))
        
        # Extract race/faction
        race_match = re.search(r'\["race"\]\s*=\s*(\d+)', block)
        if race_match:
            quest_info['race'] = int(race_match.group(1))
        
        # Extract prerequisite
        pre_match = re.search(r'\["pre"\]\s*=\s*\{\s*(\d+)', block)
        if pre_match:
            quest_info['pre'] = int(pre_match.group(1))
        
        # Extract next quest
        next_match = re.search(r'\["next"\]\s*=\s*(\d+)', block)
        if next_match:
            quest_info['next'] = int(next_match.group(1))
        
        # Extract start NPCs
        start_match = re.search(r'\["start"\]\s*=\s*\{[^}]*\["U"\]\s*=\s*\{([^}]+)\}', block)
        if start_match:
            npc_ids = re.findall(r'\d+', start_match.group(1))
            quest_info['start_npcs'] = [int(npc) for npc in npc_ids]
        
        # Extract end NPCs  
        end_match = re.search(r'\["end"\]\s*=\s*\{[^}]*\["U"\]\s*=\s*\{([^}]+)\}', block)
        if end_match:
            npc_ids = re.findall(r'\d+', end_match.group(1))
            quest_info['end_npcs'] = [int(npc) for npc in npc_ids]
        
        # Extract objectives (items, NPCs to kill, etc.)
        obj_match = re.search(r'\["obj"\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', block)
        if obj_match:
            obj_block = obj_match.group(1)
            
            # Extract item objectives
            item_match = re.search(r'\["I"\]\s*=\s*\{([^}]+)\}', obj_block)
            if item_match:
                item_ids = re.findall(r'\d+', item_match.group(1))
                quest_info['objectives']['items'] = [int(item) for item in item_ids]
            
            # Extract NPC kill objectives
            npc_match = re.search(r'\["U"\]\s*=\s*\{([^}]+)\}', obj_block)
            if npc_match:
                npc_ids = re.findall(r'\d+', npc_match.group(1))
                quest_info['objectives']['npcs'] = [int(npc) for npc in npc_ids]
        
        quests[quest_id] = quest_info
    
    return quests

def parse_pfquest_texts(filepath):
    """Parse pfQuest quest text data"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    texts = {}
    
    # Split by quest entries
    quest_blocks = re.split(r'\n\s*\[(\d+)\]\s*=\s*', content)
    
    for i in range(1, len(quest_blocks), 2):
        quest_id = int(quest_blocks[i])
        quest_data = quest_blocks[i+1]
        
        # Extract the full quest block
        block_end = quest_data.find('\n  [')
        if block_end == -1:
            block = quest_data
        else:
            block = quest_data[:block_end]
        
        text_info = {}
        
        # Extract title
        title_match = re.search(r'\["T"\]\s*=\s*"([^"]+(?:\\"[^"]*)*)"', block)
        if title_match:
            text_info['title'] = title_match.group(1).replace('\\"', '"').replace('\\\'', "'")
        
        # Extract objectives
        obj_match = re.search(r'\["O"\]\s*=\s*"([^"]+(?:\\"[^"]*)*)"', block)
        if obj_match:
            text_info['objectives'] = obj_match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\\'', "'")
        
        # Extract description
        desc_match = re.search(r'\["D"\]\s*=\s*"([^"]+(?:\\"[^"]*)*)"', block)
        if desc_match:
            text_info['description'] = desc_match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\\'', "'")
        
        if text_info:
            texts[quest_id] = text_info
    
    return texts

def parse_pfquest_npcs(filepath):
    """Parse pfQuest NPC/unit data"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    npcs = {}
    
    # Parse NPC entries
    npc_blocks = re.split(r'\n\s*\[(\d+)\]\s*=\s*', content)
    
    for i in range(1, len(npc_blocks), 2):
        npc_id = int(npc_blocks[i])
        npc_data = npc_blocks[i+1]
        
        # Extract the full NPC block
        block_end = npc_data.find('\n  [')
        if block_end == -1:
            block = npc_data
        else:
            block = npc_data[:block_end]
        
        npc_info = {
            'id': npc_id,
            'coords': [],
            'faction': None,
            'level': None
        }
        
        # Extract coordinates
        coords_match = re.search(r'\["coords"\]\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', block)
        if coords_match:
            coord_block = coords_match.group(1)
            # Parse individual coordinates
            coord_matches = re.findall(r'\{\s*([\d.]+),\s*([\d.]+),\s*(\d+)', coord_block)
            for x, y, zone in coord_matches:
                npc_info['coords'].append({
                    'x': float(x),
                    'y': float(y),
                    'zone': int(zone)
                })
        
        # Extract faction
        fac_match = re.search(r'\["fac"\]\s*=\s*"([AH])"', block)
        if fac_match:
            npc_info['faction'] = fac_match.group(1)
        
        # Extract level
        lvl_match = re.search(r'\["lvl"\]\s*=\s*"(\d+)"', block)
        if lvl_match:
            npc_info['level'] = int(lvl_match.group(1))
        
        if npc_info['coords'] or npc_info['faction'] or npc_info['level']:
            npcs[npc_id] = npc_info
    
    return npcs

def parse_pfquest_npc_names(filepath):
    """Parse pfQuest NPC names from enUS file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    names = {}
    
    # Parse name entries
    name_matches = re.finditer(r'\[(\d+)\]\s*=\s*\{\s*\["N"\]\s*=\s*"([^"]+)"', content)
    
    for match in name_matches:
        npc_id = int(match.group(1))
        npc_name = match.group(2)
        names[npc_id] = npc_name
    
    return names

def convert_faction(race_flag):
    """Convert pfQuest race flag to Questie faction"""
    if not race_flag:
        return 3  # Both factions
    
    # Alliance races: 1 (Human), 4 (Night Elf), 8 (Gnome), 64 (Draenei) = 77
    alliance_flags = [1, 3, 4, 5, 7, 8, 64, 65, 68, 69, 71, 72, 73, 76, 77]
    
    # Horde races: 2 (Orc), 16 (Tauren), 32 (Troll), 128 (Blood Elf) = 178
    horde_flags = [2, 10, 16, 18, 32, 128, 130, 138, 146, 154, 162, 170, 178]
    
    if race_flag in alliance_flags:
        return 2  # Alliance
    elif race_flag in horde_flags:
        return 1  # Horde
    else:
        return 3  # Both factions

def convert_npc_faction(fac_str):
    """Convert pfQuest NPC faction to Questie format"""
    if fac_str == 'A':
        return 2  # Alliance
    elif fac_str == 'H':
        return 1  # Horde
    else:
        return 3  # Both/Neutral

def generate_questie_quest_db(quests, texts):
    """Generate Questie format quest database"""
    output = []
    output.append("-- Auto-generated from pfQuest-epoch database")
    output.append(f"-- Generated on {datetime.now()}")
    output.append("-- This file contains ALL quests from pfQuest converted to Questie format")
    output.append("")
    output.append("local QuestieLoader = {}")
    output.append("QuestieLoader.ImportModule = function() return {} end")
    output.append("local QuestieDB = QuestieLoader:ImportModule(\"QuestieDB\")")
    output.append("")
    output.append("pfQuestConvertedData = {")
    
    for quest_id in sorted(quests.keys()):
        quest = quests[quest_id]
        text = texts.get(quest_id, {})
        
        # Skip quests without titles
        if not text.get('title'):
            continue
        
        # Build Questie format entry
        title = text['title'].replace('"', '\\"')
        level = quest['level'] or 1
        faction = convert_faction(quest['race'])
        
        line = f'  [{quest_id}] = {{"{title}",'
        
        # Start NPCs
        if quest['start_npcs']:
            line += '{{' + ','.join(map(str, quest['start_npcs'])) + '}},'
        else:
            line += 'nil,'
        
        # End NPCs
        if quest['end_npcs']:
            line += '{{' + ','.join(map(str, quest['end_npcs'])) + '}},'
        else:
            line += 'nil,'
        
        # Required skill, level, quest level, faction
        line += f'nil,{level},nil,{faction},'
        
        # Objectives
        if text.get('objectives'):
            objectives = text['objectives'].replace('"', '\\"')
            line += f'{{"{objectives}"}},'.replace('$B', ' ').replace('$N', 'Hero')
        else:
            line += 'nil,'
        
        # Add objective NPCs/items if present
        if quest['objectives']:
            # For now, just nil - could be expanded to include detailed objectives
            line += 'nil,'
        else:
            line += 'nil,'
        
        # More fields (most will be nil for pfQuest data)
        line += 'nil,nil,nil,'
        
        # Prerequisite
        if quest['pre']:
            line += f'{quest["pre"]},'
        else:
            line += 'nil,'
        
        # More nil fields
        line += 'nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,0,'
        
        # Prerequisite again
        if quest['pre']:
            line += f'{quest["pre"]},'
        else:
            line += 'nil,'
        
        # Final nil fields
        line += 'nil,nil,nil,nil,nil},'
        
        # Add comment with level and source
        line += f' -- Level {level}, pfQuest-epoch'
        
        output.append(line)
    
    output.append("}")
    output.append("")
    output.append("-- Export for merging")
    output.append("return pfQuestConvertedData")
    
    return '\n'.join(output)

def generate_questie_npc_db(npcs, npc_names):
    """Generate Questie format NPC database"""
    output = []
    output.append("-- Auto-generated from pfQuest-epoch NPC database")
    output.append(f"-- Generated on {datetime.now()}")
    output.append("")
    output.append("pfQuestNpcData = {")
    
    for npc_id in sorted(npcs.keys()):
        npc = npcs[npc_id]
        name = npc_names.get(npc_id, f"NPC {npc_id}")
        
        # Skip NPCs without coordinates
        if not npc['coords']:
            continue
        
        # Group coordinates by zone
        zones = {}
        for coord in npc['coords']:
            zone = coord['zone']
            if zone not in zones:
                zones[zone] = []
            zones[zone].append([coord['x'], coord['y']])
        
        # Build coordinate string
        coord_str = '{'
        for zone, coords in zones.items():
            coord_str += f'[{zone}]={{'
            for x, y in coords:
                coord_str += f'{{{x:.1f},{y:.1f}}},'
            coord_str = coord_str.rstrip(',') + '},'
        coord_str = coord_str.rstrip(',') + '}'
        
        # Determine faction
        faction = convert_npc_faction(npc.get('faction'))
        level = npc.get('level', 1)
        
        # Build NPC entry
        line = f'  [{npc_id}] = {{"{name}",nil,nil,{level},{level},0,{coord_str},nil,'
        
        # Get primary zone (first zone with coords)
        primary_zone = list(zones.keys())[0] if zones else 0
        line += f'{primary_zone},'
        
        # Quest starts/ends (we don't have this data from pfQuest, so nil)
        line += 'nil,nil,'
        
        # Faction
        line += f'{faction},'
        
        # Alliance/Horde indicator
        if npc.get('faction') == 'A':
            line += '"A",'
        elif npc.get('faction') == 'H':
            line += '"H",'
        else:
            line += 'nil,'
        
        # Type and classification
        line += 'nil,0},'
        
        line += ' -- pfQuest-epoch'
        
        output.append(line)
    
    output.append("}")
    output.append("")
    output.append("-- Export for merging")
    output.append("return pfQuestNpcData")
    
    return '\n'.join(output)

def main():
    base_path = "/Users/travisheryford/Library/CloudStorage/Dropbox/WoW Interfaces/epoch/AddOns/"
    workspace = base_path + "Questie/pfquest_conversion_workspace/"
    
    print("Loading pfQuest-epoch databases...")
    
    # Load pfQuest data
    pf_quests = parse_pfquest_quests(base_path + "pfQuest-epoch/db/quests-epoch.lua")
    pf_texts = parse_pfquest_texts(base_path + "pfQuest-epoch/db/enUS/quests-epoch.lua")
    pf_npcs = parse_pfquest_npcs(base_path + "pfQuest-epoch/db/units-epoch.lua")
    pf_npc_names = parse_pfquest_npc_names(base_path + "pfQuest-epoch/db/enUS/units-epoch.lua")
    
    print(f"Loaded {len(pf_quests)} quests")
    print(f"Loaded {len(pf_npcs)} NPCs")
    print(f"Loaded {len(pf_npc_names)} NPC names")
    
    # Generate Questie format databases
    print("\nGenerating Questie format quest database...")
    quest_db = generate_questie_quest_db(pf_quests, pf_texts)
    
    # Save quest database
    with open(workspace + "pfquest_converted_quests.lua", 'w', encoding='utf-8') as f:
        f.write(quest_db)
    print(f"Saved to: pfquest_converted_quests.lua")
    
    print("\nGenerating Questie format NPC database...")
    npc_db = generate_questie_npc_db(pf_npcs, pf_npc_names)
    
    # Save NPC database
    with open(workspace + "pfquest_converted_npcs.lua", 'w', encoding='utf-8') as f:
        f.write(npc_db)
    print(f"Saved to: pfquest_converted_npcs.lua")
    
    print("\nConversion complete!")
    print(f"Check the workspace folder: {workspace}")

if __name__ == "__main__":
    main()