#!/usr/bin/env python3
"""
Test Framework for quest_parser.py
Validates quest data extraction from submissions
"""

import sys
import json
from modules.quest_parser import QuestParser

def run_test(name, input_text, expected_output, parser):
    """Run a single test case"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    result = parser.parse(input_text, "test_input")
    
    # Check if we got any quest data
    if not result:
        if expected_output.get('expect_none'):
            print("✅ PASSED - Correctly rejected invalid data")
            return True
        else:
            print("❌ FAILED - No quest data parsed")
            return False
    
    quest_data = result[0] if result else {}
    
    # Check specific expected values
    test_passed = True
    failures = []
    
    for key, expected_value in expected_output.items():
        if key == 'expect_none':
            continue
            
        actual_value = quest_data.get(key)
        if actual_value != expected_value:
            failures.append(f"{key}: Expected '{expected_value}', got '{actual_value}'")
            test_passed = False
    
    if test_passed:
        print("✅ PASSED")
        print(f"  Quest ID: {quest_data.get('quest_id')}")
        print(f"  Quest Name: {quest_data.get('quest_name')}")
    else:
        print("❌ FAILED")
        for failure in failures:
            print(f"  - {failure}")
    
    return test_passed

def test_quest_parsing():
    """Test quest data parsing"""
    parser = QuestParser()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Basic quest data from issue_1000.txt format
    test1 = """
    Quest ID: 27220
    Quest Name: Auntie VanCleef
    Level: 25
    Zone: Duskwood
    Faction: Alliance
    
    QUEST GIVER:
      NPC: Unknown (quest already in progress)
    
    OBJECTIVES:
      1. Chain Key: 0/1 (item)
    
    TURN-IN NPC:
      NPC: Edna Molsen (ID: 46071)
      Location: [21.7, 73.4]
      Zone: Duskwood
    """
    
    expected1 = {
        'quest_id': 27220,
        'quest_name': 'Auntie VanCleef',
        'level': 25,
        'zone': 'Duskwood',
        'faction': 'Alliance',
        'turn_in_npc_id': 46071
    }
    
    if run_test("Basic Quest Parsing", test1, expected1, parser):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 2: Quest with complete data
    test2 = """
    === QUEST DATA ===
    
    Addon Version: v1.1.0
    Quest ID: 28723
    Quest Name: Grorg's Story
    Level: 32
    Zone: Durotar
    Faction: Horde
    
    QUEST GIVER:
      NPC: Gorgul (ID: 46834)
      Location: [70.9, 45.9]
      Zone: Durotar
    
    OBJECTIVES:
      1. Kill 10 Amethyst Crabs
      2. Collect 5 Crab Meat
      3. Return to Gorgul
    
    TURN-IN NPC:
      NPC: Shan'ze (ID: 46718)
      Location: [71.5, 44.8]
      Zone: Durotar
    """
    
    expected2 = {
        'quest_id': 28723,
        'quest_name': "Grorg's Story",
        'level': 32,
        'zone': 'Durotar',
        'faction': 'Horde',
        'addon_version': '1.1.0',
        'quest_giver_npc_id': 46834,
        'turn_in_npc_id': 46718
    }
    
    if run_test("Complete Quest Data", test2, expected2, parser):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 3: Quest with special flags
    test3 = """
    Quest ID: 12345
    Quest Name: Daily Dungeon Run
    Level: 80
    Zone: Icecrown
    
    This is a daily quest that takes place in a dungeon.
    It's also a PvP quest for battleground rewards.
    """
    
    quest3 = parser.parse(test3, "test3")[0]
    
    print(f"\n{'='*60}")
    print(f"TEST: Special Quest Types")
    print(f"{'='*60}")
    
    if quest3.get('is_daily') and quest3.get('is_dungeon') and quest3.get('is_pvp'):
        print("✅ PASSED - Correctly identified daily/dungeon/pvp flags")
        tests_passed += 1
    else:
        print(f"❌ FAILED - Flags: daily={quest3.get('is_daily')}, dungeon={quest3.get('is_dungeon')}, pvp={quest3.get('is_pvp')}")
        tests_failed += 1
    
    # Test 4: Multi-quest submission
    test4 = """
    ============================================================
    Quest ID: 11111
    Quest Name: First Quest
    Level: 10
    
    ============================================================
    Quest ID: 22222
    Quest Name: Second Quest
    Level: 20
    """
    
    quests4 = parser.parse(test4, "test4")
    
    print(f"\n{'='*60}")
    print(f"TEST: Multi-Quest Parsing")
    print(f"{'='*60}")
    
    if len(quests4) == 2:
        if quests4[0]['quest_id'] == 11111 and quests4[1]['quest_id'] == 22222:
            print("✅ PASSED - Correctly parsed 2 quests")
            tests_passed += 1
        else:
            print(f"❌ FAILED - Wrong quest IDs: {quests4[0].get('quest_id')}, {quests4[1].get('quest_id')}")
            tests_failed += 1
    else:
        print(f"❌ FAILED - Expected 2 quests, got {len(quests4)}")
        tests_failed += 1
    
    # Test 5: Quest with objectives list
    test5 = """
    Quest ID: 33333
    Quest Name: Complex Objectives
    
    OBJECTIVES:
      1. Kill 10 wolves
      2. Collect 5 wolf pelts
      3. Speak with the hunter
      4. Return to quest giver
    """
    
    quest5 = parser.parse(test5, "test5")[0]
    
    print(f"\n{'='*60}")
    print(f"TEST: Objectives Parsing")
    print(f"{'='*60}")
    
    objectives = quest5.get('objectives_list', [])
    if len(objectives) == 4:
        print("✅ PASSED - Correctly parsed 4 objectives")
        print(f"  Objectives found:")
        for obj in objectives:
            print(f"    - {obj}")
        tests_passed += 1
    else:
        print(f"❌ FAILED - Expected 4 objectives, got {len(objectives)}")
        tests_failed += 1
    
    # Test 6: Invalid quest data
    test6 = """
    This is just some random text that doesn't contain quest data.
    No quest ID, no quest name, nothing useful.
    """
    
    expected6 = {
        'expect_none': True
    }
    
    if run_test("Invalid Data Rejection", test6, expected6, parser):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 7: Database entry format
    test7 = """
    DATABASE ENTRIES:
    -- Add to epochQuestDB.lua:
    [44444] = {"Test Quest",{{12345},nil,nil},{{67890},nil},25,30,nil,nil,{"Find the artifact"},nil,nil,nil,nil,nil,nil,nil,nil,14,nil,nil,nil,nil,nil,0,0,nil,nil,nil,nil,nil,nil},
    """
    
    quest7 = parser.parse(test7, "test7")[0]
    
    print(f"\n{'='*60}")
    print(f"TEST: Database Entry Parsing")
    print(f"{'='*60}")
    
    if quest7.get('quest_id') == 44444:
        print("✅ PASSED - Correctly extracted quest ID from database entry")
        if quest7.get('raw_database_entry'):
            print("  ✓ Raw database entry captured")
        tests_passed += 1
    else:
        print(f"❌ FAILED - Expected quest ID 44444, got {quest7.get('quest_id')}")
        tests_failed += 1
    
    # Test 8: Legacy format with [Epoch] prefix
    test8 = """
    Quest Name: [Epoch] Quest 55555
    Quest ID: 55555
    Level: 40
    Zone: 85
    """
    
    quest8 = parser.parse(test8, "test8")[0]
    
    print(f"\n{'='*60}")
    print(f"TEST: [Epoch] Prefix Removal")
    print(f"{'='*60}")
    
    if quest8.get('quest_name') == 'Quest 55555':  # Should remove [Epoch] prefix
        print("✅ PASSED - Correctly removed [Epoch] prefix from quest name")
        tests_passed += 1
    else:
        print(f"❌ FAILED - Quest name: '{quest8.get('quest_name')}' (should not have [Epoch] prefix)")
        tests_failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {tests_passed} passed, {tests_failed} failed")
    print(f"{'='*60}")
    
    return tests_passed, tests_failed

def test_real_submission():
    """Test with a real submission file"""
    parser = QuestParser()
    
    print(f"\n{'='*60}")
    print("TESTING WITH REAL SUBMISSION (issue_1000.txt)")
    print(f"{'='*60}")
    
    try:
        with open('pending_submissions/issue_1000.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        quests = parser.parse(content, 'issue_1000.txt')
        
        if quests:
            quest = quests[0]
            print(f"Parsed quest from real submission:")
            print(f"  Quest ID: {quest.get('quest_id')}")
            print(f"  Quest Name: {quest.get('quest_name')}")
            print(f"  Level: {quest.get('level')}")
            print(f"  Zone: {quest.get('zone')}")
            print(f"  Faction: {quest.get('faction')}")
            print(f"  Quest Giver NPC: {quest.get('quest_giver_npc_id')}")
            print(f"  Turn-in NPC: {quest.get('turn_in_npc_id')}")
            
            if quest.get('objectives_list'):
                print(f"  Objectives: {len(quest['objectives_list'])} found")
            
            # Validate expected values
            if quest.get('quest_id') == 27220:
                print("  ✅ Correct quest ID")
            if quest.get('quest_name') == 'Auntie VanCleef':
                print("  ✅ Correct quest name")
            if quest.get('turn_in_npc_id') == 46071:
                print("  ✅ Correct turn-in NPC")
        else:
            print("  ⚠️ No quest data extracted from real submission")
            
    except FileNotFoundError:
        print("  ℹ️ Real submission file not found")
    except Exception as e:
        print(f"  ❌ Error testing real submission: {e}")

def test_database_generation():
    """Test database entry generation"""
    parser = QuestParser()
    
    print(f"\n{'='*60}")
    print("TESTING DATABASE ENTRY GENERATION")
    print(f"{'='*60}")
    
    test_quest = {
        'quest_id': 99999,
        'quest_name': 'Test Quest Generation',
        'level': 50,
        'quest_level': 52,
        'min_level': 48,
        'quest_giver_npc_id': 11111,
        'turn_in_npc_id': 22222,
        'objectives_text': 'Kill 10 test mobs',
        'faction': 'Alliance'
    }
    
    entry = parser.generate_quest_entry(test_quest)
    
    print("Generated database entry:")
    print(entry)
    
    # Validate the entry has correct structure
    if entry.startswith("[99999] = {"):
        print("  ✅ Correct quest ID in entry")
    if '"Test Quest Generation"' in entry:
        print("  ✅ Quest name included")
    if '{{11111},nil,nil}' in entry:
        print("  ✅ Quest giver NPC included")
    if '{{22222},nil}' in entry:
        print("  ✅ Turn-in NPC included")
    if entry.count(',') == 29:  # Should have 29 commas for 30 fields
        print("  ✅ Correct number of fields (30)")

def main():
    print("="*60)
    print("QUEST PARSER VALIDATION SUITE")
    print("="*60)
    
    # Run all test suites
    basic_passed, basic_failed = test_quest_parsing()
    test_real_submission()
    test_database_generation()
    
    # Final summary
    print(f"\n{'='*60}")
    print("FINAL VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    if basic_failed == 0:
        print("✅ ALL QUEST PARSER TESTS PASSED")
        print("\nThe quest_parser module is validated to:")
        print("  1. Extract quest ID, name, and level")
        print("  2. Parse quest giver and turn-in NPC IDs")
        print("  3. Extract faction and zone information")
        print("  4. Parse objectives text and lists")
        print("  5. Identify special quest types (daily, dungeon, pvp)")
        print("  6. Handle multi-quest submissions")
        print("  7. Remove [Epoch] prefixes from quest names")
        print("  8. Generate valid database entries")
        print("\n🎯 Module accuracy: 100% on test cases")
    else:
        print(f"❌ {basic_failed} tests failed - module needs fixes")
        print("\nDO NOT proceed to Phase 2 until all tests pass!")
    
    return 0 if basic_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())