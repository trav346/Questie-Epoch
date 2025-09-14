#!/usr/bin/env python3
"""
Fetch quest data submissions from GitHub issues.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
import requests
from pathlib import Path

class GitHubIssueFetcher:
    def __init__(self, config_path: str = "config.json", output_root: Optional[str] = None):
        """Initialize with configuration."""
        self.config = self.load_config(config_path)
        token = self.config.get('github_token', '')
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        self.repo = self.config.get('repo', 'owner/repository')
        
        # Resolve base output directory (default to script directory for stability)
        self.base_dir = Path(output_root) if output_root else Path(__file__).parent
        
        # Create directories
        self.pending_dir = self.base_dir / "pending_submissions"
        self.pending_dir.mkdir(exist_ok=True)
        
        self.processed_dir = self.base_dir / "processed"
        self.processed_dir.mkdir(exist_ok=True)
        
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)
    
    def load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Create default config
            default_config = {
                "github_token": "YOUR_GITHUB_TOKEN_HERE",
                "repository": "owner/repository",
                "labels": {
                    "data_submission": "quest-data",
                    "needs_processing": "needs-processing",
                    "processing": "processing",
                    "processed": "processed",
                    "needs_investigation": "needs-investigation"
                }
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config at {config_path}")
            print("Please update with your GitHub token!")
            return default_config
    
    def fetch_issues(self, labels: Optional[List[str]] = None, state: str = "all") -> List[Dict]:
        """Fetch issues from GitHub with quest data submissions."""
        url = f"{self.base_url}/repos/{self.repo}/issues"
        params = {
            "state": state,
            "per_page": 100,
            "sort": "updated",
            "direction": "desc"
        }
        
        all_issues = []
        page = 1
        
        while True:
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching issues: {response.status_code}")
                print(response.text)
                break
            
            issues = response.json()
            if not issues:
                break
            
            # Filter for quest-related issues by title and content
            quest_issues = []
            for issue in issues:
                title = issue.get('title', '').lower()
                body = issue.get('body', '') or ''
                
                # Check if this looks like a quest submission (enhanced detection)
                is_quest_issue = (
                    ('quest data' in title) or  # Catches [Quest Data], Quest Data, etc.
                    ('quest' in title and ('missing' in title or 'batch' in title)) or
                    ('missing quest' in title) or
                    ('batch submission' in title.lower()) or
                    ('=== QUEST DATA ===' in body) or
                    ('quest id:' in body.lower()) or
                    ('addon version:' in body.lower()) or
                    ('questie data collection' in body.lower()) or
                    ('.txt](' in body)  # GitHub file attachment pattern
                )
                
                if is_quest_issue:
                    print(f"Found quest issue #{issue['number']}: {issue['title']}")
                    quest_issues.append(issue)
                    
            all_issues.extend(quest_issues)
            page += 1
        
        print(f"Total quest issues found: {len(all_issues)}")
        return all_issues
    
    def parse_quest_ids(self, title: str, body: str) -> List[int]:
        """Extract all quest IDs from issue title or body (handles batch submissions)."""
        quest_ids = []
        
        # Check if this is a batch submission
        if 'Batch Submission' in title:
            # Extract all Quest ID: entries from body
            quest_id_matches = re.findall(r'Quest ID:\s*(\d+)', body)
            quest_ids.extend([int(qid) for qid in quest_id_matches])
            
            # Also check for Missing Quests: format with comma-separated IDs
            missing_quests_matches = re.findall(r'Missing Quests?:\s*([\d,\s]+)', title + ' ' + body)
            for match in missing_quests_matches:
                # Split by commas and extract numbers
                ids = re.findall(r'\d+', match)
                quest_ids.extend([int(qid) for qid in ids])
        else:
            # Single quest submission - try title first
            match = re.search(r'ID:\s*#?(\d+)', title, re.IGNORECASE)
            if match:
                quest_ids.append(int(match.group(1)))
            else:
                # Try body for single quest
                match = re.search(r'Quest ID:\s*(\d+)', body)
                if match:
                    quest_ids.append(int(match.group(1)))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for qid in quest_ids:
            if qid not in seen:
                seen.add(qid)
                unique_ids.append(qid)
                
        return unique_ids
    
    def parse_quest_id(self, title: str, body: str) -> Optional[int]:
        """Extract primary quest ID (for backwards compatibility)."""
        quest_ids = self.parse_quest_ids(title, body)
        return quest_ids[0] if quest_ids else None
    
    def save_submission(self, issue: Dict) -> Dict:
        """Save issue content to pending submissions."""
        issue_number = issue['number']
        title = issue['title']
        body = issue['body'] or ""
        created_at = issue['created_at']
        user = issue['user']['login']
        
        # Parse all quest IDs (handles batch submissions)
        quest_ids = self.parse_quest_ids(title, body)
        primary_quest_id = quest_ids[0] if quest_ids else None
        
        # Save raw submission
        submission_file = self.pending_dir / f"issue_{issue_number}.txt"
        with open(submission_file, 'w', encoding='utf-8') as f:
            f.write(f"GitHub Issue #{issue_number}\n")
            f.write(f"Title: {title}\n")
            f.write(f"User: {user}\n")
            f.write(f"Created: {created_at}\n")
            if len(quest_ids) > 1:
                f.write(f"Quest IDs: {', '.join(map(str, quest_ids))}\n")
            f.write(f"{'='*60}\n\n")
            f.write(body)
        
        # Return metadata with batch info
        return {
            "issue_number": issue_number,
            "quest_id": primary_quest_id,  # For backwards compatibility
            "quest_ids": quest_ids,        # All quest IDs
            "quest_count": len(quest_ids),
            "is_batch": len(quest_ids) > 1,
            "title": title,
            "user": user,
            "created_at": created_at,
            "file": str(submission_file)
        }
    
    def update_manifest(self, submissions: List[Dict]):
        """Update manifest with submission metadata."""
        manifest_file = self.pending_dir / "manifest.json"
        
        # Load existing manifest
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
        else:
            manifest = {
                "last_fetch": None,
                "submissions": {}
            }
        
        # Update with new submissions
        manifest["last_fetch"] = datetime.now().isoformat()
        
        for submission in submissions:
            issue_num = str(submission["issue_number"])
            manifest["submissions"][issue_num] = submission
        
        # Save manifest
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Updated manifest with {len(submissions)} submissions")
    
    def mark_as_processing(self, issue_number: int):
        """Update issue labels to mark as processing."""
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}"
        
        # Get current labels
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error fetching issue {issue_number}")
            return
        
        current_labels = [label['name'] for label in response.json()['labels']]
        
        # Update labels
        if self.config['labels']['needs_processing'] in current_labels:
            current_labels.remove(self.config['labels']['needs_processing'])
        if self.config['labels']['processing'] not in current_labels:
            current_labels.append(self.config['labels']['processing'])
        
        # Apply new labels
        labels_url = f"{url}/labels"
        response = requests.put(
            labels_url,
            headers=self.headers,
            json=current_labels
        )
        
        if response.status_code == 200:
            print(f"Marked issue #{issue_number} as processing")
        else:
            print(f"Error updating labels for issue #{issue_number}")
    
    def close_issue(self, issue_number: int, comment: str = None):
        """Close a GitHub issue with optional comment."""
        url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}"
        
        # Add comment if provided
        if comment:
            comment_url = f"{url}/comments"
            comment_response = requests.post(
                comment_url,
                headers=self.headers,
                json={"body": comment}
            )
            if comment_response.status_code == 201:
                print(f"  ✓ Added comment to issue #{issue_number}")
            else:
                print(f"  ⚠️ Failed to add comment to issue #{issue_number}")
        
        # Close the issue
        close_response = requests.patch(
            url,
            headers=self.headers,
            json={
                "state": "closed",
                "labels": [self.config['labels']['processed']]
            }
        )
        
        if close_response.status_code == 200:
            print(f"  ✅ Closed issue #{issue_number}")
            return True
        else:
            print(f"  ❌ Failed to close issue #{issue_number}: {close_response.status_code}")
            return False
    
    def run(self, mark_processing: bool = False, close_issues: bool = True, state: str = "all"):
        """Main execution flow."""
        print(f"Fetching quest data submissions from GitHub (state: {state})...")
        
        # Fetch issues
        issues = self.fetch_issues(state=state)
        print(f"Found {len(issues)} issues to process")
        
        if not issues:
            print("No new submissions found")
            return
        
        # Process each issue
        submissions = []
        successfully_processed = []
        
        for issue in issues:
            print(f"\nProcessing issue #{issue['number']}: {issue['title']}")
            
            # Save submission
            try:
                metadata = self.save_submission(issue)
                submissions.append(metadata)
                successfully_processed.append(issue['number'])
                print(f"  ✓ Successfully saved submission")
                
                # Optionally mark as processing
                if mark_processing:
                    self.mark_as_processing(issue['number'])
                    
            except Exception as e:
                print(f"  ❌ Failed to save submission: {e}")
                continue
        
        # Close quest submission issues (but keep bug reports and features open)
        if close_issues:
            print(f"\n🔄 Closing quest submission issues...")
            
            for issue_num in successfully_processed:
                # Add a thank you comment and close the issue
                comment = """Thank you for submitting this quest data! 

Your submission has been processed and the quest data has been extracted for inclusion in the Questie database. This issue will now be closed.

🎯 **Next Steps:**
- The quest data will be reviewed and added to the database in the next update
- No further action is needed from you

⚠️ **Important Notice:**
**Please update your addon to the latest version!** We will not be accepting legacy submissions soon. The new version has improved quest data collection that provides better quality submissions.

**Download the latest version:** [Check repository releases]

Thanks for contributing to the Questie project! 🚀"""
                
                success = self.close_issue(issue_num, comment)
                if success:
                    print(f"  ✅ Closed and thanked issue #{issue_num}")
                else:
                    print(f"  ❌ Failed to close issue #{issue_num}")
        else:
            print(f"\n⏭️  Skipping issue closing (--no-close flag used)")
        
        # Update manifest
        self.update_manifest(submissions)
        
        # Log activity
        log_file = self.logs_dir / f"fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_file, 'w') as f:
            f.write(f"Fetched {len(submissions)} submissions\n")
            f.write(f"Time: {datetime.now().isoformat()}\n\n")
            for sub in submissions:
                f.write(f"Issue #{sub['issue_number']}: Quest {sub['quest_id']}\n")
        
        print(f"\n✅ Saved {len(submissions)} submissions to pending_submissions/")
        print(f"📋 Manifest updated at pending_submissions/manifest.json")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch quest data from GitHub issues")
    parser.add_argument('--mark-processing', action='store_true',
                       help='Mark issues as processing (legacy option)')
    parser.add_argument('--no-close', action='store_true',
                       help='Do not close issues after download (default: close issues)')
    parser.add_argument('--state', default='open', choices=['open', 'closed', 'all'],
                       help='Issue state to fetch (default: open)')
    parser.add_argument('--config', default='config.json',
                       help='Path to config file')
    parser.add_argument('--output-root', default=str(Path(__file__).parent),
                       help='Directory under which pending_submissions/, processed/, logs/ will be created (default: script directory)')
    
    args = parser.parse_args()
    
    fetcher = GitHubIssueFetcher(args.config, args.output_root)
    fetcher.run(
        mark_processing=args.mark_processing,
        close_issues=not args.no_close,  # Default to True, --no-close makes it False
        state=args.state
    )

if __name__ == "__main__":
    main()
