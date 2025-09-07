### ☕ Support Development
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support%20Development-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/trav346)

If you find this version of Questie with data collection helpful, consider [buying me a coffee](https://buymeacoffee.com/trav346) to support continued development!

---

# Questie for Project Epoch
NOTE: Data submissions prior to v1.1.1 will soon be deprecated.

**An actively maintained version of Questie for Project Epoch with enhanced data collection capabilities.**


### 🎯 **Data Collection System** *(Unique Feature)*
- **Missing Quest Detection**: Automatically detects quests not in database
- **Real-time Data Capture**: Records quest objectives, NPCs, items, and locations as you play
- **Progress Tracking**: Captures detailed progress locations with mob kill information
- **Community Contributions**: Easy export system for submitting data to improve the database

### ⚙️ **Customization Options**
- **Minimap Button**: Quick access to settings and data export
- **Slash Commands**: `/questie` for settings, `/qdc` for data collection
- **Visual Options**: Customize marker icons, colors, and display preferences
- **Performance Tuning**: Adjustable update frequencies and memory optimization

## 📦 Installation

### **Automatic Installation (Recommended)**
1. **Download**: Get the latest release from [GitHub Releases](https://github.com/trav346/Questie-Epoch/releases/)
2. **Extract**: Unzip the downloaded file
3. **Install**: Copy the `Questie` folder to your WoW AddOns directory:
   ```
   /Interface/AddOns/Questie
   ```

## 🚀 Getting Started

### **Basic Usage**
**Enable Data Collection**: Type `/qdc enable` to help improve quest database, or don't. No sweat!
3. **Accept Quests**: Quest objectives will automatically appear on map and minimap
4. **Track Progress**: Watch your progress update in real-time as you complete objectives
5. **Turn In**: Quest completion markers guide you to turn-in NPCs

### **Essential Commands**
```
/questie                    - Open main settings
/questie refreshcomplete    - Refresh completed quests from server
/qdc enable                 - Enable data collection 
/qdc export                 - Export data for GitHub submission
```

## 🔧 Data Collection System

**Help improve Questie for everyone by enabling data collection!**

### **What It Does**
- **Automatic Detection**: Identifies quests missing from the database
- **Real-time Tracking**: Records quest objectives, NPCs, and locations as you play
- **Progress Logging**: Captures where objectives are completed with detailed information
- **No Performance Impact**: Lightweight system that doesn't affect gameplay

### **How to Contribute**
 **Play Normally**: Accept and complete quests as usual
**Export Data**: Use `/qdc export` when quest is complete
**Submit to GitHub**: Create issue at [GitHub Issues](https://github.com/trav346/Questie/issues)
**Help the Community**: Your data helps everyone get better quest information

### **Known Compatibility**
- ✅ For map zooming you'll want to get https://warperia.com/addon-wotlk/magnify/
- ✅ For waypoint arrow support you'll want to get https://warperia.com/addon-wotlk/tomtom/
- ⚠️ If you use Leatrix Plus you may encounter frame drops. This is still being researched, but you can try to disable minimap buttons as a workaround.

## 🐛 Known Issues & Troubleshooting

### **Common Issues**
- **Quest Markers Missing**: Some Project Epoch quests have incomplete data - enable data collection to help fix this
- **Quests show up that don't exist** Project Epoch has modified lots of vanilla quests that exists in Questie's Vanilla database. This is on ongoing process of cleanup. Please bear with me through updates.

### **Getting Help**
1. **Check Issues**: Browse [GitHub Issues](https://github.com/trav346/Questie/issues) for known problems
2. **Enable Debug**: Use `/console scriptErrors 1` to see detailed error information  
3. **Report Bugs**: Create detailed issue reports with steps to reproduce
4. **Discord Support**: Join Project Epoch Discord for community help

## 📈 Version History

### **Latest: v1.1.1** *(Current)*
- 🐛 Fixed coordinate formatting crashes
- 🐛 Fixed QuestieSlash command errors  
- 🚀 Enhanced objective tracking with mob kill correlation
- 📍 Improved progress location display matching v1.0.68 quality

### **Previous Releases**
- **v1.1.0**: Data collection overhaul, completed quest sync
- **v1.0.68**: Enhanced objective tracking, turn-in NPC fixes
- **v1.0.63**: Initial Project Epoch compatibility

[View Full Changelog](CHANGELOG.md)

## 📊 Database Statistics

**Current Epoch Quest Coverage**: **757 quests** and growing!
- 🎉 **Recent Achievement**: Integrated 173 legacy quest submissions from community
- 📈 **30% Database Growth**: Thanks to 875 GitHub quest submissions from dedicated players
- 🌟 **Community Success**: 97% validation success rate on legacy data processing

*Special thanks to every player who took time to submit quest data - you've made Questie significantly better for everyone!*

## 🙏 Credits & Support

### **Special Thanks**
- **@esurm**: Original Questie author and data collection system
- **@desizt**: Data collection enhancements and testing
- **@Bennylavaa**: Extensive testing and bug reporting
- **Project Epoch Community**: 875+ quest data submissions over the past week - incredible dedication!
- **All GitHub Contributors**: Every quest submission helped build our database of 757 quests
- **Legacy Data Heroes**: Special recognition for v1.0.68 era players who provided foundational quest data

### **Support Development**
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support%20Development-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/trav346)

If you find this enhanced version of Questie helpful, consider [buying me a coffee](https://buymeacoffee.com/trav346) to support continued development and maintenance!