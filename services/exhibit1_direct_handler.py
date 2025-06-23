"""
Direct handler for Exhibit 1 fields to avoid truncation issues
"""

from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
import os

def create_exhibit1_overlay_direct(template_path, form_data, ocr_data, output_path):
    """
    Create Exhibit 1 overlay using the direct approach that works
    This bypasses the complex anchor processor logic
    """
    
    # Create overlay with exact template dimensions
    overlay_path = output_path.replace('.pdf', '_exhibit1_overlay.pdf')
    
    # Get template page count
    with open(template_path, 'rb') as f:
        template_reader = PdfReader(f)
        page_count = len(template_reader.pages)
    
    # Create canvas
    c = canvas.Canvas(overlay_path, pagesize=(792, 612))
    
    # Create blank pages up to page 9
    for i in range(9):
        c.showPage()
    
    # Page 10 - Exhibit 1
    # Based on working test: Y position = 612 - 131.1 = 480.9
    y_pos = 480.9
    
    # Utility Company
    c.setFont("Helvetica", 8)
    c.drawString(98.6, y_pos, str(ocr_data.get('utility_name', '')))
    
    # Name on Utility Account
    c.drawString(249.2, y_pos, str(form_data.get('account_name', '')))
    
    # Utility Account Number
    c.drawString(419.2, y_pos, str(ocr_data.get('account_number', '')))
    
    # Service Address - smaller font
    c.setFont("Helvetica", 7)
    c.drawString(560.6, y_pos, str(ocr_data.get('service_address', '')))
    
    # Finish remaining pages
    c.showPage()  # Page 10
    
    # Add page 11 if template has it
    if page_count > 10:
        c.showPage()  # Page 11
    
    c.save()
    
    # Now merge with template
    template_reader = PdfReader(template_path)
    overlay_reader = PdfReader(overlay_path)
    writer = PdfWriter()
    
    # Process each page
    for page_num in range(len(template_reader.pages)):
        template_page = template_reader.pages[page_num]
        
        # Only merge overlay on page 10 (index 9)
        if page_num == 9 and page_num < len(overlay_reader.pages):
            overlay_page = overlay_reader.pages[page_num]
            template_page.merge_page(overlay_page)
        
        writer.add_page(template_page)
    
    # Write the output
    with open(output_path, 'wb') as output_file:
        writer.write(output_file)
    
    # Clean up overlay
    if os.path.exists(overlay_path):
        os.remove(overlay_path)
    
    return output_path