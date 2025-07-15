#!/bin/bash

echo "🚀 Quick Google Workspace Migration Test"
echo "========================================"

# Test server availability
echo -e "\n1. Testing server availability..."
curl -s -o /dev/null -w "Server response: %{http_code}\n" http://localhost:5001/test

# Test utilities endpoint
echo -e "\n2. Testing utilities endpoint..."
curl -s http://localhost:5001/api/utilities | python -m json.tool

# Test developers endpoint  
echo -e "\n3. Testing developers endpoint..."
curl -s http://localhost:5001/api/developers | python -m json.tool

# Test PDF generation
echo -e "\n4. Testing PDF generation..."
curl -X POST http://localhost:5001/test-pdf \
  -H "Content-Type: application/json" \
  -d '{"utility_provider":"National Grid","developer_assigned":"Meadow Energy"}' \
  -s -w "\nPDF test response: %{http_code}\n"

echo -e "\n✅ Quick test complete!"
echo "Check the above outputs to verify:"
echo "- Server is running (should see 200 responses)"
echo "- Utilities are loaded from new sheet"
echo "- Developers are loaded from new sheet"
echo "- PDF generation works"