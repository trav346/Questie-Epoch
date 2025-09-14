#!/usr/bin/env python3
"""
Pipeline Runner - Main orchestrator for modular pipeline
Coordinates entire processing workflow from input to database updates
"""

import sys
import logging
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum

# Import all modules
from data_aggregator import DataAggregator
from validation_engine import ValidationEngine
from database_comparator import DatabaseComparator, ComparisonResult
from merge_decision_engine import MergeDecisionEngine, MergeStrategy, MergeDecision
from database_writer import DatabaseWriter
from backup_manager import BackupManager


class PipelineStatus(Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class PipelineRunner:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize modules
        self.aggregator = DataAggregator()
        self.validation_engine = ValidationEngine()
        self.database_comparator = DatabaseComparator()
        self.merge_engine = MergeDecisionEngine()
        self.database_writer = DatabaseWriter(self.config.get('database_writer', {}))
        self.backup_manager = BackupManager(self.config.get('backup_manager', {}))
        
        # Processing state
        self.current_batch = None
        self.processing_stats = {
            'submissions_processed': 0,
            'quests_extracted': 0,
            'npcs_extracted': 0,
            'validation_failures': 0,
            'merge_conflicts': 0,
            'database_updates': 0
        }
        
        # Setup logging
        self.setup_logging()
    
    def run_pipeline(self, input_path: str, output_path: str = None, 
                    database_paths: Dict = None) -> Dict:
        """
        Run complete pipeline on input data
        
        Args:
            input_path: Path to input file or directory
            output_path: Optional path for output files
            database_paths: Optional dict with 'quest_db' and 'npc_db' paths
            
        Returns:
            Dictionary with pipeline results
        """
        try:
            self.logger.info(f"Starting pipeline for: {input_path}")
            
            # 1. Load submissions
            submissions = self._load_submissions(input_path)
            if not submissions:
                return self._create_error_result("No submissions found in input path")
            
            # 2. Process through aggregator
            aggregated_results = self._process_submissions(submissions)
            
            # 3. Validate aggregated data
            validation_results = self._validate_aggregated_data(aggregated_results)
            
            # 4. Compare with existing database
            comparison_results = {}
            if database_paths:
                comparison_results = self._compare_with_database(
                    aggregated_results, database_paths
                )
            
            # 5. Make merge decisions
            merge_decisions = []
            if comparison_results:
                merge_decisions = self._make_merge_decisions(
                    aggregated_results, comparison_results
                )
            
            # 6. Create backups if updating database
            backup_results = {}
            if database_paths and aggregated_results.get('quests'):
                backup_results = self._create_database_backups(database_paths)
            
            # 7. Write to database
            write_results = {}
            if database_paths:
                write_results = self._write_database_changes(
                    aggregated_results, merge_decisions, database_paths
                )
            
            # 8. Generate output files
            output_results = {}
            if output_path:
                output_results = self._generate_output_files(
                    aggregated_results, validation_results, output_path
                )
            
            # 9. Compile results
            return self._compile_results(
                submissions, aggregated_results, validation_results,
                comparison_results, merge_decisions, write_results,
                output_results, backup_results
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            return self._create_error_result(f"Pipeline execution failed: {e}", e)
    
    def run_batch_processing(self, batch_config: Dict) -> Dict:
        """
        Process multiple submission groups in batch
        
        Args:
            batch_config: Configuration for batch processing
            
        Returns:
            Dictionary with batch results
        """
        try:
            self.current_batch = batch_config.get('batch_id', 
                                                 datetime.now().strftime('%Y%m%d_%H%M%S'))
            
            # Track batch in database
            self._init_batch_tracking()
            
            # Process each group
            all_results = []
            total_submissions = 0
            
            for group in batch_config.get('groups', []):
                self.logger.info(f"Processing group: {group.get('name', 'unnamed')}")
                
                # Run pipeline for this group
                results = self.run_pipeline(
                    input_path=group['input_path'],
                    output_path=group.get('output_path'),
                    database_paths=group.get('database_paths')
                )
                
                all_results.append(results)
                total_submissions += results.get('submissions_processed', 0)
            
            # Compile batch summary
            return self._compile_batch_summary(all_results, total_submissions)
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}", exc_info=True)
            return self._create_error_result(f"Batch processing failed: {e}", e)
    
    def _init_batch_tracking(self):
        """Initialize batch tracking in database"""
        try:
            tracker_db = self.config.get('tracker_db', 'submission_tracker.db')
            conn = sqlite3.connect(tracker_db)
            cursor = conn.cursor()
            
            # Create tables if needed
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id TEXT PRIMARY KEY,
                    started_at TIMESTAMP,
                    status TEXT,
                    stats JSON
                )
            ''')
            
            # Insert batch record
            cursor.execute(
                "INSERT INTO batches (batch_id, started_at, status) VALUES (?, ?, ?)",
                (self.current_batch, datetime.now(), PipelineStatus.RUNNING.value)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.warning(f"Batch tracking initialization failed: {e}")
    
    def _load_submissions(self, input_path: str) -> List[Dict]:
        """Load submissions from file or directory"""
        submissions = []
        path = Path(input_path)
        
        if path.is_file():
            # Single file
            submission = self._load_single_submission(path)
            if submission:
                submissions.append(submission)
        
        elif path.is_dir():
            # Directory of submissions
            for file_path in path.glob('*.txt'):
                submission = self._load_single_submission(file_path)
                if submission:
                    submissions.append(submission)
        
        self.logger.info(f"Loaded {len(submissions)} submissions")
        return submissions
    
    def _load_single_submission(self, file_path: Path) -> Optional[Dict]:
        """Load a single submission file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from filename if available
            metadata = self._extract_metadata_from_filename(file_path)
            
            return {
                'content': content,
                'source_file': str(file_path),
                'metadata': metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            return None
    
    def _extract_metadata_from_filename(self, file_path: Path) -> Dict:
        """Extract metadata from submission filename"""
        # Expected format: issue_####_questname.txt
        try:
            parts = file_path.stem.split('_')
            if len(parts) >= 2 and parts[0] == 'issue':
                return {
                    'issue_number': int(parts[1]),
                    'title': parts[2] if len(parts) > 2 else 'Unknown'
                }
        except:
            pass
        
        return {'issue_number': None, 'title': file_path.stem}
    
    def _process_submissions(self, submissions: List[Dict]) -> Dict:
        """Process submissions through the data aggregator"""
        all_results = {
            'quests': [],
            'npcs': [],
            'items': [],
            'objects': [],
            'errors': [],
            'warnings': [],
            'format_info': []
        }
        
        for i, submission in enumerate(submissions):
            try:
                self.logger.info(f"Processing submission {i+1}/{len(submissions)}")
                
                content = submission.get('content', '')
                source_file = submission.get('source_file')
                
                # Process through aggregator
                results = self.aggregator.process_submission(content, source_file)
                
                # Merge results
                for key in ['quests', 'npcs', 'items', 'objects', 'errors', 'warnings']:
                    if key in results:
                        all_results[key].extend(results[key])
                
                # Track format information
                if results.get('format_info'):
                    all_results['format_info'].append({
                        'source': source_file,
                        'format': results['format_info']
                    })
                
                self.processing_stats['submissions_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error processing submission {i+1}: {e}"
                self.logger.error(error_msg)
                all_results['errors'].append(error_msg)
        
        # Update stats
        self.processing_stats['quests_extracted'] = len(all_results['quests'])
        self.processing_stats['npcs_extracted'] = len(all_results['npcs'])
        
        self.logger.info(f"Aggregation complete: {len(all_results['quests'])} quests, {len(all_results['npcs'])} NPCs")
        return all_results
    
    def _validate_aggregated_data(self, aggregated_results: Dict) -> Dict:
        """Validate all aggregated data"""
        validation_results = {
            'quest_validations': [],
            'npc_validations': [],
            'overall_quality': 0,
            'validation_summary': {}
        }
        
        try:
            # Validate quests
            for quest in aggregated_results.get('quests', []):
                validation = self.validation_engine.validate_quest(quest)
                validation_results['quest_validations'].append(validation)
                
                if validation.get('overall_score', 0) < 50:
                    self.processing_stats['validation_failures'] += 1
            
            # Validate NPCs
            for npc in aggregated_results.get('npcs', []):
                validation = self.validation_engine.validate_npc(npc)
                validation_results['npc_validations'].append(validation)
            
            # Calculate overall quality
            all_scores = []
            for v in validation_results['quest_validations']:
                all_scores.append(v.get('overall_score', 0))
            for v in validation_results['npc_validations']:
                all_scores.append(v.get('overall_score', 0))
            
            if all_scores:
                validation_results['overall_quality'] = sum(all_scores) / len(all_scores)
            
            # Generate validation summary
            validation_results['validation_summary'] = self._generate_validation_summary(
                validation_results
            )
            
            self.logger.info(f"Validation complete: {validation_results['overall_quality']:.1f}% average quality")
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            validation_results['errors'] = [str(e)]
        
        return validation_results
    
    def _compare_with_database(self, aggregated_results: Dict, 
                              database_paths: Dict) -> Dict:
        """Compare aggregated data with existing database"""
        comparison_results = {
            'quest_comparisons': [],
            'npc_comparisons': [],
            'summary': {}
        }
        
        try:
            # Load databases
            quest_db_path = database_paths.get('quest_db')
            npc_db_path = database_paths.get('npc_db')
            
            if quest_db_path or npc_db_path:
                success = self.database_comparator.load_databases(quest_db_path, npc_db_path)
                if not success:
                    self.logger.warning("Database comparison skipped - could not load existing databases")
                    return comparison_results
            
            # Compare quests
            if aggregated_results.get('quests'):
                quest_dict = {q['id']: q for q in aggregated_results['quests']}
                quest_comparisons = self.database_comparator.compare_quest_data(quest_dict)
                comparison_results['quest_comparisons'] = quest_comparisons
            
            # Compare NPCs
            if aggregated_results.get('npcs'):
                npc_dict = {n['id']: n for n in aggregated_results['npcs']}
                npc_comparisons = self.database_comparator.compare_npc_data(npc_dict)
                comparison_results['npc_comparisons'] = npc_comparisons
            
            # Generate comparison summary
            all_comparisons = (comparison_results['quest_comparisons'] + 
                             comparison_results['npc_comparisons'])
            comparison_results['summary'] = self.database_comparator.generate_comparison_report(
                all_comparisons
            )
            
            self.logger.info(f"Database comparison complete: {comparison_results['summary']}")
            
        except Exception as e:
            self.logger.error(f"Database comparison failed: {e}")
            comparison_results['errors'] = [str(e)]
        
        return comparison_results
    
    def _make_merge_decisions(self, aggregated_results: Dict, 
                             comparison_results: Dict) -> List:
        """Make merge decisions for all data"""
        merge_decisions = []
        
        try:
            # Get all comparison results
            all_comparisons = (comparison_results.get('quest_comparisons', []) + 
                             comparison_results.get('npc_comparisons', []))
            
            # Make decisions for each comparison
            for comparison in all_comparisons:
                try:
                    decision = self.merge_engine.decide_merge_strategy(
                        comparison.entry_id,
                        comparison.entry_type,
                        comparison.existing_data or {},
                        comparison.new_data or {}
                    )
                    merge_decisions.append(decision)
                    
                    # Track conflicts
                    if decision.strategy == MergeStrategy.MANUAL_REVIEW:
                        self.processing_stats['merge_conflicts'] += 1
                
                except Exception as e:
                    self.logger.error(f"Merge decision failed for {comparison.entry_type} {comparison.entry_id}: {e}")
            
            # Log merge decision summary
            strategy_counts = {}
            for decision in merge_decisions:
                strategy = decision.strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            self.logger.info(f"Merge decisions: {strategy_counts}")
            
        except Exception as e:
            self.logger.error(f"Merge decision process failed: {e}")
        
        return merge_decisions
    
    def _create_database_backups(self, database_paths: Dict) -> Dict:
        """Create backups of database files"""
        backup_results = {
            'backups_created': [],
            'errors': []
        }
        
        try:
            files_to_backup = []
            for db_type, db_path in database_paths.items():
                if db_path and Path(db_path).exists():
                    files_to_backup.append(db_path)
            
            if files_to_backup:
                backup_ids = self.backup_manager.create_batch_backup(
                    files_to_backup,
                    f"Pre-pipeline backup for batch {self.current_batch or 'manual'}"
                )
                backup_results['backups_created'] = backup_ids
                self.logger.info(f"Created {len(backup_ids)} database backups")
        
        except Exception as e:
            error_msg = f"Backup creation failed: {e}"
            backup_results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return backup_results
    
    def _write_database_changes(self, aggregated_results: Dict, 
                               merge_decisions: List, database_paths: Dict) -> Dict:
        """Write approved changes to database files"""
        write_results = {
            'changes_applied': 0,
            'files_updated': [],
            'errors': []
        }
        
        try:
            # Filter for approved changes only
            approved_changes = {
                'quests': [],
                'npcs': []
            }
            
            # Apply merge decisions
            decision_map = {d.entry_id: d for d in merge_decisions}
            
            for quest in aggregated_results.get('quests', []):
                quest_id = quest['id']
                decision = decision_map.get(quest_id)
                
                if not decision or decision.strategy in [MergeStrategy.REPLACE_ALL, MergeStrategy.MERGE_FIELDS]:
                    approved_changes['quests'].append(quest)
            
            for npc in aggregated_results.get('npcs', []):
                npc_id = npc['id']
                decision = decision_map.get(npc_id)
                
                if not decision or decision.strategy in [MergeStrategy.REPLACE_ALL, MergeStrategy.MERGE_FIELDS]:
                    approved_changes['npcs'].append(npc)
            
            # Write to database files
            if database_paths:
                db_write_results = self.database_writer.write_aggregated_data(
                    approved_changes, database_paths
                )
                
                write_results['changes_applied'] = (
                    db_write_results.get('quests_written', 0) + 
                    db_write_results.get('npcs_written', 0)
                )
                
                if db_write_results.get('errors'):
                    write_results['errors'].extend(db_write_results['errors'])
            
            self.processing_stats['database_updates'] = write_results['changes_applied']
            self.logger.info(f"Database updates applied: {write_results['changes_applied']} entries")
            
        except Exception as e:
            error_msg = f"Database write failed: {e}"
            write_results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return write_results
    
    def _generate_output_files(self, aggregated_results: Dict, 
                              validation_results: Dict, output_path: str) -> Dict:
        """Generate output files with processed data"""
        output_results = {
            'files_created': [],
            'errors': []
        }
        
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate Lua database files
            if aggregated_results.get('quests'):
                quest_file = output_dir / 'epochQuestDB_updates.lua'
                with open(quest_file, 'w', encoding='utf-8') as f:
                    f.write("-- Quest Database Updates\n")
                    f.write(f"-- Generated by Pipeline Runner\n\n")
                    
                    for quest in aggregated_results['quests']:
                        entry = self.database_writer._generate_enhanced_quest_entry(quest)
                        f.write(entry + "\n")
                
                output_results['files_created'].append(str(quest_file))
            
            if aggregated_results.get('npcs'):
                npc_file = output_dir / 'epochNpcDB_updates.lua'
                with open(npc_file, 'w', encoding='utf-8') as f:
                    f.write("-- NPC Database Updates\n")
                    f.write(f"-- Generated by Pipeline Runner\n\n")
                    
                    for npc in aggregated_results['npcs']:
                        entry = self.database_writer._generate_npc_entry(npc)
                        f.write(entry + "\n")
                
                output_results['files_created'].append(str(npc_file))
            
            # Generate processing report
            report_file = output_dir / 'pipeline_report.json'
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'processing_stats': self.processing_stats,
                'validation_summary': validation_results.get('validation_summary', {}),
                'aggregated_results_summary': {
                    'quests': len(aggregated_results.get('quests', [])),
                    'npcs': len(aggregated_results.get('npcs', [])),
                    'items': len(aggregated_results.get('items', [])),
                    'errors': len(aggregated_results.get('errors', [])),
                    'warnings': len(aggregated_results.get('warnings', []))
                }
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            
            output_results['files_created'].append(str(report_file))
            
            self.logger.info(f"Generated {len(output_results['files_created'])} output files")
            
        except Exception as e:
            error_msg = f"Output generation failed: {e}"
            output_results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return output_results
    
    def _compile_results(self, submissions: List, aggregated_results: Dict,
                        validation_results: Dict, comparison_results: Dict,
                        merge_decisions: List, write_results: Dict,
                        output_results: Dict, backup_results: Dict) -> Dict:
        """Compile final pipeline results"""
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'submissions_processed': len(submissions),
            'processing_stats': self.processing_stats,
            'summary': {
                'quests_processed': len(aggregated_results.get('quests', [])),
                'npcs_processed': len(aggregated_results.get('npcs', [])),
                'validation_score': validation_results.get('overall_quality', 0),
                'database_updates': write_results.get('changes_applied', 0),
                'backups_created': len(backup_results.get('backups_created', [])),
                'output_files': len(output_results.get('files_created', [])),
                'merge_conflicts': self.processing_stats['merge_conflicts']
            },
            'detailed_results': {
                'aggregated_results': aggregated_results,
                'validation_results': validation_results,
                'comparison_results': comparison_results,
                'merge_decisions': [{
                    'entry_id': d.entry_id,
                    'entry_type': d.entry_type,
                    'strategy': d.strategy.value,
                    'confidence': d.confidence,
                    'reasoning': d.reasoning
                } for d in merge_decisions],
                'write_results': write_results,
                'output_results': output_results,
                'backup_results': backup_results
            }
        }
    
    def _create_error_result(self, error_message: str, exception: Exception = None) -> Dict:
        """Create error result dictionary"""
        return {
            'success': False,
            'error': error_message,
            'timestamp': datetime.now().isoformat(),
            'exception': str(exception) if exception else None,
            'processing_stats': self.processing_stats
        }
    
    def _generate_validation_summary(self, validation_results: Dict) -> Dict:
        """Generate validation summary"""
        quest_scores = [v.get('overall_score', 0) for v in validation_results.get('quest_validations', [])]
        npc_scores = [v.get('overall_score', 0) for v in validation_results.get('npc_validations', [])]
        
        return {
            'total_validations': len(quest_scores) + len(npc_scores),
            'average_quest_score': sum(quest_scores) / len(quest_scores) if quest_scores else 0,
            'average_npc_score': sum(npc_scores) / len(npc_scores) if npc_scores else 0,
            'high_quality_entries': len([s for s in quest_scores + npc_scores if s >= 80]),
            'failed_validations': len([s for s in quest_scores + npc_scores if s < 50])
        }
    
    def _compile_batch_summary(self, all_results: List, total_submissions: int) -> Dict:
        """Compile batch processing summary"""
        total_quests = sum(r.get('summary', {}).get('quests_processed', 0) for r in all_results)
        total_npcs = sum(r.get('summary', {}).get('npcs_processed', 0) for r in all_results)
        total_updates = sum(r.get('summary', {}).get('database_updates', 0) for r in all_results)
        total_conflicts = sum(r.get('summary', {}).get('merge_conflicts', 0) for r in all_results)
        
        return {
            'batch_id': self.current_batch,
            'success': True,
            'total_submissions': total_submissions,
            'total_quests': total_quests,
            'total_npcs': total_npcs,
            'database_updates': total_updates,
            'merge_conflicts': total_conflicts,
            'group_results': all_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = self.config.get('log_level', 'INFO')
        log_file = self.config.get('log_file')
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ] + ([logging.FileHandler(log_file)] if log_file else [])
        )
    
    def _get_default_config(self) -> Dict:
        """Get default pipeline configuration"""
        return {
            'log_level': 'INFO',
            'tracker_db': 'submission_tracker.db',
            'backup_dir': './backups',
            'database_writer': {
                'auto_backup': True
            },
            'backup_manager': {
                'compression': True,
                'retention_days': 30
            },
            'merge_engine': {
                'conservative_mode': False
            }
        }


def main():
    """CLI entry point for pipeline runner"""
    parser = argparse.ArgumentParser(description='Questie Pipeline Runner')
    parser.add_argument('--input', '-i', required=True,
                       help='Input path (file or directory)')
    parser.add_argument('--output', '-o',
                       help='Output directory for processed files')
    parser.add_argument('--quest-db',
                       help='Path to quest database file')
    parser.add_argument('--npc-db',
                       help='Path to NPC database file')
    parser.add_argument('--config', '-c',
                       help='Configuration file path')
    parser.add_argument('--batch', '-b',
                       help='Batch configuration file')
    parser.add_argument('--legacy', action='store_true',
                       help='Process legacy v1.0.68 format submissions')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    if args.verbose:
        config['log_level'] = 'DEBUG'
    
    # Initialize pipeline
    runner = PipelineRunner(config)
    
    try:
        if args.batch:
            # Batch processing
            with open(args.batch, 'r') as f:
                batch_config = json.load(f)
            
            results = runner.run_batch_processing(batch_config)
        
        else:
            # Single run
            database_paths = {}
            if args.quest_db:
                database_paths['quest_db'] = args.quest_db
            if args.npc_db:
                database_paths['npc_db'] = args.npc_db
            
            results = runner.run_pipeline(
                input_path=args.input,
                output_path=args.output,
                database_paths=database_paths if database_paths else None
            )
        
        # Print summary
        if results['success']:
            summary = results.get('summary', {})
            print(f"\n✅ Pipeline completed successfully!")
            print(f"   Submissions processed: {results.get('submissions_processed', 0)}")
            print(f"   Quests processed: {summary.get('quests_processed', 0)}")
            print(f"   NPCs processed: {summary.get('npcs_processed', 0)}")
            print(f"   Database updates: {summary.get('database_updates', 0)}")
            print(f"   Average quality: {summary.get('validation_score', 0):.1f}%")
            
            if summary.get('merge_conflicts', 0) > 0:
                print(f"   ⚠️  Merge conflicts: {summary['merge_conflicts']} (require manual review)")
        
        else:
            print(f"\n❌ Pipeline failed: {results.get('error')}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ Pipeline interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()