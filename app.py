from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import json
import uuid
import threading
import time
from datetime import datetime
from werkzeug.utils import secure_filename
from services.ocr_service import process_utility_bill
from services.pdf_generator import generate_poa_pdf, generate_agreement_pdf
from services.google_drive_service import GoogleDriveService
from services.google_sheets_service import GoogleSheetsService
from services.email_service import send_notification_email
from services.sms_service import SMSService
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

# Global progress tracking
progress_sessions = {}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('temp', exist_ok=True)

# Load service account credentials from environment variable or file
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if SERVICE_ACCOUNT_JSON:
    SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)
else:
    # Fallback to file for local development
    try:
        with open('upwork-greenwatt-drive-sheets-3be108764560.json', 'r') as f:
            SERVICE_ACCOUNT_INFO = json.load(f)
    except FileNotFoundError:
        raise Exception("Service account credentials not found. Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable.")

drive_service = GoogleDriveService(SERVICE_ACCOUNT_INFO, os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID'))
sheets_service = GoogleSheetsService(
    SERVICE_ACCOUNT_INFO, 
    os.getenv('GOOGLE_SHEETS_ID'),
    os.getenv('GOOGLE_AGENT_SHEETS_ID')
)
sms_service = SMSService()

# Initialize Google Sheets structure on startup
try:
    sheets_service.setup_required_tabs()
    print("Google Sheets setup completed")
except Exception as e:
    print(f"Warning: Could not setup Google Sheets tabs: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_id():
    """Generate a unique submission ID in format: SUB-YYYYMMDDHHMMS-{uuid_hex}"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    uuid_hex = uuid.uuid4().hex[:6]  # First 6 characters of UUID
    return f"SUB-{timestamp}-{uuid_hex}"

# Progress tracking functions
def create_progress_session():
    """Create a new progress tracking session"""
    session_id = str(uuid.uuid4())
    progress_sessions[session_id] = {
        'current_step': 0,
        'total_steps': 7,
        'percentage': 0,
        'step_name': 'Initializing',
        'step_description': 'Preparing to process your submission',
        'start_time': time.time(),
        'estimated_completion': time.time() + 120,  # 2 minutes estimate
        'completed': False,
        'error': None
    }
    return session_id

def update_progress(session_id, step, step_name, step_description, percentage=None):
    """Update progress for a session"""
    if session_id not in progress_sessions:
        return
    
    session = progress_sessions[session_id]
    session['current_step'] = step
    session['step_name'] = step_name
    session['step_description'] = step_description
    
    if percentage is None:
        # Calculate percentage based on step
        percentage = min(int((step / session['total_steps']) * 100), 100)
    
    session['percentage'] = percentage
    
    # Update time estimates
    elapsed = time.time() - session['start_time']
    if step > 0:
        estimated_total = (elapsed / step) * session['total_steps']
        session['estimated_completion'] = session['start_time'] + estimated_total
    
    print(f"Progress {session_id}: Step {step}/7 - {step_name} ({percentage}%)")

def complete_progress(session_id, success=True, error=None):
    """Mark progress as completed"""
    if session_id not in progress_sessions:
        return
    
    session = progress_sessions[session_id]
    session['completed'] = True
    session['percentage'] = 100 if success else session['percentage']
    session['error'] = error
    
    if success:
        session['step_name'] = 'Complete'
        session['step_description'] = 'Submission processed successfully'

def cleanup_old_sessions():
    """Remove old progress sessions (older than 10 minutes)"""
    current_time = time.time()
    to_remove = []
    for session_id, session in progress_sessions.items():
        if current_time - session['start_time'] > 600:  # 10 minutes
            to_remove.append(session_id)
    
    for session_id in to_remove:
        del progress_sessions[session_id]

@app.route('/progress/<session_id>')
def get_progress(session_id):
    """Get current progress for a session"""
    cleanup_old_sessions()  # Clean up old sessions
    
    if session_id not in progress_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = progress_sessions[session_id]
    
    # Calculate remaining time estimate
    current_time = time.time()
    elapsed = current_time - session['start_time']
    
    if session['completed']:
        remaining_time = 0
        time_text = "Complete!"
    elif session['current_step'] > 0:
        estimated_total = session['estimated_completion'] - session['start_time']
        remaining = max(0, estimated_total - elapsed)
        remaining_time = int(remaining)
        
        if remaining_time > 60:
            time_text = f"About {remaining_time//60} minute(s) remaining"
        elif remaining_time > 0:
            time_text = f"About {remaining_time} seconds remaining"
        else:
            time_text = "Almost done..."
    else:
        remaining_time = 120  # Default estimate
        time_text = "Estimated time: 1-2 minutes"
    
    # Determine status for JavaScript
    if session['completed'] and not session['error']:
        status = 'completed'
    elif session['error']:
        status = 'error'
    else:
        status = 'processing'
        
    response_data = {
        'session_id': session_id,
        'current_step': session['current_step'],
        'total_steps': session['total_steps'],
        'percentage': session['percentage'],
        'step_name': session['step_name'],
        'step_description': session['step_description'],
        'remaining_time': remaining_time,
        'time_text': time_text,
        'completed': session['completed'],
        'error': session['error'],
        'status': status
    }
    
    # Include result data if completed successfully
    if status == 'completed' and 'result' in session:
        response_data['result_data'] = session['result']
        
    return jsonify(response_data)

@app.route('/')
def index():
    try:
        # Get dynamic data from Google Sheets
        utilities = sheets_service.get_active_utilities()
        developers = sheets_service.get_active_developers()
        
        return render_template('index.html', utilities=utilities, developers=developers)
    except Exception as e:
        print(f"Error loading dynamic data: {e}")
        # Fallback to default data if sheets are unavailable
        fallback_utilities = ["National Grid", "NYSEG", "RG&E"]
        fallback_developers = ["Meadow Energy", "Solar Simplified"]
        return render_template('index.html', utilities=fallback_utilities, developers=fallback_developers)

@app.route('/test')
def test_dashboard():
    return render_template('test.html')

@app.route('/test-pixel-perfect')
def test_pixel_perfect():
    return render_template('test_pixel_perfect.html')

@app.route('/phase1-test')
def phase1_test():
    return render_template('phase1_test.html')

@app.route('/test-agent-lookup', methods=['GET', 'POST'])
def test_agent_lookup():
    if request.method == 'GET':
        return '''
        <html>
        <head><title>Agent Lookup Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🕵️ Agent Name Lookup Test</h2>
            <p>This test verifies the agent ID → agent name resolution system.</p>
            
            <form method="POST">
                <label>Enter Agent ID to test:</label><br>
                <input type="text" name="agent_id" placeholder="e.g., AG001" required style="padding: 8px; margin: 10px 0;">
                <button type="submit" style="padding: 8px 15px;">Lookup Agent Name</button>
            </form>
            
            <hr>
            <h3>📊 Bulk Test Common IDs</h3>
            <button onclick="location.href='/test-agent-lookup?bulk=true'" style="padding: 8px 15px;">Test AG001-AG010</button>
        </body>
        </html>
        '''
    
    # Handle POST request
    if request.form.get('agent_id'):
        agent_id = request.form.get('agent_id').strip()
        try:
            agent_name = sheets_service.get_agent_name(agent_id)
            
            return f'''
            <html>
            <head><title>Agent Lookup Result</title></head>
            <body style="font-family: Arial; padding: 20px;">
                <h2>🕵️ Agent Lookup Result</h2>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <strong>Agent ID:</strong> {agent_id}<br>
                    <strong>Agent Name:</strong> <span style="color: {'green' if agent_name != 'Unknown' else 'red'};">{agent_name}</span>
                </div>
                
                <p><strong>Status:</strong> {'✅ Found in sheets' if agent_name != 'Unknown' else '❌ Not found in sheets'}</p>
                
                <button onclick="history.back()" style="padding: 8px 15px;">Test Another</button>
                <button onclick="location.href='/test-agent-lookup?bulk=true'" style="padding: 8px 15px;">Bulk Test</button>
            </body>
            </html>
            '''
        except Exception as e:
            return f'''
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <h2>❌ Error</h2>
                <p>Error looking up agent: {str(e)}</p>
                <button onclick="history.back()">Try Again</button>
            </body>
            </html>
            '''
    
    # Handle bulk test
    if request.args.get('bulk') == 'true':
        test_ids = ['AG001', 'AG002', 'AG003', 'AG004', 'AG005', 'AG006', 'AG007', 'AG008', 'AG009', 'AG010']
        results = []
        
        for agent_id in test_ids:
            try:
                agent_name = sheets_service.get_agent_name(agent_id)
                results.append({
                    'id': agent_id, 
                    'name': agent_name,
                    'found': agent_name != 'Unknown'
                })
            except Exception as e:
                results.append({
                    'id': agent_id,
                    'name': f'ERROR: {str(e)}',
                    'found': False
                })
        
        results_html = ''
        for result in results:
            color = 'green' if result['found'] else 'red'
            icon = '✅' if result['found'] else '❌'
            results_html += f'''
            <tr style="background: {'#e8f5e8' if result['found'] else '#ffe8e8'};">
                <td style="padding: 8px;">{icon} {result['id']}</td>
                <td style="padding: 8px; color: {color};">{result['name']}</td>
            </tr>
            '''
        
        found_count = sum(1 for r in results if r['found'])
        
        return f'''
        <html>
        <head><title>Bulk Agent Lookup Results</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📊 Bulk Agent Lookup Results</h2>
            <p><strong>Summary:</strong> {found_count}/{len(results)} agents found in Google Sheets</p>
            
            <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                <tr style="background: #2c5530; color: white;">
                    <th style="padding: 10px; text-align: left;">Agent ID</th>
                    <th style="padding: 10px; text-align: left;">Agent Name</th>
                </tr>
                {results_html}
            </table>
            
            <button onclick="location.href='/test-agent-lookup'" style="padding: 8px 15px;">Single Test</button>
            <button onclick="location.href='/debug-agent-sheet'" style="padding: 8px 15px;">🔍 Debug Sheet Data</button>
            <button onclick="location.reload()" style="padding: 8px 15px;">Refresh Test</button>
        </body>
        </html>
        '''

@app.route('/debug-agent-sheet')
def debug_agent_sheet():
    try:
        debug_html = f'''
        <html>
        <head><title>Agent Sheet Debug</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🔍 Agent Sheet Debug</h2>
            <div style="background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <strong>Agent Spreadsheet ID:</strong> {sheets_service.agent_spreadsheet_id}<br>
            </div>
        '''
        
        # First, let's see what sheet tabs exist
        try:
            debug_html += f'<p><strong>🔍 Testing spreadsheet access...</strong></p>'
            sheet_metadata = sheets_service.service.spreadsheets().get(
                spreadsheetId=sheets_service.agent_spreadsheet_id
            ).execute()
            
            sheet_tabs = [sheet['properties']['title'] for sheet in sheet_metadata['sheets']]
            debug_html += f'<p><strong>✅ Connected to spreadsheet!</strong></p>'
            debug_html += f'<p><strong>Available Tabs:</strong> {", ".join(sheet_tabs)}</p>'
            
            # Try to get data from each tab
            found_data = False
            for tab_name in sheet_tabs:
                try:
                    result = sheets_service.service.spreadsheets().values().get(
                        spreadsheetId=sheets_service.agent_spreadsheet_id,
                        range=f"{tab_name}!A:B"
                    ).execute()
                    
                    tab_data = result.get("values", [])
                    debug_html += f'<p><strong>Tab "{tab_name}":</strong> {len(tab_data)} rows</p>'
                    
                    if tab_data and len(tab_data) > 0:
                        found_data = True
                        debug_html += f'<p><strong>✅ Found data in tab "{tab_name}"!</strong></p>'
                        
                        # Show first few rows
                        debug_html += '<table style="border-collapse: collapse; margin: 10px 0; border: 1px solid #ddd;">'
                        debug_html += '<tr style="background: #2c5530; color: white;"><th style="padding: 8px; border: 1px solid #ddd;">Row</th><th style="padding: 8px; border: 1px solid #ddd;">Column A</th><th style="padding: 8px; border: 1px solid #ddd;">Column B</th></tr>'
                        
                        for i, row in enumerate(tab_data[:10]):  # Show first 10 rows
                            col_a = row[0] if len(row) > 0 else "EMPTY"
                            col_b = row[1] if len(row) > 1 else "EMPTY"
                            debug_html += f'<tr><td style="padding: 8px; border: 1px solid #ddd;">{i+1}</td><td style="padding: 8px; border: 1px solid #ddd;"><code>{col_a}</code></td><td style="padding: 8px; border: 1px solid #ddd;"><code>{col_b}</code></td></tr>'
                        
                        debug_html += '</table>'
                        
                        # Test lookup with the data we found
                        if len(tab_data) > 1:  # Skip header row
                            test_id = tab_data[1][0] if len(tab_data[1]) > 0 else None
                            if test_id:
                                agent_name = sheets_service.get_agent_name(test_id)
                                debug_html += f'<p><strong>Test lookup "{test_id}":</strong> <span style="color: {"green" if agent_name != "Unknown" else "red"};">{agent_name}</span></p>'
                        
                except Exception as e:
                    debug_html += f'<p><strong>❌ Error reading tab "{tab_name}":</strong> {str(e)}</p>'
            
            if not found_data:
                debug_html += '<p style="color: red;"><strong>❌ No data found in any tabs!</strong></p>'
                    
        except Exception as metadata_error:
            debug_html += f'<p><strong>❌ Cannot access spreadsheet:</strong></p>'
            debug_html += f'<pre style="background: #f8d7da; padding: 10px; border-radius: 5px; font-size: 12px; white-space: pre-wrap;">{str(metadata_error)}</pre>'
            
            # Let's also try the main sheet to verify our connection works
            debug_html += f'<h3>🔍 Testing Main Sheet Connection</h3>'
            try:
                main_sheet_metadata = sheets_service.service.spreadsheets().get(
                    spreadsheetId=sheets_service.spreadsheet_id
                ).execute()
                debug_html += f'<p><strong>✅ Main sheet access works!</strong> (ID: {sheets_service.spreadsheet_id})</p>'
                main_tabs = [sheet['properties']['title'] for sheet in main_sheet_metadata['sheets']]
                debug_html += f'<p><strong>Main sheet tabs:</strong> {", ".join(main_tabs)}</p>'
            except Exception as main_error:
                debug_html += f'<p><strong>❌ Main sheet also fails:</strong> <code>{str(main_error)}</code></p>'
        
        debug_html += '''
            <button onclick="location.href='/test-agent-lookup'" style="padding: 8px 15px; margin-top: 20px;">Back to Test</button>
        </body>
        </html>
        '''
        
        return debug_html
        
    except Exception as e:
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>❌ Debug Error</h2>
            <p>Error accessing agent sheet: {str(e)}</p>
            <button onclick="location.href='/test-agent-lookup'">Back to Test</button>
        </body>
        </html>
        '''

@app.route('/test-pdf', methods=['POST'])
def test_pdf_generation():
    try:
        data = request.get_json()
        
        # Create dummy OCR data
        ocr_data = {
            'utility_name': data['utility_provider'],
            'customer_name': 'Test Customer',
            'account_number': '123456789',
            'poid': data.get('poid', ''),
            'monthly_usage': '1000',
            'annual_usage': '12000'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Test PDF generation
        poa_pdf_path = generate_poa_pdf(data, ocr_data, timestamp)
        agreement_pdf_path = generate_agreement_pdf(data, ocr_data, data.get('developer_assigned', 'Meadow Energy'), timestamp)
        
        # Check if POA ID was generated
        poa_id = data.get('poa_id', 'N/A')
        
        # Clean up test files
        if os.path.exists(poa_pdf_path):
            os.remove(poa_pdf_path)
        if os.path.exists(agreement_pdf_path):
            os.remove(agreement_pdf_path)
        
        return jsonify({
            'success': True,
            'message': 'PDF generation successful',
            'poa_generated': True,
            'agreement_generated': True,
            'poa_id': poa_id,
            'template_processing': 'enabled'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/test-template-processing')
def test_template_processing():
    """Test endpoint to verify template processing works"""
    try:
        # Create test data
        test_form_data = {
            'business_entity': 'Test Business LLC',
            'account_name': 'Test Customer Account',
            'contact_name': 'John Doe',
            'title': 'Manager',
            'phone': '555-123-4567',
            'email': 'john@example.com',
            'service_addresses': '123 Test Street, Test City, NY 12345',
            'developer_assigned': 'Meadow Energy',
            'account_type': 'Small Demand <25 KW',
            'utility_provider': 'National Grid',
            'agent_id': 'TEST001',
            'poid': 'TEST123456'
        }
        
        test_ocr_data = {
            'utility_name': 'National Grid',
            'customer_name': 'Template Test Customer',
            'account_number': '987654321',
            'poid': 'TEST123456',
            'monthly_usage': '1500',
            'annual_usage': '18000',
            'service_address': '123 Oak Street, Buffalo, NY 14201',
            'monthly_charge': '185.45',
            'annual_charge': '2225.40'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Test template processing
        from services.pdf_template_processor import PDFTemplateProcessor
        processor = PDFTemplateProcessor()
        
        # Test POA processing
        poa_path, poa_id = processor.process_poa_template(test_form_data, test_ocr_data, timestamp)
        
        # Test agreement processing
        agreement_path = processor.process_agreement_template(
            test_form_data, test_ocr_data, 
            'Meadow Energy', 'National Grid', 'Small Demand <25 KW', 
            timestamp
        )
        
        # Get file sizes for verification
        poa_size = os.path.getsize(poa_path) if os.path.exists(poa_path) else 0
        agreement_size = os.path.getsize(agreement_path) if os.path.exists(agreement_path) else 0
        
        return f'''
        <html>
        <head><title>Template Processing Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🧪 Template Processing Test Results</h2>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>✅ POA Template Processing</h3>
                <p><strong>POA ID Generated:</strong> {poa_id}</p>
                <p><strong>File Path:</strong> {poa_path}</p>
                <p><strong>File Size:</strong> {poa_size:,} bytes</p>
                <p><strong>Status:</strong> {'✅ Generated' if poa_size > 0 else '❌ Failed'}</p>
            </div>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>✅ Agreement Template Processing</h3>
                <p><strong>Template:</strong> Meadow Energy + National Grid + Small Demand</p>
                <p><strong>File Path:</strong> {agreement_path}</p>
                <p><strong>File Size:</strong> {agreement_size:,} bytes</p>
                <p><strong>Status:</strong> {'✅ Generated' if agreement_size > 0 else '❌ Failed'}</p>
            </div>
            
            <div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📊 Test Configuration</h3>
                <p><strong>Customer:</strong> {test_form_data['contact_name']} ({test_form_data['account_name']})</p>
                <p><strong>Developer:</strong> {test_form_data['developer_assigned']}</p>
                <p><strong>Utility:</strong> {test_form_data['utility_provider']}</p>
                <p><strong>Account Type:</strong> {test_form_data['account_type']}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
            </div>
            
            <button onclick="location.reload()" style="padding: 10px 20px; margin: 10px 5px;">Run Test Again</button>
            <button onclick="location.href='/'" style="padding: 10px 20px; margin: 10px 5px;">Back to Form</button>
        </body>
        </html>
        '''
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        return f'''
        <html>
        <head><title>Template Processing Test - Error</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>❌ Template Processing Test Failed</h2>
            
            <div style="background: #ffe8e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Error Details</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; font-size: 11px; white-space: pre-wrap;">{error_trace}</pre>
            </div>
            
            <button onclick="location.reload()" style="padding: 10px 20px; margin: 10px 5px;">Try Again</button>
            <button onclick="location.href='/'" style="padding: 10px 20px; margin: 10px 5px;">Back to Form</button>
        </body>
        </html>
        '''

@app.route('/test-end-to-end')
def test_end_to_end():
    """End-to-end test with Google Drive upload and signature verification"""
    try:
        # Create comprehensive test data
        test_form_data = {
            'business_entity': 'E2E Test Business LLC',
            'account_name': 'End-to-End Test Customer',
            'contact_name': 'Jane Smith',
            'title': 'CEO',
            'phone': '555-987-6543',
            'email': 'jane@e2etest.com',
            'service_addresses': '456 Test Avenue, Test City, NY 54321',
            'developer_assigned': 'Meadow Energy',
            'account_type': 'Large Demand >25 KW',
            'utility_provider': 'NYSEG',
            'agent_id': '1016',
            'poid': 'E2E123456'
        }
        
        test_ocr_data = {
            'utility_name': 'NYSEG',
            'customer_name': 'End to End Test Customer',
            'account_number': '555-TEST-123',
            'poid': 'E2E123456',
            'monthly_usage': '2500',
            'annual_usage': '30000'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        submission_date = datetime.now()
        
        # Step 1: Generate PDFs using template processor
        poa_pdf_path = generate_poa_pdf(test_form_data, test_ocr_data, timestamp)
        agreement_pdf_path = generate_agreement_pdf(test_form_data, test_ocr_data, test_form_data['developer_assigned'], timestamp)
        
        # Get POA ID that was generated
        poa_id = test_form_data.get('poa_id', 'N/A')
        
        # Step 2: Create Google Drive folder
        folder_name = f"{submission_date.strftime('%Y-%m-%d')}_{test_form_data['account_name']}_{test_form_data['utility_provider']}_E2E_TEST"
        
        try:
            drive_folder_id = drive_service.create_folder(folder_name)
            drive_success = True
            drive_folder_link = f"https://drive.google.com/drive/folders/{drive_folder_id}"
        except Exception as drive_error:
            drive_success = False
            drive_folder_id = None
            drive_folder_link = f"ERROR: {str(drive_error)}"
        
        # Step 3: Upload PDFs to Google Drive
        upload_results = {}
        if drive_success:
            try:
                poa_pdf_id = drive_service.upload_file(poa_pdf_path, f"POA_{test_form_data['account_name']}_E2E.pdf", drive_folder_id)
                poa_link = f"https://drive.google.com/file/d/{poa_pdf_id}/view"
                upload_results['poa'] = {'success': True, 'link': poa_link, 'id': poa_pdf_id}
            except Exception as e:
                upload_results['poa'] = {'success': False, 'error': str(e)}
            
            try:
                agreement_pdf_id = drive_service.upload_file(agreement_pdf_path, f"Agreement_{test_form_data['account_name']}_E2E.pdf", drive_folder_id)
                agreement_link = f"https://drive.google.com/file/d/{agreement_pdf_id}/view"
                upload_results['agreement'] = {'success': True, 'link': agreement_link, 'id': agreement_pdf_id}
            except Exception as e:
                upload_results['agreement'] = {'success': False, 'error': str(e)}
        else:
            upload_results['poa'] = {'success': False, 'error': 'Drive folder creation failed'}
            upload_results['agreement'] = {'success': False, 'error': 'Drive folder creation failed'}
        
        # Step 4: Test Google Sheets logging
        agent_name = sheets_service.get_agent_name(test_form_data['agent_id'])
        
        # Step 5: Get file sizes and verify content
        poa_size = os.path.getsize(poa_pdf_path) if os.path.exists(poa_pdf_path) else 0
        agreement_size = os.path.getsize(agreement_pdf_path) if os.path.exists(agreement_pdf_path) else 0
        
        # Step 6: Clean up local files
        cleanup_results = []
        for file_path in [poa_pdf_path, agreement_pdf_path]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleanup_results.append(f"✅ Cleaned: {file_path}")
                else:
                    cleanup_results.append(f"⚠️ Not found: {file_path}")
            except Exception as e:
                cleanup_results.append(f"❌ Failed to clean: {file_path} - {str(e)}")
        
        # Generate comprehensive test report
        return f'''
        <html>
        <head><title>End-to-End Test Results</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🚀 End-to-End Test Results</h2>
            <p><strong>Test Timestamp:</strong> {timestamp}</p>
            
            <!-- STEP 1: PDF Generation -->
            <div style="background: {'#e8f5e8' if poa_size > 0 and agreement_size > 0 else '#ffe8e8'}; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📄 Step 1: PDF Template Processing</h3>
                <p><strong>POA Generated:</strong> {'✅ Success' if poa_size > 0 else '❌ Failed'} ({poa_size:,} bytes)</p>
                <p><strong>Agreement Generated:</strong> {'✅ Success' if agreement_size > 0 else '❌ Failed'} ({agreement_size:,} bytes)</p>
                <p><strong>POA ID:</strong> {poa_id}</p>
                <p><strong>Template Used:</strong> {test_form_data['developer_assigned']} + {test_form_data['utility_provider']} + {test_form_data['account_type']}</p>
            </div>
            
            <!-- STEP 2: Google Drive Integration -->
            <div style="background: {'#e8f5e8' if drive_success else '#ffe8e8'}; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>☁️ Step 2: Google Drive Integration</h3>
                <p><strong>Folder Creation:</strong> {'✅ Success' if drive_success else '❌ Failed'}</p>
                <p><strong>Folder Name:</strong> {folder_name}</p>
                {"<p><strong>Folder Link:</strong> <a href='" + drive_folder_link + "' target='_blank'>📁 Open in Drive</a></p>" if drive_success else f"<p><strong>Error:</strong> {drive_folder_link}</p>"}
            </div>
            
            <!-- STEP 3: File Uploads -->
            <div style="background: {'#e8f5e8' if upload_results.get('poa', {}).get('success') and upload_results.get('agreement', {}).get('success') else '#ffe8e8'}; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📤 Step 3: Document Uploads</h3>
                <p><strong>POA Upload:</strong> {'✅ Success' if upload_results.get('poa', {}).get('success') else '❌ Failed'}</p>
                {f"<p><strong>POA Link:</strong> <a href='{upload_results['poa']['link']}' target='_blank'>📄 View POA</a></p>" if upload_results.get('poa', {}).get('success') else f"<p><strong>POA Error:</strong> {upload_results.get('poa', {}).get('error', 'Unknown')}</p>"}
                
                <p><strong>Agreement Upload:</strong> {'✅ Success' if upload_results.get('agreement', {}).get('success') else '❌ Failed'}</p>
                {f"<p><strong>Agreement Link:</strong> <a href='{upload_results['agreement']['link']}' target='_blank'>📄 View Agreement</a></p>" if upload_results.get('agreement', {}).get('success') else f"<p><strong>Agreement Error:</strong> {upload_results.get('agreement', {}).get('error', 'Unknown')}</p>"}
            </div>
            
            <!-- STEP 4: Agent Lookup -->
            <div style="background: {'#e8f5e8' if agent_name != 'Unknown' else '#ffe8e8'}; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>🕵️ Step 4: Agent Lookup</h3>
                <p><strong>Agent ID:</strong> {test_form_data['agent_id']}</p>
                <p><strong>Agent Name:</strong> {agent_name}</p>
                <p><strong>Status:</strong> {'✅ Found in sheets' if agent_name != 'Unknown' else '❌ Not found'}</p>
            </div>
            
            <!-- STEP 5: System Details -->
            <div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>📊 Step 5: Test Configuration</h3>
                <p><strong>Customer:</strong> {test_form_data['contact_name']} ({test_form_data['account_name']})</p>
                <p><strong>Developer:</strong> {test_form_data['developer_assigned']}</p>
                <p><strong>Utility:</strong> {test_form_data['utility_provider']}</p>
                <p><strong>Account Type:</strong> {test_form_data['account_type']}</p>
                <p><strong>Annual Usage:</strong> {test_ocr_data['annual_usage']:,} kWh</p>
                <p><strong>Agent:</strong> {test_form_data['agent_id']} → {agent_name}</p>
            </div>
            
            <!-- STEP 6: Cleanup -->
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>🧹 Step 6: Cleanup</h3>
                {"<br>".join(cleanup_results)}
            </div>
            
            <!-- Navigation -->
            <div style="margin-top: 30px;">
                <button onclick="location.reload()" style="padding: 10px 20px; margin: 5px; background: #007bff; color: white; border: none; border-radius: 5px;">🔄 Run Test Again</button>
                <button onclick="location.href='/test-template-processing'" style="padding: 10px 20px; margin: 5px; background: #28a745; color: white; border: none; border-radius: 5px;">🧪 Template Test</button>
                <button onclick="location.href='/'" style="padding: 10px 20px; margin: 5px; background: #6c757d; color: white; border: none; border-radius: 5px;">🏠 Back to Form</button>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        return f'''
        <html>
        <head><title>End-to-End Test - Error</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>❌ End-to-End Test Failed</h2>
            
            <div style="background: #ffe8e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Error Details</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; font-size: 11px; white-space: pre-wrap;">{error_trace}</pre>
            </div>
            
            <button onclick="location.reload()" style="padding: 10px 20px; margin: 10px 5px;">Try Again</button>
            <button onclick="location.href='/'" style="padding: 10px 20px; margin: 10px 5px;">Back to Form</button>
        </body>
        </html>
        '''

@app.route('/test-pixel-perfect-poa', methods=['POST'])
def test_pixel_perfect_poa():
    """Test POA signature placement using pixel-perfect anchor system"""
    try:
        # Get JSON data
        json_data = request.get_json()
        
        form_data = {
            'business_entity': f"{json_data.get('contact_name')} Business Entity",
            'account_name': f"{json_data.get('contact_name')} Account",
            'contact_name': json_data.get('contact_name'),
            'title': json_data.get('title', 'Manager'),
            'phone': '555-123-4567',
            'email': json_data.get('email'),
            'service_addresses': '123 Test Street, Test City, NY 12345',
            'developer_assigned': json_data.get('developer_assigned', 'Meadow Energy'),
            'account_type': json_data.get('account_type', 'Small Demand <25 KW'),
            'utility_provider': json_data.get('utility_provider', 'National Grid'),
            'agent_id': 'TEST001',
            'poid': 'TEST123456'
        }
        
        # Create dummy OCR data
        ocr_data = {
            'utility_name': form_data['utility_provider'],
            'customer_name': json_data.get('contact_name', 'Pixel Perfect Customer'),
            'account_number': '123456789',
            'poid': 'TEST123456',
            'monthly_usage': '1000',
            'annual_usage': '12000',
            'service_address': '456 Maple Avenue, Rochester, NY 14614',
            'monthly_charge': '145.75',
            'annual_charge': '1749.00'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate POA using pixel-perfect anchor processor
        poa_pdf_path = generate_poa_pdf(form_data, ocr_data, timestamp)
        
        # Get POA ID that was generated
        poa_id = form_data.get('poa_id', 'N/A')
        
        # Get file info
        file_size = os.path.getsize(poa_pdf_path) if os.path.exists(poa_pdf_path) else 0
        
        # For demo, we can keep the file temporarily and provide download link
        # In production, you might upload to a temp area or clean up immediately
        
        response_data = {
            'success': True,
            'poa_id': poa_id,
            'file_size': file_size,
            'signature_page': 2,  # POA signatures are on page 2
            'test_type': 'POA Pixel-Perfect Test',
            'anchor_method': 'Anchor-based coordinate detection',
            'template_used': 'GreenWattUSA_Limited_Power_of_Attorney.pdf'
        }
        
        # Keep the test file for inspection (save to temp folder with descriptive name)
        sample_filename = f"temp/SAMPLE_POA_PixelPerfect_{timestamp}.pdf"
        if os.path.exists(poa_pdf_path):
            import shutil
            shutil.copy2(poa_pdf_path, sample_filename)
            os.remove(poa_pdf_path)  # Remove original, keep sample
            response_data['sample_file'] = sample_filename
            
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/test-pixel-perfect-agreement', methods=['POST'])
def test_pixel_perfect_agreement():
    """Test Agreement signature placement using pixel-perfect anchor system"""
    try:
        # Get JSON data
        json_data = request.get_json()
        
        form_data = {
            'business_entity': f"{json_data.get('contact_name')} Business Entity",
            'account_name': f"{json_data.get('contact_name')} Account",
            'contact_name': json_data.get('contact_name'),
            'title': json_data.get('title', 'Manager'),
            'phone': '555-123-4567',
            'email': json_data.get('email'),
            'service_addresses': '123 Test Street, Test City, NY 12345',
            'developer_assigned': json_data.get('developer_assigned', 'Meadow Energy'),
            'account_type': json_data.get('account_type', 'Small Demand <25 KW'),
            'utility_provider': json_data.get('utility_provider', 'National Grid'),
            'agent_id': 'TEST001',
            'poid': 'TEST123456'
        }
        
        # Create dummy OCR data
        ocr_data = {
            'utility_name': form_data['utility_provider'],
            'customer_name': json_data.get('contact_name', 'Agreement Test Customer'),
            'account_number': '123456789',
            'poid': 'TEST123456',
            'monthly_usage': '1000',
            'annual_usage': '12000',
            'service_address': '789 Pine Street, Syracuse, NY 13201',
            'monthly_charge': '165.25',
            'annual_charge': '1983.00'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate Agreement using pixel-perfect anchor processor
        agreement_pdf_path = generate_agreement_pdf(form_data, ocr_data, form_data['developer_assigned'], timestamp)
        
        # Get template name that was used
        from services.google_sheets_service import GoogleSheetsService
        sheets_service_local = GoogleSheetsService(
            SERVICE_ACCOUNT_INFO,
            os.getenv('GOOGLE_SHEETS_ID'),
            os.getenv('GOOGLE_AGENT_SHEETS_ID')
        )
        
        agreement_filename = sheets_service_local.get_developer_agreement(
            form_data['developer_assigned'], 
            form_data['utility_provider'], 
            form_data['account_type']
        )
        
        # Get file info
        file_size = os.path.getsize(agreement_pdf_path) if os.path.exists(agreement_pdf_path) else 0
        
        response_data = {
            'success': True,
            'template_used': agreement_filename or 'Default template',
            'file_size': file_size,
            'signature_page': '7-9',  # Agreement signatures are on pages 7-9
            'test_type': 'Agreement Pixel-Perfect Test',
            'anchor_method': 'Anchor-based coordinate detection',
            'developer': form_data['developer_assigned'],
            'utility': form_data['utility_provider'],
            'account_type': form_data['account_type']
        }
        
        # Keep the test file for inspection (save to temp folder with descriptive name)
        sample_filename = f"temp/SAMPLE_Agreement_PixelPerfect_{timestamp}.pdf"
        if os.path.exists(agreement_pdf_path):
            import shutil
            shutil.copy2(agreement_pdf_path, sample_filename)
            os.remove(agreement_pdf_path)  # Remove original, keep sample
            response_data['sample_file'] = sample_filename
            
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/test-pixel-perfect-full', methods=['POST'])
def test_pixel_perfect_full():
    """Full end-to-end test with pixel-perfect signatures and Google Drive upload"""
    try:
        # Get form data
        form_data = {
            'business_entity': f"{request.form.get('contact_name')} Business Entity",
            'account_name': f"{request.form.get('contact_name')} Account",
            'contact_name': request.form.get('contact_name'),
            'title': request.form.get('title', 'Manager'),
            'phone': '555-123-4567',
            'email': request.form.get('email'),
            'service_addresses': '123 Test Street, Test City, NY 12345',
            'developer_assigned': request.form.get('developer', 'Meadow Energy'),
            'account_type': request.form.get('account_type', 'Small Demand <25 KW'),
            'utility_provider': request.form.get('utility', 'National Grid'),
            'agent_id': 'TEST001',
            'poid': 'TEST123456'
        }
        
        # Create dummy OCR data
        ocr_data = {
            'utility_name': form_data['utility_provider'],
            'customer_name': request.form.get('contact_name', 'Full Test Customer'),
            'account_number': '123456789',
            'poid': 'TEST123456',
            'monthly_usage': '1000',
            'annual_usage': '12000',
            'service_address': '321 Elm Street, Albany, NY 12208',
            'monthly_charge': '155.90',
            'annual_charge': '1870.80'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        submission_date = datetime.now()
        
        # Generate PDFs using pixel-perfect anchor processor
        poa_pdf_path = generate_poa_pdf(form_data, ocr_data, timestamp)
        agreement_pdf_path = generate_agreement_pdf(form_data, ocr_data, form_data['developer_assigned'], timestamp)
        
        # Get POA ID that was generated
        poa_id = form_data.get('poa_id', 'N/A')
        
        # Create Google Drive folder
        folder_name = f"{submission_date.strftime('%Y-%m-%d')}_{form_data['account_name']}_{form_data['utility_provider']}_PIXEL_PERFECT_TEST"
        
        drive_folder_id = drive_service.create_folder(folder_name)
        drive_folder_link = f"https://drive.google.com/drive/folders/{drive_folder_id}"
        
        # Upload PDFs to Google Drive
        poa_pdf_id = drive_service.upload_file(poa_pdf_path, f"POA_{form_data['account_name']}_PixelPerfect.pdf", drive_folder_id)
        agreement_pdf_id = drive_service.upload_file(agreement_pdf_path, f"Agreement_{form_data['account_name']}_PixelPerfect.pdf", drive_folder_id)
        
        poa_link = f"https://drive.google.com/file/d/{poa_pdf_id}/view"
        agreement_link = f"https://drive.google.com/file/d/{agreement_pdf_id}/view"
        
        # Test agent lookup
        agent_name = sheets_service.get_agent_name(form_data['agent_id'])
        
        response_data = {
            'success': True,
            'poa_id': poa_id,
            'drive_folder': drive_folder_link,
            'poa_link': poa_link,
            'agreement_link': agreement_link,
            'agent_info': f"{form_data['agent_id']} → {agent_name}",
            'test_type': 'Full Pixel-Perfect End-to-End Test',
            'timestamp': timestamp,
            'folder_name': folder_name
        }
        
        # Clean up local test files
        if os.path.exists(poa_pdf_path):
            os.remove(poa_pdf_path)
        if os.path.exists(agreement_pdf_path):
            os.remove(agreement_pdf_path)
            
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def process_submission_background(session_id, form_data, file_path):
    """Background processing function with progress tracking"""
    try:
        update_progress(session_id, 1, "Uploading Document", "Saving your utility bill securely")
        
        # OCR Processing
        update_progress(session_id, 2, "OCR Analysis", "Reading text from your utility bill")
        ocr_data = process_utility_bill(file_path, SERVICE_ACCOUNT_INFO)
        
        # AI Processing
        update_progress(session_id, 3, "AI Processing", "Extracting account information")
        time.sleep(0.5)  # Allow progress update to be visible
        
        submission_date = datetime.now()
        folder_name = f"{submission_date.strftime('%Y-%m-%d')}_{form_data['account_name']}_{form_data['utility_provider']}"
        
        # Generate Documents
        update_progress(session_id, 4, "Generating Documents", "Creating your POA and agreement")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        poa_pdf_path = generate_poa_pdf(form_data, ocr_data, timestamp)
        agreement_pdf_path = generate_agreement_pdf(form_data, ocr_data, form_data['developer_assigned'], timestamp)
        
        # Cloud Storage
        update_progress(session_id, 5, "Cloud Storage", "Saving to Google Drive")
        drive_folder_id = drive_service.create_folder(folder_name)
        
        utility_bill_id = drive_service.upload_file(file_path, f"utility_bill_{timestamp}.pdf", drive_folder_id)
        poa_id = drive_service.upload_file(poa_pdf_path, f"poa_{timestamp}.pdf", drive_folder_id)
        agreement_id = drive_service.upload_file(agreement_pdf_path, f"agreement_{timestamp}.pdf", drive_folder_id)
        
        # Generate public links
        utility_bill_link = drive_service.get_file_link(utility_bill_id)
        poa_link = drive_service.get_file_link(poa_id)
        agreement_link = drive_service.get_file_link(agreement_id)
        
        # Logging Data
        update_progress(session_id, 6, "Logging Data", "Recording submission details")
        
        # Get agent name and other data
        agent_name = sheets_service.get_agent_name(form_data['agent_id'])
        utility_name_final = ocr_data.get('utility_name', form_data['utility_provider'])
        unique_id = generate_unique_id()
        poa_id_generated = f"POA-{timestamp}-{unique_id.split('-')[-1]}"
        
        sheet_data = [
            unique_id,                       # Unique submission ID (A)
            submission_date.strftime('%Y-%m-%d %H:%M:%S'),  # Submission Date (B)
            form_data['business_entity'],    # Business Entity Name (C)
            form_data['account_name'],       # Account Name (D)
            form_data['contact_name'],       # Contact Name (E)
            form_data['title'],              # Title (F)
            form_data['phone'],              # Phone (G)
            form_data['email'],              # Email (H)
            form_data['service_addresses'],  # Service Address (I)
            form_data['developer_assigned'], # Developer Assigned (J)
            form_data['account_type'],       # Account Type (K)
            form_data['utility_provider'],  # Utility Provider (Form) (L)
            utility_name_final,             # Utility Name (OCR) (M)
            ocr_data.get('account_number', ''),  # Account Number (OCR) (N)
            form_data.get('poid', ''),       # POID (Form) (O) - NEW
            ocr_data.get('poid', ''),        # POID (OCR) (P) - MOVED from O
            ocr_data.get('monthly_usage', ''),   # Monthly Usage (OCR) (Q)
            ocr_data.get('annual_usage', ''),    # Annual Usage (OCR) (R)
            form_data['agent_id'],           # Agent ID (S)
            agent_name,                      # Agent Name (T)
            ocr_data.get('service_address', ''),  # Service Address (OCR) (U) - NEW
            poa_id_generated,                # POA ID (V)
            utility_bill_link,              # Utility Bill Link (W)
            poa_link,                        # POA Link (X)
            agreement_link,                  # Agreement Link (Y)
            ocr_data.get('monthly_charge', ''),   # Monthly Charge (OCR) (Z) - NEW
            ocr_data.get('annual_charge', '')     # Annual Charge (OCR) (AA) - NEW
        ]
        
        try:
            result = sheets_service.append_row(sheet_data)
        except Exception as e:
            print(f"Sheet insertion failed: {e}")
        
        # Notifications
        update_progress(session_id, 7, "Notifications", "Sending confirmations")
        
        # Send email notification to internal team
        from services.email_service import send_notification_email
        send_notification_email(
            agent_name=agent_name,
            customer_name=form_data['account_name'],
            utility=form_data['utility_provider'],
            signed_date=submission_date.strftime('%Y-%m-%d'),
            annual_usage=ocr_data.get('annual_usage', 'N/A')
        )
        
        # Send SMS verification to customer
        try:
            sms_response = sms_service.send_customer_verification_sms(
                customer_phone=form_data['phone'],
                customer_name=form_data['contact_name']
            )
            print(f"SMS sent: {sms_response}")
        except Exception as sms_error:
            print(f"SMS failed: {sms_error}")
            
        # Send SMS notification to internal team
        try:
            internal_sms_data = {
                'customer_name': form_data['account_name'],
                'agent_name': agent_name,
                'utility': form_data['utility_provider'],
                'annual_usage': ocr_data.get('annual_usage', 'N/A'),
                'submission_date': submission_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            internal_sms_results = sms_service.send_internal_notification_sms(internal_sms_data)
            print(f"📱 Internal SMS notifications: {len([r for r in internal_sms_results if r.get('success') if r]) if internal_sms_results else 0} sent successfully")
            
        except Exception as e:
            print(f"⚠️  Error sending internal SMS notifications: {e}")
        
        # Store result data in session for retrieval
        progress_sessions[session_id]['result'] = {
            'drive_folder': f"https://drive.google.com/drive/folders/{drive_folder_id}",
            'documents': {
                'utility_bill': utility_bill_link,
                'poa': poa_link,
                'agreement': agreement_link
            }
        }
        
        # Clean up temporary files
        os.remove(file_path)
        os.remove(poa_pdf_path)
        os.remove(agreement_pdf_path)
        
        # Complete successfully
        complete_progress(session_id, success=True)
        
    except Exception as e:
        print(f"Background processing error: {e}")
        import traceback
        traceback.print_exc()
        complete_progress(session_id, success=False, error=str(e))

@app.route('/submit', methods=['POST'])
def submit_form():
    """Modified submit endpoint to use background processing with real-time progress tracking"""
    try:
        form_data = {
            'business_entity': request.form.get('business_entity', ''),
            'account_name': request.form.get('account_name'),
            'contact_name': request.form.get('contact_name'),
            'title': request.form.get('title'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'service_addresses': request.form.get('service_addresses'),
            'developer_assigned': request.form.get('developer_assigned'),
            'account_type': request.form.get('account_type'),
            'utility_provider': request.form.get('utility_provider'),
            'poid': request.form.get('poid', ''),
            'agent_id': request.form.get('agent_id'),
            'poa_agreement': request.form.get('poa_agreement') == 'on'
        }
        
        if not form_data['poa_agreement']:
            return jsonify({'error': 'POA agreement must be accepted'}), 400
        
        # Get the utility bill file
        if 'utility_bill' not in request.files:
            return jsonify({'error': 'No utility bill uploaded'}), 400
        
        file = request.files['utility_bill']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Save file for background processing
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Create progress session
        session_id = create_progress_session()
        
        # Start background processing thread
        import threading
        thread = threading.Thread(
            target=process_submission_background,
            args=(session_id, form_data, filepath)
        )
        thread.daemon = True
        thread.start()
        
        # Return session ID for progress tracking
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Processing started - track progress with session ID'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-sendgrid-email-verification', methods=['GET', 'POST'])
def test_sendgrid_email_verification():
    """Test email with specific data to verify both recipients receive it"""
    if request.method == 'GET':
        return '''
        <html>
        <head><title>SendGrid Email Verification Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📧 SendGrid Email Verification Test</h2>
            <p>This will send a test email to both <strong>greenwatt.intake@gmail.com</strong> and <strong>pat@persimmons.studio</strong></p>
            
            <form method="POST">
                <div style="margin: 10px 0;">
                    <label>Agent Name:</label><br>
                    <input type="text" name="agent_name" value="John Smith (TEST)" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Customer Name:</label><br>
                    <input type="text" name="customer_name" value="Sarah Wilson (TEST)" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Utility:</label><br>
                    <input type="text" name="utility" value="National Grid" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Annual Usage (kWh):</label><br>
                    <input type="number" name="annual_usage" value="15000" style="padding: 8px; width: 300px;">
                </div>
                <button type="submit" style="padding: 10px 20px; background: #2c5530; color: white; border: none; border-radius: 4px;">
                    📧 Send Verification Email
                </button>
            </form>
        </body>
        </html>
        '''
    
    try:
        from services.email_service import send_notification_email
        from datetime import datetime
        
        # Get form data
        agent_name = request.form.get('agent_name', 'Test Agent')
        customer_name = request.form.get('customer_name', 'Test Customer')
        utility = request.form.get('utility', 'National Grid')
        annual_usage = int(request.form.get('annual_usage', 15000))
        signed_date = datetime.now().strftime('%m/%d/%Y')
        
        # Send test email to both recipients
        result = send_notification_email(
            agent_name=agent_name,
            customer_name=customer_name,
            utility=utility,
            signed_date=signed_date,
            annual_usage=annual_usage
        )
        
        if result:
            return f'''
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <h2>✅ Email Verification Test Successful!</h2>
                <p><strong>TEST EMAIL SENT TO BOTH RECIPIENTS!</strong></p>
                <div style="background: #f0f8f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>📧 Email Details:</h3>
                    <strong>Recipients:</strong><br>
                    • greenwatt.intake@gmail.com<br>
                    • pat@persimmons.studio<br><br>
                    
                    <strong>Test Data Sent:</strong><br>
                    • Agent Name: {agent_name}<br>
                    • Customer Name: {customer_name}<br>
                    • Utility: {utility}<br>
                    • Signed Date: {signed_date}<br>
                    • Annual Usage: {annual_usage:,} kWh<br>
                </div>
                <p>📧 Check both email inboxes for the professional GreenWatt notification email.</p>
                <a href="/test-sendgrid-email-verification">← Send Another Test</a>
            </body>
            </html>
            '''
        else:
            return f'''
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <h2>❌ Email Verification Test Failed</h2>
                <p>SendGrid email could not be sent. Check console logs for details.</p>
                <p>Possible issues:</p>
                <ul>
                    <li>SENDGRID_API_KEY not configured</li>
                    <li>Invalid API key</li>
                    <li>Network connectivity</li>
                    <li>SendGrid account issues</li>
                </ul>
                <a href="/test-sendgrid-email-verification">← Try Again</a>
            </body>
            </html>
            '''
    
    except Exception as e:
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>💥 Email Verification Test Error</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/test-sendgrid-email-verification">← Try Again</a>
        </body>
        </html>
        '''

@app.route('/test-sendgrid-email', methods=['GET', 'POST'])
def test_sendgrid_email():
    """Test endpoint for SendGrid email functionality"""
    if request.method == 'GET':
        return '''
        <html>
        <head><title>SendGrid Email Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📧 SendGrid Email Test</h2>
            <p>Test the new SendGrid email notification system with sample data.</p>
            
            <form method="POST">
                <div style="margin: 10px 0;">
                    <label>Agent Name:</label><br>
                    <input type="text" name="agent_name" value="John Smith" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Customer Name:</label><br>
                    <input type="text" name="customer_name" value="Sarah Wilson" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Utility:</label><br>
                    <input type="text" name="utility" value="National Grid" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Annual Usage (kWh):</label><br>
                    <input type="number" name="annual_usage" value="12500" style="padding: 8px; width: 300px;">
                </div>
                <button type="submit" style="padding: 10px 20px; background: #2c5530; color: white; border: none; border-radius: 4px;">
                    🚀 Send Test Email
                </button>
            </form>
        </body>
        </html>
        '''
    
    try:
        from services.email_service import send_notification_email
        from datetime import datetime
        
        # Get form data or use defaults
        agent_name = request.form.get('agent_name', 'Test Agent')
        customer_name = request.form.get('customer_name', 'Test Customer')
        utility = request.form.get('utility', 'National Grid')
        annual_usage = int(request.form.get('annual_usage', 12500))
        signed_date = datetime.now().strftime('%m/%d/%Y')
        
        # Send test email
        result = send_notification_email(
            agent_name=agent_name,
            customer_name=customer_name,
            utility=utility,
            signed_date=signed_date,
            annual_usage=annual_usage
        )
        
        if result:
            return f'''
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <h2>✅ Email Test Successful!</h2>
                <p><strong>SendGrid email sent successfully!</strong></p>
                <div style="background: #f0f8f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>Test Data:</strong><br>
                    Agent: {agent_name}<br>
                    Customer: {customer_name}<br>
                    Utility: {utility}<br>
                    Usage: {annual_usage:,} kWh<br>
                    Date: {signed_date}
                </div>
                <p>📧 Check the recipient inboxes for the professional email notification.</p>
                <a href="/test-sendgrid-email">← Send Another Test</a>
            </body>
            </html>
            '''
        else:
            return f'''
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <h2>❌ Email Test Failed</h2>
                <p>SendGrid email could not be sent. Check console logs for details.</p>
                <p>Possible issues:</p>
                <ul>
                    <li>SENDGRID_API_KEY not configured</li>
                    <li>Invalid API key</li>
                    <li>Network connectivity</li>
                </ul>
                <a href="/test-sendgrid-email">← Try Again</a>
            </body>
            </html>
            '''
    
    except Exception as e:
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>💥 Email Test Error</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/test-sendgrid-email">← Try Again</a>
        </body>
        </html>
        '''

@app.route('/test-sms-sending', methods=['GET', 'POST'])
def test_sms_sending():
    """Test endpoint for Twilio SMS sending functionality"""
    if request.method == 'GET':
        return '''
        <html>
        <head><title>Twilio SMS Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📱 Twilio SMS Test</h2>
            <p>Test customer verification SMS and internal team notifications.</p>
            
            <form method="POST">
                <div style="margin: 10px 0;">
                    <label>Customer Name:</label><br>
                    <input type="text" name="customer_name" value="Sarah Wilson (TEST)" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Customer Phone:</label><br>
                    <input type="text" name="customer_phone" value="+15551234567" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Agent Name:</label><br>
                    <input type="text" name="agent_name" value="John Smith (TEST)" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Utility:</label><br>
                    <input type="text" name="utility" value="National Grid" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Annual Usage (kWh):</label><br>
                    <input type="number" name="annual_usage" value="15000" style="padding: 8px; width: 300px;">
                </div>
                <button type="submit" name="test_type" value="customer" style="padding: 10px 20px; background: #2c5530; color: white; border: none; border-radius: 4px; margin: 5px;">
                    📱 Test Customer SMS
                </button>
                <button type="submit" name="test_type" value="internal" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px; margin: 5px;">
                    📱 Test Internal SMS
                </button>
                <button type="submit" name="test_type" value="both" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; margin: 5px;">
                    📱 Test Both SMS
                </button>
            </form>
        </body>
        </html>
        '''
    
    try:
        # Get form data
        customer_name = request.form.get('customer_name', 'Test Customer')
        customer_phone = request.form.get('customer_phone', '+15551234567')
        agent_name = request.form.get('agent_name', 'Test Agent')
        utility = request.form.get('utility', 'National Grid')
        annual_usage = int(request.form.get('annual_usage', 15000))
        test_type = request.form.get('test_type', 'both')
        
        results = {}
        
        # Test customer verification SMS
        if test_type in ['customer', 'both']:
            try:
                customer_result = sms_service.send_customer_verification_sms(
                    customer_phone=customer_phone,
                    customer_name=customer_name
                )
                results['customer_sms'] = customer_result
            except Exception as e:
                results['customer_sms'] = {'success': False, 'error': str(e)}
        
        # Test internal team notifications
        if test_type in ['internal', 'both']:
            try:
                internal_data = {
                    'customer_name': customer_name,
                    'agent_name': agent_name,
                    'utility': utility,
                    'annual_usage': annual_usage,
                    'submission_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                internal_results = sms_service.send_internal_notification_sms(internal_data)
                results['internal_sms'] = internal_results
            except Exception as e:
                results['internal_sms'] = [{'success': False, 'error': str(e)}]
        
        # Generate results HTML
        results_html = '<h3>📱 SMS Test Results:</h3>'
        
        if 'customer_sms' in results:
            customer_result = results['customer_sms']
            if customer_result and customer_result.get('success'):
                results_html += f'''
                <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h4>✅ Customer SMS Sent Successfully</h4>
                    <strong>Phone:</strong> {customer_result.get('phone', 'N/A')}<br>
                    <strong>Message SID:</strong> {customer_result.get('message_sid', 'N/A')}<br>
                    <strong>Timestamp:</strong> {customer_result.get('timestamp', 'N/A')}
                </div>
                '''
            else:
                error_msg = customer_result.get('error', 'Unknown error') if customer_result else 'SMS service not configured'
                results_html += f'''
                <div style="background: #ffe8e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h4>❌ Customer SMS Failed</h4>
                    <strong>Error:</strong> {error_msg}
                </div>
                '''
        
        if 'internal_sms' in results:
            internal_results = results['internal_sms']
            if internal_results:
                successful_count = len([r for r in internal_results if r.get('success')])
                results_html += f'''
                <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h4>📱 Internal SMS Results</h4>
                    <strong>Success Count:</strong> {successful_count}/{len(internal_results)}<br>
                '''
                
                for i, result in enumerate(internal_results):
                    status = "✅" if result.get('success') else "❌"
                    phone = result.get('phone', 'N/A')
                    if result.get('success'):
                        results_html += f"    {status} {phone} - SID: {result.get('message_sid', 'N/A')}<br>"
                    else:
                        results_html += f"    {status} {phone} - Error: {result.get('error', 'N/A')}<br>"
                
                results_html += '</div>'
            else:
                results_html += '''
                <div style="background: #ffe8e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h4>❌ Internal SMS Failed</h4>
                    <strong>Error:</strong> No internal numbers configured or SMS service unavailable
                </div>
                '''
        
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📱 Twilio SMS Test Results</h2>
            {results_html}
            <div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4>📊 Test Configuration</h4>
                <strong>Customer:</strong> {customer_name} ({customer_phone})<br>
                <strong>Agent:</strong> {agent_name}<br>
                <strong>Utility:</strong> {utility}<br>
                <strong>Usage:</strong> {annual_usage:,} kWh<br>
                <strong>Test Type:</strong> {test_type}
            </div>
            <a href="/test-sms-sending">← Test Again</a>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>❌ SMS Test Error</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/test-sms-sending">← Try Again</a>
        </body>
        </html>
        '''

@app.route('/sms-webhook', methods=['POST'])
def sms_webhook():
    """
    Twilio webhook endpoint for handling incoming SMS responses.
    This endpoint receives customer Y/N responses to verification messages.
    """
    try:
        # Get Twilio signature for validation
        twilio_signature = request.headers.get('X-Twilio-Signature', '')
        request_url = request.url
        
        # Get POST parameters as dict
        post_params = request.form.to_dict()
        
        # Validate the request is from Twilio (security)
        is_valid = sms_service.validate_webhook_signature(
            request_url, 
            post_params, 
            twilio_signature
        )
        
        if not is_valid:
            print("❌ Invalid Twilio webhook signature - rejecting request")
            return "Forbidden", 403
        
        # Process the SMS response
        response_data = sms_service.process_webhook_response(post_params)
        
        if response_data.get('status') == 'error':
            print(f"❌ Error processing SMS webhook: {response_data.get('error')}")
            return "Internal Server Error", 500
        
        # Log the response to Google Sheets
        try:
            # Find the submission row that matches this phone number
            customer_phone = response_data['phone_number']
            parsed_response = response_data['parsed_response'] 
            message_sid = response_data['message_sid']
            timestamp = response_data['timestamp']
            
            # Update Google Sheets with SMS response data
            # Note: This would require enhancing Google Sheets service to support SMS response columns
            print(f"📊 SMS Response to log: {customer_phone} → {parsed_response}")
            print(f"    Message SID: {message_sid}")
            print(f"    Timestamp: {timestamp}")
            
            # TODO: Implement sheets_service.log_sms_response() method
            
        except Exception as e:
            print(f"⚠️  Error logging SMS response to sheets: {e}")
            # Don't fail the webhook even if logging fails
        
        # Respond to Twilio with TwiML (optional auto-reply)
        from twilio.twiml.messaging_response import MessagingResponse
        
        twiml_response = MessagingResponse()
        
        # Send confirmation message based on customer response
        if response_data['parsed_response'] == 'Y':
            twiml_response.message("✅ Thank you for confirming your participation in GreenWatt's Community Solar program! We'll be in touch soon.")
        elif response_data['parsed_response'] == 'N':
            twiml_response.message("Thank you for your response. You have opted out of the Community Solar program. Have a great day!")
        else:
            twiml_response.message("We didn't understand your response. Please reply with Y to confirm participation or N to opt out.")
        
        print(f"📱 Auto-reply sent to {customer_phone}")
        
        return str(twiml_response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        print(f"❌ SMS webhook error: {e}")
        import traceback
        traceback.print_exc()
        return "Internal Server Error", 500

@app.route('/test-ocr', methods=['GET', 'POST'])
def test_ocr():
    """Simple OCR test page - upload PDF and see extraction results"""
    if request.method == 'GET':
        return '''
        <html>
        <head>
            <title>Google Vision OCR Test</title>
            <style>
                body { font-family: Arial; padding: 20px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
                .upload-area { 
                    border: 2px dashed #ccc; 
                    padding: 60px; 
                    text-align: center; 
                    margin: 20px 0; 
                    border-radius: 8px; 
                    transition: all 0.3s ease;
                    background: #fafafa;
                    cursor: pointer;
                }
                .upload-area:hover { border-color: #2c5530; background: #f0f8f0; }
                .upload-area.dragover { border-color: #2c5530; background: #e8f5e8; border-style: solid; }
                .upload-icon { font-size: 48px; margin-bottom: 20px; color: #666; }
                .upload-text { font-size: 18px; color: #333; margin-bottom: 10px; }
                .upload-subtext { color: #666; font-size: 14px; }
                .file-input { display: none; }
                .btn { padding: 12px 24px; background: #2c5530; color: white; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }
                .btn:hover { background: #1e3d24; }
                .btn:disabled { background: #ccc; cursor: not-allowed; }
                .file-info { margin-top: 15px; padding: 10px; background: #e8f5e8; border-radius: 4px; display: none; }
                .processing { color: #2c5530; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🔍 Google Vision OCR Test</h2>
                <p>Drag and drop a utility bill or click to browse. Supports PDF, JPG, and PNG files.</p>
                
                <form id="uploadForm" method="POST" enctype="multipart/form-data">
                    <div class="upload-area" id="uploadArea">
                        <div class="upload-icon">📄</div>
                        <div class="upload-text">Drag & drop your utility bill here</div>
                        <div class="upload-subtext">or <strong>click to browse</strong></div>
                        <div class="upload-subtext" style="margin-top: 10px;">Supports PDF, JPG, PNG (max 16MB)</div>
                        <input type="file" name="utility_bill" id="fileInput" class="file-input" accept=".pdf,.jpg,.jpeg,.png" required>
                    </div>
                    <div id="fileInfo" class="file-info"></div>
                    <button type="submit" class="btn" id="submitBtn">🚀 Test OCR Extraction</button>
                </form>
            </div>
            
            <script>
                const uploadArea = document.getElementById('uploadArea');
                const fileInput = document.getElementById('fileInput');
                const fileInfo = document.getElementById('fileInfo');
                const submitBtn = document.getElementById('submitBtn');
                const uploadForm = document.getElementById('uploadForm');
                
                // Click to upload
                uploadArea.addEventListener('click', () => fileInput.click());
                
                // Drag and drop functionality
                uploadArea.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    uploadArea.classList.add('dragover');
                });
                
                uploadArea.addEventListener('dragleave', (e) => {
                    e.preventDefault();
                    uploadArea.classList.remove('dragover');
                });
                
                uploadArea.addEventListener('drop', (e) => {
                    e.preventDefault();
                    uploadArea.classList.remove('dragover');
                    
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        fileInput.files = files;
                        updateFileInfo(files[0]);
                    }
                });
                
                // File input change
                fileInput.addEventListener('change', (e) => {
                    if (e.target.files.length > 0) {
                        updateFileInfo(e.target.files[0]);
                    }
                });
                
                function updateFileInfo(file) {
                    const maxSize = 16 * 1024 * 1024; // 16MB
                    const allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png'];
                    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
                    
                    if (file.size > maxSize) {
                        fileInfo.innerHTML = '❌ File too large (max 16MB)';
                        fileInfo.style.background = '#ffe8e8';
                        submitBtn.disabled = true;
                    } else if (!allowedTypes.includes(fileExt)) {
                        fileInfo.innerHTML = '❌ Invalid file type (PDF, JPG, PNG only)';
                        fileInfo.style.background = '#ffe8e8';
                        submitBtn.disabled = true;
                    } else {
                        fileInfo.innerHTML = `✅ Ready: ${file.name} (${(file.size/1024/1024).toFixed(1)}MB)`;
                        fileInfo.style.background = '#e8f5e8';
                        submitBtn.disabled = false;
                    }
                    fileInfo.style.display = 'block';
                }
                
                // Form submission
                uploadForm.addEventListener('submit', (e) => {
                    submitBtn.innerHTML = '⏳ Processing OCR...';
                    submitBtn.disabled = true;
                });
            </script>
        </body>
        </html>
        '''
    
    try:
        print(f"🔍 DEBUG: POST request received with files: {list(request.files.keys())}")
        
        # Get the utility bill file
        if 'utility_bill' not in request.files:
            print(f"🔍 DEBUG: No 'utility_bill' in request.files")
            return "No file uploaded", 400
        
        file = request.files['utility_bill']
        if file.filename == '':
            print(f"🔍 DEBUG: Empty filename")
            return "No file selected", 400
        
        print(f"🔍 DEBUG: File object: {file}")
        print(f"🔍 DEBUG: Filename: '{file.filename}'")
        
        if not allowed_file(file.filename):
            print(f"🔍 DEBUG: File type not allowed for: {file.filename}")
            return "Invalid file type", 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ocr_test_{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process with Google Vision OCR
        print(f"🔍 OCR TEST: Processing file: {filepath}")
        print(f"🔍 OCR TEST: File size: {os.path.getsize(filepath)} bytes")
        print(f"🔍 OCR TEST: Filename: {filename}")
        
        from services.ocr_service import process_utility_bill
        print(f"🔍 OCR TEST: Starting OCR processing...")
        
        ocr_data = process_utility_bill(filepath, SERVICE_ACCOUNT_INFO)
        
        print(f"🔍 OCR TEST: OCR processing complete")
        print(f"🔍 OCR TEST: Result: {ocr_data}")
        
        # Clean up test file
        os.remove(filepath)
        
        # Display results
        return f'''
        <html>
        <head>
            <title>OCR Test Results</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
                .results {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px; }}
                .field {{ margin: 10px 0; padding: 15px; background: white; border-radius: 4px; border-left: 4px solid #2c5530; }}
                .field strong {{ color: #2c5530; display: block; margin-bottom: 5px; }}
                .field .value {{ font-size: 16px; color: #333; }}
                .btn {{ padding: 12px 24px; background: #2c5530; color: white; border: none; border-radius: 4px; text-decoration: none; display: inline-block; }}
                .raw-text {{ background: #f1f1f1; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✅ OCR Test Results</h2>
                <p><strong>File processed:</strong> {file.filename}</p>
                
                <div class="results">
                    <h3>📊 Extracted Data:</h3>
                    
                    <div class="field">
                        <strong>Utility Provider:</strong>
                        <div class="value">{ocr_data.get('utility_name', 'Not detected')}</div>
                    </div>
                    
                    <div class="field">
                        <strong>Customer Name:</strong>
                        <div class="value">{ocr_data.get('customer_name', 'Not detected')}</div>
                    </div>
                    
                    <div class="field">
                        <strong>Account Number:</strong>
                        <div class="value">{ocr_data.get('account_number', 'Not detected')}</div>
                    </div>
                    
                    <div class="field">
                        <strong>Monthly Usage (kWh):</strong>
                        <div class="value">{ocr_data.get('monthly_usage', 'Not detected')}</div>
                    </div>
                    
                    <div class="field">
                        <strong>Annual Usage (kWh):</strong>
                        <div class="value">{ocr_data.get('annual_usage', 'Not detected')}</div>
                    </div>
                    
                    <div class="field">
                        <strong>POID:</strong>
                        <div class="value">{ocr_data.get('poid', 'Not detected')}</div>
                    </div>
                </div>
                
                <a href="/test-ocr" class="btn">🔄 Test Another File</a>
                <a href="/" class="btn" style="background: #6c757d;">🏠 Back to Main</a>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        # Clean up test file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
            
        return f'''
        <html>
        <head>
            <title>OCR Processing Failed</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
                .error {{ background: #ffe8e8; padding: 20px; border-radius: 8px; border-left: 4px solid #dc3545; }}
                .btn {{ padding: 12px 24px; background: #2c5530; color: white; border: none; border-radius: 4px; text-decoration: none; display: inline-block; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>❌ OCR Processing Failed</h2>
                <div class="error">
                    <h3>Unable to process utility bill</h3>
                    <p><strong>Reason:</strong> {str(e)}</p>
                    <p>This could be due to:</p>
                    <ul>
                        <li>Poor image quality or low resolution</li>
                        <li>Unsupported utility bill format</li>
                        <li>Service connectivity issues</li>
                        <li>File corruption or invalid format</li>
                    </ul>
                    <p><strong>Suggestions:</strong></p>
                    <ul>
                        <li>Try a clearer, higher-resolution image</li>
                        <li>Ensure the bill is from a supported utility company</li>
                        <li>Check that the file is a valid PDF, JPG, or PNG</li>
                    </ul>
                </div>
                <a href="/test-ocr" class="btn">🔄 Try Another File</a>
                <a href="/" class="btn" style="background: #6c757d;">🏠 Back to Main</a>
            </div>
        </body>
        </html>
        '''

@app.route('/test-sms-webhook', methods=['GET', 'POST'])
def test_sms_webhook():
    """Test endpoint to simulate Twilio webhook for development"""
    if request.method == 'GET':
        return '''
        <html>
        <head><title>SMS Webhook Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📱 SMS Webhook Test</h2>
            <p>Simulate a Twilio webhook request to test SMS response handling.</p>
            
            <form method="POST">
                <div style="margin: 10px 0;">
                    <label>Customer Phone:</label><br>
                    <input type="text" name="From" value="+15551234567" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Message Body:</label><br>
                    <input type="text" name="Body" value="Y" style="padding: 8px; width: 300px;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Message SID:</label><br>
                    <input type="text" name="MessageSid" value="SM1234567890abcdef" style="padding: 8px; width: 300px;">
                </div>
                <button type="submit" style="padding: 10px 20px; background: #2c5530; color: white; border: none; border-radius: 4px;">
                    📱 Test SMS Webhook
                </button>
            </form>
        </body>
        </html>
        '''
    
    try:
        # Process as if it's a real webhook (but skip signature validation)
        post_params = request.form.to_dict()
        response_data = sms_service.process_webhook_response(post_params)
        
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📱 SMS Webhook Test Results</h2>
            <div style="background: #f0f8f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>📨 Processed Response:</h3>
                <strong>Phone:</strong> {response_data.get('phone_number', 'N/A')}<br>
                <strong>Message:</strong> {response_data.get('message_body', 'N/A')}<br>
                <strong>Parsed:</strong> {response_data.get('parsed_response', 'N/A')}<br>
                <strong>SID:</strong> {response_data.get('message_sid', 'N/A')}<br>
                <strong>Timestamp:</strong> {response_data.get('timestamp', 'N/A')}<br>
            </div>
            <a href="/test-sms-webhook">← Test Another</a>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>❌ SMS Webhook Test Error</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/test-sms-webhook">← Try Again</a>
        </body>
        </html>
        '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)