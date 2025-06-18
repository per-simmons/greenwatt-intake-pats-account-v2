#!/usr/bin/env python3
"""
Analyze the most recently generated PDF to see exactly where fields are placed
"""

import os
import sys
import pdfplumber
from datetime import datetime

sys.path.append('.')

def analyze_latest_pdf():
    """Analyze the most recent PDF to see field placement"""
    
    # Find the most recent PDF
    temp_files = []
    temp_dir = "temp"
    
    for filename in os.listdir(temp_dir):
        if filename.endswith('.pdf') and 'debug_' in filename:
            filepath = os.path.join(temp_dir, filename)
            mtime = os.path.getmtime(filepath)
            temp_files.append((mtime, filepath, filename))
    
    if not temp_files:
        print("❌ No debug PDF files found")
        return False
    
    # Get the most recent one
    temp_files.sort(reverse=True)
    latest_file = temp_files[0][1]
    latest_name = temp_files[0][2]
    
    print(f"🔍 Analyzing: {latest_name}")
    print(f"📄 Full path: {latest_file}")
    print("=" * 80)
    
    try:
        with pdfplumber.open(latest_file) as pdf:
            print(f"📖 PDF has {len(pdf.pages)} pages")
            
            # Check each page for our test data
            test_strings = [
                "Test Business LLC",    # business_entity  
                "Test Account Name",    # account_name
                "Jane Smith",          # contact_name (should be on pages 7 and 9)
                "123 Test St",         # service_addresses
                "jane.smith@test.com", # email
                "555-987-6543"         # phone
            ]
            
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                page_text = page.extract_text() or ""
                
                found_strings = []
                for test_string in test_strings:
                    if test_string in page_text:
                        found_strings.append(test_string)
                
                if found_strings:
                    print(f"\n📄 PAGE {page_num + 1}:")
                    for found in found_strings:
                        print(f"   ✅ Found: '{found}'")
                        
                    # Extract words with coordinates for detailed analysis
                    words = page.extract_words()
                    relevant_words = []
                    
                    for word in words:
                        word_text = word['text']
                        for test_string in test_strings:
                            if test_string in word_text or word_text in test_string:
                                relevant_words.append({
                                    'text': word_text,
                                    'x0': word['x0'],
                                    'y0': word['top'],
                                    'x1': word['x1'],
                                    'y1': word['bottom']
                                })
                                break
                    
                    if relevant_words:
                        print(f"   📍 Coordinates:")
                        for word in relevant_words[:5]:  # Show first 5 matches
                            print(f"      '{word['text']}' at ({word['x0']:.1f}, {word['y0']:.1f})")
            
            # Special analysis for expected locations
            print(f"\n📊 EXPECTED vs ACTUAL ANALYSIS:")
            print("=" * 50)
            
            # Page 7 analysis (subscriber fields)
            if len(pdf.pages) >= 7:
                page_7 = pdf.pages[6]  # 0-indexed
                page_7_text = page_7.extract_text() or ""
                
                print(f"\n📄 PAGE 7 (Subscriber Info):")
                expected_7 = ["Test Business LLC", "123 Test St", "jane.smith@test.com", "555-987-6543"]
                
                for expected in expected_7:
                    if expected in page_7_text:
                        print(f"   ✅ Expected: '{expected}' - FOUND")
                    else:
                        print(f"   ❌ Expected: '{expected}' - MISSING")
            
            # Page 9 analysis (signature fields)  
            if len(pdf.pages) >= 9:
                page_9 = pdf.pages[8]  # 0-indexed
                page_9_text = page_9.extract_text() or ""
                
                print(f"\n📄 PAGE 9 (Signatures):")
                expected_9 = ["Jane Smith"]  # Signature and printed name
                
                for expected in expected_9:
                    if expected in page_9_text:
                        print(f"   ✅ Expected: '{expected}' - FOUND")
                    else:
                        print(f"   ❌ Expected: '{expected}' - MISSING")
            
            # Page 1 analysis (should be empty of our data)
            page_1 = pdf.pages[0]
            page_1_text = page_1.extract_text() or ""
            
            print(f"\n📄 PAGE 1 (Should be clean):")
            problematic_on_1 = []
            for test_string in test_strings:
                if test_string in page_1_text:
                    problematic_on_1.append(test_string)
            
            if problematic_on_1:
                print(f"   ⚠️  PROBLEM: Found user data on Page 1:")
                for problem in problematic_on_1:
                    print(f"      '{problem}'")
            else:
                print(f"   ✅ Clean - no user data found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 ANALYZING GENERATED PDF FOR FIELD PLACEMENT")
    print("=" * 80)
    success = analyze_latest_pdf()
    print(f"\n🏁 Analysis {'completed' if success else 'failed'}")