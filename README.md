# Questie-Epoch Development Tools

## ⚠️ EXPERIMENTAL TOOLS - USE AT YOUR OWN RISK

This repository contains experimental development tools for the Questie-Epoch addon (World of Warcraft 3.3.5a). These tools were created to help process community-submitted quest data for Project Epoch's custom content.

## What's Included

### 📊 Pipeline v2 (`pipeline/`)
A data processing pipeline for extracting and merging quest data from GitHub issue submissions.
- Processes community quest submissions
- Converts data to Questie database format  
- ~60-70% accuracy, requires manual review
- **See [`pipeline/README.md`](pipeline/README.md) for details**

### 🔄 pfQuest Conversion Tools (`pipeline/pfquest_conversion/`)
Experimental scripts to test converting pfQuest addon data to Questie format.
- Tests compatibility between competing addon formats
- Proof of concept only
- **See [`pipeline/pfquest_conversion/USAGE.md`](pipeline/pfquest_conversion/USAGE.md)**

## Prerequisites

- Python 3.8+
- World of Warcraft 3.3.5a with Questie addon installed
- GitHub account (for fetching submissions)
- Understanding of Lua and WoW addon structure

## ⚠️ Critical Warnings

**THESE ARE NOT PRODUCTION TOOLS**

1. **ALWAYS BACKUP YOUR DATABASE** before using any tool
2. **Expect bugs and data corruption** - these are experimental
3. **Manual verification required** - do not trust output blindly
4. **No support provided** - use at your own risk
5. **May break your addon** - test on copies first

## Quick Start

1. Read [`DISCLAIMER.md`](pipeline/DISCLAIMER.md) - Seriously, read it!
2. Follow [`SETUP_GUIDE.md`](pipeline/SETUP_GUIDE.md) for configuration
3. Start with small test batches
4. Verify all output before applying to live addon

## Project Context

These tools were developed for [Questie-Epoch](https://github.com/trav346/Questie-Epoch), a fork of Questie addon customized for Project Epoch server which features:
- 1,300+ custom quests
- Vanilla content in WotLK client
- Community-driven quest database

## Status

🛑 **Development Status: ARCHIVED/HANDOFF**

The original developer has moved on. These tools are provided as-is for:
- Historical reference
- Learning resource  
- Starting point for new development
- Community continuation

## Contributing

Feel free to fork and improve! The community needs:
- Better data validation
- Improved accuracy
- Bug fixes
- Documentation updates

## License

Part of the Questie-Epoch project. See main repository for license details.

## Support

No active support. For questions:
- Check existing documentation
- Review code comments
- Open issues for community discussion
- Consider contributing fixes

---

**Remember**: These tools can corrupt your database. Always backup first!