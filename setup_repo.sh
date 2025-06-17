#!/bin/bash

# Setup script for GreenWatt clean repository
echo "Setting up GreenWatt clean repository..."

# Initialize git repository
git init

# Add remote origin
git remote add origin https://github.com/per-simmons/greenwatt-intake-pats-account-v2.git

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: GreenWatt intake system clean deployment

- Flask application with Google Cloud integrations
- PDF processing with signature placement
- Google Sheets and Drive integration
- Email notifications via SendGrid
- SMS integration framework (Twilio)
- Render.com deployment ready

🤖 Generated with Claude Code (https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to GitHub
git branch -M main
git push -u origin main

echo "Repository setup complete!"
echo "You can now deploy from: https://github.com/per-simmons/greenwatt-intake-pats-account-v2"