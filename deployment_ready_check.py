#!/usr/bin/env python3
"""
Quick deployment readiness check - run this before deploying to Render
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

print("🚀 DEPLOYMENT READINESS CHECK")
print("=" * 60)

# Check 1: Service account file exists
print("\n1️⃣ Checking service account...")
sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if sa_json:
    print("✅ Service account JSON found in environment")
    try:
        sa_info = json.loads(sa_json)
        print(f"   Email: {sa_info.get('client_email', 'Unknown')}")
    except:
        print("⚠️  Could not parse service account JSON")
else:
    if os.path.exists('upwork-greenwatt-drive-sheets-3be108764560.json'):
        print("✅ Using local service account file")
    else:
        print("❌ No service account found!")

# Check 2: Environment variables
print("\n2️⃣ Checking environment variables...")
env_vars = {
    "GOOGLE_DRIVE_PARENT_FOLDER_ID": "12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj",
    "GOOGLE_DRIVE_TEMPLATES_FOLDER_ID": "1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS",
    "GOOGLE_SHEETS_ID": "1R1bZuDhToHg1bIQtZUWCXQHaCJq8jsXeuKuSFBHdhpw",
    "GOOGLE_AGENT_SHEETS_ID": None  # Don't know expected value
}

for var, expected in env_vars.items():
    actual = os.getenv(var)
    if actual:
        if expected and actual != expected:
            print(f"⚠️  {var}: MISMATCH!")
            print(f"    Current: {actual}")
            print(f"    Expected: {expected}")
        else:
            print(f"✅ {var}: Set correctly")
    else:
        print(f"❌ {var}: NOT SET")

# Check 3: API Keys
print("\n3️⃣ Checking API keys...")
api_keys = [
    "OPENAI_API_KEY",
    "SENDGRID_API_KEY", 
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER"
]

for key in api_keys:
    if os.getenv(key):
        print(f"✅ {key}: Set")
    else:
        print(f"⚠️  {key}: Not set (may be OK if in Render)")

# Check 4: SSL verification
print("\n4️⃣ Checking SSL settings...")
if os.getenv('DISABLE_SSL_VERIFICATION') == 'true':
    print("⚠️  SSL verification is DISABLED - OK for local dev, NOT for production!")
else:
    print("✅ SSL verification enabled (good for production)")

# Check 5: Code fixes
print("\n5️⃣ Checking code fixes...")
try:
    with open('services/google_drive_service.py', 'r') as f:
        content = f.read()
        if "permissions().create(" in content:
            print("❌ Permission-setting code still present! Fix not applied.")
        else:
            print("✅ Permission-setting code removed")
            
        if "supportsAllDrives=True" in content:
            print("✅ Shared Drive support added")
        else:
            print("⚠️  Shared Drive support might be missing")
except:
    print("❌ Could not check google_drive_service.py")

print("\n" + "=" * 60)
print("📋 DEPLOYMENT CHECKLIST:")
print("=" * 60)

print("""
Before deploying to Render:

1. ☐ Run: python comprehensive_drive_test.py
     (Should show 100% success rate)

2. ☐ Run: python verify_production_folders.py  
     (Should confirm both folders are Shared Drives)

3. ☐ In Render Dashboard, verify environment variables:
     - GOOGLE_DRIVE_PARENT_FOLDER_ID = 12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj
     - GOOGLE_DRIVE_TEMPLATES_FOLDER_ID = 1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS
     - DISABLE_SSL_VERIFICATION should NOT be set (or = false)

4. ☐ Confirm service account has "Content Manager" access to Shared Drive

5. ☐ Push latest code to GitHub (with permission fix)

If all checks pass, deployment should succeed! 🚀
""")

print("Run these commands to verify:")
print("1. python comprehensive_drive_test.py")
print("2. python verify_production_folders.py")