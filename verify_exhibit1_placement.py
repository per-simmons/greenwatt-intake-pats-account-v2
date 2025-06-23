#!/usr/bin/env python3
"""
Verify the exact placement of text in Exhibit 1
"""

import pdfplumber
import os
from services.anchor_pdf_processor import AnchorPDFProcessor
import datetime

def verify_placement():
    """Generate a test PDF and analyze the exact text placement"""
    
    # Generate a test PDF
    processor = AnchorPDFProcessor()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    test_data = {
        "form_data": {
            "account_name": "Test Business LLC",
            "contact_name": "John Doe",
            "email": "test@example.com",
            "phone": "(555) 123-4567",
            "utility_provider": "RG&E"
        },
        "ocr_data": {
            "utility_name": "RG&E",
            "account_number": "20091840221",
            "service_address": "2900 WESTCHESTER AVE, PURCHASE NY 10577"
        }
    }
    
    print("Generating test PDF...")
    output_path = processor.process_template_with_anchors(
        "Meadow-RGE-Commercial-UCB-Agreement.pdf",
        test_data["form_data"],
        test_data["ocr_data"],
        timestamp
    )
    
    print(f"Generated: {output_path}")
    
    # Now analyze the generated PDF
    print("\nAnalyzing generated PDF placement...")
    
    with pdfplumber.open(output_path) as pdf:
        # Check page 10 (0-indexed = 9)
        if len(pdf.pages) >= 10:
            page = pdf.pages[9]
            
            # Find all text in the service address area
            print("\nText found in Service Address column area (x=554.6 to x=722.8):")
            text_in_column = []
            
            for char in page.chars:
                if 554.6 <= char['x0'] <= 722.8 and 120 <= char['y0'] <= 160:
                    text_in_column.append({
                        'char': char['text'],
                        'x': char['x0'],
                        'y': char['y0']
                    })
            
            # Group by Y position to show lines
            from collections import defaultdict
            lines_by_y = defaultdict(list)
            
            for item in text_in_column:
                y_key = round(item['y'], 0)  # Round to nearest point
                lines_by_y[y_key].append(item)
            
            for y in sorted(lines_by_y.keys()):
                line_items = sorted(lines_by_y[y], key=lambda x: x['x'])
                text = ''.join(item['char'] for item in line_items)
                if text.strip():
                    x_start = line_items[0]['x'] if line_items else 0
                    print(f"  Y={y:.1f}, X={x_start:.1f}: '{text.strip()}'")
                    
            # Also check for overlapping text in account number column
            print("\nText found in Account Number column area (x=386.4 to x=554.6):")
            overlap_text = []
            
            for char in page.chars:
                if 386.4 <= char['x0'] <= 554.6 and 120 <= char['y0'] <= 160:
                    overlap_text.append({
                        'char': char['text'],
                        'x': char['x0'],
                        'y': char['y0']
                    })
                    
            # Check if any service address text is bleeding into this column
            lines_by_y = defaultdict(list)
            for item in overlap_text:
                y_key = round(item['y'], 0)
                lines_by_y[y_key].append(item)
                
            for y in sorted(lines_by_y.keys()):
                line_items = sorted(lines_by_y[y], key=lambda x: x['x'])
                text = ''.join(item['char'] for item in line_items)
                if text.strip() and y > 130:  # Skip header row
                    x_end = line_items[-1]['x'] if line_items else 0
                    if x_end > 500:  # Text extending too far right
                        print(f"  ⚠️  OVERLAP at Y={y:.1f}: '{text.strip()}'")
                        
    return output_path

if __name__ == "__main__":
    output = verify_placement()