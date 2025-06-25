# Dynamic Google Sheets Integration - Sandbox Implementation Roadmap

## What This System Does (Plain English)

### **The Problem This Solves:**
Currently, when the client wants to make business changes, they need a developer:
- **Add a new utility company?** → Call developer, change code, redeploy website
- **Add a new solar developer/operator?** → Call developer, change code, redeploy website  
- **Change which agreement goes with which combination?** → Call developer, change code, redeploy website
- **Update contract templates?** → Call developer, update files, redeploy website

### **What This System Enables:**
The client can manage their entire business logic through simple Google Sheets - **no coding required**:

#### **What the Client Can Do Themselves:**
1. **Add/Remove Utility Companies**: 
   - Right now the client doesn't work with the utility companies: Orange & Rockland, Central Hudson, or ConEd. But he will in the future
   - This gives him the ability to edit "Utilities" tab in Google Sheet
   - Set active_flag to TRUE (appears in dropdown) or FALSE (hidden)
   - Changes appear on the form within 15 minutes

2. **Add/Remove Solar Developers**:
   - Right now the client only works with the solar developer Meadow
   - But in the future he will also be working with Solar Simplified
   - This setup allows him to: add a new row to "Developer_Mapping" tab
   - Solar Simplified will automatically appear 

3. **Manage Agreement Templates**:
   - Upload new PDF templates to Google Drive "Templates" folder
   - Map which template goes with each Developer + Utility combination
   - System automatically selects correct agreement for each submission

4. **Control Business Logic**:
   - Want to temporarily hide a utility? Set flag to FALSE
   - New developer partnership? Add their templates and mappings
   - Different agreement for different account types? All configurable

#### **What Happens Automatically:**
- Form dropdowns update to show only active utilities/developers
- System picks the right agreement template based on customer selections
- All submissions logged with proper template tracking
- **Zero code changes or deployments needed**

#### **Example Workflow:**
```
Client wants to add "Orange & Rockland" utility:
OLD WAY: Call developer → Code changes → Test → Deploy (days/weeks)
NEW WAY: Edit Google Sheet → Wait 15 minutes → Done (minutes)
```

#### **Current System Setup (Ready for Jason's Use):**

**Google Sheet Name**: "GreenWatt_Intake_Log_FOR DYNAMIC FORM REVISIONS"
- **URL**: https://docs.google.com/spreadsheets/d/1mMbbZxRrzHf_jlSWC6WWYLiByL1pGZ9kNOxyvizSLys/edit
- **Sheet ID**: `1mMbbZxRrzHf_jlSWC6WWYLiByL1pGZ9kNOxyvizSLys`
- **Purpose**: Jason can edit this sheet to control what appears on the intake form

**Google Drive Folder Name**: "GreenWatt_Dynamic_Intake" 
- **URL**: https://drive.google.com/drive/folders/1rT3Nl9Vi8JtDkY1OP_NxdPiK6JE3I7Us
- **Folder ID**: `1rT3Nl9Vi8JtDkY1OP_NxdPiK6JE3I7Us`
- **Templates Subfolder**: "Templates" (where Jason uploads new contract PDFs)

#### **How Jason Manages Contract Templates:**
Note: In order to ensure proper OCR mapping to the PDF's, the new Solar Simplified agreement should match the format of previous Meadow agreements
**Step 1: Upload New Contract PDF**
- Go to Google Drive folder: "GreenWatt_Dynamic_Intake" → "Templates"
- Upload new PDF with any name (e.g., "Solar-Simplified-NYSEG-Agreement-v3.pdf")
- No special naming rules - Jason can name it whatever makes sense

**Step 2: Update the Mapping**
- Open Google Sheet: "GreenWatt_Intake_Log_FOR DYNAMIC FORM REVISIONS"
- Go to "Developer_Mapping" tab
- Add or edit a row:
  ```
  | Solar Simplified | NYSEG | Solar-Simplified-NYSEG-Agreement-v3.pdf |
  ```
- File name in sheet MUST match exactly what was uploaded

**Step 3: Automatic Results**
- Within 15 minutes, when someone selects "Solar Simplified" + "NYSEG" on the form
- System automatically finds and uses the new PDF
- No website restarts or code changes needed

**Adding New Utilities (Future Use)**
- Go to "Utilities" tab in Google Sheet
- Change active_flag from FALSE to TRUE for any utility
- New utility appears in dropdown within 15 minutes

**Adding New Solar Developers**
- Go to "Developer_Mapping" tab 
- Add rows for new developer with all their utility combinations
- Upload their contract templates to "Templates" folder
- New developer appears in dropdown automatically

## Overview
This document outlines the complete process for creating a sandbox environment to test dynamic Google Sheets integration for the GreenWatt intake form. The sandbox will allow testing of dynamic utilities, developers, and agreement mapping without affecting the production system.

## Goals
1. Create a completely isolated sandbox environment
2. Test dynamic dropdown population from Google Sheets
3. Verify agreement template selection logic
4. Ensure POID requirement logic remains intact
5. Deploy to Render for live testing

## Phase 1: Google Resources Setup

### 1.1 Create Sandbox Google Sheet
**Name**: `GreenWatt Sandbox Intake Log`

**Required Tabs**:
1. **Submissions** (main data tab)
   - Copy exact structure from production sheet
   - Headers: Unique ID, Submission Date, Business Entity Name, etc.

2. **Utilities** tab structure:
   ```
   | utility_name      | active_flag |
   |-------------------|-------------|
   | National Grid     | TRUE        |
   | NYSEG             | TRUE        |
   | RG&E              | TRUE        |
   | Orange & Rockland | FALSE       |
   | Central Hudson    | FALSE       |
   | ConEd             | FALSE       |
   ```

3. **Developer_Mapping** tab structure:
   ```
   | developer_name    | utility_name   | file_name                                    |
   |-------------------|----------------|----------------------------------------------|
   | Meadow Energy     | National Grid  | Meadow-National-Grid-Commercial-UCB.pdf      |
   | Meadow Energy     | NYSEG          | Meadow-NYSEG-Commercial-UCB.pdf              |
   | Meadow Energy     | RG&E           | Meadow-RGE-Commercial-UCB.pdf                |
   | Meadow Energy     | Mass Market    | Form-Subscription-Mass-Market-Meadow.pdf     |
   | Solar Simplified  | National Grid  | Solar-National-Grid-Commercial-UCB.pdf       |
   | Solar Simplified  | NYSEG          | Solar-NYSEG-Commercial-UCB.pdf               |
   | Solar Simplified  | RG&E           | Solar-RGE-Commercial-UCB.pdf                 |
   | Solar Simplified  | Mass Market    | Form-Subscription-Mass-Market-Solar.pdf      |
   ```

4. **Agents** tab (optional for testing)

**Sharing**: 
- Share with: `greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com`
- Permission: Editor

### 1.2 Create Sandbox Google Drive Folder
**Name**: `GreenWatt_Sandbox_Docs`

**Structure**:
```
GreenWatt_Sandbox_Docs/
├── Templates/
│   ├── Meadow-National-Grid-Commercial-UCB.pdf
│   ├── Meadow-NYSEG-Commercial-UCB.pdf
│   ├── Meadow-RGE-Commercial-UCB.pdf
│   ├── Form-Subscription-Mass-Market-Meadow.pdf
│   └── (other agreement PDFs)
└── (uploaded documents will go here)
```

**Sharing**: Same service account with Editor permission

## Phase 2: Code Implementation

### 2.1 Environment Variables
Add to `.env` and Render:
```bash
# Sandbox Environment
SANDBOX_GOOGLE_SHEETS_ID="your_sandbox_sheet_id"
SANDBOX_GOOGLE_DRIVE_FOLDER_ID="your_sandbox_folder_id"
SANDBOX_ENABLED="true"
```

### 2.2 Create Sandbox Route (`/sandbox`)
- New route in `app.py`
- Separate template: `templates/sandbox.html`
- Use sandbox-specific Google Sheets/Drive services

### 2.3 Frontend Implementation
1. **Dynamic Dropdowns**: 
   - Populate utilities from Sheets (active_flag = TRUE)
   - Populate developers from unique entries in Developer_Mapping
   
2. **POID Logic** (Option 2 - Keep consistent):
   - JavaScript will check for exact matches: "NYSEG" and "RG&E"
   - Document requirement: These utility names must remain consistent

3. **Separate JavaScript**: `static/js/sandbox.js`
   - Copy main.js functionality
   - Add dynamic dropdown population

### 2.4 Backend Modifications
1. Create sandbox-specific service instances
2. Implement dynamic utility/developer fetching
3. Use sandbox Google Drive for uploads
4. Log to sandbox Google Sheet

## Phase 3: Testing Workflow

### 3.1 Basic Functionality Tests
1. **Dynamic Dropdown Test**:
   - Add new utility to Utilities tab with TRUE flag
   - Refresh sandbox page
   - Verify new utility appears in dropdown

2. **Developer Mapping Test**:
   - Add new developer with agreement mappings
   - Verify developer appears in dropdown
   - Test form submission with new developer

3. **Agreement Selection Test**:
   - Submit form with different developer/utility combinations
   - Verify correct PDF template is selected from mapping

### 3.2 Advanced Testing Scenarios

#### Test Case 1: Add New Utility
1. In sandbox sheet, add: `| Con Edison | TRUE |`
2. Add developer mappings for Con Edison
3. Upload Con Edison agreement templates to Drive
4. Test full submission flow

#### Test Case 2: Disable Utility
1. Change utility active_flag to FALSE
2. Verify it disappears from dropdown
3. Ensure existing submissions still display correctly

#### Test Case 3: New Developer
1. Add "Green Power Solutions" to Developer_Mapping
2. Add all utility combinations
3. Upload agreement templates
4. Test form submission

#### Test Case 4: Mass Market Priority
1. Select "Mass Market [Residential]" account type
2. Verify system uses Mass Market template even with utility selection
3. Confirm correct agreement is generated

### 3.3 POID Requirement Testing
1. Select "NYSEG" - verify POID becomes required
2. Select "RG&E" - verify POID becomes required
3. Select "National Grid" - verify POID is optional
4. Test form submission with/without POID

## Phase 4: Deployment

### 4.1 Render Deployment
1. Add sandbox environment variables to Render
2. Deploy application
3. Access via: `https://your-app.onrender.com/sandbox`

### 4.2 Production Migration Checklist
Once sandbox testing is complete:
1. Update production `index.html` with dynamic dropdowns
2. Ensure production sheet has Utilities and Developer_Mapping tabs
3. Document utility naming requirements (NYSEG/RG&E must not change)
4. Clear caches after migration
5. Monitor for any issues

## Phase 5: Maintenance & Documentation

### 5.1 Client Documentation
Create guide for client showing:
1. How to add/remove utilities
2. How to add new developers
3. How to map agreements to developer/utility combinations
4. Template file naming conventions

### 5.2 Technical Documentation
- Document the 15-minute cache TTL
- Explain fallback mechanisms
- POID logic dependencies
- Agreement selection algorithm

## Testing Checklist

- [ ] Sandbox Google Sheet created and shared
- [ ] Sandbox Drive folder created with Templates subfolder
- [ ] Environment variables configured
- [ ] `/sandbox` route implemented
- [ ] Dynamic dropdowns working
- [ ] POID logic functioning for NYSEG/RG&E
- [ ] Agreement template selection working
- [ ] Full submission flow tested
- [ ] PDFs generating correctly
- [ ] Documents uploading to sandbox Drive
- [ ] Data logging to sandbox Sheet
- [ ] Deployed to Render
- [ ] Live testing completed

## Important Notes

### Utility Naming Consistency
**CRITICAL**: The following utility names must remain exactly as shown for POID logic:
- "NYSEG" (not "NY State Electric & Gas" or any variation)
- "RG&E" (not "Rochester Gas & Electric" or any variation)

### Agreement File Naming
- Files must match exactly as specified in Developer_Mapping tab
- Include file extension (.pdf)
- Case-sensitive matching

### Cache Behavior
- Changes to Google Sheets may take up to 15 minutes to appear
- Use `sheets_service.clear_cache()` for immediate updates during testing

## Enhanced Testing Routes

### Available Test Endpoints:
- **`/sandbox`** - Main sandbox form with dynamic dropdowns
- **`/sandbox-test`** - Configuration verification and connectivity test
- **`/sandbox-clear-cache`** - Clear cache for immediate testing (no 15-minute wait)

## Troubleshooting Guide

### Common Issues and Solutions:

#### 1. "Sandbox environment is not enabled"
- **Cause**: `SANDBOX_ENABLED` not set to `true`
- **Solution**: Add `SANDBOX_ENABLED=true` to environment variables

#### 2. "Sandbox not configured"
- **Cause**: Missing `SANDBOX_GOOGLE_SHEETS_ID` or `SANDBOX_GOOGLE_DRIVE_FOLDER_ID`
- **Solution**: Create sandbox resources and add IDs to environment

#### 3. Empty Dropdowns
- **Cause**: Missing tabs in Google Sheet or incorrect data format
- **Solution**: 
  - Verify "Utilities" tab exists with columns: `utility_name | active_flag`
  - Verify "Developer_Mapping" tab exists with columns: `developer_name | utility_name | file_name`
  - Check that active_flag values are exactly "TRUE" (case-sensitive)

#### 4. "No template mapping found" 
- **Cause**: Missing developer/utility combination in Developer_Mapping tab
- **Solution**: Add row with exact developer and utility names from form dropdowns

#### 5. Cache Not Updating
- **Cause**: 15-minute cache TTL hasn't expired
- **Solution**: Use `/sandbox-clear-cache` endpoint for immediate updates

#### 6. POID Field Not Working
- **Cause**: Utility names in Google Sheets don't exactly match "NYSEG" or "RG&E"
- **Solution**: Ensure exact spelling - "NYSEG" and "RG&E" (case-sensitive)

### Template File Requirements:
- Files must exist in Google Drive Templates folder
- File names must exactly match what's in Developer_Mapping tab
- Include .pdf extension in mapping
- Case-sensitive matching

### Cache Management:
- Changes take up to 15 minutes to appear normally
- Use `/sandbox-clear-cache` for immediate testing
- Production should rarely need cache clearing

## Rollback Plan
If issues arise:
1. Sandbox remains isolated - no production impact
2. Main form continues using hardcoded dropdowns
3. Can disable sandbox route without affecting production
4. All sandbox data is separate and can be deleted

## Success Criteria
1. Client can add/modify utilities without code changes
2. Client can add new developers and agreements
3. Form dynamically updates based on Sheet changes
4. All existing functionality remains intact
5. No impact to production during testing
6. Robust error handling for missing templates
7. Clear troubleshooting documentation