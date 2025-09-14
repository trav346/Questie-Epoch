# Pipeline Setup Guide

## Quick Setup Checklist

Before running the pipeline, complete these setup steps:

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure GitHub Access
```bash
cp config.json.example config.json
```
Edit `config.json` and add:
- Your GitHub personal access token
- Repository name (format: "owner/repo")

### 3. Configure Database Paths

⚠️ **CRITICAL**: The pipeline needs to know where your Questie addon is installed.

#### Option A: Environment Variable (Recommended)
Set the `QUESTIE_PATH` environment variable:

**Windows:**
```cmd
set QUESTIE_PATH=C:\Program Files\World of Warcraft\_classic_\Interface\AddOns\Questie
```

**macOS/Linux:**
```bash
export QUESTIE_PATH="/Applications/World of Warcraft/_classic_/Interface/AddOns/Questie"
```

Add to your `.bashrc` or `.zshrc` to make permanent.

#### Option B: Manual Path Updates
Edit these files and update paths marked with `# Update this path to your Questie installation`:

| File | Line(s) | Current Path | Change To |
|------|---------|--------------|-----------|
| `modules/database_writer_v2.py` | 24 | `../../Database/Epoch` | Your Questie path |
| `modules/database_merger_v2.py` | 25 | `../../Database/Epoch` | Your Questie path |
| `modules/database_comparator_v2.py` | 26 | `../../Database/Epoch/epochQuestDB.lua` | Your Questie path |
| `modules/pipeline_state_tracker.py` | 198-200 | `../../Database/Epoch/` | Your Questie path |
| `modules/data_aggregator.py` | 1514 | `../../Database/Epoch/epochNpcDB.lua` | Your Questie path |
| `intelligent_database_merger.py` | 388 | `../Database/Epoch/epochQuestDB.lua` | Your Questie path |
| `modules/phantom_quest_processor.py` | 301, 386 | `../../Database/WotLK/wotlkQuestDB.lua` | Your Questie path |
| `modules/remove_phantom_quests.py` | 59 | `../../Database/WotLK/wotlkQuestDB.lua` | Your Questie path |

### 4. Verify Setup

Run this test script to verify paths are correct:

```python
# test_setup.py
from pathlib import Path
import os

# Check if using environment variable
questie_path = os.environ.get('QUESTIE_PATH')
if questie_path:
    print(f"✓ QUESTIE_PATH set to: {questie_path}")
    db_path = Path(questie_path) / "Database/Epoch/epochQuestDB.lua"
    if db_path.exists():
        print(f"✓ Database found at: {db_path}")
    else:
        print(f"✗ Database not found at: {db_path}")
else:
    print("✗ QUESTIE_PATH not set - using relative paths")
    # Test relative path
    db_path = Path("../../Database/Epoch/epochQuestDB.lua")
    if db_path.exists():
        print(f"✓ Database found using relative path")
    else:
        print(f"✗ Database not found - you need to update paths!")
```

## Common Path Issues

### "File not found" errors
- The pipeline can't find the Questie database files
- Solution: Set `QUESTIE_PATH` or update paths in files listed above

### Wrong database being modified
- The pipeline is modifying a different Questie installation
- Solution: Verify paths point to your active WoW addon folder

### Permission denied
- The pipeline can't write to the Questie folder
- Solution: Run with appropriate permissions or check folder ownership

## Directory Structure Expected

The pipeline expects this Questie structure:
```
Questie/
├── Database/
│   ├── Epoch/
│   │   ├── epochQuestDB.lua
│   │   ├── epochNpcDB.lua
│   │   └── epochItemDB.lua
│   └── WotLK/
│       └── wotlkQuestDB.lua
└── [other Questie files]
```

## Need Help?

1. Check that your WoW installation path is correct
2. Verify Questie addon is installed in the Interface/AddOns folder
3. Ensure you have write permissions to the Questie folder
4. Try using absolute paths instead of relative paths
5. Check the repository issues for similar problems