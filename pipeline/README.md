# Questie-Epoch Pipeline v2

A data processing pipeline for extracting, validating, and merging World of Warcraft quest data from community submissions into the Questie-Epoch addon database.

## ⚠️ IMPORTANT DISCLAIMER

**This pipeline is EXPERIMENTAL and NOT production-ready.** 

This is a community-driven data collection tool that:
- May produce incorrect or incomplete quest data
- Requires manual verification of processed submissions
- Can potentially corrupt your database if used incorrectly
- Is still under active development and testing

**ALWAYS backup your Questie database before running this pipeline!**

## Overview

This pipeline processes quest data submissions from GitHub issues, extracts structured information, and generates Lua database overlays for the Questie-Epoch WoW addon. It's designed to handle thousands of submissions efficiently while maintaining data quality through consensus filtering.

## Features

- **Batch Processing**: Handles 1000+ submission files without memory issues
- **Two-Phase Architecture**: 
  - Phase 1: Data extraction from multiple formats
  - Phase 2: Consensus filtering and database generation
- **Smart Objective Filtering**: Reduces false objectives by 82%+ using text analysis
- **Comprehensive Testing**: 17 test files for validation
- **Modular Design**: 53 specialized parser modules

## Sample Data

The `sample_submissions/` folder contains 18 real quest submissions for testing the pipeline. These are actual GitHub issues from the Questie-Epoch project.

For the complete dataset of 1,656 submissions (37MB), contact the repository maintainer.

## Quick Start

### Prerequisites

- Python 3.8+
- GitHub personal access token (for fetching issues)
- Access to Questie-Epoch repository

### Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd pipeline
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure GitHub access:
```bash
cp config.json.example config.json
# Edit config.json with your GitHub token and repository details
```

4. **IMPORTANT - Configure Database Paths:**

The pipeline needs to know where your Questie addon is installed. Many scripts use relative paths that may not work in your environment.

**Files requiring path configuration:**
- `modules/database_writer_v2.py` - Line 24
- `modules/database_merger_v2.py` - Line 25
- `modules/database_comparator_v2.py` - Line 26
- `modules/pipeline_state_tracker.py` - Lines 198-200
- `modules/data_aggregator.py` - Line 1514
- `intelligent_database_merger.py` - Line 388

Look for comments like `# Update this path to your Questie installation` and modify paths to match your setup:

```python
# Example: Change from relative path
db_path = Path("../../Database/Epoch/epochQuestDB.lua")

# To absolute path for your installation
db_path = Path("/path/to/WoW/Interface/AddOns/Questie/Database/Epoch/epochQuestDB.lua")

# Or use environment variable (recommended)
import os
QUESTIE_PATH = os.environ.get('QUESTIE_PATH', '/default/path/to/Questie')
db_path = Path(QUESTIE_PATH) / "Database/Epoch/epochQuestDB.lua"
```

**Tip:** Set the `QUESTIE_PATH` environment variable to avoid hardcoding paths:
```bash
export QUESTIE_PATH="/path/to/your/WoW/Interface/AddOns/Questie"
```

### Basic Usage

#### 1. Fetch GitHub Issues
```bash
python fetch_github_issues.py
```
This downloads quest data submissions from GitHub issues into `pending_submissions/`

#### 2. Process Submissions
```bash
python batch_processor.py
```
This runs the full pipeline on all pending submissions

#### 3. Generate Lua Files
```bash
python generate_lua.py
```
This creates Lua overlay files for the WoW addon

## Pipeline Architecture

```
GitHub Issues → Fetch → Parse → Aggregate → Filter → Generate → Merge
                          ↓
                    53 Specialized Parsers
                          ↓
                  Consensus Filtering (82% reduction)
                          ↓
                    High Confidence → Auto-merge
                    Low Confidence → Manual Review
```

### Key Components

- **batch_processor.py**: Main entry point for processing submissions
- **modules/**: 53 specialized parsers for different data types
- **data_aggregator.py**: Combines outputs from all parsers
- **objective_consensus_filter.py**: Reduces false objectives using text analysis
- **database_writer.py**: Formats data into Lua syntax
- **intelligent_database_merger.py**: Merges new data with existing database

### Parser Modules

The pipeline includes specialized parsers for:
- Quest data (name, level, requirements)
- NPCs (quest givers, targets)
- Items (quest items, rewards)
- Objects (interactable world objects)
- Coordinates (spawn locations)
- Objectives (kill, collect, interact)
- Zones (zone mapping and validation)

## Data Flow

1. **Input**: Raw text from GitHub issues containing quest data
2. **Parsing**: Extract structured data using regex patterns
3. **Aggregation**: Combine data from multiple submissions
4. **Filtering**: Remove false objectives using consensus
5. **Validation**: Check data completeness and consistency
6. **Output**: Lua database files ready for WoW addon

## Configuration

Edit `config.json` to set:
- `github_token`: Your GitHub personal access token
- `repo`: Target repository (format: "owner/repo")
- `labels`: GitHub labels for tracking submission status

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

Key test files:
- `test_database_writer.py`: Lua generation
- `test_objective_consensus_filter.py`: Objective filtering
- `test_data_aggregator.py`: Data aggregation

## Output Files

The pipeline generates:
- `batch_results/`: Processed data in JSON format
- `aggregated_data/`: Combined data from all submissions
- `Manual Review/`: Low-confidence data for human review
- `*.lua`: Final Lua overlay files for the addon

## Performance & Accuracy

**Performance:**
- Processes 1000+ files in under 10 seconds
- Memory usage: ~50MB for full dataset

**Accuracy (Approximate):**
- Quest parsing: ~98% success rate
- Objective filtering: ~82% reduction in false positives
- **BUT: Still ~60-70% overall data accuracy**
- **Manual review recommended for all output**

## Troubleshooting

### Common Issues

1. **Memory/Timeout Issues**: Use batch processing mode
2. **Lua Syntax Errors**: Check string escaping in database_writer.py
3. **Missing Data**: Verify all parser modules are running
4. **GitHub Rate Limits**: Add delays or use authentication

### Debug Mode

Enable verbose logging:
```bash
python batch_processor.py --debug
```

## Documentation

- `MODULE_TRACKER.md`: Detailed module status and architecture
- `LUA_GENERATION_ISSUES_TRACKER.md`: Known issues and solutions
- `tests/`: Example data and test cases

## Contributing

1. Check MODULE_TRACKER.md for module status
2. Run tests before submitting changes
3. Follow existing code patterns in modules/
4. Document any new parsers or features

## License

This project is part of the Questie-Epoch addon for World of Warcraft 3.3.5a.

## Support

For issues or questions:
- GitHub Issues: [Create an issue](https://github.com/trav346/Questie-Epoch/issues)
- Original Project: [Questie-Epoch Repository](https://github.com/trav346/Questie-Epoch)

## Additional Tools

### pfQuest Conversion
The `pfquest_conversion/` folder contains tools for converting pfQuest addon data to Questie format. This allows importing quest data from the competing addon. See `pfquest_conversion/USAGE.md` for details.

## Credits

Developed for Project Epoch WoW 3.3.5a server and the Questie addon community.