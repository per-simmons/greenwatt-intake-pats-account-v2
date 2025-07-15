# Google Workspace Migration Test Guide

## Quick Test Commands

Run these commands to verify the migration is working correctly:

### 1. Test Server Availability
```bash
curl http://localhost:5001/test
```
**Expected**: HTML page should load without errors

### 2. Test Utilities Configuration
```bash
curl http://localhost:5001/api/utilities
```
**Expected**: JSON array with active utilities from new sheet
```json
["National Grid", "NYSEG", "RG&E"]
```

### 3. Test Developers Configuration
```bash
curl http://localhost:5001/api/developers
```
**Expected**: JSON array with developers from new sheet
```json
["Meadow Energy"]
```

### 4. Test PDF Generation
```bash
curl -X POST http://localhost:5001/test-pdf \
  -H "Content-Type: application/json" \
  -d '{"utility_provider":"National Grid","developer_assigned":"Meadow Energy"}'
```
**Expected**: Success message with POA and Agreement URLs

### 5. Test Form Submission (Full Test)

1. Navigate to: http://localhost:5001/phase1-test
2. The form should be pre-filled with test data
3. Upload any PDF file (or use the test utility bill)
4. Click Submit

**Expected Results**:
- Progress bar should update through all steps
- Should complete without errors
- Check Google Sheets for new entry
- Check Google Drive for uploaded files

## Manual Verification Checklist

### Google Sheets
- [ ] Open the new Main Intake Sheet
- [ ] Verify new submission appears with all 25 columns filled
- [ ] Check that Utilities tab exists with correct data
- [ ] Check that Developer_Mapping tab exists with Meadow Energy entries

### Google Drive  
- [ ] Open the new GreenWatt_Signed_Docs folder
- [ ] Look for newly created folder (format: BusinessName_YYYYMMDD_HHMMSS)
- [ ] Verify 4 files are created:
  - [ ] Utility bill PDF
  - [ ] POA PDF (signed if terms accepted)
  - [ ] Developer Agreement PDF
  - [ ] Agency Agreement PDF (if applicable)

### Email Notifications
- [ ] Check email for notification (if email service is configured)
- [ ] Verify email contains:
  - Agent Name
  - Customer Name  
  - Utility
  - Signed Date
  - Annual Usage

### SMS Notifications
- [ ] Check phone for SMS (if SMS consent given and service configured)
- [ ] Verify SMS asks for Y/N confirmation for CDG enrollment

## Troubleshooting

### If tests fail:

1. **Server not running**: Start with `python app.py`

2. **403 Forbidden errors**: 
   - Verify service account has Editor access to all resources
   - Check sharing permissions in Google Workspace

3. **Storage quota errors**:
   - Migration may not be complete
   - Verify using Workspace account, not personal Gmail

4. **Missing utilities/developers**:
   - Run setup script again: `python setup_workspace_resources_auto.py`
   - Check sheet structure matches expected format

5. **PDF generation fails**:
   - Check GOOGLE_DRIVE_TEMPLATES_FOLDER_ID is set correctly
   - Verify templates exist in the folder

## Success Indicators

✅ All API endpoints return expected data
✅ Form submission completes without errors  
✅ Files appear in new Google Drive folder
✅ Data appears in new Google Sheets
✅ No storage quota errors
✅ Notifications sent successfully