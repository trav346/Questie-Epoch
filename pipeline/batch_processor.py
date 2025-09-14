#!/usr/bin/env python3
"""
Batch Processor for Pipeline
Processes submissions in batches to avoid timeouts with large datasets
"""

import os
import sys
import json
import glob
import time
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory and modules directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
sys.path.insert(0, parent_dir)
sys.path.insert(0, modules_dir)

from data_aggregator import DataAggregator
from database_writer import DatabaseWriter

class BatchProcessor:
    """Process submissions in manageable batches"""
    
    def __init__(self, batch_size: int = 100):
        print(f"[INIT] Creating BatchProcessor with batch_size={batch_size}")
        self.batch_size = batch_size
        print("[INIT] Creating DataAggregator...")
        self.aggregator = DataAggregator()
        print("[INIT] Creating DatabaseWriter...")
        self.db_writer = DatabaseWriter()
        print("[INIT] Setting up results directory...")
        self.results_dir = Path("batch_results")
        self.results_dir.mkdir(exist_ok=True)
        print("[INIT] BatchProcessor ready!")
        
    def get_submission_files(self) -> List[Path]:
        """Get all submission files"""
        submissions_dir = Path("../pending_submissions")  # GitHub Workflow/pending_submissions
        patterns = ["issue_*.txt"]  # Only get issue files
        
        files = []
        for pattern in patterns:
            files.extend(submissions_dir.glob(pattern))
        
        # Sort by file name for consistent ordering
        files.sort()
        print(f"  Found files in: {submissions_dir.resolve()}")
        if files:
            print(f"  First file: {files[0].name}")
        return files
    
    def process_batch(self, files: List[Path], batch_num: int) -> Dict[str, Any]:
        """Process a single batch of files"""
        print(f"\n=== Processing Batch {batch_num} ({len(files)} files) ===")
        
        batch_results = {
            'quests': [],
            'npcs': [],
            'items': [],
            'objects': []
        }
        
        # Process each file
        for i, file_path in enumerate(files, 1):
            if i % 10 == 0:
                print(f"  Processing file {i}/{len(files)}...")
            
            try:
                # Debug: Show what file we're processing
                if i == 1:
                    print(f"  DEBUG: Processing {file_path.name}")
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                result = self.aggregator.process_submission(content, str(file_path))
                
                # Debug: Show what we got
                if i == 1 and result:
                    print(f"  DEBUG: Got {len(result.get('quests', []))} quests, {len(result.get('npcs', []))} NPCs")
                
                # Merge results
                if result:
                    for key in batch_results:
                        if key in result:
                            batch_results[key].extend(result[key])
                            
            except Exception as e:
                print(f"  Error processing {file_path.name}: {e}")
                continue
        
        # Save batch results
        batch_file = self.results_dir / f"batch_{batch_num:03d}_results.json"
        with open(batch_file, 'w') as f:
            json.dump(batch_results, f, indent=2)
        
        print(f"  Batch {batch_num} complete:")
        print(f"    Quests: {len(batch_results['quests'])}")
        print(f"    NPCs: {len(batch_results['npcs'])}")
        print(f"    Items: {len(batch_results['items'])}")
        print(f"    Objects: {len(batch_results['objects'])}")
        print(f"    Results saved to: {batch_file}")
        
        return batch_results
    
    def merge_all_batches(self) -> Dict[str, Any]:
        """Merge all batch results into final output"""
        print("\n=== Merging All Batches ===")
        
        merged = {
            'quests': {},
            'npcs': {},
            'items': {},
            'objects': {}
        }
        
        # Load and merge each batch file
        batch_files = sorted(self.results_dir.glob("batch_*_results.json"))
        
        for batch_file in batch_files:
            print(f"  Merging {batch_file.name}...")
            
            with open(batch_file, 'r') as f:
                batch_data = json.load(f)
            
            # Merge quests (deduplicate by ID)
            for quest in batch_data.get('quests', []):
                quest_id = quest.get('id')  # Changed from 'questId' to 'id'
                if quest_id:
                    if quest_id not in merged['quests']:
                        merged['quests'][quest_id] = quest
                    else:
                        # Could implement merging logic here if needed
                        pass
            
            # Merge NPCs (deduplicate by ID)
            for npc in batch_data.get('npcs', []):
                npc_id = npc.get('id')  # Changed from 'npcId' to 'id'
                if npc_id:
                    if npc_id not in merged['npcs']:
                        merged['npcs'][npc_id] = npc
                    else:
                        # Merge spawns and quest linkage
                        existing = merged['npcs'][npc_id]
                        # Merge spawns
                        for zone_id, coords in npc.get('spawns', {}).items():
                            if zone_id not in existing['spawns']:
                                existing['spawns'][zone_id] = coords
                            else:
                                # Merge coordinates (avoiding duplicates)
                                for coord in coords:
                                    if not any(abs(c['x'] - coord['x']) < 0.5 and 
                                             abs(c['y'] - coord['y']) < 0.5 
                                             for c in existing['spawns'][zone_id]):
                                        existing['spawns'][zone_id].append(coord)
                        
                        # Merge quest linkage
                        existing['questStarts'] = list(set(existing.get('questStarts', []) + 
                                                          npc.get('questStarts', [])))
                        existing['questEnds'] = list(set(existing.get('questEnds', []) + 
                                                        npc.get('questEnds', [])))
            
            # Similar merging for items and objects
            for item in batch_data.get('items', []):
                item_id = item.get('id')  # Changed from 'itemId' to 'id'
                if item_id and item_id not in merged['items']:
                    merged['items'][item_id] = item
            
            for obj in batch_data.get('objects', []):
                obj_id = obj.get('id')  # Changed from 'objectId' to 'id'
                if obj_id and obj_id not in merged['objects']:
                    merged['objects'][obj_id] = obj
        
        # Convert back to lists
        final_results = {
            'quests': list(merged['quests'].values()),
            'npcs': list(merged['npcs'].values()),
            'items': list(merged['items'].values()),
            'objects': list(merged['objects'].values())
        }
        
        print(f"\n  Final merged results:")
        print(f"    Unique Quests: {len(final_results['quests'])}")
        print(f"    Unique NPCs: {len(final_results['npcs'])}")
        print(f"    Unique Items: {len(final_results['items'])}")
        print(f"    Unique Objects: {len(final_results['objects'])}")
        
        # Save final merged results
        final_file = Path("complete_pipeline_results.json")
        with open(final_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n  Final results saved to: {final_file}")
        
        return final_results
    
    def generate_lua_files(self, results: Dict[str, Any]):
        """Generate Lua database files from results"""
        print("\n=== Generating Lua Files ===")
        
        output_dir = Path("../ready_to_apply")
        output_dir.mkdir(exist_ok=True)
        
        # Use the write_aggregated_data method which handles all database types
        database_paths = {
            'quest': str(output_dir / "epochQuestDB_batch.lua"),
            'npc': str(output_dir / "epochNpcDB_batch.lua"),
            'item': str(output_dir / "epochItemDB_batch.lua"),
            'object': str(output_dir / "epochObjectDB_batch.lua")
        }
        
        write_results = self.db_writer.write_aggregated_data(results, database_paths)
        
        # Report results
        for db_type, info in write_results.items():
            if info['written'] > 0:
                print(f"  {db_type.capitalize()} database: {info['path']} ({info['written']} entries)")
    
    def run(self):
        """Run the batch processing pipeline"""
        print("=" * 60)
        print("BATCH PROCESSING PIPELINE")
        print("=" * 60)
        
        print("[RUN] Getting submission files...")
        # Get all submission files
        files = self.get_submission_files()
        total_files = len(files)
        
        print(f"\nFound {total_files} submission files")
        print(f"Processing in batches of {self.batch_size}")
        
        # Process in batches
        batch_num = 1
        for i in range(0, total_files, self.batch_size):
            print(f"[RUN] Preparing batch {batch_num} (files {i+1}-{min(i+self.batch_size, total_files)})...")
            batch_files = files[i:i + self.batch_size]
            self.process_batch(batch_files, batch_num)
            batch_num += 1
            
            # Small delay between batches to prevent overwhelming system
            if i + self.batch_size < total_files:
                print(f"[RUN] Sleeping 0.5s before next batch...")
                time.sleep(0.5)
        
        # Merge all batch results
        final_results = self.merge_all_batches()
        
        # Generate Lua files
        self.generate_lua_files(final_results)
        
        print("\n" + "=" * 60)
        print("BATCH PROCESSING COMPLETE")
        print("=" * 60)
        
        return final_results


if __name__ == "__main__":
    # Allow batch size override from command line
    batch_size = 100
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
            print(f"Using batch size: {batch_size}")
        except ValueError:
            print(f"Invalid batch size: {sys.argv[1]}, using default: 100")
    
    processor = BatchProcessor(batch_size=batch_size)
    processor.run()