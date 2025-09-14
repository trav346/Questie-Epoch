#!/usr/bin/env python3
"""
Quality Assurance - Final QA check before database write
Last line of defense ensuring data quality
"""

import logging
from typing import Dict, List, Tuple, Optional
from field_validator import FieldValidator
from completeness_scorer import CompletenessScorer
from consistency_checker import ConsistencyChecker


class QualityAssurance:
    """
    Final quality assurance check before database writes
    Combines all validation, scoring, and consistency checks
    """
    
    def __init__(self, min_quality_score: float = 70.0):
        self.logger = logging.getLogger(__name__)
        self.min_quality_score = min_quality_score
        
        # Initialize sub-validators
        self.field_validator = FieldValidator()
        self.completeness_scorer = CompletenessScorer()
        self.consistency_checker = ConsistencyChecker()
        
        # QA results
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def qa_check(self, data: Dict) -> Tuple[bool, Dict]:
        """
        Perform comprehensive QA check
        
        Returns:
            (passed, report) where report contains all findings
        """
        report = {
            'passed': False,
            'score': 0,
            'field_errors': [],
            'consistency_errors': [],
            'completeness_issues': [],
            'warnings': [],
            'recommendations': [],
            'verdict': '',
        }
        
        data_type = 'quest' if 'quest_id' in data else 'npc'
        entity_id = data.get(f'{data_type}_id')
        
        self.logger.info(f"Running QA check on {data_type} {entity_id}")
        
        # Step 1: Field Validation
        if data_type == 'quest':
            field_valid, field_errors, field_warnings = self.field_validator.validate_quest(data)
        else:
            field_valid, field_errors, field_warnings = self.field_validator.validate_npc(data)
        
        report['field_errors'] = field_errors
        report['warnings'].extend(field_warnings)
        
        # Step 2: Completeness Scoring
        if data_type == 'quest':
            score, breakdown = self.completeness_scorer.score_quest(data)
        else:
            score, breakdown = self.completeness_scorer.score_npc(data)
        
        report['score'] = score
        report['completeness_issues'] = breakdown.get('missing_critical', [])
        report['recommendations'] = breakdown.get('suggestions', [])
        
        # Step 3: Consistency Check
        if data_type == 'quest':
            consistent, consistency_errors, consistency_warnings = self.consistency_checker.check_quest_consistency(data)
        else:
            consistent, consistency_errors, consistency_warnings = self.consistency_checker.check_npc_consistency(data)
        
        report['consistency_errors'] = consistency_errors
        report['warnings'].extend(consistency_warnings)
        
        # Step 4: Make Final Verdict
        report['passed'] = self._make_verdict(
            field_valid, consistent, score, report
        )
        
        # Log result
        if report['passed']:
            self.passed.append(entity_id)
            self.logger.info(f"{data_type} {entity_id} PASSED QA (score: {score:.1f}%)")
        else:
            self.failed.append(entity_id)
            self.logger.warning(f"{data_type} {entity_id} FAILED QA (score: {score:.1f}%)")
        
        return report['passed'], report
    
    def qa_batch(self, data_list: List[Dict]) -> Tuple[int, int, Dict]:
        """
        Run QA on batch of data
        
        Returns:
            (passed_count, failed_count, detailed_report)
        """
        self.passed = []
        self.failed = []
        self.warnings = []
        
        detailed_report = {
            'total': len(data_list),
            'passed': [],
            'failed': [],
            'summary': {},
            'critical_issues': [],
        }
        
        for data in data_list:
            passed, report = self.qa_check(data)
            
            data_type = 'quest' if 'quest_id' in data else 'npc'
            entity_id = data.get(f'{data_type}_id')
            
            if passed:
                detailed_report['passed'].append({
                    'id': entity_id,
                    'type': data_type,
                    'score': report['score'],
                })
            else:
                detailed_report['failed'].append({
                    'id': entity_id,
                    'type': data_type,
                    'score': report['score'],
                    'verdict': report['verdict'],
                    'errors': report['field_errors'] + report['consistency_errors'],
                })
                
                # Track critical issues
                if report['field_errors']:
                    detailed_report['critical_issues'].append(
                        f"{data_type} {entity_id}: Field validation errors"
                    )
                if report['score'] < 40:
                    detailed_report['critical_issues'].append(
                        f"{data_type} {entity_id}: Very low completeness ({report['score']:.1f}%)"
                    )
        
        # Generate summary
        detailed_report['summary'] = self._generate_summary(detailed_report)
        
        return len(self.passed), len(self.failed), detailed_report
    
    def _make_verdict(self, field_valid: bool, consistent: bool, 
                     score: float, report: Dict) -> bool:
        """Make final pass/fail verdict with explanation"""
        
        # Critical failures - immediate fail
        if not field_valid:
            report['verdict'] = f"FAILED: Field validation errors ({len(report['field_errors'])} errors)"
            return False
        
        if not consistent and report['consistency_errors']:
            report['verdict'] = f"FAILED: Consistency errors ({len(report['consistency_errors'])} errors)"
            return False
        
        # Score-based failure
        if score < self.min_quality_score:
            report['verdict'] = f"FAILED: Completeness score too low ({score:.1f}% < {self.min_quality_score}%)"
            return False
        
        # Check for critical missing fields
        critical_missing = report.get('completeness_issues', [])
        if critical_missing:
            report['verdict'] = f"FAILED: Missing critical fields: {', '.join(critical_missing)}"
            return False
        
        # Passed with warnings
        if report['warnings']:
            report['verdict'] = f"PASSED with {len(report['warnings'])} warnings"
        else:
            report['verdict'] = f"PASSED: Score {score:.1f}%"
        
        return True
    
    def _generate_summary(self, detailed_report: Dict) -> Dict:
        """Generate QA summary statistics"""
        total = detailed_report['total']
        passed = len(detailed_report['passed'])
        failed = len(detailed_report['failed'])
        
        summary = {
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'fail_rate': (failed / total * 100) if total > 0 else 0,
            'average_score': 0,
            'score_distribution': {
                'excellent': 0,  # 90+
                'good': 0,       # 75-89
                'acceptable': 0, # 60-74
                'poor': 0,       # 40-59
                'failing': 0,    # <40
            },
        }
        
        # Calculate average score
        all_scores = []
        for entry in detailed_report['passed']:
            all_scores.append(entry['score'])
        for entry in detailed_report['failed']:
            all_scores.append(entry['score'])
        
        if all_scores:
            summary['average_score'] = sum(all_scores) / len(all_scores)
            
            # Score distribution
            for score in all_scores:
                if score >= 90:
                    summary['score_distribution']['excellent'] += 1
                elif score >= 75:
                    summary['score_distribution']['good'] += 1
                elif score >= 60:
                    summary['score_distribution']['acceptable'] += 1
                elif score >= 40:
                    summary['score_distribution']['poor'] += 1
                else:
                    summary['score_distribution']['failing'] += 1
        
        return summary
    
    def generate_qa_report(self, detailed_report: Dict) -> str:
        """Generate human-readable QA report"""
        lines = []
        lines.append("=" * 70)
        lines.append("QUALITY ASSURANCE REPORT")
        lines.append("=" * 70)
        
        summary = detailed_report['summary']
        
        # Overall statistics
        lines.append(f"\nTotal Entries: {detailed_report['total']}")
        lines.append(f"Passed: {len(detailed_report['passed'])} ({summary['pass_rate']:.1f}%)")
        lines.append(f"Failed: {len(detailed_report['failed'])} ({summary['fail_rate']:.1f}%)")
        lines.append(f"Average Score: {summary['average_score']:.1f}%")
        
        # Score distribution
        lines.append("\nScore Distribution:")
        dist = summary['score_distribution']
        lines.append(f"  Excellent (90+):  {dist['excellent']}")
        lines.append(f"  Good (75-89):     {dist['good']}")
        lines.append(f"  Acceptable (60-74): {dist['acceptable']}")
        lines.append(f"  Poor (40-59):     {dist['poor']}")
        lines.append(f"  Failing (<40):    {dist['failing']}")
        
        # Critical issues
        if detailed_report['critical_issues']:
            lines.append("\nCRITICAL ISSUES:")
            for issue in detailed_report['critical_issues'][:10]:  # Show first 10
                lines.append(f"  - {issue}")
            if len(detailed_report['critical_issues']) > 10:
                lines.append(f"  ... and {len(detailed_report['critical_issues'])-10} more")
        
        # Failed entries details
        if detailed_report['failed']:
            lines.append("\nFAILED ENTRIES:")
            for entry in detailed_report['failed'][:10]:  # Show first 10
                lines.append(f"  {entry['type'].upper()} {entry['id']}: {entry['verdict']}")
                if entry.get('errors'):
                    for error in entry['errors'][:2]:  # Show first 2 errors
                        lines.append(f"    - {error}")
            if len(detailed_report['failed']) > 10:
                lines.append(f"  ... and {len(detailed_report['failed'])-10} more")
        
        # Recommendations
        lines.append("\nRECOMMENDATIONS:")
        if summary['pass_rate'] < 50:
            lines.append("  ⚠ Less than 50% pass rate - review data collection process")
        if summary['average_score'] < 60:
            lines.append("  ⚠ Low average score - need more complete data collection")
        if dist['failing'] > detailed_report['total'] * 0.2:
            lines.append("  ⚠ High failure rate - check for systematic issues")
        
        if summary['pass_rate'] >= 90:
            lines.append("  ✓ Excellent pass rate - data quality is high")
        elif summary['pass_rate'] >= 70:
            lines.append("  ✓ Good pass rate - minor improvements needed")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)


def main():
    """Test the quality assurance module"""
    qa = QualityAssurance(min_quality_score=70.0)
    
    # Test single quest
    test_quest = {
        'quest_id': 12345,
        'name': 'Test Quest',
        'startedBy': ([46834], None, None),
        'finishedBy': ([46718], None),
        'questLevel': 10,
        'requiredLevel': 8,
        'objectives': {
            'creatures': [{'npc_id': 100, 'count': 10}]
        },
        'objectivesText': ['Kill 10 wolves in the forest'],
        'zoneOrSort': 12,
    }
    
    passed, report = qa.qa_check(test_quest)
    print(f"QA Result: {'PASSED' if passed else 'FAILED'}")
    print(f"Score: {report['score']:.1f}%")
    print(f"Verdict: {report['verdict']}")
    
    # Test batch
    test_batch = [test_quest, test_quest.copy()]
    test_batch[1]['quest_id'] = 12346
    test_batch[1]['name'] = None  # This should fail
    
    passed_count, failed_count, detailed = qa.qa_batch(test_batch)
    print(f"\nBatch Results: {passed_count} passed, {failed_count} failed")
    print(qa.generate_qa_report(detailed))


if __name__ == "__main__":
    main()