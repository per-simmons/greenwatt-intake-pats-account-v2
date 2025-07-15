#!/bin/bash

echo "🚀 Pushing Shared Drive fix to GitHub..."

# Stage the modified files
git add services/google_drive_service.py CLAUDE.md Google-Workspace-Migration-7-15-25.md setup_workspace_resources_auto.py

# Create the commit
git commit -m "Fix Google Drive Shared Drive access - add supportsAllDrives parameter

- Updated GoogleDriveService to support Shared Drives
- Added supportsAllDrives=True to all Drive API calls  
- Added includeItemsFromAllDrives=True to list operations
- Updated documentation with new Shared Drive folder IDs
- Updated CLAUDE.md to note Shared Drive requirement

This fixes the File not found error when accessing Shared Drive folders."

# Push to GitHub
git push origin main

echo "✅ Changes pushed to GitHub!"
echo "🔄 Render should auto-deploy shortly..."