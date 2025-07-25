# GreenWatt Intake System - Implementation Roadmap

## Executive Summary
This roadmap outlines the step-by-step implementation plan to bring the current GreenWatt intake system up to full PRD specifications. The approach is divided into 5 phases, each building upon the previous with clear testing checkpoints.

## Current State vs Target State

### ✅ What's Working
- Basic Flask web application with form
- Google Cloud Vision OCR + OpenAI LLM parsing
- Basic PDF generation (template-based)
- Google Drive integration
- Google Sheets logging
- Email notifications

### ❌ What's Missing
- Dynamic Google Sheets integration (Agents, Utilities, Developer_Mapping tabs)
- Proper PDF template processing with signature overlay
- SMS integration (customer verification + internal notifications)
- Complete form fields (Business Entity, Account Type)
- Agreement mapping logic based on Developer + Utility + Account Type

---

## PHASE 1: Foundation & Infrastructure Setup
**Goal**: Establish solid data connections and update service accounts

### 1.1 Service Account Update
- [ ] Update `SERVICE_ACCOUNT_JSON` environment variable with new credentials
- [ ] Test Google Drive access with new service account
- [ ] Test Google Sheets access with new service account
- [ ] Update Google Cloud Vision API access

### 1.2 Google Sheets Structure Setup
- [ ] Create/verify `Agents` tab in Agent sheet (ID: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I`)
  - Column A: `agent_id`
  - Column B: `agent_name`
- [ ] Create `Utilities` tab in main sheet (ID: `11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o`)
  - Column A: `utility_name`
  - Column B: `active_flag` (TRUE/FALSE)
- [ ] Create `Developer_Mapping` tab in main sheet
  - Column A: `developer_name`
  - Column B: `utility_name` (or "Mass Market")
  - Column C: `file_name`
- [ ] Populate initial data in all tabs

### 1.3 Environment Variables Update
- [ ] Update all Sheet IDs and Drive folder IDs in environment
- [ ] Add Twilio credentials to environment
- [ ] Add OpenAI API key verification
- [ ] Test all external service connections

### 1.4 Dependencies Update
- [ ] Add `twilio` to requirements.txt
- [ ] Add `PyPDF2` or `pypdf` for PDF manipulation
- [ ] Add `cachetools` for sheet data caching
- [ ] Test dependency installation

**Acceptance Criteria**: All external services connect successfully with new credentials

---

## PHASE 2: Form Enhancement & Dynamic Data Integration
**Goal**: Complete the form and make it dynamic based on Google Sheets

### 2.1 Form Field Additions
- [ ] Add "Legal Business Entity Name" (optional field)
- [ ] Add "Account Type" dropdown:
  - Small Demand <25 KW
  - Large Demand >25 KW  
  - Mass Market [Residential]
- [ ] Update form validation for new fields

### 2.2 Google Sheets Lookup Functions
- [ ] Implement `get_agent_name(agent_id)` function
- [ ] Implement `get_active_utilities()` function with caching
- [ ] Implement `get_active_developers()` function
- [ ] Implement `get_developer_agreement(developer, utility, account_type)` function
- [ ] Add 15-minute TTL cache for all sheet lookups

### 2.3 Dynamic Form Population
- [ ] Update route to pass dynamic utilities list to template
- [ ] Update route to pass dynamic developers list to template
- [ ] Update template to render dynamic dropdowns
- [ ] Add JavaScript for conditional field requirements (POID for NYSEG/RG&E)

### 2.4 Backend Form Processing Updates
- [ ] Update form submission handler to use agent name lookup
- [ ] Update submission to log both agent ID and resolved name
- [ ] Add validation for new required fields
- [ ] Update Google Sheets logging with new columns

**Acceptance Criteria**: Form populates dynamically from sheets, all new fields work

---

## PHASE 3: Document Processing & PDF Template Integration
**Goal**: Replace generated PDFs with actual template processing and signature overlay

### 3.1 PDF Template Analysis ✅ COMPLETED
- [x] Analyze existing PDF templates in `/GreenWatt-documents/`
- [x] Map signature placement coordinates for each template
- [x] Identify fillable form fields in templates
- [x] Test PDF reading and writing with PyPDF2/pypdf

### 3.2 Agreement Selection Logic ✅ COMPLETED
- [x] Implement developer + utility + account type mapping
- [x] Add "Mass Market" special case handling
- [x] Create agreement file path resolution
- [x] Add error handling for missing agreements

### 3.3 PDF Processing Implementation ✅ COMPLETED
- [x] Replace `generate_poa_pdf()` to use actual POA template
- [x] Replace `generate_agreement_pdf()` to use mapped agreement template
- [x] Implement signature overlay on existing templates
- [x] Add unique POA ID generation and stamping

### 3.4 Document Integration Testing ✅ COMPLETED
- [x] Test all developer + utility combinations
- [x] Verify signature placement accuracy
- [x] Test with sample documents from PRD
- [x] Validate PDF output quality

### 3.5 **COMPLETED**: Pixel-Perfect Signature & Field Overlay System ✅
**Goal**: Implement anchor-text based signature placement with pixel-perfect precision

#### 3.5.1 Library Dependencies ✅
- [x] Add `pdfplumber` to requirements.txt for coordinate extraction
- [x] Update `reportlab` for overlay PDF generation
- [x] Ensure `pypdf` ≥ 3.0 for advanced merging capabilities
- [x] Test all libraries work together

#### 3.5.2 Anchor Mapping System ✅
- [x] Create anchor dictionaries for each agreement template
- [x] Map signature field locations: Customer Signature, Printed Name, Date, Email
- [x] Define offset values (dx, dy) for precise placement
- [x] Create shared anchor configuration for UCB agreement series

#### 3.5.3 Coordinate Detection Engine ✅
- [x] Implement `find_anchor_across_pages()` function using pdfplumber
- [x] Extract word coordinates with proper tolerance settings
- [x] Handle anchor text variations across templates
- [x] Add error handling for missing anchors

#### 3.5.4 Overlay Generation System ✅
- [x] Build `create_overlay_pdf()` function using reportlab
- [x] Create transparent overlay PDFs with exact positioning
- [x] Implement signature font styling (Arizonia cursive/script appearance)
- [x] Handle multi-page documents and coordinate transformations

#### 3.5.5 PDF Merging & Finalization ✅
- [x] Implement precise PDF merging with pypdf
- [x] Preserve original template formatting and quality
- [x] Add validation for successful merges

#### 3.5.6 Enhanced POA ID System ✅
- [x] Update POA ID generation to include UUID components
- [x] Format: `POA-{YYYYMMDDHHMMS}-{uuid_hex}`
- [x] Ensure POA ID placement on actual template coordinates
- [x] Test POA ID visibility and readability

#### 3.5.7 Template-Specific Configuration ✅
- [x] Create anchor mappings for National Grid UCB agreements
- [x] Create anchor mappings for NYSEG UCB agreements  
- [x] Create anchor mappings for RG&E UCB agreements
- [x] Create anchor mappings for Mass Market agreements
- [x] Test signature placement accuracy for each template

#### 3.5.8 Integration & Testing ✅
- [x] Replace current signature overlay system with anchor-based system
- [x] Test pixel-perfect placement across all templates
- [x] Validate signature appearance matches Adobe PDF standards (Arizonia font)
- [x] Perform end-to-end testing with real document generation

**Acceptance Criteria**: System places signatures and data with pixel-perfect precision using anchor-text detection ✅

### 3.6 **COMPLETED**: Document ID & Timestamp Integration ✅
**Goal**: Add unique identifiers and generation timestamps to all PDF documents

#### 3.6.1 POA Document Enhancement ✅
- [x] Add Submission ID (SUB-YYYYMMDDHHMSS-xxxxxx) below customer phone number field
- [x] Add POA ID (POA-YYYYMMDDHHMSS-xxxxxx) below customer phone number field  
- [x] Add generation timestamp in format "Generated 12/18/2024 at 2:17 PM EST"
- [x] Create anchor mapping for phone number field placement
- [x] Implement precise coordinate offset calculation for ID placement

#### 3.6.2 Community Solar Agreement Enhancement ✅
- [x] Add Submission ID (SUB-YYYYMMDDHHMSS-xxxxxx) below Title field in Subscriber section
- [x] Add generation timestamp in format "Generated 12/18/2024 at 2:17 PM EST"
- [x] Create anchor mapping for Title field in Subscriber section
- [x] Focus on Meadow Energy templates (primary use case)
- [x] Ensure placement doesn't interfere with signature areas

#### 3.6.3 Timestamp Generation System ✅
- [x] Implement EST timezone-aware timestamp generation with pytz
- [x] Create consistent timestamp format across all documents
- [x] Ensure timestamp reflects actual document generation time
- [x] Add timestamp to both overlay generation and Google Sheets logging

#### 3.6.4 Anchor Configuration Updates ✅
- [x] Add phone number anchor detection to POA templates ("Phone Number" anchor)
- [x] Add Title field anchor detection to UCB agreement templates
- [x] Test coordinate accuracy for new ID/timestamp placement
- [x] Verify text doesn't overlap with existing form fields

#### 3.6.5 Integration Testing ✅
- [x] Test POA documents show both Submission ID and POA ID with timestamp
- [x] Test Community Solar Agreements show only Submission ID with timestamp
- [x] Verify placement positioning is consistent across template variations
- [x] Validate timestamp accuracy and EST timezone formatting

#### 3.6.6 Professional Formatting Enhancement ✅
- [x] Format fields with labels: "Unique ID: [id]" and "Date Generated: [timestamp]"
- [x] Position fields with adequate white space for professional appearance
- [x] Test both POA and Agreement templates successfully

**Acceptance Criteria**: All generated PDFs include appropriate unique identifiers and generation timestamps with precise placement ✅

### 3.7 **COMPLETED**: Meadow Agreement Subscriber Fields Implementation ✅  
**Goal**: Populate subscriber information fields on page 7 of all Meadow agreements (National Grid, NYSEG, RGE)

#### 3.7.1 PDF Text Analysis & Anchor Detection ✅
- [x] Extract text from page 7 of Meadow agreement templates using pdfplumber
- [x] Identify anchor text for Subscriber section (likely "Subscriber" or "SUBSCRIBER")  
- [x] Map exact coordinates for 5 subscriber fields to the right of labels:
  - [x] Attention field coordinate mapping
  - [x] Business Name field coordinate mapping  
  - [x] Address field coordinate mapping
  - [x] Email field coordinate mapping
  - [x] Phone field coordinate mapping

#### 3.7.2 Anchor Configuration Updates ✅
- [x] Add subscriber field anchors to `UCB_COMMERCIAL_ANCHORS` in `anchor_mappings.py`
- [x] Calculate dx/dy offsets for proper right-alignment of text
- [x] Test coordinate accuracy across all three Meadow templates
- [x] Verify text positioning doesn't interfere with signature areas

#### 3.7.3 Field Processing Logic Enhancement ✅
- [x] Add subscriber field mapping logic to `anchor_pdf_processor.py`:
  - [x] `subscriber_attention` → `contact_name` from form
  - [x] `subscriber_business_name` → `business_entity` from form (fallback to `account_name`)
  - [x] `subscriber_address` → `service_addresses` from form
  - [x] `subscriber_email` → `email` from form  
  - [x] `subscriber_phone` → `phone` from form
- [x] Handle business name fallback logic for empty business entity
- [x] Implement address formatting for field constraints

#### 3.7.4 Template Testing & Validation ✅
- [x] Create test script similar to Mass Market customer info test
- [x] Test field population with all three Meadow templates:
  - [x] Meadow-National-Grid-Commercial-UCB-Agreement.pdf
  - [x] Meadow-NYSEG-Commercial-UCB-Agreement.pdf  
  - [x] Meadow-RGE-Commercial-UCB-Agreement.pdf
- [x] Verify field alignment and text legibility
- [x] Test with various data lengths (long business names, addresses)

#### 3.7.5 Integration Testing ✅
- [x] Test complete form submission flow with subscriber field population
- [x] Verify fields appear correctly alongside existing signature functionality
- [x] Test with different account types (Small Demand, Large Demand)
- [x] Validate that page 7 subscriber info doesn't affect other pages

#### 3.7.6 **ENHANCEMENT COMPLETED**: Page 2 Agreement Header Fields ✅
- [x] Add effective date field with today's date (MM/DD/YYYY format)
- [x] Add business name field mapped to account_name from form
- [x] Position fields in blank lines after "Effective Date" and "between" anchors
- [x] Fine-tune positioning through iterative testing for pixel-perfect alignment

**Acceptance Criteria**: All Meadow agreements automatically populate subscriber information fields on page 7 AND agreement header fields on page 2 with form data, properly positioned and formatted ✅

---

## PHASE 4: SMS Integration & Enhanced Notifications
**Goal**: Add complete SMS workflow and improve notifications

### 4.1 Twilio Integration Setup
- [x] Add Twilio client initialization
- [x] Create SMS sending service class
- [x] Add phone number validation and formatting
- [ ] **🚨 REQUIRED: Purchase Twilio Phone Number & A2P 10DLC Registration**
  - [ ] Purchase US local phone number from Twilio (~$1/month)
  - [ ] Complete A2P 10DLC brand registration (business details, EIN)
  - [ ] Register SMS campaign ("Community solar enrollment confirmation")
  - [ ] Associate phone number with registered campaign
  - [ ] Update `TWILIO_FROM_NUMBER` environment variable
- [ ] Test SMS sending capability with registered phone number

### 4.2 Customer Verification SMS
- [x] Implement post-submission customer SMS
- [x] Add SMS response webhook endpoint
- [ ] **🚨 PENDING JASON: Add SMS response columns to Google Sheets**
  - [ ] Add columns: SMS Sent, SMS Sent Timestamp, SMS Response, SMS Response Timestamp, Phone Number, Message SID
  - [ ] Implement `sheets_service.log_sms_response()` method
- [x] Add Y/N response validation and processing

### 4.3 Internal Team Notifications
- [x] Add SMS alerts to internal team for new submissions
- [x] Update email notifications with enhanced formatting
- [x] Add submission summary with key metrics
- [x] Include links to generated documents

### 4.4 SMS Response Handling
- [x] Create webhook endpoint for Twilio responses
- [x] Parse and validate customer Y/N responses  
- [ ] **🚨 PENDING JASON: Complete Google Sheets SMS logging integration**
- [x] Handle edge cases (invalid responses, late responses)

**Acceptance Criteria**: Complete SMS workflow with customer verification and team notifications

---

## PHASE 5: Testing, Polish & Deployment
**Goal**: Comprehensive testing and production readiness

### 5.1 End-to-End Testing
- [ ] Test complete workflow with each utility
- [ ] Test all developer + utility + account type combinations
- [ ] Verify Google Sheets logging accuracy
- [ ] Test SMS workflows with real phone numbers

### 5.2 Error Handling & Resilience
- [ ] Add comprehensive try/catch blocks
- [ ] Implement graceful degradation for service failures
- [ ] Add logging for debugging
- [ ] Create health check endpoint

### 5.3 Performance & Optimization
- [ ] Optimize sheet lookup caching
- [ ] Add file cleanup routines
- [ ] Optimize PDF processing performance
- [ ] Add request timeout handling

### 5.4 Documentation & Deployment
- [ ] Update README with new setup instructions
- [ ] Document environment variables
- [ ] Create deployment checklist
- [ ] Test production deployment
- [x] **SSL Certificate Resolution**: Confirmed Render.com auto-resolves SSL issues (no `DISABLE_SSL_VERIFICATION` needed in production)

**Acceptance Criteria**: System is production-ready with comprehensive error handling

---

## SSL Certificate Deployment Resolution

### ✅ **Issue Identified & Resolved**
**Development Environment:**
- SSL verification failures with SendGrid API due to corporate firewall/proxy self-signed certificates
- **Solution:** `DISABLE_SSL_VERIFICATION="true"` environment variable for local testing

**Production Environment (Render.com):**
✅ **SSL issues automatically resolved** - Render.com provides:
- Fully managed TLS certificates for all deployments
- Clean SSL environment without corporate proxies/interceptors
- No SSL verification issues in production (confirmed by multiple developers)
- Automatic HTTPS with proper certificate chains

**Deployment Strategy:**
- **Development:** Set `DISABLE_SSL_VERIFICATION="true"` for testing
- **Production:** Omit `DISABLE_SSL_VERIFICATION` or set to `"false"` for security
- **No code changes** required between environments

---

## Implementation Dependencies

### Critical Path Items
1. **Service Account Access** → All subsequent phases depend on this
2. **Google Sheets Structure** → Required for dynamic form functionality
3. **PDF Template Access** → Required for document generation
4. **Twilio A2P 10DLC Registration** → Required for SMS functionality in production

### Parallel Development Opportunities
- Form enhancements can be developed while PDF processing is being built
- SMS integration can be built independently of document processing
- Testing frameworks can be set up during development phases

### Risk Mitigation
- **PDF Template Risk**: Test PDF manipulation early, have fallback to current generation method
- **SMS Integration Risk**: Implement basic SMS first, enhance with response handling later
- **Google Sheets Risk**: Maintain fallback to hardcoded values if sheets are unavailable
- **SSL Certificate Risk**: Resolved - Render.com provides managed TLS certificates with no SSL verification issues
- **Twilio A2P 10DLC Risk**: Registration process can take 1-3 weeks; begin early or use alternative verification methods during development

---

## Success Metrics

### Phase Completion Criteria
Each phase must pass all acceptance criteria before moving to the next phase.

### Overall Success Metrics
- ✅ 100% PRD feature coverage
- ✅ All external integrations working
- ✅ End-to-end workflow tested and documented
- ✅ Production deployment successful
- ✅ Jason can manage utilities/developers via Google Sheets without code changes

## Next Steps
1. Review and approve this roadmap
2. Set up development environment with new service accounts
3. Begin Phase 1 implementation
4. Establish regular check-ins for each phase completion