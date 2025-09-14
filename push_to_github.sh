#!/bin/bash

# Script to push Development Tools to GitHub
# Run this from the Development Tools directory

echo "Setting up git repository for Development Tools..."

# Initialize git if needed
if [ ! -d .git ]; then
    git init
    echo "Git repository initialized"
else
    echo "Git repository already exists"
fi

# Add GitHub remote
git remote remove origin 2>/dev/null
git remote add origin https://github.com/trav346/Questie-Epoch.git
echo "Remote added: https://github.com/trav346/Questie-Epoch.git"

# Create new branch for development tools
git checkout -b development-tools

# Add all files
git add .
echo "Files added to staging"

# Show what will be committed
echo "Files to be committed:"
git status --short

# Commit
git commit -m "feat: Add experimental development tools for quest data processing

- Pipeline v2 for processing GitHub issue submissions  
- pfQuest conversion tools (experimental)
- Comprehensive documentation with warnings
- 53 processing modules with test suite

⚠️ EXPERIMENTAL: These tools are not production-ready and can corrupt databases
Requires manual configuration and testing before use
~60-70% data accuracy - manual review required

See README.md and DISCLAIMER.md for important warnings"

echo "Files committed"

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin development-tools

echo "Done! Check https://github.com/trav346/Questie-Epoch/tree/development-tools"