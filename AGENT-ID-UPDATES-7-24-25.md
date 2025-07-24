# Agent ID Mapping Fix - July 24, 2025

## Issue Summary
The agent ID → agent name mapping was returning "Unknown" for all agent lookups, preventing proper agent identification in the intake form and related notifications.

## Root Causes Identified

### 1. Outdated Environment Variables
The `.env` file contained pre-migration Google Sheets IDs that were no longer valid after the Google Workspace migration completed on January 15, 2025.

**Incorrect (Pre-Migration):**
```bash
GOOGLE_SHEETS_ID=11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o
GOOGLE_DRIVE_PARENT_FOLDER_ID=1i1SAHRnrgA-eWKgaZaShwF3zzOqewO3W
GOOGLE_DRIVE_TEMPLATES_FOLDER_ID=1YPUFTwKP5uzOMTKp1OZcWuwCeZA2nFqE
```

**Corrected (Post-Migration):**
```bash
GOOGLE_SHEETS_ID=1R1bZuDhToHg1bIQtZUWCXQHaCJq8jsXeuKuSFBHdhpw
GOOGLE_DRIVE_PARENT_FOLDER_ID=12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj
GOOGLE_DRIVE_TEMPLATES_FOLDER_ID=1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS
```

### 2. Incorrect Column Mapping
The agent lookup code in `services/google_sheets_service.py` had incorrect column mapping assumptions.

**Agent Sheet Structure (Actual):**
- Column A: `Name` (Agent Name)
- Column B: `ID` (Agent ID)  
- Column C: `Phone #`
- Column D: `Email Address`
- Column E: `Home Territory`
- Column F: `Sales Manager`
- Column G: `Sales Manager Email Address`

**Code Fix Applied:**
```python
# BEFORE (Incorrect):
if len(row) >= 1 and row[0] == agent_id:  # Looking in Column A
    agent_info = {
        "name": row[1],  # Getting name from Column B
        "email": row[3],
        "sales_manager_email": row[6]
    }

# AFTER (Correct):
if len(row) >= 2 and row[1] == agent_id:  # Looking in Column B  
    agent_info = {
        "name": row[0],  # Getting name from Column A
        "email": row[3],
        "sales_manager_email": row[6]
    }
```

## Agent ID Format
Agent IDs are **numeric** (not alphanumeric with prefixes):
- ✅ Valid: `1015`, `1016`, `1017`, `1018`, `1019`, `1020`
- ❌ Invalid: `AG001`, `AG002`, `AG003`

## Testing Results
After fixes were applied, agent lookup is working correctly:

| Agent ID | Agent Name | Email | Status |
|----------|------------|-------|--------|
| 1015 | Charles Cramble | artsandfarms@aol.com | ✅ |
| 1016 | Victor Minna | vittoriominna@gmail.com | ✅ |
| 1017 | Korre Butler | korrebutler7@gmail.com | ✅ |
| 1018 | Heavin Criss | heavenc2005@gmail.com | ✅ |
| 1019 | Devlin Cameron | devcam19@gmail.com | ✅ |
| 1020 | Lora Santiago | womenwihgrace@gmail.com | ✅ |

## Files Modified
1. **`.env`** - Updated Google Sheets and Drive IDs to post-migration values
2. **`services/google_sheets_service.py`** - Fixed column mapping in `get_agent_info()` method (lines 323-331)

## Testing Infrastructure
The system includes comprehensive testing via:
- **`/test-agent-lookup`** endpoint for individual agent testing
- **Bulk testing** for common agent IDs
- **Hardcoded fallbacks** for development (agents 0000, 0001)

## Impact
This fix restores:
- ✅ Agent name display in intake forms
- ✅ Proper agent identification in Google Sheets logging
- ✅ Correct recipient routing for email notifications
- ✅ Accurate agent information in SMS notifications
- ✅ Agent data in PDF generation metadata

## Google Sheets Resource
**Agent ID Spreadsheet:** https://docs.google.com/spreadsheets/d/1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I

**Total Agents:** 83 active agents in system as of July 24, 2025

---

## Email Notification System Implementation ✅

### System Overview
The email notification system is **fully functional** and automatically sends notifications to all required recipients when a form is submitted, using the fixed agent mapping system to dynamically resolve recipient email addresses.

### Email Recipients Configuration

**✅ Three Primary Recipients (All Working):**

1. **Agent Email Notifications**
   - Source: Column D of Agent ID Sheet (dynamically resolved)
   - Tested Examples:
     - Agent 1015 (Charles Cramble): `artsandfarms@aol.com`
     - Agent 1016 (Victor Minna): `vittoriominna@gmail.com`

2. **Operations Team Email**
   - Email: `operations@greenwattusa.com` 
   - Configuration: Hardcoded in `services/email_service.py` (line 42)
   - Delivery: CC recipient (always included)

3. **Sales Manager Email**
   - Source: Column G of Agent ID Sheet (dynamically resolved)
   - Tested Example: `jpritchard@greenwattusa.com`
   - Configuration: Pulled per agent from spreadsheet

**Additional Recipients:**
- `greenwatt.intake@gmail.com` (hardcoded fallback, always included)

### Technical Implementation

**Email Service:** SendGrid API integration  
**Configuration Added to `.env`:**
```bash
# Email Configuration (SendGrid)
SENDGRID_API_KEY=SG.[YOUR_SENDGRID_API_KEY_HERE]

# Development Only - SSL Bypass (DO NOT SET IN PRODUCTION)
DISABLE_SSL_VERIFICATION=true
```

**Email Format:**
- Professional HTML template with GreenWatt branding
- Customer details (agent, customer name, utility, date, usage)
- Plain text fallback included
- Automated system attribution

### Testing Results

**Email Delivery Verification:**
```
✅ Test 1 - Agent 1015 (Charles Cramble):
   TO: artsandfarms@aol.com, jpritchard@greenwattusa.com, greenwatt.intake@gmail.com
   CC: operations@greenwattusa.com
   Status: 202 (Success)

✅ Test 2 - Agent 1016 (Victor Minna):
   TO: vittoriominna@gmail.com, jpritchard@greenwattusa.com, greenwatt.intake@gmail.com
   CC: operations@greenwattusa.com
   Status: 202 (Success)
```

### Files Modified for Email Implementation
3. **`.env`** - Added SendGrid API key and SSL bypass for development
4. **Email service verified** - `services/email_service.py` working correctly with agent data

### Integration Points
- **Form Submission**: Automatically triggers email after successful form processing
- **Agent Data**: Uses fixed agent mapping to resolve recipient emails dynamically
- **Error Handling**: Graceful fallback if agent emails not found
- **Development Support**: SSL bypass for corporate/development environments

---

**Resolution Date:** July 24, 2025  
**Resolution Status:** ✅ Complete - Agent mapping AND email notifications fully functional  
**Email System Status:** ✅ All recipients verified and working