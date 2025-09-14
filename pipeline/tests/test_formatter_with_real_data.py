#!/usr/bin/env python3
"""
Test the Lua formatter with real aggregated quest data
Ensures the formatter properly handles all the data from our pipeline
"""

import sys
import json
from pathlib import Path

# Add modules to path
modules_dir = Path(__file__).parent.parent / "modules"
sys.path.insert(0, str(modules_dir))

from lua_formatter import LuaFormatter

def main():
    print("="*70)
    print("TESTING LUA FORMATTER WITH REAL AGGREGATED DATA")
    print("="*70)
    
    formatter = LuaFormatter()
    
    # Load aggregated data cache
    cache_file = Path(".pipeline_cache/aggregated_quests.json")
    if not cache_file.exists():
        print("❌ No aggregated data cache found. Run create_aggregated_cache.py first")
        return
    
    with open(cache_file, 'r') as f:
        aggregated_quests = json.load(f)
    
    print(f"\n📊 Loaded {len(aggregated_quests)} aggregated quests")
    
    # Find quests with different completeness levels to test
    test_cases = {
        'complete': None,      # 100% complete quest
        'partial': None,       # Partially complete
        'minimal': None,       # Minimal data
    }
    
    for quest_id_str, quest_data in aggregated_quests.items():
        quest_id = int(quest_id_str)
        
        # Calculate completeness
        completeness = 0
        if quest_data.get('name') and not quest_data['name'].startswith('Quest'):
            completeness += 20
        if quest_data.get('startedBy', {}).get('npcs'):
            completeness += 20
        if quest_data.get('finishedBy', {}).get('npcs'):
            completeness += 20
        if quest_data.get('objectives'):
            completeness += 20
        if quest_data.get('questLevel') or quest_data.get('level'):
            completeness += 10
        if quest_data.get('zoneOrSort') or quest_data.get('zone'):
            completeness += 10
        
        # Categorize
        if completeness == 100 and not test_cases['complete']:
            test_cases['complete'] = (quest_id, quest_data, completeness)
        elif 50 <= completeness < 100 and not test_cases['partial']:
            test_cases['partial'] = (quest_id, quest_data, completeness)
        elif completeness < 50 and not test_cases['minimal']:
            test_cases['minimal'] = (quest_id, quest_data, completeness)
        
        # Stop if we have all test cases
        if all(test_cases.values()):
            break
    
    # Test each case
    print("\n🧪 Testing formatter with different data completeness levels:")
    print("-" * 50)
    
    for category, test_data in test_cases.items():
        if not test_data:
            continue
            
        quest_id, quest_data, completeness = test_data
        
        print(f"\n📝 {category.upper()} QUEST ({completeness}% complete)")
        print(f"   Quest {quest_id}: {quest_data.get('name', f'Quest {quest_id}')}")
        
        try:
            # Format the quest
            lua_entry = formatter.format_quest_entry(quest_id, quest_data)
            
            # Count fields at top level
            entry_content = lua_entry.split(' = {', 1)[1].rstrip('}')
            depth = 0
            field_count = 1
            for char in entry_content:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                elif char == ',' and depth == 0:
                    field_count += 1
            
            print(f"   ✅ Successfully formatted - {field_count} fields")
            
            # Show a snippet of the output
            if len(lua_entry) > 200:
                print(f"   Output: {lua_entry[:200]}...")
            else:
                print(f"   Output: {lua_entry}")
            
            # Validate structure
            issues = []
            
            # Check brackets match
            if lua_entry.count('{') != lua_entry.count('}'):
                issues.append("Mismatched brackets")
            
            # Check for required fields
            if quest_data.get('name') and f'"{quest_data["name"]}"' not in lua_entry:
                issues.append("Name not properly formatted")
            
            if issues:
                print(f"   ⚠️ Issues: {', '.join(issues)}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test batch formatting
    print("\n" + "="*70)
    print("BATCH FORMATTING TEST")
    print("-" * 50)
    
    # Format top 10 complete quests
    complete_quests = []
    for quest_id_str, quest_data in aggregated_quests.items():
        quest_id = int(quest_id_str)
        
        if (quest_data.get('name') and 
            quest_data.get('startedBy', {}).get('npcs') and
            quest_data.get('finishedBy', {}).get('npcs')):
            
            complete_quests.append((quest_id, quest_data))
            
            if len(complete_quests) >= 10:
                break
    
    print(f"\n📦 Formatting batch of {len(complete_quests)} complete quests...")
    
    success_count = 0
    error_count = 0
    
    for quest_id, quest_data in complete_quests:
        try:
            lua_entry = formatter.format_quest_entry(quest_id, quest_data)
            
            # Quick validation
            entry_content = lua_entry.split(' = {', 1)[1].rstrip('}')
            depth = 0
            field_count = 1
            for char in entry_content:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                elif char == ',' and depth == 0:
                    field_count += 1
            
            if field_count == 30:
                success_count += 1
            else:
                error_count += 1
                print(f"   ⚠️ Quest {quest_id} has {field_count} fields instead of 30")
                
        except Exception as e:
            error_count += 1
            print(f"   ❌ Quest {quest_id} failed: {e}")
    
    print(f"\n📊 Results:")
    print(f"   ✅ Success: {success_count}/{len(complete_quests)}")
    print(f"   ❌ Errors: {error_count}/{len(complete_quests)}")
    
    if success_count == len(complete_quests):
        print("\n🎉 ALL TESTS PASSED! Formatter is ready for production!")
    else:
        print("\n⚠️ Some issues found. Review errors above.")
    
    # Generate a sample output file
    if complete_quests:
        print("\n💾 Generating sample output file...")
        output_lines = []
        output_lines.append("-- Sample formatted quests from aggregator")
        output_lines.append("-- Generated by test_formatter_with_real_data.py")
        output_lines.append("")
        
        for quest_id, quest_data in complete_quests[:5]:
            try:
                lua_entry = formatter.format_quest_entry(quest_id, quest_data)
                output_lines.append(lua_entry + ",")
            except:
                pass
        
        output_file = Path("sample_formatted_quests.lua")
        with open(output_file, 'w') as f:
            f.write('\n'.join(output_lines))
        
        print(f"   Saved to: {output_file}")

if __name__ == "__main__":
    main()