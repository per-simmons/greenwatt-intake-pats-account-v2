# Correct Twilio Environment Variables for Render.com

**IMPORTANT**: Update these in Render.com Dashboard → Environment tab

## Required Twilio Environment Variables

```bash
# Twilio Account Credentials (already correct)
TWILIO_ACCOUNT_SID=AC[your_actual_sid]
TWILIO_AUTH_TOKEN=[your_actual_auth_token]

# ⚠️ UPDATE THESE - Currently using placeholders
TWILIO_FROM_NUMBER=+15858889205
TWILIO_INTERNAL_NUMBERS=+15857668518
```

## Current Issues (as of Jan 15, 2025)
- `TWILIO_FROM_NUMBER` is set to placeholder `+1234567890` → Should be `+15858889205`
- `TWILIO_INTERNAL_NUMBERS` is set to placeholders `+1234567890,+1987654321` → Should be `+15857668518`

## Verified Phone Numbers
- **Twilio Phone Number**: +15858889205 (585-888-9205) - This is your registered Twilio number
- **Internal Team Number**: +15857668518 (585-766-8518) - Receives team notifications

## How to Update on Render.com
1. Go to https://dashboard.render.com
2. Select your `greenwatt-intake` service
3. Click on "Environment" tab
4. Update the values for:
   - `TWILIO_FROM_NUMBER`
   - `TWILIO_INTERNAL_NUMBERS`
5. Click "Save Changes"
6. The service will automatically redeploy with correct values

## Testing After Update
1. Submit a test form with SMS consent checked
2. Verify:
   - Customer receives verification SMS from +15858889205
   - Team member at (585) 766-8518 receives notification SMS