#!/usr/bin/env python3
"""
Test script for modular pipeline components
Tests with real fresh submissions
"""

import sys
import json
from pathlib import Path

# Add modules directory to path
sys.path.append(str(Path(__file__).parent / "modules"))
sys.path.append(str(Path(__file__).parent.parent / "Live Pipeline"))

from quest_parser import QuestParser
from live_processor_with_npc_flags import LiveProcessorWithFlags

def test_quest_parser():
    """Test quest parser with various submissions"""
    print("\n" + "="*60)
    print("TESTING QUEST PARSER")
    print("="*60)
    
    parser = QuestParser()
    test_files = [
        "pending_submissions/issue_1186.txt",  # Single quest, new format
        "pending_submissions/issue_1185.txt",  # 8 quests batch
        "pending_submissions/issue_1184.txt",  # 4 quests
    ]
    
    results = {}
    for file in test_files:
        file_path = Path(__file__).parent.parent / file
        if not file_path.exists():
            print(f"⚠️  File not found: {file}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        quests = parser.parse(content, str(file))
        results[file] = {
            'total_quests': len(quests),
            'quest_ids': [q.get('quest_id') for q in quests],
            'has_npcs': sum(1 for q in quests if q.get('quest_giver_npc_id') or q.get('turn_in_npc_id')),
            'has_objectives': sum(1 for q in quests if q.get('objectives_list'))
        }
        
        print(f"\n📄 {file}")
        print(f"   Quests parsed: {len(quests)}")
        print(f"   Quest IDs: {results[file]['quest_ids']}")
        print(f"   With NPC data: {results[file]['has_npcs']}")
        print(f"   With objectives: {results[file]['has_objectives']}")
    
    return results

def test_npc_processor():
    """Test NPC processor with service flag detection"""
    print("\n" + "="*60)
    print("TESTING NPC PROCESSOR WITH SERVICE FLAGS")
    print("="*60)
    
    processor = LiveProcessorWithFlags()
    test_files = [
        "pending_submissions/issue_1186.txt",  # Has 4 service NPCs
        "pending_submissions/issue_1185.txt",  # Multiple quests
    ]
    
    results = {}
    for file in test_files:
        file_path = Path(__file__).parent.parent / file
        if not file_path.exists():
            print(f"⚠️  File not found: {file}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse service NPCs
        service_npcs = processor.parse_service_npcs(content)
        
        results[file] = {
            'total_service_npcs': len(service_npcs),
            'services_found': {},
        }
        
        print(f"\n📄 {file}")
        print(f"   Service NPCs found: {len(service_npcs)}")
        
        for npc_id, npc_info in service_npcs.items():
            services = npc_info.get('services', set())
            if services:
                for service in services:
                    if service not in results[file]['services_found']:
                        results[file]['services_found'][service] = []
                    results[file]['services_found'][service].append(npc_id)
                    
        # Display service summary
        if results[file]['services_found']:
            print("   Services detected:")
            for service, npc_ids in results[file]['services_found'].items():
                print(f"      • {service}: {len(npc_ids)} NPCs ({', '.join(map(str, npc_ids[:3]))}{'...' if len(npc_ids) > 3 else ''})")
    
    return results

def test_multi_quest_detection():
    """Test if multi-quest submissions are properly detected"""
    print("\n" + "="*60)
    print("TESTING MULTI-QUEST DETECTION")
    print("="*60)
    
    test_file = Path(__file__).parent.parent / "pending_submissions/issue_1185.txt"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count actual quests in file
    import re
    quest_ids = re.findall(r'Quest ID:\s*(\d+)', content)
    print(f"\n📊 Actual quests in file: {len(quest_ids)}")
    print(f"   Quest IDs found: {quest_ids}")
    
    # Test parser detection
    parser = QuestParser()
    detected = parser._split_multi_quest_submission(content)
    print(f"\n🔍 Parser detected sections: {len(detected)}")
    
    # Parse all quests
    quests = parser.parse(content, "issue_1185.txt")
    print(f"\n✅ Parser extracted quests: {len(quests)}")
    print(f"   Quest IDs parsed: {[q.get('quest_id') for q in quests]}")
    
    # Show what's missing
    parsed_ids = [str(q.get('quest_id')) for q in quests if q.get('quest_id')]
    missing = set(quest_ids) - set(parsed_ids)
    if missing:
        print(f"\n❌ Missing quests: {missing}")

def test_data_quality():
    """Test data quality and completeness"""
    print("\n" + "="*60)
    print("TESTING DATA QUALITY")
    print("="*60)
    
    parser = QuestParser()
    test_file = Path(__file__).parent.parent / "pending_submissions/issue_1186.txt"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    quests = parser.parse(content, "issue_1186.txt")
    
    if quests:
        quest = quests[0]
        print(f"\n📋 Quest {quest.get('quest_id')}: {quest.get('quest_name')}")
        
        # Check field completeness
        fields = {
            'quest_id': '✅' if quest.get('quest_id') else '❌',
            'quest_name': '✅' if quest.get('quest_name') else '❌',
            'level': '✅' if quest.get('level') else '❌',
            'zone': '✅' if quest.get('zone') else '❌',
            'faction': '✅' if quest.get('faction') else '❌',
            'quest_giver_npc_id': '✅' if quest.get('quest_giver_npc_id') else '❌',
            'turn_in_npc_id': '✅' if quest.get('turn_in_npc_id') else '❌',
            'objectives_list': '✅' if quest.get('objectives_list') else '❌',
        }
        
        print("\n   Field completeness:")
        for field, status in fields.items():
            value = quest.get(field)
            print(f"      {status} {field}: {value if value else 'Missing'}")

def main():
    print("\n" + "="*60)
    print("MODULAR PIPELINE TESTING SUITE")
    print("Testing with fresh GitHub submissions")
    print("="*60)
    
    # Run all tests
    quest_results = test_quest_parser()
    npc_results = test_npc_processor()
    test_multi_quest_detection()
    test_data_quality()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_quests = sum(r['total_quests'] for r in quest_results.values())
    total_service_npcs = sum(r['total_service_npcs'] for r in npc_results.values())
    
    print(f"\n📊 Overall Statistics:")
    print(f"   • Total quests parsed: {total_quests}")
    print(f"   • Total service NPCs detected: {total_service_npcs}")
    print(f"   • Files tested: {len(quest_results)}")
    
    # Identify issues
    print(f"\n⚠️  Known Issues:")
    print(f"   • Multi-quest detection needs improvement (only parsing first quest)")
    print(f"   • Player faction/class not being extracted")
    print(f"   • Zone IDs not mapped from names")
    print(f"   • Objectives parsing needs enhancement")

if __name__ == "__main__":
    main()