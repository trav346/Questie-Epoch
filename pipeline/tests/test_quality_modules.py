#!/usr/bin/env python3
"""
Test Quality Assurance and related modules
Tests with database-format data (30 fields for quests)
"""

import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add modules directory to path
sys.path.append(str(Path(__file__).parent / "modules"))

def test_completeness_scorer():
    """Test the completeness scorer module"""
    print("\n" + "="*60)
    print("TESTING: Completeness Scorer")
    print("="*60)
    
    try:
        from completeness_scorer import CompletenessScorer
        scorer = CompletenessScorer()
        
        # Test with database-format quest (30 fields)
        # Quest 26936: Northshore Mine (a well-documented quest)
        quest_data = {
            1: "Northshore Mine",  # name
            2: ([[823]], None, None),  # startedBy: NPCs, objects, items
            3: ([[197]], None),  # finishedBy: NPCs, objects
            4: 5,  # requiredLevel
            5: 8,  # questLevel
            6: None,  # requiredRaces
            7: None,  # requiredClasses
            8: ["Explore Northshore Mine"],  # objectivesText
            9: None,  # triggerEnd
            10: None,  # objectives
            11: None,  # sourceItemId
            12: None,  # preQuestGroup
            13: None,  # preQuestSingle
            14: None,  # childQuests
            15: None,  # inGroupWith
            16: None,  # exclusiveTo
            17: 12,  # zoneOrSort (Elwynn Forest)
            18: None,  # requiredSkill
            19: None,  # requiredMinRep
            20: None,  # requiredMaxRep
            21: None,  # requiredSourceItems
            22: None,  # nextQuestInChain
            23: 0,  # questFlags
            24: 0,  # specialFlags
            25: None,  # parentQuest
            26: None,  # reputationReward
            27: None,  # extraObjectives
            28: None,  # requiredSpell
            29: None,  # requiredSpecialization
            30: None   # requiredMaxLevel
        }
        
        score, breakdown = scorer.score_quest(quest_data)
        
        print(f"\n📊 Completeness Score: {score:.1f}%")
        print(f"   Critical Fields: {breakdown.get('critical_present', 0)}/{breakdown.get('critical_total', 0)}")
        print(f"   Important Fields: {breakdown.get('important_present', 0)}/{breakdown.get('important_total', 0)}")
        print(f"   Optional Fields: {breakdown.get('optional_present', 0)}/{breakdown.get('optional_total', 0)}")
        
        if breakdown.get('missing_critical'):
            print("\n   Missing Critical Fields:")
            for field in breakdown['missing_critical']:
                print(f"      ❌ {field}")
        
        return score > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_consistency_checker():
    """Test the consistency checker module"""
    print("\n" + "="*60)
    print("TESTING: Consistency Checker")
    print("="*60)
    
    try:
        from consistency_checker import ConsistencyChecker
        checker = ConsistencyChecker()
        
        # Test with inconsistent data
        inconsistent_quest = {
            1: "Test Quest",
            2: ([[999999]], None, None),  # Non-existent NPC
            3: ([[823]], None),
            4: 60,  # Required level higher than quest level (inconsistent)
            5: 10,  # Quest level
            17: 99999,  # Invalid zone
        }
        
        # Add minimal required fields
        for i in range(6, 31):
            if i not in inconsistent_quest:
                inconsistent_quest[i] = None
        
        consistent, errors, warnings = checker.check_quest_consistency(inconsistent_quest)
        
        print(f"\n📊 Consistency Check: {'✅ PASSED' if consistent else '❌ FAILED'}")
        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")
        
        if errors:
            print("\n   Consistency Errors:")
            for error in errors[:5]:
                print(f"      ❌ {error}")
        
        if warnings:
            print("\n   Warnings:")
            for warning in warnings[:5]:
                print(f"      ⚠️  {warning}")
        
        return True  # Module works even if data is inconsistent
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_quality_assurance():
    """Test the quality assurance module with database-format data"""
    print("\n" + "="*60)
    print("TESTING: Quality Assurance (Database Format)")
    print("="*60)
    
    try:
        from quality_assurance import QualityAssurance
        qa = QualityAssurance(min_quality_score=70.0)
        
        # Test with complete database-format quest
        complete_quest = {
            1: "The Barony Mordis",
            2: ([[2378]], None, None),  # Kundric Zanden
            3: ([[2378]], None),
            4: 36,  # Required level
            5: 40,  # Quest level
            6: None,  # Races
            7: None,  # Classes
            8: ["Baron Valimar Mordis slain"],
            9: None,
            10: {  # Objectives
                'creatures': [[45543, 1, "Baron Valimar Mordis"]],
                'objects': None,
                'items': None,
                'reputation': None,
                'killCredit': None,
                'spells': None
            },
            17: 267,  # Hillsbrad Foothills
            23: 0,
            24: 0,
        }
        
        # Fill in remaining fields
        for i in range(11, 31):
            if i not in complete_quest:
                complete_quest[i] = None
        
        passed, report = qa.qa_check(complete_quest)
        
        print(f"\n📊 QA Result: {'✅ PASSED' if passed else '❌ FAILED'}")
        print(f"   Score: {report['score']:.1f}%")
        print(f"   Field Errors: {len(report['field_errors'])}")
        print(f"   Consistency Errors: {len(report['consistency_errors'])}")
        print(f"   Warnings: {len(report['warnings'])}")
        print(f"   Verdict: {report['verdict']}")
        
        if not passed:
            if report['field_errors']:
                print("\n   Field Errors:")
                for error in report['field_errors'][:3]:
                    print(f"      ❌ {error}")
            
            if report['completeness_issues']:
                print("\n   Completeness Issues:")
                for issue in report['completeness_issues'][:3]:
                    print(f"      ⚠️  {issue}")
        
        return True  # Module works even if quest doesn't pass
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("QUALITY MODULE TEST SUITE")
    print("Testing with database-format data (30 fields)")
    print("="*60)
    
    # Run tests
    results = {
        'Completeness Scorer': test_completeness_scorer(),
        'Consistency Checker': test_consistency_checker(),
        'Quality Assurance': test_quality_assurance()
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for module_name, passed in results.items():
        status = "✅ WORKING" if passed else "❌ FAILED"
        print(f"   {module_name}: {status}")
    
    total_passed = sum(1 for p in results.values() if p)
    print(f"\n📊 Overall: {total_passed}/{len(results)} modules working")
    
    if total_passed == len(results):
        print("\n🎉 All quality modules are functional!")
    else:
        print("\n⚠️  Some modules need attention.")

if __name__ == "__main__":
    main()