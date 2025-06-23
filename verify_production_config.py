#!/usr/bin/env python3
"""
Script to verify production configuration for debugging OCR issues.
Run this on your production server to check API keys and service accounts.
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def check_configuration():
    """Check all required environment variables and API configurations"""
    
    print("🔍 Verifying Production Configuration")
    print("=" * 50)
    
    # Check Google Service Account
    print("\n1. Google Service Account (for Vision API):")
    google_sa = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if google_sa:
        try:
            sa_data = json.loads(google_sa)
            print(f"   ✅ Service Account configured")
            print(f"   - Project ID: {sa_data.get('project_id', 'N/A')}")
            print(f"   - Client Email: {sa_data.get('client_email', 'N/A')}")
        except:
            print("   ❌ Invalid JSON format")
    else:
        print("   ❌ NOT CONFIGURED - Vision API will fail")
    
    # Check OpenAI API Key
    print("\n2. OpenAI API Key (for LLM parsing):")
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        if openai_key.startswith('sk-proj-'):
            # Mask the key for security
            masked_key = openai_key[:15] + "..." + openai_key[-4:]
            print(f"   ✅ API Key configured: {masked_key}")
        else:
            print("   ⚠️  Key doesn't match expected format")
    else:
        print("   ❌ NOT CONFIGURED - LLM parsing will fail")
    
    # Check Google Sheets ID
    print("\n3. Google Sheets Configuration:")
    sheets_id = os.getenv('GOOGLE_SHEETS_ID')
    if sheets_id:
        print(f"   ✅ Sheets ID: {sheets_id}")
    else:
        print("   ❌ Sheets ID not configured")
    
    # Check Google Drive
    print("\n4. Google Drive Configuration:")
    drive_id = os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')
    if drive_id:
        print(f"   ✅ Drive Folder ID: {drive_id}")
    else:
        print("   ❌ Drive Folder ID not configured")
    
    # Check SendGrid
    print("\n5. SendGrid Configuration:")
    sendgrid_key = os.getenv('SENDGRID_API_KEY')
    if sendgrid_key:
        masked = sendgrid_key[:10] + "..." if len(sendgrid_key) > 10 else "***"
        print(f"   ✅ API Key configured: {masked}")
    else:
        print("   ⚠️  Not configured (emails won't send)")
    
    # Check Twilio
    print("\n6. Twilio Configuration:")
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_auth = os.getenv('TWILIO_AUTH_TOKEN')
    if twilio_sid and twilio_auth:
        print(f"   ✅ Account SID: {twilio_sid}")
        print(f"   ✅ Auth Token: {'*' * 8}")
    else:
        print("   ⚠️  Not configured (SMS won't work)")
    
    print("\n" + "=" * 50)
    print("\n📋 Summary:")
    
    critical_missing = []
    if not google_sa:
        critical_missing.append("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not openai_key:
        critical_missing.append("OPENAI_API_KEY")
    
    if critical_missing:
        print(f"❌ CRITICAL: Missing {', '.join(critical_missing)}")
        print("   OCR will NOT work without these!")
    else:
        print("✅ All critical services configured")
        print("   OCR should work properly")
    
    print("\n💡 To add missing variables in Render.com:")
    print("   1. Go to your service dashboard")
    print("   2. Click on 'Environment' tab")
    print("   3. Add the missing environment variables")
    print("   4. Redeploy the service")

if __name__ == "__main__":
    check_configuration()