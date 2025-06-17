import os
import pypdf
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

class PDFTemplateProcessor:
    def __init__(self, templates_folder="GreenWatt-documents"):
        self.templates_folder = templates_folder
        self.poa_counter = self._get_daily_poa_counter()
        
        # Try to register a signature font (fallback to default if not available)
        try:
            # Try to use a script-style font for signatures
            # This would need to be added to the project if desired
            pass
        except:
            # Fallback to italic for signatures
            pass
    
    def _get_daily_poa_counter(self):
        """Get and increment the daily POA counter"""
        today = datetime.now().strftime('%Y%m%d')
        counter_file = f"temp/poa_counter_{today}.txt"
        
        try:
            if os.path.exists(counter_file):
                with open(counter_file, 'r') as f:
                    count = int(f.read().strip())
            else:
                count = 0
            
            # Increment and save
            count += 1
            os.makedirs('temp', exist_ok=True)
            with open(counter_file, 'w') as f:
                f.write(str(count))
            
            return count
        except:
            return 1
    
    def _generate_poa_id(self):
        """Generate unique POA ID in format POA-YYYYMMDD-XXX"""
        today = datetime.now().strftime('%Y%m%d')
        return f"POA-{today}-{self.poa_counter:03d}"
    
    def _create_signature_overlay(self, signature_text, x, y, page_width, page_height):
        """Create a PDF overlay with signature text in italic style"""
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        # Use italic font for signature
        can.setFont("Helvetica-Oblique", 12)
        can.drawString(x, y, signature_text)
        
        can.save()
        packet.seek(0)
        
        return pypdf.PdfReader(packet)
    
    def _create_text_overlay(self, text, x, y, page_width, page_height, font_size=10):
        """Create a PDF overlay with regular text"""
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))
        
        can.setFont("Helvetica", font_size)
        can.drawString(x, y, text)
        
        can.save()
        packet.seek(0)
        
        return pypdf.PdfReader(packet)
    
    def process_poa_template(self, form_data, ocr_data, timestamp):
        """Process the Power of Attorney template with form data"""
        template_path = os.path.join(self.templates_folder, "GreenWattUSA_Limited_Power_of_Attorney.pdf")
        output_path = f"temp/POA_{timestamp}.pdf"
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"POA template not found: {template_path}")
        
        try:
            # Read the template
            reader = pypdf.PdfReader(template_path)
            writer = pypdf.PdfWriter()
            
            # Generate unique POA ID
            poa_id = self._generate_poa_id()
            
            # Process each page
            for page_num, page in enumerate(reader.pages):
                if page_num == 0:  # First page - add POA ID to header
                    # Get page dimensions
                    page_width = float(page.mediabox.width)
                    page_height = float(page.mediabox.height)
                    
                    # Add POA ID to top right corner
                    poa_id_overlay = self._create_text_overlay(
                        f"POA ID: {poa_id}", 
                        page_width - 150, page_height - 50,
                        page_width, page_height, 8
                    )
                    page.merge_page(poa_id_overlay.pages[0])
                
                elif page_num == 1:  # Second page - signature page
                    # Get page dimensions
                    page_width = float(page.mediabox.width)
                    page_height = float(page.mediabox.height)
                    
                    # Add customer information overlays
                    # These coordinates would need to be adjusted based on the actual template
                    overlays = [
                        # Customer Name
                        (form_data['contact_name'], 150, 550),
                        # Account Name
                        (form_data['account_name'], 150, 520),
                        # Service Address
                        (form_data['service_addresses'], 150, 490),
                        # Utility Provider
                        (form_data['utility_provider'], 150, 460),
                        # Account Number
                        (ocr_data.get('account_number', 'N/A'), 150, 430),
                        # Date
                        (datetime.now().strftime('%B %d, %Y'), 150, 300)
                    ]
                    
                    # Add POID if present
                    poid_value = form_data.get('poid') or ocr_data.get('poid', '')
                    if poid_value:
                        overlays.append((f"POID: {poid_value}", 150, 400))
                    
                    # Apply text overlays
                    for text, x, y in overlays:
                        if text and text != 'N/A':
                            text_overlay = self._create_text_overlay(text, x, y, page_width, page_height)
                            page.merge_page(text_overlay.pages[0])
                    
                    # Add signature overlay (in italic/script style)
                    signature_overlay = self._create_signature_overlay(
                        form_data['contact_name'], 
                        150, 200,  # Signature line coordinates
                        page_width, page_height
                    )
                    page.merge_page(signature_overlay.pages[0])
                
                writer.add_page(page)
            
            # Write the processed PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path, poa_id
            
        except Exception as e:
            print(f"Error processing POA template: {e}")
            raise
    
    def process_agreement_template(self, form_data, ocr_data, developer, utility, account_type, timestamp):
        """Process the appropriate agreement template with form data"""
        
        # Get the agreement filename from mapping
        from services.google_sheets_service import GoogleSheetsService
        import json
        import os
        
        # Load service account info
        SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if SERVICE_ACCOUNT_JSON:
            SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)
        else:
            with open('upwork-greenwatt-drive-sheets-3be108764560.json', 'r') as f:
                SERVICE_ACCOUNT_INFO = json.load(f)
        
        sheets_service = GoogleSheetsService(
            SERVICE_ACCOUNT_INFO, 
            os.getenv('GOOGLE_SHEETS_ID'),
            os.getenv('GOOGLE_AGENT_SHEETS_ID')
        )
        
        # Get agreement filename
        agreement_filename = sheets_service.get_developer_agreement(developer, utility, account_type)
        
        if not agreement_filename:
            raise ValueError(f"No agreement template found for {developer} + {utility} + {account_type}")
        
        template_path = os.path.join(self.templates_folder, agreement_filename)
        output_path = f"temp/Agreement_{timestamp}.pdf"
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Agreement template not found: {template_path}")
        
        try:
            # Read the template
            reader = pypdf.PdfReader(template_path)
            writer = pypdf.PdfWriter()
            
            # Process each page
            for page_num, page in enumerate(reader.pages):
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Add customer information overlays based on template type
                if "Mass Market" in agreement_filename:
                    # Residential agreement - signature on last page
                    if page_num == len(reader.pages) - 1:
                        # Add signature
                        signature_overlay = self._create_signature_overlay(
                            form_data['contact_name'], 
                            200, 150,  # Adjust coordinates for actual template
                            page_width, page_height
                        )
                        page.merge_page(signature_overlay.pages[0])
                        
                        # Add date
                        date_overlay = self._create_text_overlay(
                            datetime.now().strftime('%m/%d/%Y'), 
                            400, 150,
                            page_width, page_height
                        )
                        page.merge_page(date_overlay.pages[0])
                
                elif "Commercial-UCB" in agreement_filename:
                    # Commercial agreement - signature on page 9 (0-indexed page 8)
                    if page_num == 8:  # 9th page (0-indexed)
                        # Add customer/subscriber signature only
                        # (Solar Producer signature would be handled separately)
                        signature_overlay = self._create_signature_overlay(
                            form_data['contact_name'], 
                            200, 300,  # Adjust coordinates for subscriber signature
                            page_width, page_height
                        )
                        page.merge_page(signature_overlay.pages[0])
                        
                        # Add title
                        if form_data.get('title'):
                            title_overlay = self._create_text_overlay(
                                form_data['title'], 
                                200, 270,
                                page_width, page_height
                            )
                            page.merge_page(title_overlay.pages[0])
                        
                        # Add date
                        date_overlay = self._create_text_overlay(
                            datetime.now().strftime('%m/%d/%Y'), 
                            400, 300,
                            page_width, page_height
                        )
                        page.merge_page(date_overlay.pages[0])
                
                # Add general customer information on first page for all templates
                if page_num == 0:
                    # Customer details overlay (coordinates need adjustment per template)
                    customer_overlays = [
                        (form_data['account_name'], 150, 650),  # Company name
                        (form_data['contact_name'], 150, 620),  # Contact name
                        (form_data['service_addresses'], 150, 590),  # Address
                        (form_data['phone'], 150, 560),  # Phone
                        (form_data['email'], 150, 530),  # Email
                    ]
                    
                    for text, x, y in customer_overlays:
                        if text:
                            text_overlay = self._create_text_overlay(text, x, y, page_width, page_height)
                            page.merge_page(text_overlay.pages[0])
                
                writer.add_page(page)
            
            # Write the processed PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            print(f"Error processing agreement template: {e}")
            raise
    
    def process_agency_agreement(self, form_data, timestamp):
        """Process the agency agreement template"""
        template_path = os.path.join(self.templates_folder, "GreenWATT-USA-Inc-Communtiy-Solar-Agency-Agreement.pdf")
        output_path = f"temp/Agency_{timestamp}.pdf"
        
        if not os.path.exists(template_path):
            print(f"Warning: Agency agreement template not found: {template_path}")
            return None
        
        try:
            # Read the template
            reader = pypdf.PdfReader(template_path)
            writer = pypdf.PdfWriter()
            
            # Process each page
            for page_num, page in enumerate(reader.pages):
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Add electronic signature format: "[USER NAME] BY GreenWATT USA Inc. (LOA)"
                if page_num == len(reader.pages) - 1:  # Last page signature
                    electronic_signature = f"{form_data['contact_name']} BY GreenWATT USA Inc. (LOA)"
                    signature_overlay = self._create_text_overlay(
                        electronic_signature, 
                        150, 200,
                        page_width, page_height
                    )
                    page.merge_page(signature_overlay.pages[0])
                
                writer.add_page(page)
            
            # Write the processed PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            print(f"Error processing agency agreement template: {e}")
            return None