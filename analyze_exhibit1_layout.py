#!/usr/bin/env python3
"""
Analyze the Exhibit 1 table layout to find exact column boundaries
"""

import pdfplumber
import os

def analyze_exhibit1_layout():
    """Analyze the template PDF to find table column boundaries"""
    
    # Path to template
    template_path = "GreenWatt-documents/Meadow-RGE-Commercial-UCB-Agreement.pdf"
    
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return
    
    print(f"Analyzing template: {template_path}")
    
    with pdfplumber.open(template_path) as pdf:
        # Look at page 10 (second to last page, 0-indexed = page 9)
        if len(pdf.pages) >= 10:
            page = pdf.pages[9]  # Page 10 (0-indexed)
            
            print(f"\nPage 10 dimensions: {page.width} x {page.height}")
            
            # Extract tables
            tables = page.extract_tables()
            if tables:
                print(f"\nFound {len(tables)} table(s) on page 10")
                
            # Look for text containing our headers
            text_instances = page.extract_text_simple()
            
            # Find specific text positions
            for text_obj in page.chars:
                if "Service Address" in text_obj.get('text', ''):
                    print(f"\nFound 'Service Address' text:")
                    print(f"  Position: x={text_obj['x0']:.1f} to x={text_obj['x1']:.1f}")
                    print(f"  Y position: {text_obj['y0']:.1f}")
                    
            # Try to find table lines/cells
            print("\n\nAnalyzing table structure...")
            
            # Look for horizontal lines that might indicate table rows
            if hasattr(page, 'lines'):
                h_lines = [line for line in page.lines if line['y0'] == line['y1']]
                v_lines = [line for line in page.lines if line['x0'] == line['x1']]
                
                print(f"\nFound {len(h_lines)} horizontal lines")
                print(f"Found {len(v_lines)} vertical lines")
                
                # Find vertical lines that might be column boundaries
                if v_lines:
                    v_positions = sorted(set(line['x0'] for line in v_lines))
                    print("\nVertical line positions (potential column boundaries):")
                    for i, x in enumerate(v_positions):
                        print(f"  Line {i}: x={x:.1f}")
                        
            # Use find_tables to get table structure
            table_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
            }
            
            tables = page.find_tables(table_settings)
            if tables:
                print(f"\n\nFound {len(tables)} table(s) with find_tables")
                for i, table in enumerate(tables):
                    print(f"\nTable {i}:")
                    print(f"  Bounding box: {table.bbox}")
                    
                    # Extract cells
                    cells = table.cells
                    if cells:
                        # Find cells in the header row
                        header_cells = [cell for cell in cells if cell[1] < 120]  # y0 < 120
                        
                        print(f"\n  Header cells:")
                        for cell in sorted(header_cells, key=lambda c: c[0]):  # sort by x0
                            print(f"    Cell: x={cell[0]:.1f} to {cell[2]:.1f}, y={cell[1]:.1f} to {cell[3]:.1f}")
                            
                        # Find Service Address column
                        service_cells = [cell for cell in cells if cell[0] > 400]  # rightmost cells
                        if service_cells:
                            print(f"\n  Service Address column boundaries:")
                            cell = service_cells[0]
                            print(f"    Left edge: x={cell[0]:.1f}")
                            print(f"    Right edge: x={cell[2]:.1f}")
                            print(f"    Width: {cell[2] - cell[0]:.1f} points")
                            
            # Search for all text in the rightmost area
            print("\n\nText in rightmost column area (x > 400):")
            for char in page.chars:
                if char['x0'] > 400 and char['y0'] < 150:
                    if not char['text'].isspace():
                        print(f"  '{char['text']}' at x={char['x0']:.1f}")

if __name__ == "__main__":
    analyze_exhibit1_layout()