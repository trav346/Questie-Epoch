#!/usr/bin/env python3
"""Generate Lua database files from merged results"""

import json
from pathlib import Path

# Load merged results
with open('complete_pipeline_results.json', 'r') as f:
    data = json.load(f)

print(f"Loaded data: {len(data['quests'])} quests, {len(data['npcs'])} NPCs")

# Output directory
output_dir = Path("../ready_to_apply")
output_dir.mkdir(exist_ok=True)

# Generate NPC database
if data['npcs']:
    npc_file = output_dir / "epochNpcDB_batch.lua"
    with open(npc_file, 'w') as f:
        f.write("-- Generated NPC database from batch processing\n")
        f.write("-- NPCs with corrected parent zone IDs\n\n")
        f.write("if not EpochDB then EpochDB = {} end\n")
        f.write("if not EpochDB.npc then EpochDB.npc = {} end\n\n")
        f.write("local npcs = {\n")
        
        for npc in data['npcs']:
            # Format NPC entry as Lua table
            npc_id = npc['id']
            name = npc['name'].replace('"', '\\"') if npc['name'] else ""
            
            # Build spawn table
            spawns = "nil"
            if npc.get('spawns'):
                spawn_parts = []
                for zone_id, coords in npc['spawns'].items():
                    coord_list = ",".join([f"{{{c['x']},{c['y']}}}" for c in coords])
                    spawn_parts.append(f"[{zone_id}]={{{coord_list}}}")
                if spawn_parts:
                    spawns = "{" + ",".join(spawn_parts) + "}"
            
            # Build quest lists
            quest_starts = "{" + ",".join(str(q) for q in npc.get('questStarts', [])) + "}" if npc.get('questStarts') else "nil"
            quest_ends = "{" + ",".join(str(q) for q in npc.get('questEnds', [])) + "}" if npc.get('questEnds') else "nil"
            
            # Format the full entry
            f.write(f'    [{npc_id}] = {{"{name}",')
            f.write(f'{npc.get("minLevelHealth") or "nil"},')
            f.write(f'{npc.get("maxLevelHealth") or "nil"},')
            f.write(f'{npc.get("minLevel") or "nil"},')
            f.write(f'{npc.get("maxLevel") or "nil"},')
            f.write(f'{npc.get("rank") or 0},')
            f.write(f'{spawns},')
            f.write(f'nil,')  # waypoints
            f.write(f'{npc.get("zoneID") or "nil"},')
            f.write(f'{quest_starts},')
            f.write(f'{quest_ends},')
            f.write(f'{npc.get("factionID") or "nil"},')
            f.write(f'"{npc.get("friendlyToFaction") or ""}",')
            subname = f'"{npc.get("subName")}"' if npc.get("subName") else "nil"
            f.write(f'{subname},')
            f.write(f'{npc.get("npcFlags") or 0}')
            f.write('},\n')
        
        f.write("}\n\n")
        f.write("-- Merge into EpochDB\n")
        f.write("for id, data in pairs(npcs) do\n")
        f.write("    EpochDB.npc[id] = data\n")
        f.write("end\n")
    
    print(f"Generated {npc_file} with {len(data['npcs'])} NPCs")

# Generate Quest database
if data['quests']:
    quest_file = output_dir / "epochQuestDB_batch.lua"
    with open(quest_file, 'w') as f:
        f.write("-- Generated Quest database from batch processing\n\n")
        f.write("if not EpochDB then EpochDB = {} end\n")
        f.write("if not EpochDB.quest then EpochDB.quest = {} end\n\n")
        f.write("local quests = {\n")
        
        for quest in data['quests']:
            quest_id = quest['id']
            name = quest['name'].replace('"', '\\"') if quest['name'] else ""
            
            # Format the quest entry (simplified for now)
            f.write(f'    [{quest_id}] = {{"{name}",nil,nil,')
            f.write(f'{quest.get("requiredLevel") or "nil"},')
            f.write(f'{quest.get("questLevel") or "nil"},')
            f.write(f'nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,nil,')
            f.write(f'{quest.get("zoneOrSort") or "nil"},')
            f.write(f'nil,nil,nil,nil,nil,0,0,nil,nil,nil,nil,nil,nil}},\n')
        
        f.write("}\n\n")
        f.write("-- Merge into EpochDB\n")
        f.write("for id, data in pairs(quests) do\n")
        f.write("    EpochDB.quest[id] = data\n")
        f.write("end\n")
    
    print(f"Generated {quest_file} with {len(data['quests'])} quests")

print("\nLua files generated successfully!")
print(f"NPCs now use correct parent zone IDs for proper map display")