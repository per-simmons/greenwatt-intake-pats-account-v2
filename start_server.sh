#!/bin/bash

# Set environment variables for GreenWatt OCR testing
export OPENAI_API_KEY="sk-proj-your_openai_api_key_here"
export PORT=5001

# Google service account will use local fallback file
echo "🚀 Starting GreenWatt server with OpenAI API key..."
echo "📍 Port: $PORT"
echo "🔑 OpenAI API Key: ${OPENAI_API_KEY:0:10}..."

# Kill any existing processes
pkill -f "python.*app.py" 2>/dev/null

# Start the server
# Enable debug mode for better error reporting
export FLASK_DEBUG=1
python app.py