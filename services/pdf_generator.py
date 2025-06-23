# PDF generators - now using pixel-perfect anchor-based signature placement
# Legacy generators kept as fallback

from services.anchor_pdf_processor import AnchorPDFProcessor
from services.pdf_template_processor import PDFTemplateProcessor
import os

# Initialize processors
anchor_processor = AnchorPDFProcessor()
template_processor = PDFTemplateProcessor()  # Keep as fallback

def generate_poa_pdf(form_data, ocr_data, timestamp):
    """Generate POA PDF using pixel-perfect anchor-based signature placement"""
    try:
        # Use anchor-based processing for pixel-perfect placement
        poa_template = 'GreenWattUSA_Limited_Power_of_Attorney.pdf'
        result = anchor_processor.process_template_with_anchors(
            poa_template, form_data, ocr_data, timestamp
        )
        
        if isinstance(result, tuple):
            output_path, poa_id = result
            # Store POA ID for later use in Google Sheets
            form_data['poa_id'] = poa_id
            return output_path
        else:
            return result
            
    except Exception as e:
        print(f"Error with anchor-based POA generation: {e}")
        # Fallback to template processor
        try:
            output_path, poa_id = template_processor.process_poa_template(form_data, ocr_data, timestamp)
            form_data['poa_id'] = poa_id
            return output_path
        except Exception as e2:
            print(f"Error with template POA generation: {e2}")
            # Final fallback to legacy generator
            return _legacy_generate_poa_pdf(form_data, ocr_data, timestamp)

def generate_agreement_pdf(form_data, ocr_data, developer, timestamp):
    """Generate Agreement PDF using pixel-perfect anchor-based signature placement"""
    try:
        # Get the correct agreement template filename
        from services.google_sheets_service import GoogleSheetsService
        import json
        
        # Load service account info for sheets lookup
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
        
        # Get agreement filename based on developer + utility + account type
        account_type = form_data.get('account_type', 'Mass Market [Residential]')
        utility = form_data.get('utility_provider', 'National Grid')
        
        agreement_filename = sheets_service.get_developer_agreement(developer, utility, account_type)
        
        if agreement_filename:
            # Use anchor-based processing for pixel-perfect placement
            output_path = anchor_processor.process_template_with_anchors(
                agreement_filename, form_data, ocr_data, timestamp
            )
            return output_path
        else:
            # Try fallback with Mass Market if no specific utility match found
            fallback_filename = sheets_service.get_developer_agreement(developer, "Mass Market", account_type)
            if fallback_filename:
                print(f"Using Mass Market fallback template for {developer}")
                output_path = anchor_processor.process_template_with_anchors(
                    fallback_filename, form_data, ocr_data, timestamp
                )
                return output_path
            else:
                raise ValueError(f"No agreement template found for {developer} + {utility} + {account_type}")
            
    except Exception as e:
        print(f"Error with anchor-based agreement generation: {e}")
        # Fallback to template processor
        try:
            output_path = template_processor.process_agreement_template(
                form_data, ocr_data, developer, utility, account_type, timestamp
            )
            return output_path
        except Exception as e2:
            print(f"Error with template agreement generation: {e2}")
            # Final fallback to legacy generator
            return _legacy_generate_agreement_pdf(form_data, ocr_data, developer, timestamp)

def generate_agency_agreement_pdf(form_data, ocr_data, timestamp):
    """Generate Agency Agreement PDF (Terms & Conditions)"""
    try:
        # Try to find and use the GWUSA Agency Agreement template
        agency_template = 'GreenWatt-USA-Inc-Communtiy-Solar-Agency-Agreement.pdf'
        
        # Use anchor-based processing for pixel-perfect placement
        output_path = anchor_processor.process_template_with_anchors(
            agency_template, form_data, ocr_data, timestamp
        )
        return output_path
            
    except Exception as e:
        print(f"Error with anchor-based agency agreement generation: {e}")
        # Fallback to legacy generator
        return _legacy_generate_agency_agreement_pdf(form_data, ocr_data, timestamp)

# Legacy generators kept as fallback
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
from xml.sax.saxutils import escape

def safe(txt):
    """Escape &, <, >, and quotes for ReportLab mini-html."""
    return escape(str(txt), {"'": "&#39;", '"': "&quot;"})

def _legacy_generate_poa_pdf(form_data, ocr_data, timestamp):
    """Legacy POA generator - fallback only"""
    filename = f"temp/POA_{timestamp}_legacy.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c5530'),
        spaceAfter=30,
        alignment=1
    )
    
    story.append(Paragraph("GreenWatt USA Power of Attorney (Legacy)", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    # Add content as separate paragraphs - all user data escaped
    intro_text = f'This Power of Attorney ("POA") is entered into on {datetime.now().strftime("%B %d, %Y")} between <b>{safe(form_data["account_name"])}</b> ("Customer") and GreenWatt USA LLC ("Company").'
    story.append(Paragraph(intro_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    whereas_text = '<b>WHEREAS</b>, Customer desires to participate in community solar programs and authorize Company to act on their behalf with utility providers;'
    story.append(Paragraph(whereas_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    therefore_text = '<b>NOW THEREFORE</b>, Customer hereby appoints Company as their attorney-in-fact to:'
    story.append(Paragraph(therefore_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    powers_style = ParagraphStyle(
        'Powers',
        parent=styles['Normal'],
        leftIndent=20
    )
    
    powers_text = """1. Submit enrollment applications for community solar programs<br/>
    2. Access utility account information necessary for enrollment<br/>
    3. Manage allocations and subscriptions on Customer's behalf<br/>
    4. Receive and review utility bills for credit verification<br/>
    5. Handle all communications with utility providers regarding solar credits"""
    story.append(Paragraph(powers_text, powers_style))
    story.append(Spacer(1, 12))
    
    # Customer information section - all user data escaped
    customer_info = f"""<b>Customer Information:</b><br/>
    Account Name: {safe(form_data['account_name'])}<br/>
    Contact Name: {safe(form_data['contact_name'])}<br/>
    Service Address: {safe(form_data['service_addresses'])}<br/>
    Utility Provider: {safe(form_data['utility_provider'])}<br/>
    Account Number: {safe(ocr_data.get('account_number', 'N/A'))}"""
    
    # Add POID if present
    poid_value = form_data.get('poid') or ocr_data.get('poid', '')
    if poid_value:
        customer_info += f"<br/>POID: {safe(poid_value)}"
    
    story.append(Paragraph(customer_info, styles['Normal']))
    story.append(Spacer(1, 12))
    
    termination_text = 'This POA shall remain in effect until revoked in writing by Customer.'
    story.append(Paragraph(termination_text, styles['Normal']))
    
    story.append(Spacer(1, 0.5*inch))
    
    signature_data = [
        ['Customer Signature:', safe(form_data['contact_name']) + ' (Electronic Signature)'],
        ['Date:', datetime.now().strftime('%B %d, %Y')],
        ['Time:', datetime.now().strftime('%I:%M %p')],
        ['IP Address:', '192.168.1.1'],
        ['Agent ID:', safe(form_data['agent_id'])]
    ]
    
    sig_table = Table(signature_data, colWidths=[2*inch, 4*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(sig_table)
    
    doc.build(story)
    return filename

def _legacy_generate_agency_agreement_pdf(form_data, ocr_data, timestamp):
    """Legacy Agency Agreement generator - fallback only"""
    filename = f"temp/agency_agreement_{timestamp}_legacy.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c5530'),
        spaceAfter=30,
        alignment=1
    )
    
    story.append(Paragraph("GreenWatt USA Inc. Community Solar Agency Agreement (Legacy)", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Agreement intro - all user data escaped
    intro_text = f'This Agency Agreement is entered into on {datetime.now().strftime("%B %d, %Y")} between GreenWatt USA Inc. ("Agent") and <b>{safe(form_data["account_name"])}</b> ("Principal").'
    story.append(Paragraph(intro_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 1
    section1_text = '<b>1. APPOINTMENT</b><br/>Principal hereby appoints Agent as their exclusive representative for community solar enrollment and management services.'
    story.append(Paragraph(section1_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 2
    section2_text = '<b>2. AUTHORITY</b><br/>Agent is authorized to act on Principal\'s behalf in all matters related to community solar subscriptions, including but not limited to enrollment, account management, and utility communications.'
    story.append(Paragraph(section2_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 3 - all user data escaped
    section3_text = f"""<b>3. PRINCIPAL INFORMATION</b><br/>
    Account Name: {safe(form_data['account_name'])}<br/>
    Contact Name: {safe(form_data['contact_name'])}<br/>
    Title: {safe(form_data['title'])}<br/>
    Phone: {safe(form_data['phone'])}<br/>
    Email: {safe(form_data['email'])}<br/>
    Service Address: {safe(form_data['service_addresses'])}<br/>
    Utility Provider: {safe(form_data['utility_provider'])}"""
    story.append(Paragraph(section3_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 4
    section4_text = '<b>4. TERM</b><br/>This agreement shall remain in effect until terminated by either party with 30 days written notice.'
    story.append(Paragraph(section4_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 5
    section5_text = '<b>5. COMPLIANCE</b><br/>Agent agrees to comply with all applicable laws and regulations in the performance of services under this agreement.'
    story.append(Paragraph(section5_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    story.append(Spacer(1, 0.5*inch))
    
    signature_data = [
        ['Principal Signature:', safe(form_data['contact_name']) + ' (Electronic Signature)'],
        ['Date:', datetime.now().strftime('%B %d, %Y')],
        ['Time:', datetime.now().strftime('%I:%M %p')],
        ['Agent ID:', safe(form_data['agent_id'])],
        ['Agreement Type:', 'Community Solar Agency Agreement']
    ]
    
    sig_table = Table(signature_data, colWidths=[2*inch, 4*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(sig_table)
    
    doc.build(story)
    return filename

def _legacy_generate_agreement_pdf(form_data, ocr_data, developer, timestamp):
    """Legacy Agreement generator - fallback only"""
    filename = f"temp/Agreement_{timestamp}_legacy.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c5530'),
        spaceAfter=30,
        alignment=1
    )
    
    story.append(Paragraph(f"{safe(developer)} Community Solar Agreement (Legacy)", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Header
    header_text = '<b>COMMUNITY SOLAR SUBSCRIPTION AGREEMENT</b>'
    story.append(Paragraph(header_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Agreement intro - all user data escaped
    intro_text = f'This Agreement is entered into on {datetime.now().strftime("%B %d, %Y")} between <b>{safe(developer)}</b> ("Developer") and <b>{safe(form_data["account_name"])}</b> ("Subscriber").'
    story.append(Paragraph(intro_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 1
    section1_text = '<b>1. SUBSCRIPTION DETAILS</b><br/>Subscriber agrees to purchase solar credits generated from Developer\'s community solar facility.'
    story.append(Paragraph(section1_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 2 - all user data escaped
    section2_text = f"""<b>2. BILLING INFORMATION</b><br/>
    Utility Provider: {safe(form_data['utility_provider'])}<br/>
    Account Number: {safe(ocr_data.get('account_number', 'N/A'))}<br/>
    Estimated Annual Usage: {safe(ocr_data.get('annual_usage', 'N/A'))} kWh<br/>
    Subscription Size: {safe(ocr_data.get('annual_usage', 'TBD'))} kWh annually"""
    story.append(Paragraph(section2_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 3
    discount = '10%' if developer == 'Developer A' else '15%'
    section3_text = f'<b>3. SAVINGS AND CREDITS</b><br/>Subscriber will receive a {discount} discount on solar credits applied to their utility bill.'
    story.append(Paragraph(section3_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 4
    term_years = '20 years' if developer == 'Developer A' else '25 years'
    section4_text = f'<b>4. TERM</b><br/>This agreement shall commence upon utility approval and continue for a period of {term_years} unless terminated earlier in accordance with Section 5.'
    story.append(Paragraph(section4_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 5
    section5_text = '<b>5. TERMINATION</b><br/>Either party may terminate this agreement with 60 days written notice.'
    story.append(Paragraph(section5_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 6 - all user data escaped
    section6_text = f"""<b>6. CONTACT INFORMATION</b><br/>
    Subscriber Name: {safe(form_data['contact_name'])}<br/>
    Title: {safe(form_data['title'])}<br/>
    Phone: {safe(form_data['phone'])}<br/>
    Email: {safe(form_data['email'])}<br/>
    Service Address: {safe(form_data['service_addresses'])}"""
    story.append(Paragraph(section6_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Special provisions based on developer
    if developer == 'Developer B':
        section7_text = '<b>7. SPECIAL PROVISIONS - DEVELOPER B</b><br/>Enhanced monitoring and reporting services included at no additional cost.'
        story.append(Paragraph(section7_text, styles['Normal']))
        story.append(Spacer(1, 12))
    elif developer == 'Developer C':
        section7_text = '<b>7. SPECIAL PROVISIONS - DEVELOPER C</b><br/>Guaranteed production levels with make-whole provisions for underperformance.'
        story.append(Paragraph(section7_text, styles['Normal']))
        story.append(Spacer(1, 12))
    
    story.append(Spacer(1, 0.5*inch))
    
    signature_data = [
        ['Subscriber Signature:', safe(form_data['contact_name']) + ' (Electronic Signature)'],
        ['Date:', datetime.now().strftime('%B %d, %Y')],
        ['Time:', datetime.now().strftime('%I:%M %p')],
        ['Acceptance Method:', 'Electronic - Web Form'],
        ['Agent ID:', safe(form_data['agent_id'])]
    ]
    
    sig_table = Table(signature_data, colWidths=[2*inch, 4*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(sig_table)
    
    doc.build(story)
    return filename

def _legacy_generate_agency_agreement_pdf(form_data, ocr_data, timestamp):
    """Legacy Agency Agreement generator - fallback only"""
    filename = f"temp/agency_agreement_{timestamp}_legacy.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c5530'),
        spaceAfter=30,
        alignment=1
    )
    
    story.append(Paragraph("GreenWatt USA Inc. Community Solar Agency Agreement (Legacy)", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Agreement intro - all user data escaped
    intro_text = f'This Agency Agreement is entered into on {datetime.now().strftime("%B %d, %Y")} between GreenWatt USA Inc. ("Agent") and <b>{safe(form_data["account_name"])}</b> ("Principal").'
    story.append(Paragraph(intro_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 1
    section1_text = '<b>1. APPOINTMENT</b><br/>Principal hereby appoints Agent as their exclusive representative for community solar enrollment and management services.'
    story.append(Paragraph(section1_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 2
    section2_text = '<b>2. AUTHORITY</b><br/>Agent is authorized to act on Principal\'s behalf in all matters related to community solar subscriptions, including but not limited to enrollment, account management, and utility communications.'
    story.append(Paragraph(section2_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 3 - all user data escaped
    section3_text = f"""<b>3. PRINCIPAL INFORMATION</b><br/>
    Account Name: {safe(form_data['account_name'])}<br/>
    Contact Name: {safe(form_data['contact_name'])}<br/>
    Title: {safe(form_data['title'])}<br/>
    Phone: {safe(form_data['phone'])}<br/>
    Email: {safe(form_data['email'])}<br/>
    Service Address: {safe(form_data['service_addresses'])}<br/>
    Utility Provider: {safe(form_data['utility_provider'])}"""
    story.append(Paragraph(section3_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 4
    section4_text = '<b>4. TERM</b><br/>This agreement shall remain in effect until terminated by either party with 30 days written notice.'
    story.append(Paragraph(section4_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Section 5
    section5_text = '<b>5. COMPLIANCE</b><br/>Agent agrees to comply with all applicable laws and regulations in the performance of services under this agreement.'
    story.append(Paragraph(section5_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    story.append(Spacer(1, 0.5*inch))
    
    signature_data = [
        ['Principal Signature:', safe(form_data['contact_name']) + ' (Electronic Signature)'],
        ['Date:', datetime.now().strftime('%B %d, %Y')],
        ['Time:', datetime.now().strftime('%I:%M %p')],
        ['Agent ID:', safe(form_data['agent_id'])],
        ['Agreement Type:', 'Community Solar Agency Agreement']
    ]
    
    sig_table = Table(signature_data, colWidths=[2*inch, 4*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(sig_table)
    
    doc.build(story)
    return filename