#!/usr/bin/env python3
"""
Check what text appears around the Distribution Utility section
"""

import pdfplumber
import os

template_path = "GreenWatt-documents/Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf"

print(f"Analyzing: {template_path}")
print("=" * 80)

with pdfplumber.open(template_path) as pdf:
    # Check first few pages for Distribution text
    for page_num in range(min(3, len(pdf.pages))):
        page = pdf.pages[page_num]
        print(f"\n📄 Page {page_num + 1}:")
        
        # Extract all text
        text = page.extract_text()
        
        if text:
            # Look for lines containing "Distribution" or "Utility"
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'distribution' in line.lower() or 'utility' in line.lower():
                    print(f"  Found: '{line.strip()}'")
                    # Show context (lines before and after)
                    if i > 0:
                        print(f"    Before: '{lines[i-1].strip()}'")
                    if i < len(lines) - 1:
                        print(f"    After: '{lines[i+1].strip()}'")
                    print()
        
        # Also try searching for specific text patterns
        search_patterns = ["Distribution", "Utility", "Distribution Utility", "Distribution\nUtility"]
        for pattern in search_patterns:
            results = page.search(pattern)
            if results:
                print(f"  🔍 Search found '{pattern}': {len(results)} matches")
                for result in results[:3]:  # Show first 3 matches
                    print(f"     at ({result['x0']:.1f}, {result['top']:.1f})")