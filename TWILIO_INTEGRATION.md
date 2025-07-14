# Twilio SMS Integration Documentation

## Client Requirements

### Original Request (Weekend Communication)
> "One item that came to me over the weekend was a SMS verification sent to the customer. Is it possible for a verification to be sent to the customer asking them to reply Y/N agreeing to participate in a CDG bill credit program guaranteeing up to 10% saving off their electricity bill. This would trigger once the field agent hits submit and then the reply logged in the Google sheet with a date and time stamp."

### Key Requirements
1. **Trigger**: SMS sent automatically when field agent submits form
2. **Message Content**: Ask customer to confirm participation in CDG bill credit program with 10% savings guarantee
3. **Response Options**: Y/N reply from customer
4. **Logging**: Responses logged in Google Sheet with date/time stamp
5. **Purpose**: Customer verification and consent for enrollment

### Confirmed Implementation Flow

#### Who receives notifications?
- **Team Members**: Phone numbers in `TWILIO_INTERNAL_NUMBERS` (currently Pat: +12084848906)
- **Customers**: Using phone number provided in form submission

#### What triggers the SMS?
A successful form submission triggers:
1. Data logging to Google Sheets
2. SMS verification to customer asking Y/N for CDG program participation
3. SMS alert to team members with submission details

#### What number sends the SMS?
- **Sending Number**: +15858889205 (GreenWatt's verified Twilio number)

#### Team Notification Message
Dynamically includes all requested information:
```
🌱 NEW GREENWATT SUBMISSION

Customer: [Customer Name] ✅
Agent: [Agent Name] ✅
Utility: [Utility Provider] ✅
Usage: [Annual Usage] kWh/year ✅

Submitted: [Date/Time]

Check Google Sheets for full details.
```

#### Customer Verification Message
```
Hello [Customer Name],

Thank you for your interest in GreenWatt USA's Community Solar program!

Please reply Y to confirm your participation in our Community Distributed Generation (CDG) bill credit program, which guarantees up to 10% savings off your electricity bill.

Reply N if you do not wish to participate at this time.

Your response helps us finalize your enrollment.

Best regards,
GreenWatt USA Team
```

#### Response Tracking
Customer responses (Y/N) are automatically:
- Captured via Twilio webhook at `/sms-webhook`
- Logged to Google Sheets with timestamp
- Tracked in columns U-Z for complete SMS audit trail

## Current Implementation Status

### ✅ Completed Components

#### 1. SMS Service (`services/sms_service.py`)
- **Customer Verification SMS**: Sends Y/N prompt to customers
- **Internal Team Notifications**: Alerts team of new submissions
- **Response Parsing**: Handles Y/YES/CONFIRM or N/NO/DECLINE variations
- **Phone Formatting**: Converts to E.164 format (+1XXXXXXXXXX)
- **Webhook Security**: Validates Twilio signatures

#### 2. Integration Points
- **Form Submission**: SMS triggered in Step 7 of background processing
- **Progress Tracking**: "Sending SMS verification" status shown to agent
- **Dual Notifications**: Both customer and team receive messages

#### 3. Message Templates
```
Customer Message:
Hello {customer_name},

Thank you for your interest in community solar with GreenWatt USA! 

Please reply with Y to confirm your participation in our Community Distributed Generation (CDG) program, or N if you wish to opt out.

Your response helps us finalize your enrollment.

Best regards,
GreenWatt USA Team
```

```
Team Message:
🌱 NEW GREENWATT SUBMISSION

Customer: {customer_name}
Agent: {agent_name}
Utility: {utility}
Usage: {annual_usage} kWh/year

Submitted: {submission_date}

Check Google Sheets for full details.
```

#### 4. Webhook Infrastructure
- **Endpoint**: `/sms-webhook` - Receives Twilio POST requests
- **Test Endpoint**: `/test-sms-webhook` - Manual testing interface
- **Security**: Signature validation prevents spoofing
- **Response Processing**: Extracts and parses customer replies

### ❌ Pending Implementation

#### 1. A2P 10DLC Registration (CRITICAL)
**Status**: Initial registration rejected - needs resubmission

**Required Steps**:
1. Purchase Twilio phone number (~$1/month)
2. Complete brand registration with business details
3. Create new campaign with updated messaging
4. Associate phone number with campaign

**Campaign Details for Resubmission**:
- **Use Case**: Community solar enrollment confirmation
- **Message Sample**: Include exact CDG program message with 10% savings mention
- **Opt-in Process**: "Customer provides phone number on intake form"
- **Opt-out Instructions**: "Reply STOP to unsubscribe"
- **Message Volume**: Estimate based on expected submissions

#### 2. Google Sheets SMS Tracking (✅ IMPLEMENTED)
**Simplified to Single Column**:
- Column Y: `CDG Enrollment Status` (PENDING/ENROLLED/DECLINED/INVALID)

**Implementation Details**:
- Phone number already exists in Column G (no need to duplicate)
- SMS is sent automatically on form submission (no need for sent flag)
- Status tracking:
  - `PENDING` - Set when SMS is sent
  - `ENROLLED` - Customer replied Y/YES
  - `DECLINED` - Customer replied N/NO  
  - `INVALID: [response]` - Unrecognized response

**Implemented Methods**:
```python
def log_sms_sent(self, row_index):
    """Update CDG Enrollment Status to PENDING when SMS is sent"""
    # Updates column Y to 'PENDING'
    
def log_sms_response(self, phone, response):
    """Find row by phone number and update CDG Enrollment Status"""
    # Matches phone in column G, updates column Y with final status
```

#### 3. Enhanced Message Content
**Updated Customer Message** (per client request):
```
Hello {customer_name},

Thank you for your interest in GreenWatt USA's Community Solar program!

Please reply Y to confirm your participation in our Community Distributed Generation (CDG) bill credit program, which guarantees up to 10% savings off your electricity bill.

Reply N if you do not wish to participate at this time.

Your response helps us finalize your enrollment.

Best regards,
GreenWatt USA Team
```

## Technical Architecture

### SMS Flow Diagram
```
1. Agent Submits Form
   ↓
2. Background Processing Starts
   ↓
3. Step 7: SMS Service Called
   ├→ Customer SMS (Y/N prompt)
   └→ Team SMS (notification)
   ↓
4. Customer Receives SMS
   ↓
5. Customer Replies Y/N
   ↓
6. Twilio Webhook POST to /sms-webhook
   ↓
7. Webhook Validates & Parses Response
   ↓
8. Google Sheets Updated with Response
   ↓
9. Process Complete
```

### Environment Configuration

#### Required Variables
```bash
# Twilio Credentials
TWILIO_ACCOUNT_SID=AC_your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1XXXXXXXXXX  # Must be registered with A2P 10DLC

# Internal Team Numbers (comma-separated)
TWILIO_INTERNAL_NUMBERS=+1234567890,+1987654321,+1555555555
```

#### Webhook Configuration
1. **Production URL**: `https://your-domain.com/sms-webhook`
2. **Method**: POST
3. **Configure in Twilio Console**: 
   - Phone Numbers > Manage > Active Numbers
   - Select your number
   - Configure "A message comes in" webhook

### Security Considerations

1. **Webhook Validation**: Always verify X-Twilio-Signature header
2. **Phone Number Privacy**: Store formatted numbers, never log full messages
3. **Rate Limiting**: Implement limits to prevent SMS bombing
4. **HTTPS Only**: Webhook must use SSL/TLS encryption

## Testing Checklist

### Pre-Production Testing
- [ ] Verify Twilio credentials in .env file
- [ ] Test with personal phone numbers first
- [ ] Use `/test-sms` endpoint for manual testing
- [ ] Verify webhook receives responses
- [ ] Check response parsing (Y/N/YES/NO variations)
- [ ] Confirm Google Sheets columns exist
- [ ] Test phone number matching logic
- [ ] Verify timezone handling (EST)

### Production Deployment
- [ ] A2P 10DLC registration approved
- [ ] Production phone number purchased
- [ ] Webhook URL configured in Twilio
- [ ] SSL certificate valid
- [ ] Error monitoring in place
- [ ] Team phone numbers configured
- [ ] Google Sheets permissions verified

## Troubleshooting Guide

### Common Issues

#### 1. SMS Not Sending
- Check Twilio credentials in environment
- Verify phone number format (+1 prefix)
- Confirm Twilio account has credits
- Check for A2P 10DLC compliance

#### 2. Webhook Not Receiving
- Verify webhook URL in Twilio console
- Check server logs for POST requests
- Confirm SSL certificate is valid
- Test with Twilio webhook debugger

#### 3. Response Not Logging
- Verify Google Sheets columns exist
- Check phone number matching logic
- Confirm service account permissions
- Review webhook processing logs

#### 4. Invalid Signatures
- Ensure webhook URL matches exactly
- Check for proxy/CDN modifications
- Verify auth token is correct
- Use Twilio's signature validator

## Future Enhancements

1. **Multi-language Support**: Spanish SMS options
2. **Retry Logic**: Resend if no response in 24 hours
3. **Analytics Dashboard**: Track response rates
4. **Automated Follow-up**: Different messages based on response
5. **MMS Support**: Include program brochure image

## A2P 10DLC Campaign Resubmission Guide

### Why Was It Rejected?
Common rejection reasons:
- Insufficient use case description
- Missing opt-in/opt-out details
- Vague message samples
- Incomplete business verification

### Resubmission Strategy

1. **Enhanced Use Case Description**:
   ```
   GreenWatt USA provides community solar enrollment services. After 
   customers complete our intake form with field agents, we send a 
   single SMS verification to confirm their intent to participate in 
   our Community Distributed Generation (CDG) program. This ensures 
   customer consent and reduces enrollment errors.
   ```

2. **Clear Message Sample**:
   ```
   Hello [Name], Thank you for your interest in GreenWatt USA's 
   Community Solar program! Reply Y to confirm participation in our 
   CDG bill credit program (up to 10% savings on electricity). 
   Reply N to decline. Reply STOP to unsubscribe.
   ```

3. **Opt-in Process**:
   ```
   Customers provide explicit consent by:
   1. Providing phone number on intake form
   2. Checking "I agree to receive SMS communications"
   3. Field agent verbally confirms SMS consent
   ```

4. **Campaign Attributes**:
   - **Campaign Type**: Customer Care
   - **Message Flow**: One-time verification only
   - **Expected Volume**: 100-500 messages/month
   - **No marketing**: Transactional verification only

## Contact Information

### Internal Contacts
- **Technical Lead**: Pat Simmons
- **Client Contact**: Jason (GreenWatt USA)
- **Twilio Support**: support@twilio.com

### Useful Links
- [Twilio Console](https://console.twilio.com)
- [A2P 10DLC Guide](https://www.twilio.com/docs/sms/a2p-10dlc)
- [Webhook Security](https://www.twilio.com/docs/usage/webhooks/webhooks-security)
- [SMS Best Practices](https://www.twilio.com/docs/sms/best-practices)

---

*Last Updated: December 2024*
*Status: Awaiting A2P 10DLC Resubmission*