#!/usr/bin/env python3
"""
Change Tracker - Track all changes made during processing
Maintains audit trail of all database modifications
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class ChangeTracker:
    """
    Tracks all changes made to the database
    Provides audit trail and rollback capability
    """
    
    def __init__(self, log_directory: str = None):
        self.logger = logging.getLogger(__name__)
        self.log_dir = Path(log_directory) if log_directory else Path('change_logs')
        self.log_dir.mkdir(exist_ok=True)
        
        # Current session changes
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.changes = []
        self.summary = {
            'additions': 0,
            'updates': 0,
            'deletions': 0,
            'fields_modified': 0,
        }
        
        # Change log file
        self.log_file = self.log_dir / f"changes_{self.session_id}.json"
    
    def track_addition(self, entity_type: str, entity_id: int, data: Dict):
        """Track addition of new entity"""
        change = {
            'timestamp': datetime.now().isoformat(),
            'action': 'add',
            'entity_type': entity_type,
            'entity_id': entity_id,
            'new_data': self._sanitize_data(data),
            'old_data': None,
        }
        
        self.changes.append(change)
        self.summary['additions'] += 1
        
        self.logger.info(f"Tracked addition: {entity_type} {entity_id}")
        self._save_changes()
    
    def track_update(self, entity_type: str, entity_id: int, 
                    old_data: Dict, new_data: Dict):
        """Track update of existing entity"""
        # Calculate field changes
        field_changes = self._calculate_field_changes(old_data, new_data)
        
        change = {
            'timestamp': datetime.now().isoformat(),
            'action': 'update',
            'entity_type': entity_type,
            'entity_id': entity_id,
            'old_data': self._sanitize_data(old_data),
            'new_data': self._sanitize_data(new_data),
            'field_changes': field_changes,
        }
        
        self.changes.append(change)
        self.summary['updates'] += 1
        self.summary['fields_modified'] += len(field_changes)
        
        self.logger.info(
            f"Tracked update: {entity_type} {entity_id} "
            f"({len(field_changes)} fields changed)"
        )
        self._save_changes()
    
    def track_deletion(self, entity_type: str, entity_id: int, data: Dict):
        """Track deletion of entity"""
        change = {
            'timestamp': datetime.now().isoformat(),
            'action': 'delete',
            'entity_type': entity_type,
            'entity_id': entity_id,
            'old_data': self._sanitize_data(data),
            'new_data': None,
        }
        
        self.changes.append(change)
        self.summary['deletions'] += 1
        
        self.logger.info(f"Tracked deletion: {entity_type} {entity_id}")
        self._save_changes()
    
    def track_field_change(self, entity_type: str, entity_id: int,
                          field: str, old_value: Any, new_value: Any):
        """Track individual field change"""
        change = {
            'timestamp': datetime.now().isoformat(),
            'action': 'field_update',
            'entity_type': entity_type,
            'entity_id': entity_id,
            'field': field,
            'old_value': self._sanitize_value(old_value),
            'new_value': self._sanitize_value(new_value),
        }
        
        self.changes.append(change)
        self.summary['fields_modified'] += 1
        
        self.logger.debug(
            f"Tracked field change: {entity_type} {entity_id}.{field}"
        )
        self._save_changes()
    
    def _calculate_field_changes(self, old_data: Dict, new_data: Dict) -> List[Dict]:
        """Calculate which fields changed between versions"""
        field_changes = []
        
        # Check all fields
        all_fields = set(old_data.keys()) | set(new_data.keys())
        
        for field in all_fields:
            if field in ['quest_id', 'npc_id']:  # Skip ID fields
                continue
            
            old_value = old_data.get(field)
            new_value = new_data.get(field)
            
            if old_value != new_value:
                field_changes.append({
                    'field': field,
                    'old_value': self._sanitize_value(old_value),
                    'new_value': self._sanitize_value(new_value),
                    'change_type': self._classify_change(old_value, new_value),
                })
        
        return field_changes
    
    def _classify_change(self, old_value: Any, new_value: Any) -> str:
        """Classify the type of change"""
        if old_value is None and new_value is not None:
            return 'added'
        elif old_value is not None and new_value is None:
            return 'removed'
        elif isinstance(old_value, str) and isinstance(new_value, str):
            if len(new_value) > len(old_value):
                return 'expanded'
            elif len(new_value) < len(old_value):
                return 'shortened'
            else:
                return 'modified'
        elif isinstance(old_value, (list, dict)) and isinstance(new_value, (list, dict)):
            if len(new_value) > len(old_value):
                return 'expanded'
            elif len(new_value) < len(old_value):
                return 'reduced'
            else:
                return 'modified'
        else:
            return 'changed'
    
    def _sanitize_data(self, data: Dict) -> Dict:
        """Sanitize data for JSON serialization"""
        if data is None:
            return None
        
        sanitized = {}
        for key, value in data.items():
            sanitized[key] = self._sanitize_value(value)
        
        return sanitized
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize individual value for JSON"""
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._sanitize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        else:
            return str(value)
    
    def _save_changes(self):
        """Save changes to log file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'summary': self.summary,
                    'changes': self.changes,
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save change log: {str(e)}")
    
    def get_changes_by_entity(self, entity_type: str, entity_id: int) -> List[Dict]:
        """Get all changes for specific entity"""
        entity_changes = []
        
        for change in self.changes:
            if (change['entity_type'] == entity_type and 
                change['entity_id'] == entity_id):
                entity_changes.append(change)
        
        return entity_changes
    
    def get_changes_by_action(self, action: str) -> List[Dict]:
        """Get all changes of specific action type"""
        return [c for c in self.changes if c['action'] == action]
    
    def get_recent_changes(self, limit: int = 10) -> List[Dict]:
        """Get most recent changes"""
        return self.changes[-limit:] if len(self.changes) > limit else self.changes
    
    def generate_change_report(self) -> str:
        """Generate human-readable change report"""
        lines = []
        lines.append("=" * 70)
        lines.append("CHANGE TRACKING REPORT")
        lines.append(f"Session: {self.session_id}")
        lines.append("=" * 70)
        
        # Summary
        lines.append("\n--- Summary ---")
        lines.append(f"Total Changes: {len(self.changes)}")
        lines.append(f"  Additions: {self.summary['additions']}")
        lines.append(f"  Updates: {self.summary['updates']}")
        lines.append(f"  Deletions: {self.summary['deletions']}")
        lines.append(f"  Fields Modified: {self.summary['fields_modified']}")
        
        # Recent changes
        recent = self.get_recent_changes(10)
        if recent:
            lines.append("\n--- Recent Changes (Last 10) ---")
            for change in recent:
                lines.append(self._format_change(change))
        
        # Additions detail
        additions = self.get_changes_by_action('add')
        if additions:
            lines.append(f"\n--- New Entities Added ({len(additions)}) ---")
            for add in additions[:5]:  # Show first 5
                lines.append(f"  {add['entity_type']} {add['entity_id']}")
            if len(additions) > 5:
                lines.append(f"  ... and {len(additions)-5} more")
        
        # Updates detail
        updates = self.get_changes_by_action('update')
        if updates:
            lines.append(f"\n--- Entities Updated ({len(updates)}) ---")
            for update in updates[:5]:  # Show first 5
                field_count = len(update.get('field_changes', []))
                lines.append(
                    f"  {update['entity_type']} {update['entity_id']} "
                    f"({field_count} fields)"
                )
            if len(updates) > 5:
                lines.append(f"  ... and {len(updates)-5} more")
        
        return '\n'.join(lines)
    
    def _format_change(self, change: Dict) -> str:
        """Format single change for display"""
        timestamp = change['timestamp'].split('T')[1].split('.')[0]  # Time only
        entity = f"{change['entity_type']} {change['entity_id']}"
        
        if change['action'] == 'add':
            return f"  [{timestamp}] ADDED {entity}"
        elif change['action'] == 'update':
            fields = len(change.get('field_changes', []))
            return f"  [{timestamp}] UPDATED {entity} ({fields} fields)"
        elif change['action'] == 'delete':
            return f"  [{timestamp}] DELETED {entity}"
        elif change['action'] == 'field_update':
            field = change['field']
            return f"  [{timestamp}] FIELD {entity}.{field}"
        else:
            return f"  [{timestamp}] {change['action'].upper()} {entity}"
    
    def generate_rollback_script(self) -> List[Dict]:
        """Generate rollback commands to undo changes"""
        rollback_commands = []
        
        # Process changes in reverse order
        for change in reversed(self.changes):
            if change['action'] == 'add':
                # To rollback addition, delete it
                rollback_commands.append({
                    'action': 'delete',
                    'entity_type': change['entity_type'],
                    'entity_id': change['entity_id'],
                })
            
            elif change['action'] == 'update':
                # To rollback update, restore old data
                rollback_commands.append({
                    'action': 'restore',
                    'entity_type': change['entity_type'],
                    'entity_id': change['entity_id'],
                    'data': change['old_data'],
                })
            
            elif change['action'] == 'delete':
                # To rollback deletion, restore it
                rollback_commands.append({
                    'action': 'restore',
                    'entity_type': change['entity_type'],
                    'entity_id': change['entity_id'],
                    'data': change['old_data'],
                })
        
        return rollback_commands
    
    def export_changes(self, filepath: str = None) -> str:
        """Export changes to file"""
        if not filepath:
            filepath = self.log_dir / f"export_{self.session_id}.json"
        
        export_data = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'summary': self.summary,
            'total_changes': len(self.changes),
            'changes': self.changes,
            'rollback_script': self.generate_rollback_script(),
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Exported changes to {filepath}")
        return str(filepath)
    
    def load_changes(self, filepath: str) -> bool:
        """Load changes from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.session_id = data.get('session_id', self.session_id)
            self.summary = data.get('summary', self.summary)
            self.changes = data.get('changes', [])
            
            self.logger.info(f"Loaded {len(self.changes)} changes from {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load changes: {str(e)}")
            return False


def main():
    """Test the change tracker"""
    tracker = ChangeTracker()
    
    # Track some changes
    tracker.track_addition('quest', 12345, {
        'name': 'New Quest',
        'level': 10,
        'objectives': ['Do something'],
    })
    
    tracker.track_update('quest', 12346, 
        old_data={'name': 'Old Name', 'level': 5},
        new_data={'name': 'New Name', 'level': 10}
    )
    
    tracker.track_field_change('npc', 100, 'spawns', 
        old_value=[[50, 50]], 
        new_value=[[60, 60], [70, 70]]
    )
    
    # Generate report
    report = tracker.generate_change_report()
    print(report)
    
    # Generate rollback script
    rollback = tracker.generate_rollback_script()
    print(f"\nRollback commands: {len(rollback)}")
    
    # Export changes
    export_path = tracker.export_changes()
    print(f"\nExported to: {export_path}")


if __name__ == "__main__":
    main()