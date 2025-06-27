#!/bin/bash
# Memory monitoring script for GreenWatt Render deployment
# Run this to continuously monitor memory usage

echo "🔍 Starting memory monitor for GreenWatt service..."
echo "Press Ctrl+C to stop"

SERVICE_URL="${SERVICE_URL:-https://greenwatt-intake-clean.onrender.com}"

while true; do
    echo -n "$(date '+%Y-%m-%d %H:%M:%S') - "
    
    # Call the memory status endpoint
    response=$(curl -s "${SERVICE_URL}/memory-status" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Parse the JSON response
        rss_mb=$(echo "$response" | grep -o '"rss_mb":[0-9.]*' | cut -d: -f2)
        sessions=$(echo "$response" | grep -o '"progress_sessions":[0-9]*' | cut -d: -f2)
        cleaned=$(echo "$response" | grep -o '"cleaned":[a-z]*' | cut -d: -f2)
        
        echo "Memory: ${rss_mb}MB | Sessions: ${sessions} | Cleaned: ${cleaned}"
        
        # Alert if memory is high
        if (( $(echo "$rss_mb > 400" | bc -l) )); then
            echo "⚠️  WARNING: High memory usage detected!"
        fi
    else
        echo "❌ Failed to fetch memory status"
    fi
    
    # Wait 30 seconds before next check
    sleep 30
done
