"""
Anchor-based PDF signature and field placement system.
Uses pdfplumber for coordinate detection, reportlab for overlay generation,
and pypdf for precise merging.
"""

import os
import uuid
import datetime as dt
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter
from io import BytesIO
from .anchor_mappings import get_anchor_config, get_signature_font_config


class AnchorPDFProcessor:
    def __init__(self, templates_folder="GreenWatt-documents"):
        self.templates_folder = templates_folder
        self.temp_folder = "temp"
        os.makedirs(self.temp_folder, exist_ok=True)
        
        # Load signature font configuration
        self.signature_config = get_signature_font_config()
        
        # Register the custom signature font
        self._register_signature_font()
    
    def _register_signature_font(self):
        """Register the custom signature font with ReportLab."""
        try:
            # Try to register the primary signature font
            font_file = self.signature_config["font_file"]
            font_name = self.signature_config["font_name"]
            font_path = font_file  # Use direct path from config
            
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                print(f"✅ Successfully registered signature font: {font_name} ({font_file})")
                
                # Store the working font name for use in overlay creation
                self.working_signature_font = font_name
                self.working_signature_size = self.signature_config["font_size"]
                
            else:
                raise FileNotFoundError(f"Font file not found: {font_path}")
                
        except Exception as e:
            print(f"⚠️  Failed to register primary signature font: {e}")
            
            # Try alternative fonts
            for alt_font in self.signature_config.get("alternative_fonts", []):
                try:
                    alt_path = os.path.join("fonts", alt_font["file"])
                    if os.path.exists(alt_path):
                        pdfmetrics.registerFont(TTFont(alt_font["name"], alt_path))
                        print(f"✅ Using alternative signature font: {alt_font['name']}")
                        
                        self.working_signature_font = alt_font["name"]
                        self.working_signature_size = alt_font["size"]
                        return
                        
                except Exception as alt_e:
                    print(f"⚠️  Failed to register alternative font {alt_font['name']}: {alt_e}")
                    continue
            
            # Fallback to system font
            fallback_font = self.signature_config.get("fallback_font", "Helvetica-Oblique")
            print(f"⚠️  Using fallback signature font: {fallback_font}")
            self.working_signature_font = fallback_font
            self.working_signature_size = self.signature_config["font_size"]
    
    def find_anchor_across_pages(self, pdf_path, anchor_text, context=None, context_preference=None):
        """
        Find the coordinates of anchor text across ALL pages in a PDF.
        
        Args:
            pdf_path (str): Path to the PDF file
            anchor_text (str): Text to search for
            context (str): Optional context to narrow search (e.g., "SUBSCRIBER:")
            context_preference (str): Which match to use if multiple found ("first", "second", "last")
            
        Returns:
            tuple: (page_num, x, y) coordinates of the anchor text, or None if not found
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"🔍 Searching for '{anchor_text}' across {len(pdf.pages)} pages")
                if context:
                    print(f"   With context: '{context}'")
                if context_preference:
                    print(f"   Preference: {context_preference} match")
                
                all_matches = []
                
                # Search all pages
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Use search() method - more reliable than extract_words()
                        search_results = page.search(anchor_text)
                        
                        if search_results:
                            print(f"   📄 Page {page_num + 1}: Found {len(search_results)} matches for '{anchor_text}'")
                            
                            for result in search_results:
                                match_data = {
                                    "page": page_num,
                                    "text": result["text"],
                                    "x0": float(result["x0"]),
                                    "top": float(result["top"]),
                                    "context_valid": True
                                }
                                
                                # If context specified, verify it's on the same page
                                if context:
                                    context_results = page.search(context)
                                    if not context_results:
                                        match_data["context_valid"] = False
                                        print(f"     ❌ No context '{context}' found on page {page_num + 1}")
                                    else:
                                        match_data["context_valid"] = True
                                        print(f"     ✅ Context '{context}' found on page {page_num + 1}")
                                else:
                                    # If no context specified, this match is valid
                                    match_data["context_valid"] = True
                                
                                if match_data["context_valid"]:
                                    all_matches.append(match_data)
                                    print(f"     🎯 Valid match: '{result['text']}' at ({result['x0']:.1f}, {result['top']:.1f})")
                    
                    except Exception as e:
                        print(f"   ❌ Error searching page {page_num + 1}: {e}")
                        continue
                
                # Select the appropriate match based on preference
                if not all_matches:
                    print(f"   ❌ No valid matches found for '{anchor_text}'")
                    return None
                
                # Apply context preference
                if context_preference and len(all_matches) > 1:
                    if context_preference == "first":
                        selected_match = all_matches[0]
                    elif context_preference == "second" and len(all_matches) >= 2:
                        selected_match = all_matches[1]
                    elif context_preference == "last":
                        selected_match = all_matches[-1]
                    else:
                        selected_match = all_matches[0]  # Default to first
                    
                    print(f"   🎯 Using {context_preference} match: page {selected_match['page'] + 1}")
                else:
                    selected_match = all_matches[0]  # Use first match
                
                return selected_match["page"], selected_match["x0"], selected_match["top"]
                
        except Exception as e:
            print(f"❌ Error finding anchor '{anchor_text}': {e}")
            return None
    
    def create_overlay_pdf(self, template_path, field_data_by_page):
        """
        Create a transparent overlay PDF with text positioned at specific coordinates.
        
        Args:
            template_path (str): Path to the template PDF to get page dimensions
            field_data_by_page (dict): Dictionary of page numbers to field data
                                     Format: {page_num: {field_name: {"text": str, "x": float, "y": float, "is_signature": bool}}}
            
        Returns:
            str: Path to the created overlay PDF
        """
        overlay_path = os.path.join(self.temp_folder, f"overlay_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        # Get template dimensions
        with pdfplumber.open(template_path) as pdf:
            # Create canvas with dimensions of the first page
            first_page = pdf.pages[0]
            page_width = first_page.width
            page_height = first_page.height
            
            c = canvas.Canvas(overlay_path, pagesize=(page_width, page_height))
            
            # Create enough blank pages to reach the target page numbers
            max_page_num = max(field_data_by_page.keys())
            
            # Create all pages up to the maximum page number
            # Note: We need to create pages 1-based to match PDF page numbering
            for canvas_page in range(max_page_num + 1):
                # Show new page for all pages except the first one (which is created automatically)
                if canvas_page > 0:
                    c.showPage()
                
                # Process field data if it exists for this page (0-indexed)
                if canvas_page in field_data_by_page:
                    field_data = field_data_by_page[canvas_page]
                    
                    # Get page dimensions for this specific page
                    if canvas_page < len(pdf.pages):
                        page = pdf.pages[canvas_page]
                        current_page_width = page.width
                        current_page_height = page.height
                    else:
                        current_page_width = page_width
                        current_page_height = page_height
                    
                    for field_name, data in field_data.items():
                        text = data["text"]
                        x = data["x"]
                        y = data["y"]
                        is_signature = data.get("is_signature", False)
                        
                        if not text:
                            continue
                            
                        # Apply signature font for signature fields
                        if is_signature:
                            # Use the working signature font (registered during initialization)
                            c.setFont(self.working_signature_font, self.working_signature_size)
                            # Set signature color (solid black like Adobe)
                            c.setFillColorRGB(self.signature_config["color"][0], 
                                             self.signature_config["color"][1], 
                                             self.signature_config["color"][2])
                        else:
                            c.setFont("Helvetica", 10)
                            c.setFillColorRGB(0, 0, 0)  # Black for non-signatures
                        
                        # Convert coordinates (pdfplumber uses top-down, reportlab uses bottom-up)
                        reportlab_y = current_page_height - y
                        
                        c.drawString(x, reportlab_y, str(text))
            
            c.save()
            return overlay_path
    
    def merge_overlay_with_template(self, template_path, overlay_path, output_path):
        """
        Merge the overlay PDF with the template PDF.
        
        Args:
            template_path (str): Path to the template PDF
            overlay_path (str): Path to the overlay PDF
            output_path (str): Path for the output PDF
            
        Returns:
            str: Path to the merged PDF
        """
        try:
            # Read both PDFs
            template_reader = PdfReader(template_path)
            overlay_reader = PdfReader(overlay_path)
            writer = PdfWriter()
            
            # Process each page
            for page_num in range(len(template_reader.pages)):
                template_page = template_reader.pages[page_num]
                
                # Merge overlay page if it exists for this page number
                if page_num < len(overlay_reader.pages):
                    overlay_page = overlay_reader.pages[page_num]
                    template_page.merge_page(overlay_page)
                
                writer.add_page(template_page)
            
            # Write the merged PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            print(f"Error merging PDFs: {e}")
            raise
        finally:
            # Clean up overlay file
            if os.path.exists(overlay_path):
                try:
                    os.remove(overlay_path)
                except:
                    pass
    
    def generate_enhanced_poa_id(self):
        """
        Generate enhanced POA ID with timestamp and UUID.
        
        Returns:
            str: POA ID in format POA-YYYYMMDDHHMMS-{uuid_hex}
        """
        timestamp = dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')
        uuid_part = uuid.uuid4().hex[:6]
        return f"POA-{timestamp}-{uuid_part}"
    
    def process_template_with_anchors(self, template_filename, form_data, ocr_data, timestamp):
        """
        Process a PDF template using anchor-based field placement.
        
        Args:
            template_filename (str): Name of the template file
            form_data (dict): Form data from user input
            ocr_data (dict): OCR extracted data
            timestamp (str): Timestamp for file naming
            
        Returns:
            tuple: (output_path, poa_id) if POA, or just output_path for agreements
        """
        template_path = os.path.join(self.templates_folder, template_filename)
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        # Get anchor configuration for this template
        anchor_config = get_anchor_config(template_filename)
        if not anchor_config:
            raise ValueError(f"No anchor configuration found for template: {template_filename}")
        
        # Generate output path
        base_name = template_filename.replace('.pdf', '')
        output_path = os.path.join(self.temp_folder, f"{base_name}_{timestamp}.pdf")
        
        # Get page dimensions
        with pdfplumber.open(template_path) as pdf:
            first_page = pdf.pages[0]
            page_width = first_page.width
            page_height = first_page.height
        
        # Prepare field data organized by page
        field_data_by_page = {}
        poa_id = None
        
        # Generate POA ID for POA templates
        if "POA" in template_filename or "Power_of_Attorney" in template_filename:
            poa_id = self.generate_enhanced_poa_id()
            form_data['poa_id'] = poa_id  # Store for later use
        
        # Map form data to template fields
        for field_name, anchor_info in anchor_config.items():
            # Handle both anchor-based positioning and fixed coordinate positioning
            if "x" in anchor_info and "y" in anchor_info:
                # Fixed coordinate positioning (Page 7 subscriber fields)
                page_num = 6  # Page 7 (0-indexed)
                final_x = anchor_info["x"]
                final_y = anchor_info["y"]
                
                print(f"✅ Using fixed coordinates for '{field_name}' on page {page_num + 1} at ({final_x:.1f}, {final_y:.1f})")
            else:
                # Anchor-based positioning (existing signature fields)
                anchor_text = anchor_info["anchor"]
                dx = anchor_info["dx"]
                dy = anchor_info["dy"]
                context = anchor_info.get("context")
                context_preference = anchor_info.get("context_preference")
                
                # Find anchor coordinates across all pages
                result = self.find_anchor_across_pages(template_path, anchor_text, context, context_preference)
                if not result:
                    print(f"Warning: Could not find anchor '{anchor_text}' anywhere in {template_filename}")
                    continue
                
                page_num, x, y = result
                final_x = x + dx
                final_y = y + dy
                
                print(f"✅ Found '{anchor_text}' on page {page_num + 1} at ({x:.1f}, {y:.1f}) -> placing at ({final_x:.1f}, {final_y:.1f})")
            
            # Determine field value and whether it's a signature
            text_value = ""
            is_signature = False
            
            # POA Page 1: Customer Information Fields
            if field_name == "customer_name_page1":
                text_value = form_data.get('account_name', '')  # Primary account name
            elif field_name == "service_address_page1":
                text_value = form_data.get('service_addresses', '')  # Service addresses from form
            elif field_name == "utility_provider_page1":
                text_value = form_data.get('utility_provider', '')  # Utility provider from dropdown
            elif field_name == "utility_account_page1":
                text_value = ocr_data.get('account_number', '')  # Account number from OCR extraction
            
            # POA Page 2: Signature Fields
            elif field_name == "customer_signature":
                text_value = form_data.get('contact_name', '')
                is_signature = True
            elif field_name == "printed_name":
                text_value = form_data.get('contact_name', '')
            elif field_name == "title":
                text_value = form_data.get('title', '')
            elif field_name == "date" or field_name == "date_signed":
                text_value = dt.datetime.now().strftime('%m/%d/%Y')
            elif field_name == "email":
                text_value = form_data.get('email', '')
            elif field_name == "poa_id":
                text_value = poa_id or ""
            
            # Mass Market Customer Information Fields
            elif field_name == "customer_info_name":
                text_value = form_data.get('contact_name', '') or form_data.get('account_name', '')
            elif field_name == "customer_info_address":
                # Extract street address from service addresses
                addresses = form_data.get('service_addresses', '')
                text_value = self._parse_street_address(addresses)
            elif field_name == "customer_info_city":
                addresses = form_data.get('service_addresses', '')
                text_value = self._parse_city(addresses)
            elif field_name == "customer_info_state":
                addresses = form_data.get('service_addresses', '')
                text_value = self._parse_state(addresses)
            elif field_name == "customer_info_zip":
                addresses = form_data.get('service_addresses', '')
                text_value = self._parse_zip(addresses)
            elif field_name == "customer_info_phone":
                text_value = form_data.get('phone', '')
            elif field_name == "customer_info_email":
                text_value = form_data.get('email', '')
            
            # Meadow Commercial UCB Agreement - Page 2 Header Fields
            elif field_name == "effective_date":
                # Effective Date - use today's date in MM/DD/YYYY format
                text_value = dt.datetime.now().strftime('%m/%d/%Y')
            elif field_name == "agreement_business_name":
                # Business name in agreement header - use account name from form
                text_value = form_data.get('account_name', '') or form_data.get('business_entity', '')
            
            # Meadow Commercial UCB Agreement - Page 7 Subscriber Fields
            elif field_name == "subscriber_attention":
                # Attention field - can use contact name or a specific attention line
                text_value = form_data.get('attention', '') or form_data.get('contact_name', '')
            elif field_name == "subscriber_business_name":
                # Business name field - use account name (business entity)
                text_value = form_data.get('account_name', '') or form_data.get('business_entity', '')
            elif field_name == "subscriber_address":
                # Address field - use full service address
                text_value = form_data.get('service_addresses', '')
            elif field_name == "subscriber_email":
                # Email field - use form email
                text_value = form_data.get('email', '')
            elif field_name == "subscriber_phone":
                # Phone field - use form phone
                text_value = form_data.get('phone', '')
            
            if text_value:
                # Organize field data by page
                if page_num not in field_data_by_page:
                    field_data_by_page[page_num] = {}
                
                field_data_by_page[page_num][field_name] = {
                    "text": text_value,
                    "x": final_x,
                    "y": final_y,
                    "is_signature": is_signature
                }
        
        # Create overlay and merge
        if field_data_by_page:
            overlay_path = self.create_overlay_pdf(template_path, field_data_by_page)
            self.merge_overlay_with_template(template_path, overlay_path, output_path)
        else:
            # If no fields to overlay, just copy the template
            import shutil
            shutil.copy2(template_path, output_path)
        
        # Return appropriate result
        if poa_id:
            return output_path, poa_id
        else:
            return output_path
    
    def _parse_street_address(self, address_text):
        """Extract street address from service addresses field"""
        if not address_text:
            return ""
        
        # Handle common address formats:
        # "123 Main St, New York, NY 10001"
        # "123 Main St\nNew York, NY 10001" 
        
        # Split by comma or newline, take first part
        lines = address_text.replace('\n', ',').split(',')
        street = lines[0].strip() if lines else ""
        return street
    
    def _parse_city(self, address_text):
        """Extract city from service addresses field"""
        if not address_text:
            return ""
        
        try:
            # Handle format: "123 Main St, New York, NY 10001"
            parts = address_text.replace('\n', ',').split(',')
            if len(parts) >= 2:
                city = parts[1].strip()
                return city
        except:
            pass
        
        return ""
    
    def _parse_state(self, address_text):
        """Extract state from service addresses field"""
        if not address_text:
            return ""
        
        try:
            # Handle format: "123 Main St, New York, NY 10001"
            parts = address_text.replace('\n', ',').split(',')
            if len(parts) >= 3:
                # State and zip are usually in the last part: "NY 10001"
                state_zip = parts[2].strip().split()
                if state_zip:
                    state = state_zip[0]
                    return state
        except:
            pass
        
        return ""
    
    def _parse_zip(self, address_text):
        """Extract ZIP code from service addresses field"""
        if not address_text:
            return ""
        
        try:
            # Handle format: "123 Main St, New York, NY 10001"
            parts = address_text.replace('\n', ',').split(',')
            if len(parts) >= 3:
                # State and zip are usually in the last part: "NY 10001"
                state_zip = parts[2].strip().split()
                if len(state_zip) >= 2:
                    zip_code = state_zip[1]
                    return zip_code
        except:
            pass
        
        return ""