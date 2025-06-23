# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
# Server starts on http://localhost:5000

# Run with different port
PORT=5001 python app.py
```

### Testing
```bash
# Test endpoints
curl http://localhost:5000/test
curl http://localhost:5000/phase1-test

# Test PDF generation endpoint
curl -X POST http://localhost:5000/test-pdf \
  -H "Content-Type: application/json" \
  -d '{"utility_provider":"National Grid","developer_assigned":"Meadow Energy"}'
```

### Deployment
```bash
# Build for Render.com (configured in render.yaml)
pip install -r requirements.txt
gunicorn app:app
```

## Application Architecture

### Service-Oriented Design
The application uses a modular service architecture where each service has a single responsibility:

- **OCR Service**: Coordinates Google Vision API + OpenAI LLM for utility bill parsing
- **PDF Generator**: Creates POA and Developer Agreement documents using ReportLab
- **Google Drive Service**: Manages document storage and folder organization
- **Google Sheets Service**: Handles data logging and dynamic configuration via spreadsheets
- **Email/SMS Services**: Send notifications to team and customers

### Dynamic Configuration via Google Sheets
The application reads business logic from Google Sheets tabs, allowing non-technical updates:
- `Utilities` tab controls which utilities appear in dropdown (TRUE/FALSE flag)
- `Developer_Mapping` tab maps Developer + Utility combinations to agreement templates
- `Agents` tab maps agent IDs to agent names
- All changes reflect immediately due to 15-minute TTL caching

### Google Cloud Integration Pattern
All Google services use a shared service account credential pattern:
```python
SERVICE_ACCOUNT_INFO = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
# Services instantiated with this credential object
drive_service = GoogleDriveService(SERVICE_ACCOUNT_INFO, folder_id)
```

### Document Processing Pipeline
1. **File Upload** → Secure upload with type/size validation
2. **OCR Processing** → Google Vision API extracts raw text
3. **LLM Parsing** → OpenAI GPT-3.5 structures the data
4. **PDF Generation** → ReportLab creates POA + Developer Agreement
5. **Cloud Storage** → Google Drive with organized folder structure
6. **Data Logging** → Google Sheets with formatted columns
7. **Notifications** → Email to team, SMS to customer

### Error Handling Strategy
The application uses "graceful degradation" - if external services fail, it falls back to mock data to continue processing. This ensures the workflow never completely breaks.

## Key Implementation Details

### OCR Data Flow
The system implements an "OCR wins" policy where OCR-extracted utility names take precedence over form selections, but both are logged separately for comparison.

### PDF Template System
Currently generates PDFs programmatically with ReportLab, but the architecture supports migration to template-based generation in Phase 3. Templates are stored in Google Drive `GreenWatt_Templates` folder.

### Agent ID Resolution
Agent IDs (e.g., "AG001") are resolved to names via Google Sheets lookup, allowing the client to manage agents without code changes.

### Signature Implementation
Electronic signatures are applied as text overlays using customer names with Arizonia cursive font for authentic Adobe PDF signature appearance when T&C checkbox is checked.

### Unique POA ID System
POA documents use unique identifiers in format `POA-{YYYYMMDDHHMMS}-{uuid_hex}` (e.g., POA-20250617141754-cf4bc8) for tracking and auditing purposes.

### Email Notification System
Email notifications are sent to internal team members (up to 3) using SendGrid API for reliable delivery. Each notification includes:
- Agent Name
- Customer Name
- Utility
- Signed Date
- Annual Usage (kWh)
- Professional HTML formatting with GreenWatt branding

### SMS Verification System
Customer verification SMS is triggered immediately after form submission:
- Sends Y/N participation confirmation request
- Logs SMS status in Google Sheets with timestamps
- Handles responses via Twilio webhook
- Tracks: SMS Sent, SMS Sent Timestamp, SMS Response, SMS Response Timestamp, Phone Number, Message SID

## Environment Configuration

### System Dependencies
The application requires the following system packages:
- **poppler-utils**: Required for PDF to image conversion (used by pdf2image Python package)
  - Production: Automatically installed via render.yaml buildCommand
  - Local Ubuntu/Debian: `sudo apt-get install -y poppler-utils`
  - Local macOS: `brew install poppler`
  - Local Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/

### Required Environment Variables
```bash
# Google Cloud
GOOGLE_SERVICE_ACCOUNT_JSON="{...json content...}"
GOOGLE_SHEETS_ID="spreadsheet_id_here"
GOOGLE_DRIVE_PARENT_FOLDER_ID="folder_id_here"
GOOGLE_AGENT_SHEETS_ID="agent_spreadsheet_id_here"
GOOGLE_DRIVE_TEMPLATES_FOLDER_ID="templates_folder_id_here"

# Email/SMS
SENDGRID_API_KEY="SG.your_sendgrid_api_key_here"
TWILIO_ACCOUNT_SID="AC_your_twilio_account_sid_here"
TWILIO_AUTH_TOKEN="your_twilio_auth_token_here"
TWILIO_FROM_NUMBER="+1..."
TWILIO_INTERNAL_NUMBERS="phone1,phone2,phone3"

# AI
OPENAI_API_KEY="sk-..."

# Development Only - SSL Bypass (DO NOT SET IN PRODUCTION)
DISABLE_SSL_VERIFICATION="true"  # Only for local development to bypass corporate SSL issues
```

### Google Cloud Console
- **Project Name**: GreenWatt Intake Form
- **Service Account Name**: GreenWatt Intake Service
- **Service Account ID**: `greenwatt-intake-service`
- **Service Account Email**: `greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com`

### Google Sheets
- **Intake Log**: [URL](https://docs.google.com/spreadsheets/d/11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o) ID: `11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o`
- **Submissions tab**: Raw dump of every submission
- **Developer_Mapping tab**: Links Developer + Utility → Agreement
- **Utilities tab**: Controls which utilities appear
- **Agents Sheet**: [URL](https://docs.google.com/spreadsheets/d/1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I) ID: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I`

### Google Drive
- **Signed Docs root**: Final PDFs + template store ID: `1i1SAHRnrgA-eWKgaZaShwF3zzOqewO3W`
- **Templates/**: Sub-folder holding all agreement PDFs Path: `GreenWatt_Signed_Docs/Templates/`

### Twilio API
- **Account SID**: `AC_your_twilio_account_sid_here`
- **Auth Token**: `your_twilio_auth_token_here`

#### 🚨 Twilio A2P 10DLC Registration Required for Production

**IMPORTANT:** Before production deployment, Jason must complete Twilio A2P 10DLC registration:

1. **Purchase a Twilio Phone Number**
   - Buy any US local 10-digit number (location doesn't matter for SMS functionality)
   - Update `TWILIO_FROM_NUMBER` environment variable with purchased number
   - Cost: ~$1/month per number

2. **A2P 10DLC Registration Requirements** (for US SMS compliance)
   - **Create a Brand**: Verify company details (name, EIN, contact info)
   - **Register a Campaign**: Describe message use case ("Community solar enrollment confirmation")
   - **Associate Phone Numbers**: Link Twilio numbers to the registered campaign
   - **Timeline**: Setup typically takes under a week, sometimes up to 2-3 weeks with vetting
   - **Cost**: Registration fees $4-$44 + $15 per campaign + ~$2-$10/month per campaign

3. **What Jason Needs to Provide:**
   - Business information (legal name, EIN, address, contact email)
   - Campaign details (use case, example message content, opt-in/opt-out copy)
   - Phone number(s) to register under 10DLC

4. **Without A2P 10DLC Registration:**
   - Messages may be filtered or blocked by carriers
   - Higher carrier fees may apply
   - Reduced deliverability for business messaging

**Current Status**: Trial account with no phone number purchased. Registration must be completed before production SMS deployment.

### SendGrid API
- **API Key**: `SG.your_sendgrid_api_key_here`

### OpenAI API
- **API Key**: `sk-proj-your_openai_api_key_here`

### Local Development Fallback
If `GOOGLE_SERVICE_ACCOUNT_JSON` is not set, the app falls back to reading `upwork-greenwatt-drive-sheets-3be108764560.json` for local development.

### SSL Certificate Issues & Render.com Deployment

**Development Environment SSL Issue:**
- Local development environments may encounter `SSL: CERTIFICATE_VERIFY_FAILED` errors with SendGrid
- This is due to corporate firewalls/proxies using self-signed certificates
- **Solution:** Set `DISABLE_SSL_VERIFICATION="true"` for local testing only

**Render.com Production Deployment:**
✅ **SSL issues are automatically resolved in production** - Render.com provides:
- Fully managed TLS certificates for all deployments
- Clean SSL environment without corporate proxies/interceptors  
- No SSL verification issues in production (confirmed by multiple developers)
- Automatic HTTPS with proper certificate chains

**Important:** Never set `DISABLE_SSL_VERIFICATION="true"` in production. The environment variable should be omitted or set to `"false"` on Render.com for security.

## Testing Infrastructure

### Built-in Test Routes
- `/test` - Basic test dashboard
- `/phase1-test` - Comprehensive Phase 1 testing with pre-filled data
- `/test-pdf` - JSON endpoint for testing PDF generation

### Mock Data System
When `test_utility_bill` appears in filename or processing fails, the system returns consistent mock data for testing.

## Security Considerations

### Input Validation
- File uploads restricted to PDF, JPEG, PNG with 16MB limit
- All user input escaped in PDF generation
- Secure filename handling with werkzeug

### Credential Management
- All secrets via environment variables
- Service account with minimal required permissions
- No hardcoded credentials in code

## Development Workflow

### Adding New Utilities
1. Add row to `Utilities` tab in Google Sheets with TRUE flag
2. Add corresponding rows to `Developer_Mapping` tab
3. Upload agreement templates to Google Drive `GreenWatt_Templates` folder
4. No code changes required

### Adding New Developers
1. Add rows to `Developer_Mapping` tab for each utility combination
2. Upload agreement templates to Google Drive
3. System automatically detects new developers for dropdown

### Debugging Tips
- Check Google Sheets tabs for configuration issues
- Verify service account permissions for Google APIs
- Monitor console logs for detailed error messages
- Use test routes to isolate issues

## Phase Implementation Status

**Phase 1 Complete**: Foundation & Infrastructure
- Google Sheets dynamic lookup ✅
- Google Drive integration ✅
- Basic PDF generation ✅
- Email notifications ✅

**Phase 2 Complete**: Form Enhancement
- Business Entity field ✅
- Account Type dropdown ✅
- Enhanced validation ✅

**Phase 3 Complete**: PDF Template Processing
- Template-based generation with pixel-perfect placement ✅
- Signature font implementation (Arizonia cursive) ✅
- Unique POA ID generation ✅
- POA Page 1 field population ✅

**Phase 4 Mostly Complete**: SMS Integration
- Customer verification workflow triggered on form submit ✅
- Y/N response parsing via Twilio webhook ✅
- Internal team SMS notifications ✅ 
- Enhanced email notifications ✅
- **PENDING JASON:** 
  - Purchase Twilio phone number & A2P 10DLC registration
  - Add SMS response columns to Google Sheets structure
  - SMS status tracking (sent/pending/responded)
  - Phone number → submission row mapping

**Phase 5 Pending**: Testing & Deployment
- Comprehensive test suite
- Production deployment

## Testing and Development Instructions for Claude

### Pre-Run Configuration
- Before running the server, ensure that all API keys associated with any test or production run are properly configured. This includes keys for Google Cloud, Twilio, SendGrid, and OpenAI.

### Automated Testing with Playwright MCP Server
- Use the Playwright MCP server for all frontend testing, console log checks, and server log references.
- You have the autonomy to perform these tests without needing to ask for permission.

### Running the Server
- The application should be run on port 5001.
- After making any code changes, restart the server and then start it up again to run your tests.

### Testing Workflow
1. Make necessary code changes.
2. Restart the server on port 5001.
3. Use Playwright MCP server to:
   - View the frontend.
   - Check console logs.
   - Refer to server logs.
4. Conduct tests autonomously to ensure functionality and performance.
5. After the server has been successfully shut down and restarted, run the appropriate curl command to access the browser using Playwright MCP.

## Server Management

- Pat will always start the server.

## GitHub Contribution Guidelines

**Repository**: [greenwatt-intake-pats-account-v2](https://github.com/per-simmons/greenwatt-intake-pats-account-v2)

### Important Guidelines for Git Commits:
- **NEVER** include "Co-authored-by: Claude" in commit messages
- **NEVER** list Claude as a contributor in any capacity
- All commits should be attributed solely to the human developer
- Use standard commit message format without any AI attribution

### Commit Message Format:
```bash
# ✅ CORRECT - Clean commit without AI attribution
git commit -m "Add SMS verification workflow to intake form"

# ❌ INCORRECT - Never include Claude attribution
git commit -m "Add SMS verification workflow to intake form

Co-authored-by: Claude <claude@anthropic.com>"
```

### Repository Access:
- Push changes to the GitHub repository when instructed to "push changes"
- Note: This repository address will eventually change to the client's own repository

