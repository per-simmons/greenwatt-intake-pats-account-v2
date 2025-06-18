#!/usr/bin/env python3
"""
Generate test PDF with corrected positioning for Page 7 and Page 9 fields.
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path to import services
sys.path.append('.')

def generate_test_pdf():
    """Generate test PDF with corrected positioning"""
    
    try:
        from services.anchor_pdf_processor import AnchorPDFProcessor
        print("✅ Successfully imported AnchorPDFProcessor")
    except ImportError as e:
        print(f"❌ Failed to import modules: {e}")
        return False
    
    # Test data with comprehensive subscriber information
    test_form_data = {
        'business_entity': 'Positioning Test Business LLC',
        'account_name': 'Test Account for Positioning',
        'contact_name': 'Jane Smith',
        'title': 'Chief Operations Officer',
        'phone': '555-987-6543',
        'email': 'jane.smith@positiontest.com',
        'service_addresses': '123 Business Park Drive, Albany, NY 12345',
        'developer_assigned': 'Meadow Energy',
        'account_type': 'Small Demand <25 KW',
        'utility_provider': 'National Grid',
        'agent_id': 'TEST001',
        'poid': 'TEST123456'
    }
    
    test_ocr_data = {
        'utility_name': 'National Grid',
        'customer_name': 'Positioning Test Customer',
        'account_number': '987654321',
        'poid': 'TEST123456',
        'monthly_usage': '2000',
        'annual_usage': '24000'
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    template = 'Meadow-National-Grid-Commercial-UCB-Agreement.pdf'
    
    print(f"\n🧪 Generating test PDF with corrected positioning...")
    print(f"📁 Template: {template}")
    print(f"🕐 Timestamp: {timestamp}")
    
    try:
        # Create processor and generate PDF
        processor = AnchorPDFProcessor()
        output_path = processor.process_template_with_anchors(
            template, test_form_data, test_ocr_data, f"positioning_test_{timestamp}"
        )
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"\n🎉 SUCCESS!")
            print(f"📄 PDF Generated: {output_path}")
            print(f"📊 File Size: {file_size:,} bytes")
            print(f"\n🔍 Changes Made:")
            print(f"   📋 Page 7 Subscriber Fields: Moved DOWN 15px, LEFT 7px")
            print(f"   ✍️  Page 9 Signature Fields: Moved UP 13px (dy: 15→2)")
            print(f"\n📂 Location: temp/")
            print(f"🗂️  Filename: {os.path.basename(output_path)}")
            
            return True
        else:
            print(f"❌ PDF generation failed - file not created")
            return False
            
    except Exception as e:
        print(f"❌ PDF processing error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 PDF Positioning Test Generator")
    print("=" * 50)
    success = generate_test_pdf()
    
    if success:
        print("\n✅ Test PDF ready for review in temp/ folder")
    else:
        print("\n❌ Test PDF generation failed")
    
    sys.exit(0 if success else 1)