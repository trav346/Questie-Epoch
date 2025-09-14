#!/usr/bin/env python3
"""
Test script for Quality Assurance module
Tests with real quest data from submissions
"""

import sys
import json
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add modules directory to path
sys.path.append(str(Path(__file__).parent / "modules"))

from quality_assurance import QualityAssurance
from quest_parser import QuestParser

def test_good_quest():
    """Test QA with a complete quest"""
    print("\n" + "="*60)
    print("TESTING: Complete Quest Data")
    print("="*60)
    
    good_quest = {
        'quest_id': 26936,
        'quest_name': 'Northshore Mine',
        'level': 8,
        'required_level': 5,
        'zone': 'Elwynn Forest',
        'zone_id': 12,
        'faction': 'Alliance',
        'quest_giver_npc_id': 823,
        'quest_giver_npc_name': 'Deputy Willem',
        'quest_giver_coords': [47.7, 41.4],
        'turn_in_npc_id': 197,
        'turn_in_npc_name': 'Marshal McBride',
        'turn_in_coords': [48.2, 42.1],
        'objectives_list': ['Explore Northshore Mine'],
        'objectives_raw': {
            'explore': [{'text': 'Explore Northshore Mine', 'coords': [24.5, 49.5]}]
        }
    }
    
    qa = QualityAssurance(min_quality_score=70.0)
    passed, report = qa.qa_check(good_quest)
    
    print(f"\n📊 QA Result: {'✅ PASSED' if passed else '❌ FAILED'}")
    print(f"   Score: {report['score']:.1f}%")
    print(f"   Field Errors: {len(report['field_errors'])}")
    print(f"   Consistency Errors: {len(report['consistency_errors'])}")
    print(f"   Warnings: {len(report['warnings'])}")
    
    if report['field_errors']:
        print("\n   Field Errors:")
        for error in report['field_errors']:
            print(f"      ❌ {error}")
    
    if report['warnings']:
        print("\n   Warnings:")
        for warning in report['warnings']:
            print(f"      ⚠️  {warning}")
    
    return passed

def test_minimal_quest():
    """Test QA with minimal quest data"""
    print("\n" + "="*60)
    print("TESTING: Minimal Quest Data")
    print("="*60)
    
    minimal_quest = {
        'quest_id': 27001,
        'quest_name': 'Test Quest',
        'level': 10,
        'zone': 'Unknown Zone'
    }
    
    qa = QualityAssurance(min_quality_score=70.0)
    passed, report = qa.qa_check(minimal_quest)
    
    print(f"\n📊 QA Result: {'✅ PASSED' if passed else '❌ FAILED'}")
    print(f"   Score: {report['score']:.1f}%")
    print(f"   Field Errors: {len(report['field_errors'])}")
    print(f"   Completeness Issues: {len(report['completeness_issues'])}")
    print(f"   Verdict: {report['verdict']}")
    
    if report['completeness_issues']:
        print("\n   Missing Critical Fields:")
        for issue in report['completeness_issues']:
            print(f"      ❌ {issue}")
    
    if report['recommendations']:
        print("\n   Recommendations:")
        for rec in report['recommendations']:
            print(f"      💡 {rec}")
    
    return passed

def test_invalid_quest():
    """Test QA with invalid data"""
    print("\n" + "="*60)
    print("TESTING: Invalid Quest Data")
    print("="*60)
    
    invalid_quest = {
        'quest_id': 'not_a_number',  # Invalid ID
        'quest_name': '',  # Empty name
        'level': -5,  # Invalid level
        'zone_id': 99999,  # Invalid zone
        'quest_giver_coords': [200, 300],  # Out of bounds coords
    }
    
    qa = QualityAssurance(min_quality_score=70.0)
    passed, report = qa.qa_check(invalid_quest)
    
    print(f"\n📊 QA Result: {'✅ PASSED' if passed else '❌ FAILED'}")
    print(f"   Score: {report['score']:.1f}%")
    print(f"   Field Errors: {len(report['field_errors'])}")
    print(f"   Consistency Errors: {len(report['consistency_errors'])}")
    
    if report['field_errors']:
        print("\n   Field Validation Errors:")
        for error in report['field_errors'][:5]:  # Show first 5
            print(f"      ❌ {error}")
        if len(report['field_errors']) > 5:
            print(f"      ... and {len(report['field_errors']) - 5} more")
    
    return passed

def test_real_submission():
    """Test QA with real submission data"""
    print("\n" + "="*60)
    print("TESTING: Real Submission Data")
    print("="*60)
    
    # Parse a real submission
    parser = QuestParser()
    test_file = Path(__file__).parent.parent / "pending_submissions/issue_1186.txt"
    
    if not test_file.exists():
        print("⚠️  Test file not found, skipping real submission test")
        return False
    
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    quests = parser.parse(content, "issue_1186.txt")
    
    if not quests:
        print("❌ No quests parsed from submission")
        return False
    
    qa = QualityAssurance(min_quality_score=70.0)
    
    for quest in quests[:3]:  # Test first 3 quests
        print(f"\n📋 Quest {quest.get('quest_id')}: {quest.get('quest_name')}")
        passed, report = qa.qa_check(quest)
        
        print(f"   Result: {'✅ PASSED' if passed else '❌ FAILED'} (Score: {report['score']:.1f}%)")
        
        if not passed and report['completeness_issues']:
            print(f"   Issues: {', '.join(report['completeness_issues'][:3])}")
    
    # Get overall stats
    print(f"\n📊 Batch Results:")
    print(f"   Passed: {len(qa.passed)}")
    print(f"   Failed: {len(qa.failed)}")
    print(f"   Pass Rate: {len(qa.passed) / max(1, len(qa.passed) + len(qa.failed)) * 100:.1f}%")
    
    return len(qa.passed) > 0

def test_batch_processing():
    """Test batch QA processing"""
    print("\n" + "="*60)
    print("TESTING: Batch Processing")
    print("="*60)
    
    test_batch = [
        {
            'quest_id': 26936,
            'quest_name': 'Good Quest',
            'level': 8,
            'zone': 'Elwynn Forest',
            'quest_giver_npc_id': 823,
            'turn_in_npc_id': 197,
            'objectives_list': ['Do something']
        },
        {
            'quest_id': 27001,
            'quest_name': 'Minimal Quest',
            'level': 10
        },
        {
            'quest_id': 'invalid',
            'quest_name': '',
            'level': -1
        }
    ]
    
    qa = QualityAssurance(min_quality_score=70.0)
    passed_count, failed_count, batch_report = qa.qa_batch(test_batch)
    
    print(f"\n📊 Batch Processing Results:")
    print(f"   Total Processed: {len(test_batch)}")
    print(f"   Passed: {passed_count}")
    print(f"   Failed: {failed_count}")
    print(f"   Pass Rate: {batch_report['pass_rate']:.1f}%")
    print(f"   Average Score: {batch_report['average_score']:.1f}%")
    
    if batch_report['common_issues']:
        print("\n   Common Issues:")
        for issue, count in batch_report['common_issues'].items():
            print(f"      • {issue}: {count} occurrences")
    
    return passed_count > 0

def main():
    print("\n" + "="*60)
    print("QUALITY ASSURANCE MODULE TEST SUITE")
    print("="*60)
    
    # Run all tests
    results = {
        'Good Quest': test_good_quest(),
        'Minimal Quest': test_minimal_quest(),
        'Invalid Quest': test_invalid_quest(),
        'Real Submission': test_real_submission(),
        'Batch Processing': test_batch_processing()
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    total_passed = sum(1 for p in results.values() if p)
    print(f"\n📊 Overall: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        print("\n🎉 All tests passed! QA module is ready for production.")
    else:
        print("\n⚠️  Some tests failed. Review the QA module implementation.")

if __name__ == "__main__":
    main()