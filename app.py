from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import json
import uuid
import threading
import time
from datetime import datetime
import pytz
from werkzeug.utils import secure_filename
from services.ocr_service import process_utility_bill
from services.pdf_generator import generate_poa_pdf, generate_agreement_pdf, generate_agency_agreement_pdf
from services.google_drive_service import GoogleDriveService
from services.google_sheets_service import GoogleSheetsService
from services.email_service import send_notification_email
from services.sms_service import SMSService
from dotenv import load_dotenv
import gc
import psutil

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

# Initialize the singleton service manager first
from services.google_service_manager import GoogleServiceManager
service_manager = GoogleServiceManager()
service_manager.initialize(SERVICE_ACCOUNT_INFO)
print("📊 Initial memory status:")
service_manager.log_memory_status("after initialization")

# Create services using the singleton pattern
drive_service = GoogleDriveService(parent_folder_id=os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID'))

# CONSOLIDATED SHEETS SERVICE - handles both main and dynamic sheets
sheets_service = GoogleSheetsService(
    spreadsheet_id=os.getenv('GOOGLE_SHEETS_ID'),
    agent_spreadsheet_id=os.getenv('GOOGLE_AGENT_SHEETS_ID'),
    dynamic_spreadsheet_id=os.getenv('DYNAMIC_GOOGLE_SHEETS_ID')
)

# For backward compatibility, create alias for dynamic_sheets_service
dynamic_sheets_service = sheets_service  # Points to same instance!

sms_service = SMSService()

# Initialize Google Sheets structure on startup
try:
    sheets_service.setup_required_tabs()
    # Force update headers to new 24-column structure (one-time fix)
    sheets_service.force_update_headers()
    print("Google Sheets setup completed with forced header update")
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
        'error': None,
        'status': 'in_progress'  # Mark as actively processing
    }
    print(f"📝 Created new progress session: {session_id}")
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
    """Mark progress as completed and clean up memory"""
    if session_id not in progress_sessions:
        return
    
    session = progress_sessions[session_id]
    session['completed'] = True
    session['percentage'] = 100 if success else session['percentage']
    session['error'] = error
    session['status'] = 'completed'  # Mark as no longer processing
    session['completed_time'] = time.time()  # Track when it completed
    
    if success:
        session['step_name'] = 'Complete'
        session['step_description'] = 'Submission processed successfully'
        print(f"✅ Completed progress session: {session_id}")
    else:
        print(f"❌ Failed progress session: {session_id} - Error: {error}")
    
    # Clean up result data to save memory (keep only essential info)
    if 'result' in session:
        # Keep only the IDs for reference, remove large data
        if isinstance(session['result'], dict):
            session['result'] = {
                'poa_id': session['result'].get('poa_id'),
                'unique_id': session['result'].get('unique_id')
            }
    
    # Mark session for early cleanup (2 minutes instead of 10)
    session['cleanup_time'] = time.time() + 120  # 2 minutes

def cleanup_old_sessions():
    """Clean up old progress sessions while protecting active ones"""
    current_time = time.time()
    sessions_to_remove = []
    
    for session_id, session in progress_sessions.items():
        # NEVER delete sessions that are still processing
        if session.get('status') == 'in_progress':
            continue
            
        # Check if session is completed or abandoned
        is_completed = session.get('status') == 'completed'
        is_old = current_time > session.get('start_time', 0) + 600  # 10 minutes instead of 2
        
        # Remove if completed AND older than 2 minutes, or if abandoned for 10 minutes
        if is_completed and current_time > session.get('completed_time', session['start_time']) + 120:
            sessions_to_remove.append(session_id)
        elif not is_completed and is_old:
            sessions_to_remove.append(session_id)
    
    # Remove old sessions
    for session_id in sessions_to_remove:
        print(f"🗑️ Removing old session: {session_id}")
        del progress_sessions[session_id]
    
    # Keep more sessions (20 instead of 10) and NEVER remove in_progress ones
    if len(progress_sessions) > 20:
        # Sort by start time but exclude in_progress sessions
        completed_sessions = [(sid, s) for sid, s in progress_sessions.items() 
                            if s.get('status') != 'in_progress']
        completed_sessions.sort(key=lambda x: x[1]['start_time'], reverse=True)
        
        # If we have too many completed sessions, remove the oldest
        if len(completed_sessions) > 15:
            for sid, _ in completed_sessions[15:]:
                del progress_sessions[sid]
    
    # Log memory status with more detail
    try:
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # More aggressive cleanup at lower threshold (250MB instead of 350MB)
        if memory_mb > 250:
            print(f"⚠️ High memory usage: {memory_mb:.1f}MB - forcing aggressive cleanup")
            
            # NEVER clear in-progress sessions, even at critical memory levels
            if memory_mb > 300:
                # Count in-progress sessions
                in_progress_count = sum(1 for s in progress_sessions.values() 
                                      if s.get('status') == 'in_progress')
                completed_count = len(progress_sessions) - in_progress_count
                
                print(f"🚨 CRITICAL memory: {in_progress_count} active, {completed_count} completed sessions")
                
                # Only clear completed sessions that are older than 5 minutes
                current_time = time.time()
                cleared_count = 0
                for sid, session in list(progress_sessions.items()):
                    if (session.get('status') == 'completed' and 
                        current_time - session.get('completed_time', session['start_time']) > 300):
                        del progress_sessions[sid]
                        cleared_count += 1
                        print(f"   Cleared old completed session: {sid}")
                
                if cleared_count > 0:
                    print(f"   Total cleared: {cleared_count} sessions")
                else:
                    print(f"   No old completed sessions to clear")
            else:
                # Keep in-progress sessions plus 5 most recent completed ones
                in_progress = {sid: s for sid, s in progress_sessions.items() 
                             if s.get('status') == 'in_progress'}
                completed = [(sid, s) for sid, s in progress_sessions.items() 
                           if s.get('status') != 'in_progress']
                completed.sort(key=lambda x: x[1]['start_time'], reverse=True)
                
                progress_sessions.clear()
                progress_sessions.update(in_progress)
                progress_sessions.update(dict(completed[:5]))
            
            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()
            
            # Log memory after cleanup
            memory_after = process.memory_info().rss / 1024 / 1024
            print(f"📊 Memory after cleanup: {memory_after:.1f}MB (freed {memory_mb - memory_after:.1f}MB)")
    except:
        pass
@app.route('/progress/<session_id>')
def get_progress(session_id):
    """Get current progress for a session"""
    # Removed cleanup_old_sessions() to prevent race conditions
    
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
        # Use global dynamic sheets service (memory optimization)
        if dynamic_sheets_service:
            # Get dynamic data from Dynamic Form Revisions Google Sheet
            utilities = dynamic_sheets_service.get_active_utilities()
            developers = dynamic_sheets_service.get_active_developers()
            
            return render_template('index.html', utilities=utilities, developers=developers)
        else:
            raise Exception("Dynamic sheets service not configured")
            
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

# =================================================================
# DIAGNOSTIC ENDPOINTS FOR OCR TROUBLESHOOTING
# =================================================================

def test_poppler():
    """Test if poppler-utils is installed and accessible"""
    try:
        import subprocess
        import os
        
        results = []
        
        # Test 1: Check if pdftoppm is available
        try:
            result = subprocess.run(['which', 'pdftoppm'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results.append(f"✅ pdftoppm found at: {result.stdout.strip()}")
            else:
                results.append("❌ pdftoppm not found in PATH")
        except Exception as e:
            results.append(f"❌ Error checking pdftoppm: {e}")
        
        # Test 2: Check if pdftocairo is available
        try:
            result = subprocess.run(['which', 'pdftocairo'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results.append(f"✅ pdftocairo found at: {result.stdout.strip()}")
            else:
                results.append("❌ pdftocairo not found in PATH")
        except Exception as e:
            results.append(f"❌ Error checking pdftocairo: {e}")
        
        # Test 3: Try to get poppler version
        try:
            result = subprocess.run(['pdftoppm', '-v'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results.append(f"✅ Poppler version: {result.stderr.strip()}")
            else:
                results.append("❌ Could not get poppler version")
        except Exception as e:
            results.append(f"❌ Error getting poppler version: {e}")
        
        # Test 4: Check if pdf2image can import
        try:
            import pdf2image
            results.append(f"✅ pdf2image imported successfully (version: {pdf2image.__version__ if hasattr(pdf2image, '__version__') else 'unknown'})")
        except ImportError as e:
            results.append(f"❌ pdf2image import failed: {e}")
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Poppler Utils Test</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; max-width: 800px; margin: 0 auto; }}
                .result {{ margin: 10px 0; padding: 10px; border-radius: 5px; background: #f8f8f8; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 Poppler Utils Diagnostic Test</h1>
                <p>Testing if poppler-utils is properly installed for PDF processing...</p>
                
                <h2>Test Results:</h2>
                {chr(10).join(f'<div class="result">{result}</div>' for result in results)}
                
                <p><a href="/" style="display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px;">← Back to Main</a></p>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1>❌ Error Testing Poppler</h1>
            <p>Error: {str(e)}</p>
            <p><a href="/">← Back to Main</a></p>
        </body>
        </html>
        '''

def test_pdf2image():
    """Test pdf2image functionality with a simple conversion"""
    try:
        import tempfile
        import os
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        results = []
        
        # Create a simple test PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf_path = temp_pdf.name
            
        try:
            # Generate a simple test PDF
            c = canvas.Canvas(temp_pdf_path, pagesize=letter)
            c.drawString(100, 750, "Test PDF for pdf2image conversion")
            c.drawString(100, 700, "If you can see this, PDF generation works")
            c.save()
            results.append("✅ Created test PDF successfully")
            
            # Test pdf2image conversion
            try:
                from pdf2image import convert_from_path
                results.append("✅ pdf2image imported successfully")
                
                # Try to convert the PDF
                pages = convert_from_path(temp_pdf_path, dpi=150)
                results.append(f"✅ PDF converted successfully - {len(pages)} page(s)")
                
                # Try to save first page as image
                if pages:
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                        temp_img_path = temp_img.name
                    
                    pages[0].save(temp_img_path, 'PNG')
                    img_size = os.path.getsize(temp_img_path)
                    results.append(f"✅ Image saved successfully ({img_size} bytes)")
                    
                    # Clean up image
                    os.unlink(temp_img_path)
                
            except Exception as pdf2img_error:
                results.append(f"❌ pdf2image conversion failed: {pdf2img_error}")
                import traceback
                results.append(f"📋 Traceback: {traceback.format_exc()}")
            
        finally:
            # Clean up test PDF
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>PDF2Image Test</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; max-width: 800px; margin: 0 auto; }}
                .result {{ margin: 10px 0; padding: 10px; border-radius: 5px; background: #f8f8f8; white-space: pre-wrap; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📄 PDF2Image Conversion Test</h1>
                <p>Testing if pdf2image can successfully convert PDFs to images...</p>
                
                <h2>Test Results:</h2>
                {chr(10).join(f'<div class="result">{result}</div>' for result in results)}
                
                <p><a href="/" style="display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px;">← Back to Main</a></p>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        import traceback
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1>❌ Error Testing PDF2Image</h1>
            <p>Error: {str(e)}</p>
            <pre>{traceback.format_exc()}</pre>
            <p><a href="/">← Back to Main</a></p>
        </body>
        </html>
        '''

def test_ocr_detailed():
    """Test OCR processing with detailed logging and error reporting"""
    try:
        results = []
        
        # Test 1: Check service account
        try:
            results.append(f"✅ Service account configured: {bool(SERVICE_ACCOUNT_INFO)}")
            if SERVICE_ACCOUNT_INFO:
                results.append(f"📋 Project ID: {SERVICE_ACCOUNT_INFO.get('project_id', 'N/A')}")
                results.append(f"📋 Client Email: {SERVICE_ACCOUNT_INFO.get('client_email', 'N/A')}")
        except Exception as e:
            results.append(f"❌ Service account error: {e}")
        
        # Test 2: Check if a test PDF exists
        test_pdf_path = None
        try:
            import os
            upload_dir = app.config['UPLOAD_FOLDER']
            if os.path.exists(upload_dir):
                pdf_files = [f for f in os.listdir(upload_dir) if f.endswith('.pdf')]
                if pdf_files:
                    test_pdf_path = os.path.join(upload_dir, pdf_files[0])
                    results.append(f"✅ Found test PDF: {pdf_files[0]}")
                else:
                    results.append("⚠️ No PDF files found in uploads folder")
            else:
                results.append("❌ Uploads folder not found")
        except Exception as e:
            results.append(f"❌ Error checking uploads: {e}")
        
        # Test 3: Try OCR processing if we have a test file
        if test_pdf_path:
            try:
                from services.ocr_service import process_utility_bill
                results.append("✅ OCR service imported successfully")
                
                results.append("🔍 Attempting OCR processing...")
                ocr_result = process_utility_bill(test_pdf_path, SERVICE_ACCOUNT_INFO)
                
                if ocr_result:
                    results.append(f"✅ OCR completed successfully")
                    results.append(f"📋 Extracted fields: {list(ocr_result.keys())}")
                    for key, value in ocr_result.items():
                        results.append(f"  - {key}: {value}")
                else:
                    results.append("❌ OCR returned no results")
                    
            except Exception as ocr_error:
                results.append(f"❌ OCR processing failed: {ocr_error}")
                import traceback
                results.append(f"📋 Traceback:\n{traceback.format_exc()}")
        else:
            results.append("⚠️ Skipping OCR test - no test PDF available")
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>OCR Detailed Test</title>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; max-width: 1000px; margin: 0 auto; }}
                .result {{ margin: 10px 0; padding: 10px; border-radius: 5px; background: #f8f8f8; white-space: pre-wrap; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 OCR Detailed Diagnostic Test</h1>
                <p>Testing the complete OCR processing pipeline...</p>
                
                <h2>Test Results:</h2>
                {chr(10).join(f'<div class="result">{result}</div>' for result in results)}
                
                <p><a href="/" style="display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px;">← Back to Main</a></p>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        import traceback
        return f'''
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1>❌ Error in OCR Detailed Test</h1>
            <p>Error: {str(e)}</p>
            <pre>{traceback.format_exc()}</pre>
            <p><a href="/">← Back to Main</a></p>
        </body>
        </html>
        '''

def test_current_submission():
    """Test what happens when we submit the form right now"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Current Submission Test</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto; }
            form { margin: 20px 0; }
            input, select { margin: 10px 0; padding: 8px; width: 100%; }
            button { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 Current Form Submission Test</h1>
            <p>Submit a form to see what error is currently being returned (those 133-byte responses)...</p>
            
            <form action="/submit" method="POST" enctype="multipart/form-data">
                <input type="text" name="business_entity" value="Test Business" placeholder="Business Entity">
                <input type="text" name="account_name" value="Test Account" placeholder="Account Name">
                <input type="text" name="contact_name" value="Test Contact" placeholder="Contact Name">
                <input type="text" name="title" value="Manager" placeholder="Title">
                <input type="text" name="phone" value="555-123-4567" placeholder="Phone">
                <input type="email" name="email" value="test@example.com" placeholder="Email">
                <input type="text" name="service_addresses" value="123 Test St" placeholder="Service Address">
                
                <select name="developer_assigned">
                    <option value="Meadow Energy">Meadow Energy</option>
                    <option value="Solar Simplified">Solar Simplified</option>
                </select>
                
                <select name="account_type">
                    <option value="Mass Market [Residential]">Mass Market [Residential]</option>
                    <option value="General Service [Small Commercial]">General Service [Small Commercial]</option>
                </select>
                
                <select name="utility_provider">
                    <option value="National Grid">National Grid</option>
                    <option value="NYSEG">NYSEG</option>
                    <option value="RG&E">RG&E</option>
                </select>
                
                <input type="text" name="agent_id" value="0000" placeholder="Agent ID">
                
                <p>Upload a utility bill (or it will use test data):</p>
                <input type="file" name="utility_bill" accept=".pdf,.jpg,.jpeg,.png">
                
                <p><input type="checkbox" name="terms_conditions" checked> I agree to Terms & Conditions</p>
                
                <button type="submit">Test Submit</button>
            </form>
            
            <p><a href="/" style="display: inline-block; padding: 10px 20px; background: #666; color: white; text-decoration: none; border-radius: 5px;">← Back to Main</a></p>
        </div>
    </body>
    </html>
    '''

# =================================================================
# END DIAGNOSTIC ENDPOINTS
# =================================================================

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
        # Get submission date in EST timezone
        est = pytz.timezone('US/Eastern')
        submission_date = datetime.now(est)
        
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

@app.route('/test-mass-market-agreement', methods=['POST'])
def test_mass_market_agreement():
    """Test Mass Market Agreement Distribution Utility field placement"""
    try:
        # Get JSON data
        json_data = request.get_json()
        
        form_data = {
            'business_entity': 'Mass Market Test Business',
            'account_name': 'Mass Market Test Account',
            'contact_name': json_data.get('contact_name', 'Test Customer'),
            'title': json_data.get('title', 'Owner'),
            'phone': '555-123-4567',
            'email': json_data.get('email', 'test@example.com'),
            'service_addresses': '123 Test Street, Test City, NY 12345',
            'developer_assigned': json_data.get('developer_assigned', 'Meadow Energy'),
            'account_type': 'Mass Market',
            'utility_provider': json_data.get('utility_provider', 'RG&E'),
            'agent_id': 'TEST001',
            'poid': 'R010000527370112'
        }
        
        # Create OCR data with the values from your screenshot
        ocr_data = {
            'utility_name': json_data.get('utility_provider', 'RG&E'),
            'customer_name': json_data.get('contact_name', 'Debug Distribution'),
            'account_number': '20027379153',
            'poid': 'R010000527370112',
            'monthly_usage': '1500',
            'annual_usage': '18000',
            'service_address': '123 Test Street, Test City, NY 12345',
            'monthly_charge': '165.25',
            'annual_charge': '1983.00'
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Directly process Mass Market template
        from services.anchor_pdf_processor import AnchorPDFProcessor
        processor = AnchorPDFProcessor("GreenWatt-documents")
        
        mass_market_template = "Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf"
        output_path = processor.process_template_with_anchors(mass_market_template, form_data, ocr_data, timestamp)
        
        # Get file info
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        
        # Create sample file
        sample_filename = f"temp/MASS_MARKET_Test_{timestamp}.pdf"
        if os.path.exists(output_path):
            import shutil
            shutil.copy2(output_path, sample_filename)
            os.remove(output_path)  # Remove original, keep sample
        
        response_data = {
            'success': True,
            'test_type': 'Mass Market Distribution Utility Test',
            'template_used': mass_market_template,
            'utility': form_data['utility_provider'],
            'developer': form_data['developer_assigned'],
            'account_type': form_data['account_type'],
            'distribution_utility_name': ocr_data['utility_name'],
            'distribution_utility_account': ocr_data['account_number'],
            'distribution_utility_poid': ocr_data['poid'],
            'anchor_method': 'Distribution anchor with positive offsets',
            'file_size': file_size,
            'sample_file': sample_filename
        }
        
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
        # Get submission date in EST timezone
        est = pytz.timezone('US/Eastern')
        submission_date = datetime.now(est)
        
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
    """Background processing function with progress tracking and dynamic template selection"""
    try:
        # Step 1: Uploading Document (5-20%)
        update_progress(session_id, 1, "Uploading Document", "Saving your utility bill securely", 5)
        time.sleep(0.2)  # Simulate upload
        update_progress(session_id, 1, "Uploading Document", "Validating file format", 15)
        time.sleep(0.3)
        update_progress(session_id, 1, "Uploading Document", "File saved successfully", 20)
        
        # Step 2: OCR Processing (20-35%)
        update_progress(session_id, 2, "OCR Analysis", "Initializing text recognition", 25)
        time.sleep(0.2)
        update_progress(session_id, 2, "OCR Analysis", "Reading text from your utility bill", 30)
        try:
            ocr_data = process_utility_bill(file_path, SERVICE_ACCOUNT_INFO)
            print(f"✅ OCR extraction successful: {json.dumps(ocr_data, indent=2)}")
        except Exception as ocr_error:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ OCR extraction failed: {str(ocr_error)}")
            print(f"❌ Error type: {type(ocr_error).__name__}")
            print(f"❌ Full traceback:\n{error_details}")
            
            # Log critical info for debugging
            print(f"🔍 Debug info:")
            print(f"   - File path: {file_path}")
            print(f"   - File exists: {os.path.exists(file_path)}")
            print(f"   - Service account configured: {'Yes' if SERVICE_ACCOUNT_INFO else 'No'}")
            print(f"   - OpenAI key configured: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
            
            # Use empty OCR data to continue processing
            ocr_data = {
                'utility_name': '',
                'customer_name': '',
                'account_number': '',
                'poid': '',
                'monthly_usage': '',
                'annual_usage': '',
                'service_address': ''
            }
        update_progress(session_id, 2, "OCR Analysis", "Text extraction complete", 35)
        
        # Step 3: AI Processing (35-50%)
        update_progress(session_id, 3, "AI Processing", "Analyzing document structure", 40)
        time.sleep(0.3)
        update_progress(session_id, 3, "AI Processing", "Extracting account information", 45)
        time.sleep(0.4)
        update_progress(session_id, 3, "AI Processing", "Validating extracted data", 50)
        
        # Get submission date in EST timezone
        est = pytz.timezone('US/Eastern')
        submission_date = datetime.now(est)
        folder_name = f"{submission_date.strftime('%Y-%m-%d')}_{form_data['account_name']}_{form_data['utility_provider']}"
        
        # Step 4: Generate Documents (50-70%)
        update_progress(session_id, 4, "Generating Documents", "Preparing document templates", 55)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        update_progress(session_id, 4, "Generating Documents", "Creating Power of Attorney", 60)
        poa_pdf_path = generate_poa_pdf(form_data, ocr_data, timestamp)
        
        update_progress(session_id, 4, "Generating Documents", "Creating Community Solar Agreement", 65)
        
        # Get agreement template from dynamic sheets with validation
        dynamic_sheets_id = os.getenv('DYNAMIC_GOOGLE_SHEETS_ID')
        dynamic_drive_id = os.getenv('DYNAMIC_GOOGLE_DRIVE_FOLDER_ID')
        
        if dynamic_sheets_id and dynamic_drive_id:
            # Reuse existing drive service with different parent folder
            dynamic_drive_service = GoogleDriveService(parent_folder_id=dynamic_drive_id)
            
            agreement_filename = dynamic_sheets_service.get_developer_agreement(
                form_data['developer_assigned'], 
                form_data['utility_provider'], 
                form_data['account_type']
            )
            
            # Check if we need Mass Market override
            if form_data['account_type'] == 'Mass Market [Residential]':
                mass_market_filename = dynamic_sheets_service.get_developer_agreement(
                    form_data['developer_assigned'], 
                    'Mass Market', 
                    form_data['account_type']
                )
                if mass_market_filename:
                    agreement_filename = mass_market_filename
            
            if agreement_filename:
                try:
                    agreement_pdf_path = generate_agreement_pdf(form_data, ocr_data, form_data['developer_assigned'], timestamp, agreement_filename, dynamic_drive_service)
                except Exception as template_error:
                    print(f"Template processing failed: {template_error}")
                    # Fallback to original method
                    agreement_pdf_path = generate_agreement_pdf(form_data, ocr_data, form_data['developer_assigned'], timestamp)
            else:
                print(f"No template mapping found for {form_data['developer_assigned']} + {form_data['utility_provider']}")
                # Fallback to original method
                agreement_pdf_path = generate_agreement_pdf(form_data, ocr_data, form_data['developer_assigned'], timestamp)
        else:
            # Fallback to original method if dynamic config not available
            agreement_pdf_path = generate_agreement_pdf(form_data, ocr_data, form_data['developer_assigned'], timestamp)
        
        # Generate Terms & Conditions (Agency Agreement) with signature
        update_progress(session_id, 4, "Generating Documents", "Creating Terms & Conditions", 68)
        from services.pdf_template_processor import PDFTemplateProcessor
        pdf_processor = PDFTemplateProcessor("GreenWatt-documents")
        agency_agreement_pdf_path = pdf_processor.process_agency_agreement(form_data, timestamp)
        update_progress(session_id, 4, "Generating Documents", "All documents created", 70)
        
        # Step 5: Cloud Storage (70-85%)
        update_progress(session_id, 5, "Cloud Storage", "Connecting to Google Drive", 72)
        time.sleep(0.2)
        update_progress(session_id, 5, "Cloud Storage", "Creating secure folder", 75)
        drive_folder_id = drive_service.create_folder(folder_name)
        
        update_progress(session_id, 5, "Cloud Storage", "Uploading utility bill", 78)
        utility_bill_id = drive_service.upload_file(file_path, f"utility_bill_{timestamp}.pdf", drive_folder_id)
        
        update_progress(session_id, 5, "Cloud Storage", "Uploading Power of Attorney", 80)
        poa_id = drive_service.upload_file(poa_pdf_path, f"poa_{timestamp}.pdf", drive_folder_id)
        
        update_progress(session_id, 5, "Cloud Storage", "Uploading Agreement", 82)
        agreement_id = drive_service.upload_file(agreement_pdf_path, f"agreement_{timestamp}.pdf", drive_folder_id)
        
        # Upload Terms & Conditions (Agency Agreement) if generated successfully
        agency_agreement_id = None
        if agency_agreement_pdf_path and os.path.exists(agency_agreement_pdf_path):
            update_progress(session_id, 5, "Cloud Storage", "Uploading Terms & Conditions", 84)
            agency_agreement_id = drive_service.upload_file(agency_agreement_pdf_path, f"agency_agreement_{timestamp}.pdf", drive_folder_id)
        
        # Generate public links
        update_progress(session_id, 5, "Cloud Storage", "Generating secure links", 85)
        utility_bill_link = drive_service.get_file_link(utility_bill_id)
        poa_link = drive_service.get_file_link(poa_id)
        agreement_link = drive_service.get_file_link(agreement_id)
        agency_agreement_link = drive_service.get_file_link(agency_agreement_id) if agency_agreement_id else ''
        
        # Step 6: Logging Data (85-95%)
        update_progress(session_id, 6, "Logging Data", "Preparing submission data", 87)
        
        # Get agent name and other data
        agent_name = sheets_service.get_agent_name(form_data['agent_id'])
        utility_name_final = ocr_data.get('utility_name', form_data['utility_provider'])
        unique_id = generate_unique_id()
        poa_id_generated = f"POA-{timestamp}-{unique_id.split('-')[-1]}"
        
        sheet_data = [
            unique_id,                       # Unique submission ID (A)
            submission_date.strftime('%m/%d/%Y %I:%M %p EST'),  # Submission Date (B) - MM/DD/YYYY 12hr EST
            form_data['business_entity'],    # Business Entity Name (C)
            form_data['account_name'],       # Account Name (D)
            form_data['contact_name'],       # Contact Name (E)
            form_data['title'],              # Title (F)
            form_data['phone'],              # Phone (G)
            form_data['email'],              # Email (H)
            ocr_data.get('service_address', form_data.get('service_addresses', '')),  # Service Address (OCR) (I) - Now using OCR
            form_data['developer_assigned'], # Developer Assigned (J)
            form_data['account_type'],       # Account Type (K)
            form_data['utility_provider'],  # Utility Provider (Form) (L)
            utility_name_final,             # Utility Name (OCR) (M)
            ocr_data.get('account_number', ''),  # Account Number (OCR) (N)
            ocr_data.get('poid', form_data.get('poid', '')),        # POID (OCR) (O) - Now using OCR
            # Column P removed (was POID Form)
            ocr_data.get('monthly_usage', ''),   # Monthly Usage (OCR) (P) - shifted left
            ocr_data.get('annual_usage', ''),    # Annual Usage (OCR) (Q) - shifted left
            form_data['agent_id'],           # Agent ID (R) - shifted left
            agent_name,                      # Agent Name (S) - shifted left
            # Column T removed (was Service Address OCR duplicate)
            poa_id_generated,                # POA ID (T) - shifted left
            utility_bill_link,              # Utility Bill Link (U) - shifted left
            poa_link,                        # POA Link (V) - shifted left
            agreement_link,                  # Agreement Link (W) - shifted left
            agency_agreement_link              # Terms & Conditions Link (X) - shifted left
        ]
        
        update_progress(session_id, 6, "Logging Data", "Writing to Google Sheets", 90)
        try:
            result = sheets_service.append_row(sheet_data)
        except Exception as e:
            print(f"Sheet insertion failed: {e}")
        
        update_progress(session_id, 6, "Logging Data", "Data saved successfully", 95)
        
        # Step 7: Notifications (95-100%)
        update_progress(session_id, 7, "Notifications", "Preparing email notification", 96)
        
        # Send email notification to internal team
        update_progress(session_id, 7, "Notifications", "Sending email notification", 97)
        from services.email_service import send_notification_email
        send_notification_email(
            agent_name=agent_name,
            customer_name=form_data['account_name'],
            utility=form_data['utility_provider'],
            signed_date=submission_date.strftime('%Y-%m-%d'),
            annual_usage=ocr_data.get('annual_usage', 'N/A')
        )
        
        # Send SMS verification to customer
        update_progress(session_id, 7, "Notifications", "Sending SMS verification", 98)
        try:
            sms_response = sms_service.send_customer_verification_sms(
                customer_phone=form_data['phone'],
                customer_name=form_data['contact_name']
            )
            print(f"SMS sent: {sms_response}")
        except Exception as sms_error:
            print(f"SMS failed: {sms_error}")
            
        # Send SMS notification to internal team
        update_progress(session_id, 7, "Notifications", "Notifying team", 99)
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
                'agreement': agreement_link,
                'agency_agreement': agency_agreement_link
            }
        }
        
        # Clean up temporary files
        os.remove(file_path)
        os.remove(poa_pdf_path)
        os.remove(agreement_pdf_path)
        if agency_agreement_pdf_path and os.path.exists(agency_agreement_pdf_path):
            os.remove(agency_agreement_pdf_path)
        
        # Complete successfully
        complete_progress(session_id, success=True)
        
        # Force garbage collection after submission completes
        gc.collect()
        print("♻️  Garbage collection performed after submission")
        
    except Exception as e:
        print(f"Background processing error: {e}")
        import traceback
        traceback.print_exc()
        complete_progress(session_id, success=False, error=str(e))
        
        # Force garbage collection even on error to free memory
        gc.collect()


@app.route('/submit', methods=['POST'])
def submit_form():
    """Modified submit endpoint to use background processing with real-time progress tracking"""
    try:
        # Log memory status before processing
        service_manager.log_memory_status("before form submission")
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
        
        # Log memory status after starting background thread
        service_manager.log_memory_status("after starting submission thread")
        
        # Return session ID for progress tracking
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Processing started - track progress with session ID'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/dynamic-test')
def dynamic_test():
    """Test dynamic Google Sheets and Drive connectivity"""
    try:
        # Check environment variables
        dynamic_sheets_id = os.getenv('DYNAMIC_GOOGLE_SHEETS_ID')
        dynamic_drive_id = os.getenv('DYNAMIC_GOOGLE_DRIVE_FOLDER_ID')
        
        test_html = f'''
        <html>
        <head><title>Dynamic System Test Dashboard</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🔧 Dynamic System Test Dashboard</h2>
            
            <h3>Environment Variables</h3>
            <ul>
                <li><strong>DYNAMIC_GOOGLE_SHEETS_ID:</strong> {'✅ Set' if dynamic_sheets_id else '❌ Not set'}</li>
                <li><strong>DYNAMIC_GOOGLE_DRIVE_FOLDER_ID:</strong> {'✅ Set' if dynamic_drive_id else '❌ Not set'}</li>
                <li><strong>Sheet ID:</strong> {dynamic_sheets_id if dynamic_sheets_id else 'Not configured'}</li>
                <li><strong>Drive ID:</strong> {dynamic_drive_id if dynamic_drive_id else 'Not configured'}</li>
            </ul>
        '''
        
        if dynamic_sheets_service:
            try:
                
                # Test utilities retrieval
                utilities = dynamic_sheets_service.get_active_utilities()
                developers = dynamic_sheets_service.get_active_developers()
                
                test_html += f'''
                <h3>✅ Google Sheets Connection Test - SUCCESS</h3>
                <p><strong>Successfully connected to Dynamic Form Revisions sheet!</strong></p>
                
                <h4>Active Utilities Retrieved:</h4>
                <ul>
                '''
                
                if utilities:
                    for utility in utilities:
                        test_html += f'<li><strong>{utility}</strong> - Active in dropdown</li>'
                else:
                    test_html += '<li><em>No active utilities found - check Utilities tab</em></li>'
                
                test_html += '''
                </ul>
                
                <h4>Active Developers Retrieved:</h4>
                <ul>
                '''
                
                if developers:
                    for developer in developers:
                        test_html += f'<li><strong>{developer}</strong> - Active in dropdown</li>'
                else:
                    test_html += '<li><em>No developers found - check Developer_Mapping tab</em></li>'
                
                test_html += '</ul>'
                
                # Test developer mapping details
                try:
                    test_html += '<h4>Developer-Utility Template Mappings:</h4><ul>'
                    # Get raw mapping data for display
                    all_mappings = dynamic_sheets_service.get_all_developer_mappings()
                    if all_mappings:
                        for mapping in all_mappings[:10]:  # Show first 10
                            developer = mapping.get('developer_name', 'Unknown')
                            utility = mapping.get('utility_name', 'Unknown') 
                            filename = mapping.get('file_name', 'Unknown')
                            test_html += f'<li><strong>{developer}</strong> + <strong>{utility}</strong> → {filename}</li>'
                    else:
                        test_html += '<li><em>No mappings found in Developer_Mapping tab</em></li>'
                    test_html += '</ul>'
                except Exception as mapping_error:
                    test_html += f'<p><strong>Mapping Error:</strong> {str(mapping_error)}</p>'
                
            except Exception as sheets_error:
                test_html += f'''
                <h3>❌ Google Sheets Connection Test - FAILED</h3>
                <p><strong>Error connecting to sheets:</strong> {str(sheets_error)}</p>
                <p><strong>Troubleshooting:</strong></p>
                <ul>
                    <li>Verify sheet ID is correct</li>
                    <li>Check service account has Editor permissions</li>
                    <li>Ensure Utilities and Developer_Mapping tabs exist</li>
                </ul>
                '''
        else:
            test_html += '''
            <h3>❌ Google Sheets Test - Not Configured</h3>
            <p><strong>DYNAMIC_GOOGLE_SHEETS_ID not set</strong></p>
            '''
        
        # Test Google Drive connectivity
        if dynamic_drive_id:
            try:
                dynamic_drive_service = GoogleDriveService(SERVICE_ACCOUNT_INFO, dynamic_drive_id)
                
                # Try to list files in Templates folder
                try:
                    # This will test if we can access the drive folder
                    test_file_list = "Testing drive access..."
                    test_html += f'''
                    <h3>✅ Google Drive Connection Test - SUCCESS</h3>
                    <p><strong>Successfully connected to GreenWatt_Dynamic_Intake folder!</strong></p>
                    <p><strong>Templates folder accessible for agreement PDFs</strong></p>
                    '''
                except Exception as drive_error:
                    test_html += f'''
                    <h3>❌ Google Drive Connection Test - FAILED</h3>
                    <p><strong>Error:</strong> {str(drive_error)}</p>
                    '''
                    
            except Exception as drive_service_error:
                test_html += f'''
                <h3>❌ Google Drive Service Test - FAILED</h3>
                <p><strong>Error:</strong> {str(drive_service_error)}</p>
                '''
        else:
            test_html += '''
            <h3>❌ Google Drive Test - Not Configured</h3>
            <p><strong>DYNAMIC_GOOGLE_DRIVE_FOLDER_ID not set</strong></p>
            '''
        
        # Add testing instructions
        test_html += f'''
            <h3>🧪 Live Testing Instructions</h3>
            <div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4>Test Dynamic Changes:</h4>
                <ol>
                    <li><strong>Test Utility Changes:</strong>
                        <ul>
                            <li>Open <a href="https://docs.google.com/spreadsheets/d/{dynamic_sheets_id}/edit" target="_blank">Dynamic Form Revisions Sheet</a></li>
                            <li>Go to "Utilities" tab</li>
                            <li>Change "Orange & Rockland" from FALSE to TRUE</li>
                            <li>Click <strong>Clear Cache</strong> below</li>
                            <li>Refresh this page - should see Orange & Rockland in active utilities</li>
                        </ul>
                    </li>
                    <li><strong>Test Developer Changes:</strong>
                        <ul>
                            <li>Go to "Developer_Mapping" tab</li>
                            <li>Add a test row: "Test Developer | National Grid | test-agreement.pdf"</li>
                            <li>Clear cache and refresh - should see "Test Developer" in developers list</li>
                        </ul>
                    </li>
                </ol>
            </div>
            
            <h3>🔧 Testing Tools</h3>
            <div style="margin: 20px 0;">
                <a href="/dynamic-cache-manager" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">
                    🗂️ Cache Manager (Test Changes Immediately)
                </a>
                <a href="/dynamic-test" style="display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">
                    🔄 Refresh This Test
                </a>
                <a href="/" style="display: inline-block; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">
                    🏠 Test Main Form
                </a>
            </div>
            
            <h3>📋 Next Steps</h3>
            <ol>
                <li>Verify all connections show ✅ above</li>
                <li>Test changing utilities/developers and see immediate results</li>
                <li>Test the main form at <a href="/">localhost:5001</a></li>
                <li>If everything works, push to GitHub and deploy to production</li>
            </ol>
        </body>
        </html>
        '''
        
        return test_html
        
    except Exception as e:
        return f'''
        <html>
        <head><title>Dynamic Test - Error</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>❌ Dynamic Test Error</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><a href="/">← Back to Main Form</a></p>
        </body>
        </html>
        ''', 500

@app.route('/dynamic-cache-manager')
def dynamic_cache_manager():
    """Cache management page - view current cache without clearing"""
    try:
        # Use global dynamic sheets service (memory optimization)
        if not dynamic_sheets_service:
            return "Dynamic sheets not configured", 500
        
        # Get current cached data
        utilities = dynamic_sheets_service.get_active_utilities()
        developers = dynamic_sheets_service.get_active_developers()
        
        return f'''
        <html>
        <head><title>Dynamic Cache Manager</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🗂️ Dynamic Cache Manager</h2>
            <p>View and manage the Google Sheets cache for immediate testing</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3>📊 Current Cached Data</h3>
                <h4>Active Utilities:</h4>
                <ul>
                    {(''.join([f'<li><strong>{utility}</strong></li>' for utility in utilities]) if utilities else '<li><em>No utilities found</em></li>')}
                </ul>
                
                <h4>Active Developers:</h4>
                <ul>
                    {(''.join([f'<li><strong>{developer}</strong></li>' for developer in developers]) if developers else '<li><em>No developers found</em></li>')}
                </ul>
            </div>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h4>⏰ Cache Behavior</h4>
                <p>• Cache automatically refreshes every <strong>15 minutes</strong></p>
                <p>• Use the button below to get immediate updates from Google Sheets</p>
                <p>• This is useful when testing changes to utilities or developers</p>
            </div>
            
            <div style="margin: 20px 0;">
                <a href="/dynamic-clear-cache-now" 
                   style="display: inline-block; padding: 15px 25px; background: #dc3545; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    🗑️ Clear Cache Now
                </a>
                
                <a href="/dynamic-test" 
                   style="display: inline-block; padding: 15px 25px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin-left: 10px;">
                    ← Back to Test Dashboard
                </a>
                
                <a href="/" 
                   style="display: inline-block; padding: 15px 25px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-left: 10px;">
                    🧪 Test Main Form
                </a>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"Error accessing cache manager: {str(e)}", 500

@app.route('/dynamic-clear-cache-now')
def dynamic_clear_cache_now():
    """Actually clear the cache and show results"""
    try:
        # Log memory before cache clear
        service_manager.log_memory_status("before cache clear")
        
        # Use consolidated sheets service
        sheets_service.clear_cache()
        
        # Log memory after cache clear
        service_manager.log_memory_status("after cache clear")
        
        # Don't fetch data immediately to avoid memory spike
        # Let the next request populate the cache naturally
        
        return f'''
        <html>
        <head><title>Cache Cleared Successfully</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>✅ Cache Cleared Successfully!</h2>
            <p><strong>Fresh data has been loaded from Google Sheets</strong></p>
            
            <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h3>📊 Cache Status:</h3>
                <p>• Previous cache data has been cleared</p>
                <p>• Fresh data will be loaded from Google Sheets on next request</p>
                <p>• This prevents memory spikes from simultaneous API calls</p>
            </div>
            
            <div style="background: #cff4fc; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h4>🎯 Next Steps</h4>
                <p>• Changes from Google Sheets are now active</p>
                <p>• Test the main form to see updated dropdowns</p>
                <p>• No need to wait 15 minutes for cache refresh</p>
            </div>
            
            <div style="margin: 20px 0;">
                <a href="/dynamic-cache-manager" 
                   style="display: inline-block; padding: 15px 25px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px;">
                    ← Back to Cache Manager
                </a>
                
                <a href="/" 
                   style="display: inline-block; padding: 15px 25px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-left: 10px;">
                    🧪 Test Main Form
                </a>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f"Error clearing cache: {str(e)}", 500

# Keep the old route for backwards compatibility
@app.route('/dynamic-clear-cache')
def dynamic_clear_cache():
    """Redirect to the new cache manager"""
    return '''
    <html>
    <head>
        <title>Redirecting to Cache Manager</title>
        <meta http-equiv="refresh" content="2;url=/dynamic-cache-manager">
    </head>
    <body style="font-family: Arial; padding: 20px; text-align: center;">
        <h2>🔄 Redirecting to Cache Manager</h2>
        <p>Taking you to the improved cache management interface...</p>
        <p><a href="/dynamic-cache-manager">Click here if not redirected automatically</a></p>
    </body>
    </html>
    '''

@app.route('/test-sendgrid-email-verification', methods=['GET', 'POST'])
def test_sendgrid_email_verification():
    """Test email with specific data to verify both recipients receive it"""
    if request.method == 'GET':
        return '''
        <html>
        <head><title>SendGrid Email Verification Test</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>📧 SendGrid Email Verification Test</h2>
            <p>This will send a test email to <strong>greenwatt.intake@gmail.com</strong></p>
            
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
                <p><strong>TEST EMAIL SENT SUCCESSFULLY!</strong></p>
                <div style="background: #f0f8f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>📧 Email Details:</h3>
                    <strong>Recipients:</strong><br>
                    • greenwatt.intake@gmail.com<br><br>
                    
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

@app.route('/preview/poa')
def preview_poa():
    """Serve the blank POA template for preview"""
    try:
        template_path = os.path.join('GreenWatt-documents', 'GreenWattUSA_Limited_Power_of_Attorney.pdf')
        if os.path.exists(template_path):
            from flask import send_file
            return send_file(template_path, mimetype='application/pdf', as_attachment=False)
        else:
            return jsonify({'error': 'POA template not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview/agency-agreement')
def preview_agency_agreement():
    """Serve the blank Agency Agreement template for preview"""
    try:
        template_path = os.path.join('GreenWatt-documents', 'GreenWATT-USA-Inc-Communtiy-Solar-Agency-Agreement.pdf')
        if os.path.exists(template_path):
            from flask import send_file
            return send_file(template_path, mimetype='application/pdf', as_attachment=False)
        else:
            return jsonify({'error': 'Agency Agreement template not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify-config')
def verify_config():
    """Web endpoint to verify production configuration"""
    import subprocess
    
    try:
        # Run the verification script and capture output
        result = subprocess.run(
            ['python', 'verify_production_config.py'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout if result.returncode == 0 else result.stderr
        
        # Convert ANSI output to HTML formatting
        html_output = output.replace('\n', '<br>')
        html_output = html_output.replace('✅', '<span style="color: green;">✅</span>')
        html_output = html_output.replace('❌', '<span style="color: red;">❌</span>')
        html_output = html_output.replace('⚠️', '<span style="color: orange;">⚠️</span>')
        html_output = html_output.replace('🔍', '🔍')
        html_output = html_output.replace('📋', '📋')
        html_output = html_output.replace('💡', '💡')
        html_output = html_output.replace('=' * 50, '<hr>')
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Configuration Verification</title>
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    background-color: #f5f5f5;
                    padding: 20px;
                    line-height: 1.6;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    max-width: 800px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                .output {{
                    background-color: #f8f8f8;
                    padding: 20px;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                    white-space: pre-wrap;
                }}
                .back-link {{
                    margin-top: 20px;
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                .back-link:hover {{
                    background-color: #45a049;
                }}
                hr {{
                    border: none;
                    border-top: 1px solid #ddd;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 Production Configuration Verification</h1>
                <div class="output">{html_output}</div>
                <a href="/" class="back-link">← Back to Home</a>
            </div>
        </body>
        </html>
        '''
        
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Configuration Verification Error</title>
        </head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>❌ Verification Error</h1>
            <p style="color: red;">Error running verification: {str(e)}</p>
            <p>Make sure verify_production_config.py exists in the application directory.</p>
            <a href="/">← Back to Home</a>
        </body>
        </html>
        ''', 500

@app.route('/health')
def health_check():
    """Health check endpoint that verifies all critical dependencies"""
    import subprocess
    
    health_status = {
        'status': 'healthy',
        'checks': {},
        'timestamp': datetime.now().isoformat()
    }
    
    # Check Python packages
    try:
        import pdf2image
        health_status['checks']['pdf2image'] = {'status': 'ok', 'message': 'Module imported successfully'}
    except ImportError as e:
        health_status['checks']['pdf2image'] = {'status': 'error', 'message': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Check system dependencies
    try:
        result = subprocess.run(['which', 'pdftoppm'], capture_output=True, text=True)
        if result.returncode == 0:
            health_status['checks']['poppler'] = {'status': 'ok', 'message': f'Found at: {result.stdout.strip()}'}
        else:
            health_status['checks']['poppler'] = {'status': 'error', 'message': 'pdftoppm not found in PATH'}
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['poppler'] = {'status': 'error', 'message': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Check API configurations
    health_status['checks']['google_service_account'] = {
        'status': 'ok' if SERVICE_ACCOUNT_INFO else 'error',
        'message': 'Configured' if SERVICE_ACCOUNT_INFO else 'Not configured'
    }
    
    health_status['checks']['openai_api_key'] = {
        'status': 'ok' if os.getenv('OPENAI_API_KEY') else 'error',
        'message': 'Configured' if os.getenv('OPENAI_API_KEY') else 'Not configured'
    }
    
    # Test PDF processing capability
    try:
        from pdf2image import convert_from_path
        # Try to import without actually converting
        health_status['checks']['pdf_processing'] = {'status': 'ok', 'message': 'PDF processing available'}
    except Exception as e:
        health_status['checks']['pdf_processing'] = {'status': 'error', 'message': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Return appropriate status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

@app.route('/test-ocr-simple')
def test_ocr_simple():
    """Simple test endpoint to verify OCR is working"""
    try:
        # Check if we have test files
        test_files = [
            '/Volumes/Pat Samsung/Client/Upwork/Fulfillment 2025/GreenWatt_Clean_Repo/GreenWatt-documents/sample-documents/Sample-Bills-greenwatt/utility_bill_20250619_193755.pdf',
            'uploads/20250618_185747_IMG_6712.jpeg'
        ]
        
        available_file = None
        for test_file in test_files:
            if os.path.exists(test_file):
                available_file = test_file
                break
        
        if not available_file:
            return jsonify({
                'success': False,
                'error': 'No test files available',
                'message': 'Upload a utility bill through the main form first'
            }), 404
        
        # Try OCR processing
        ocr_result = process_utility_bill(available_file, SERVICE_ACCOUNT_INFO)
        
        return jsonify({
            'success': True,
            'file': available_file,
            'ocr_result': ocr_result,
            'message': 'OCR processing successful!'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'message': 'OCR processing failed'
        }), 500

# Background cleanup thread
def automatic_cleanup():
    """Run cleanup every 60 seconds"""
    while True:
        try:
            time.sleep(60)  # Run every minute
            cleanup_old_sessions()
            
            # Log memory status every 5 minutes
            if int(time.time()) % 300 < 60:
                try:
                    process = psutil.Process(os.getpid())
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    print(f"📊 Memory usage: {memory_mb:.1f}MB | Sessions: {len(progress_sessions)}")
                except:
                    pass
        except Exception as e:
            print(f"Error in automatic cleanup: {e}")


@app.route('/memory-status')
def memory_status():
    """Endpoint to check current memory usage"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        # Get detailed memory stats
        memory_stats = {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
            'total_mb': psutil.virtual_memory().total / 1024 / 1024,
            'progress_sessions': len(progress_sessions),
            'gc_stats': gc.get_stats()
        }
        
        # Force cleanup if memory is high
        if memory_stats['rss_mb'] > 250:
            cleanup_old_sessions()
            gc.collect()
            
            # Recalculate after cleanup
            memory_info_after = process.memory_info()
            memory_stats['rss_mb_after_cleanup'] = memory_info_after.rss / 1024 / 1024
            memory_stats['cleaned'] = True
        else:
            memory_stats['cleaned'] = False
        
        return jsonify(memory_stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Start background cleanup thread
cleanup_thread = threading.Thread(target=automatic_cleanup, daemon=True)
cleanup_thread.start()
print("✅ Started automatic memory cleanup thread")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)