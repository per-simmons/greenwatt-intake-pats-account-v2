# GreenWatt Notification System Documentation - July 16, 2025

## Overview
This document outlines the current email and SMS notification system configuration for the GreenWatt Intake application as of July 16, 2025.

---

## 📧 Email Notifications (SendGrid)

### Email Recipients Configuration

#### TO Recipients:
1. **Agent Email** - Retrieved from Agent ID Sheet (Column D)
2. **Sales Manager Email** - Retrieved from Agent ID Sheet (Column G)  
3. **greenwatt.intake@gmail.com** - Always included (hardcoded)

#### CC Recipients:
1. **operations@greenwattusa.com** - Always included (hardcoded)

### Email Content Details
- **From Address**: `greenwatt.intake@gmail.com` (verified sender)
- **Subject Format**: `🌱 New Submission: [Customer Name] ([Utility])`
- **Template**: Professional HTML with GreenWatt branding
- **Fallback**: Plain text version included

### Email Data Included:
- Field Agent Name
- Customer Name
- Utility Provider
- Submission Date
- Annual Usage (formatted with commas)

### SendGrid Configuration:
- **API Key**: Set via `SENDGRID_API_KEY` environment variable
- **SSL Handling**: Supports `DISABLE_SSL_VERIFICATION` for development environments

---

## 📱 SMS Notifications (Twilio)

### SMS Types & Recipients

#### 1. Customer Verification SMS
- **Recipient**: Customer's phone number (from form submission)
- **Trigger**: Only sent if SMS consent checkbox is checked
- **Purpose**: Confirm participation in CDG bill credit program
- **Response Expected**: Y/N for enrollment confirmation

**Message Format:**
```
Hello [Customer Name],

Thank you for your interest in GreenWatt USA's Community Solar program!

Please reply Y to confirm your participation in our Community Distributed Generation (CDG) bill credit program, which guarantees up to 10% savings off your electricity bill.

Reply N if you do not wish to participate at this time.

Your response helps us finalize your enrollment.

Best regards,
GreenWatt USA Team
```

#### 2. Internal Team Notification SMS
- **Recipients**: Numbers listed in `TWILIO_INTERNAL_NUMBERS` environment variable
- **Trigger**: Immediately after successful form submission
- **Purpose**: Alert team to new submission

**Message Format:**
```
NEW GREENWATT SUBMISSION

Customer: [Customer Name]
Agent: [Agent Name]
Utility: [Utility Provider]
Usage: [Annual Usage] kWh/year

Submitted: [Submission Date]

Check Google Sheets for full details.
```

### Twilio Configuration

#### Environment Variables:
- **`TWILIO_ACCOUNT_SID`**: Twilio account identifier
- **`TWILIO_AUTH_TOKEN`**: Twilio authentication token
- **`TWILIO_FROM_NUMBER`**: Registered Twilio phone number for sending SMS
- **`TWILIO_INTERNAL_NUMBERS`**: Comma-separated list of team member phone numbers

#### Current Configuration (as of July 16, 2025):
- **From Number**: `+15858889205` (585-888-9205)
- **Internal Numbers**: Currently needs verification via Render.com

---

## 🔄 SMS Response Handling

### CDG Enrollment Status Tracking (Two-Column Approach) - **PENDING FINAL TEST/CONFIRMATION**
- **Column Y**: CDG SMS Sent
  - **Initial State**: Empty string
  - **After SMS Sent**: Updates to "YES"
- **Column Z**: CDG Enrollment Status
  - **Initial State**: Empty string
  - **After SMS Sent**: Updates to "PENDING"
  - **After Response**: Updates to "ENROLLED", "DECLINED", or "INVALID: [response]"

### Response Processing:
- **Positive Responses**: Y, YES, CONFIRM, OK, OKAY, ACCEPT → "ENROLLED"
- **Negative Responses**: N, NO, DECLINE, CANCEL, OPT OUT, OPTOUT → "DECLINED"
- **Invalid Responses**: Any other text → "INVALID: [original response]"

### Webhook Configuration:
- **Endpoint**: `/sms-webhook` (POST method)
- **Validation**: Twilio signature validation for security
- **Response**: TwiML auto-reply confirming receipt

---

## 🛠️ Technical Implementation

### Error Handling:
- **Email**: Graceful fallback if SendGrid API fails
- **SMS**: Graceful fallback if Twilio API fails
- **Logging**: All notification attempts logged with status

### Phone Number Formatting:
- **US Numbers**: Automatically formatted to E.164 (+1XXXXXXXXXX)
- **10-digit**: Adds +1 prefix
- **11-digit starting with 1**: Adds + prefix
- **International**: Passed as-is

### Security Features:
- **Webhook Validation**: Twilio signature verification
- **SSL Handling**: Configurable for development environments
- **Input Validation**: Phone number and email format validation

---

## 🔧 Configuration Updates (July 16, 2025)

### Planned Changes:
1. **Add Pat's Number**: `+12084848906` (from (208) 484-8906) to `TWILIO_INTERNAL_NUMBERS`
2. **Remove Client Number**: `+15857668518` temporarily for testing
3. **Note**: Pat's number is temporary for testing - will be swapped out later

### Current Status:
- Email notifications: ✅ Fully configured and tested
- SMS customer verification: ✅ Implemented and tested
- SMS internal notifications: ✅ Configuration updated (Pat's number added, client number removed)
- CDG status tracking: ⏳ **PENDING FINAL TEST/CONFIRMATION** - Two-column approach implemented (Column Y: SMS Sent, Column Z: Enrollment Status)

---

## 📋 Testing Checklist

### Email Testing:
- [ ] Verify SendGrid API key is active
- [ ] Test email delivery to all recipient types
- [ ] Confirm HTML formatting displays correctly
- [ ] Validate fallback plain text version

### SMS Testing:
- [ ] Verify Twilio credentials are active
- [ ] Test customer verification SMS sending
- [ ] Test internal team notification SMS
- [ ] Verify webhook response handling
- [ ] Confirm CDG status updates in Google Sheets

### Integration Testing:
- [ ] End-to-end form submission with SMS consent
- [ ] End-to-end form submission without SMS consent
- [ ] Webhook response processing (Y/N responses)
- [ ] Error handling for API failures

---

## 📞 Contact Information

### For Configuration Updates:
- **Render.com Dashboard**: https://dashboard.render.com/web/srv-d18vfefdiees73abnkv0
- **Service ID**: srv-d18vfefdiees73abnkv0
- **Environment Variables**: Update via Render.com Environment tab

### For Testing:
- **Pat's Number**: +12084848906 (temporary testing)
- **Client Number**: +15857668518 (temporarily removed)
- **From Number**: +15858889205 (verified Twilio number)

---

## 📝 TODO: Post-Testing Configuration Changes

### ⚠️ IMPORTANT: Restore Client Configuration After Testing
Once testing is complete, the following changes must be made to restore production configuration:

1. **Restore Client's Number**: Add Jason's number `+15857668518` back to `TWILIO_INTERNAL_NUMBERS`
2. **Remove Test Number**: Remove Pat's number `+12084848906` from `TWILIO_INTERNAL_NUMBERS`
3. **Update Environment Variables**: Use Render.com dashboard to make these changes

### 🔧 How to Update Environment Variables in Render.com:
1. **Login to Render.com Dashboard**: https://dashboard.render.com
2. **Navigate to Service**: Go to GreenWatt service (ID: srv-d18vfefdiees73abnkv0)
3. **Open Environment Tab**: Click on "Environment" in the left sidebar
4. **Edit Variables**: Click "Edit" next to `TWILIO_INTERNAL_NUMBERS`
5. **Update Value**: Change the comma-separated phone numbers as needed
6. **Save Changes**: Click "Save" - service will automatically redeploy

### ✅ Confirmation:
- **Environment variables CAN be updated directly in Render.com** ✅
- **Changes trigger automatic redeployment** ✅
- **No manual restart required** ✅
- **Changes take effect within 2-3 minutes** ✅

---

## 📝 Implementation Updates (July 16, 2025) - **PENDING FINAL TEST/CONFIRMATION**

### Google Sheets Structure Changes:
1. **Extended columns from Y to Z** (now 26 columns total: A-Z)
2. **Two-column CDG tracking approach**:
   - Column Y: "CDG SMS Sent" - Shows "YES" when SMS is sent
   - Column Z: "CDG Enrollment Status" - Shows "PENDING" → "ENROLLED"/"DECLINED"

### Code Changes Made:
- Updated `google_sheets_service.py`:
  - Headers array extended to include both CDG columns
  - All ranges updated from A:Y to A:Z
  - `log_sms_sent()` now updates both columns Y and Z
  - `log_sms_response()` only updates column Z
  - valueInputOption remains 'RAW' for proper data insertion
- Updated `app.py`:
  - Sheet data array extended to include two CDG columns
  - Regex pattern already correct for Z column
  - Columns U-X show full Google Drive URLs (no hyperlink formulas)

### Latest Fix (Hyperlink Issue):
- **Problem**: HYPERLINK formulas were showing "View Bill", "View POA" etc. instead of actual URLs
- **Solution**: Reverted back to inserting plain Google Drive URLs
- **Also Fixed**: Changed valueInputOption back to 'RAW' to prevent data interpretation issues

### Testing Required:
- Verify columns Y and Z appear in Google Sheets
- Confirm SMS sent updates column Y to "YES" and column Z to "PENDING"
- Confirm SMS response updates column Z to enrollment status
- Verify full Google Drive URLs appear in columns U-X (not hyperlink formulas)

---

## 🔧 Critical Webhook Fix (July 16, 2025) - **PENDING FINAL TEST/CONFIRMATION**

### Issue Discovered:
- CDG enrollment status stuck on "PENDING" after customer replies "Y"
- Twilio logs showed "no HTTP requests logged for this event"
- Direct curl testing returned 403 Forbidden error
- Root cause: HTTPS/HTTP mismatch due to Render.com reverse proxy

### Solution Implemented:

#### 1. **X-Forwarded-Proto Fix**:
When deployed on Render.com, the application runs behind a reverse proxy. Twilio signs webhooks with the public HTTPS URL, but Flask sees HTTP internally, causing signature validation to fail.

**Fix applied in `/sms-webhook` route:**
```python
# Fix HTTPS/HTTP mismatch when behind Render's proxy
proto = request.headers.get('X-Forwarded-Proto', 'http')
if proto == 'https' and request_url.startswith('http://'):
    request_url = request_url.replace('http://', 'https://', 1)
```

#### 2. **Phone Number Normalization** (Next Step):
Need to normalize phone numbers for matching in Google Sheets:
```python
def _normalize_phone(self, phone):
    """Extract last 10 digits for US phone comparison"""
    return ''.join(filter(str.isdigit, str(phone)))[-10:]
```

#### 3. **Debug Mode Added**:
New environment variable `TWILIO_WEBHOOK_DEBUG` allows bypassing signature validation for testing:
- Set to "true" in Render.com for debugging
- **IMPORTANT**: Must be removed or set to "false" in production

### Enhanced Logging Added:
- 🔔 Webhook hit logging (shows incoming requests)
- 🔧 URL fix logging (shows HTTPS correction)
- 📨 Parameter logging (shows From number and Body)

### Testing Options:

#### Option 1: Test Webhook Endpoint (Recommended)
1. Deploy changes to Render.com
2. Navigate to: `https://greenwatt.gtbsolarexchange.com/test-sms-webhook`
3. Enter the phone number from the submitted form
4. Select "Y" and submit
5. Check logs and Google Sheets for updates

#### Option 2: Real SMS Testing
1. Deploy these changes to Render.com
2. Set `TWILIO_WEBHOOK_DEBUG=true` temporarily in Render environment variables
3. Send a test SMS reply
4. Verify webhook receives and processes the response
5. Check that CDG Enrollment Status updates from "PENDING" to "ENROLLED"
6. **IMPORTANT**: Remove debug flag after confirming it works

### Important Notes:
- This is a common issue with applications deployed behind reverse proxies
- The fix ensures Twilio's signature validation works correctly
- Phone number normalization is still needed for proper row matching

### ⚠️ PRODUCTION CHECKLIST:
1. **Remove or set `TWILIO_WEBHOOK_DEBUG=false`** in Render.com environment variables
2. **Test webhook endpoint** (`/test-sms-webhook`) is safe to keep as it doesn't bypass security
3. **Your existing enrollment**: No action needed - your "ENROLLED" status in Google Sheets won't cause issues

---

*Last Updated: July 16, 2025*  
*Author: Claude Code Assistant*  
*Purpose: System documentation and configuration reference*