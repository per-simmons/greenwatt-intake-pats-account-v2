# Dynamic Google Sheets Integration - Sandbox Implementation Roadmap

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