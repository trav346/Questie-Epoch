#!/usr/bin/env python3
"""
Module Testing Framework for Modular Pipeline
Tests individual modules with sample data and validates outputs
"""

import sys
import json
import argparse
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

# Add modules directory to path
sys.path.insert(0, str(Path(__file__).parent / 'modules'))


class ModuleTester:
    """Test harness for individual pipeline modules"""
    
    def __init__(self, module_name: str, verbose: bool = False):
        self.module_name = module_name
        self.verbose = verbose
        self.test_results = []
        self.module = None
        
        # Output directory for test results
        self.output_dir = Path('test_outputs')
        self.output_dir.mkdir(exist_ok=True)
        
    def load_module(self) -> bool:
        """Load the specified module"""
        try:
            self.module = importlib.import_module(self.module_name)
            if self.verbose:
                print(f"✓ Loaded module: {self.module_name}")
            return True
        except Exception as e:
            print(f"✗ Failed to load module {self.module_name}: {e}")
            return False
    
    def run_test(self, test_input: Any, test_name: str = None) -> Dict:
        """Run a single test on the module"""
        test_name = test_name or f"test_{len(self.test_results) + 1}"
        
        try:
            # Get the main class or function from the module
            if self.module_name == 'coordinate_parser':
                from coordinate_parser import CoordinateParser
                parser = CoordinateParser()
                result = parser.parse_coordinates(test_input)
                
            elif self.module_name == 'zone_mapper':
                from zone_mapper import ZoneMapper
                mapper = ZoneMapper()
                result = mapper.get_zone_id(test_input)
                
            elif self.module_name == 'flag_parser':
                from flag_parser import FlagParser
                parser = FlagParser()
                result = parser.parse_quest_flags(test_input)
                
            elif self.module_name == 'reputation_parser':
                from reputation_parser import ReputationParser
                parser = ReputationParser()
                result = parser.parse_reputation(test_input)
                
            elif self.module_name == 'validation_engine':
                from validation_engine import ValidationEngine
                engine = ValidationEngine()
                # Assuming test_input is quest data dict
                result = engine.validate_quest(test_input)
                
            elif self.module_name == 'restriction_analyzer':
                from restriction_analyzer import RestrictionAnalyzer
                analyzer = RestrictionAnalyzer()
                result = analyzer.analyze_restrictions(test_input)
                
            elif self.module_name == 'unified_parser':
                from unified_parser import UnifiedParser
                parser = UnifiedParser()
                result = parser.parse_submission(test_input)
                
            elif self.module_name == 'npc_parser':
                from npc_parser import NPCParser
                parser = NPCParser()
                result = parser.parse_npcs(test_input)
                
            elif self.module_name == 'database_comparator':
                from database_comparator import DatabaseComparator
                comparator = DatabaseComparator()
                # Would need database loaded
                result = {'error': 'Database comparator needs database files loaded'}
                
            elif self.module_name == 'merge_decision_engine':
                from merge_decision_engine import MergeDecisionEngine
                engine = MergeDecisionEngine()
                # Assuming test_input has required structure
                result = {'error': 'Merge engine needs structured comparison input'}
                
            elif self.module_name == 'backup_manager':
                from backup_manager import BackupManager
                manager = BackupManager()
                # Test backup creation
                result = {'error': 'Backup manager needs file paths'}
                
            elif self.module_name == 'data_aggregator':
                from data_aggregator import DataAggregator
                aggregator = DataAggregator()
                result = aggregator.process_submission(test_input)
                
            elif self.module_name == 'database_writer':
                from database_writer import DatabaseWriter
                writer = DatabaseWriter()
                # Would generate Lua output
                result = {'error': 'Database writer needs full quest/npc data'}
                
            elif self.module_name == 'pipeline_runner':
                result = {'error': 'Pipeline runner needs full configuration'}
                
            else:
                result = {'error': f'Unknown module: {self.module_name}'}
            
            # Store result
            test_result = {
                'test_name': test_name,
                'input': test_input,
                'output': result,
                'success': 'error' not in str(result).lower(),
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results.append(test_result)
            
            if self.verbose:
                print(f"\nTest: {test_name}")
                print(f"Input: {test_input}")
                print(f"Output: {result}")
                print(f"Success: {test_result['success']}")
            
            return test_result
            
        except Exception as e:
            test_result = {
                'test_name': test_name,
                'input': test_input,
                'output': None,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results.append(test_result)
            
            if self.verbose:
                print(f"\nTest: {test_name}")
                print(f"✗ Error: {e}")
            
            return test_result
    
    def validate_output(self, actual: Any, expected: Any) -> Tuple[bool, List[str]]:
        """Validate actual output against expected"""
        differences = []
        
        if type(actual) != type(expected):
            differences.append(f"Type mismatch: {type(actual)} vs {type(expected)}")
            return False, differences
        
        if isinstance(actual, dict):
            # Check all keys
            for key in expected:
                if key not in actual:
                    differences.append(f"Missing key: {key}")
                elif actual[key] != expected[key]:
                    differences.append(f"Value mismatch for {key}: {actual[key]} vs {expected[key]}")
            
            for key in actual:
                if key not in expected:
                    differences.append(f"Unexpected key: {key}")
        
        elif isinstance(actual, (list, tuple)):
            if len(actual) != len(expected):
                differences.append(f"Length mismatch: {len(actual)} vs {len(expected)}")
            else:
                for i, (a, e) in enumerate(zip(actual, expected)):
                    if a != e:
                        differences.append(f"Item {i} mismatch: {a} vs {e}")
        
        else:
            if actual != expected:
                differences.append(f"Value mismatch: {actual} vs {expected}")
        
        return len(differences) == 0, differences
    
    def save_results(self):
        """Save test results to file"""
        output_file = self.output_dir / f"{self.module_name}_test.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'module': self.module_name,
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(self.test_results),
                'passed': sum(1 for r in self.test_results if r['success']),
                'failed': sum(1 for r in self.test_results if not r['success']),
                'success_rate': sum(1 for r in self.test_results if r['success']) / len(self.test_results) * 100 if self.test_results else 0,
                'results': self.test_results
            }, f, indent=2)
        
        print(f"\n✓ Results saved to: {output_file}")
    
    def print_summary(self):
        """Print test summary"""
        if not self.test_results:
            print("\nNo tests run")
            return
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['success'])
        failed = total - passed
        success_rate = (passed / total) * 100
        
        print("\n" + "="*50)
        print(f"Module: {self.module_name}")
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n🎉 100% SUCCESS - Module validated for Phase 1!")
        elif success_rate >= 90:
            print("\n⚠️  Close! Fix remaining issues for 100% success")
        else:
            print("\n❌ Module needs significant fixes")
        
        print("="*50)


def load_test_cases(file_path: str) -> List[Dict]:
    """Load test cases from file"""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Test file not found: {file_path}")
        return []
    
    if path.suffix == '.json':
        with open(path, 'r') as f:
            return json.load(f)
    else:
        # Assume text file with one test per line
        with open(path, 'r') as f:
            return [{'input': line.strip()} for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(description='Test individual pipeline modules')
    parser.add_argument('--module', '-m', required=True,
                       help='Module name to test')
    parser.add_argument('--input', '-i',
                       help='Single test input string')
    parser.add_argument('--input-file', '-f',
                       help='File containing test cases')
    parser.add_argument('--expected', '-e',
                       help='Expected output (for validation)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Create tester
    tester = ModuleTester(args.module, args.verbose)
    
    # Load module
    if not tester.load_module():
        sys.exit(1)
    
    # Run tests
    if args.input:
        # Single test
        result = tester.run_test(args.input, "manual_test")
        
        if args.expected:
            # Validate against expected
            try:
                expected = json.loads(args.expected)
                success, diffs = tester.validate_output(result['output'], expected)
                
                if success:
                    print("✓ Output matches expected!")
                else:
                    print("✗ Output differs from expected:")
                    for diff in diffs:
                        print(f"  - {diff}")
            except:
                print("Could not parse expected output")
    
    elif args.input_file:
        # Multiple tests from file
        test_cases = load_test_cases(args.input_file)
        
        for i, test_case in enumerate(test_cases):
            test_input = test_case.get('input', test_case)
            test_name = test_case.get('name', f"test_{i+1}")
            
            result = tester.run_test(test_input, test_name)
            
            # If expected output provided in test case
            if 'expected' in test_case:
                success, diffs = tester.validate_output(
                    result['output'], 
                    test_case['expected']
                )
                
                if not success and args.verbose:
                    print(f"  Validation failed:")
                    for diff in diffs:
                        print(f"    - {diff}")
    
    else:
        print("No input provided. Use --input or --input-file")
        sys.exit(1)
    
    # Save results
    tester.save_results()
    
    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    main()