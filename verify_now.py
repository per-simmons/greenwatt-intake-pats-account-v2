#!/usr/bin/env python3
"""Verify access to new Google Workspace resources and check templates"""

import os
import json
import sys

# Add the project directory to the Python path
sys.path.insert(0, '/Users/patsimmons/client-coding/GreenWatt_Clean_Repo')

from services.google_service_manager import GoogleServiceManager
from dotenv import load_dotenv

load_dotenv()

# New resource IDs
MAIN_SHEET_ID = "1sx7oULKh41KMPH47LolCF9lv7h7-kDwscAoZoVfhDw0"
AGENT_SHEET_ID = "1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I"
PARENT_FOLDER_ID = "1upNlAEg1rf7NXjx7edfZN1xHRUxOCgCc"
TEMPLATES_FOLDER_ID = "1zex9SAIqo_xn75w-5ZjbGIWMRiwGtwi0"

# Expected template files from the Developer_Mapping
EXPECTED_TEMPLATES = [
    'Meadow-National-Grid-Commercial-UCB-Agreement.pdf',
    'Meadow-NYSEG-Commercial-UCB-Agreement.pdf',
    'Meadow-RGE-Commercial-UCB-Agreement.pdf',
    'Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf',
    'Solar-Simplified-National-Grid-Commercial-UCB-Agreement.pdf',
    'Solar-Simplified-NYSEG-Commercial-UCB-Agreement.pdf',
    'Solar-Simplified-RGE-Commercial-UCB-Agreement.pdf',
    'Form-Subscription-Agreement-Mass Market UCB-Solar-Simplified-January 2023-002.pdf'
]

# Load service account credentials
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if SERVICE_ACCOUNT_JSON:
    SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)
else:
    try:
        with open('upwork-greenwatt-drive-sheets-3be108764560.json', 'r') as f:
            SERVICE_ACCOUNT_INFO = json.load(f)
    except FileNotFoundError:
        raise Exception("Service account credentials not found.")

# Initialize services
service_manager = GoogleServiceManager()
service_manager.initialize(SERVICE_ACCOUNT_INFO)
sheets_service = service_manager.get_sheets_service()
drive_service = service_manager.get_drive_service()

print("\n🔍 Verifying Google Workspace Resources")
print("=" * 50)

# 1. Check Main Sheet Access
print("\n📊 Checking Main Intake Sheet...")
try:
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=MAIN_SHEET_ID,
        range='A1:Y1'
    ).execute()
    values = result.get('values', [])
    if values:
        print(f"✅ Successfully accessed sheet!")
        print(f"   Current headers: {len(values[0])} columns")
        if len(values[0]) > 0:
            print(f"   First header: {values[0][0]}")
    else:
        print("⚠️  Sheet is empty - needs setup")
except Exception as e:
    print(f"❌ Cannot access sheet: {e}")

# 2. Check Agent Sheet Access
print("\n👥 Checking Agent Sheet...")
try:
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=AGENT_SHEET_ID,
        range='A1:G1'
    ).execute()
    values = result.get('values', [])
    print(f"✅ Successfully accessed agent sheet!")
    if values:
        print(f"   Headers: {values[0]}")
except Exception as e:
    print(f"❌ Cannot access agent sheet: {e}")

# 3. Check Drive Folders
print("\n📁 Checking Drive Folders...")
try:
    # Check parent folder
    parent = drive_service.files().get(fileId=PARENT_FOLDER_ID, fields='name').execute()
    print(f"✅ Parent folder accessible: {parent.get('name')}")
    
    # Check templates folder
    templates = drive_service.files().get(fileId=TEMPLATES_FOLDER_ID, fields='name').execute()
    print(f"✅ Templates folder accessible: {templates.get('name')}")
except Exception as e:
    print(f"❌ Cannot access folders: {e}")

# 4. List Templates in Templates Folder
print("\n📄 Checking Agreement Templates...")
try:
    # List all files in templates folder
    response = drive_service.files().list(
        q=f"'{TEMPLATES_FOLDER_ID}' in parents and trashed=false",
        pageSize=100,
        fields="files(id, name, mimeType, size)"
    ).execute()
    
    template_files = response.get('files', [])
    print(f"\nFound {len(template_files)} files in Templates folder:")
    
    found_templates = []
    for file in template_files:
        print(f"   - {file['name']}")
        found_templates.append(file['name'])
    
    # Check for missing templates
    print("\n🔍 Template Verification:")
    missing_templates = []
    for expected in EXPECTED_TEMPLATES:
        if expected not in found_templates:
            print(f"❌ MISSING: {expected}")
            missing_templates.append(expected)
        else:
            print(f"✅ Found: {expected}")
    
    if missing_templates:
        print(f"\n⚠️  Missing {len(missing_templates)} templates!")
        print("These need to be uploaded to the Templates folder")
    else:
        print("\n✅ All expected templates are present!")
        
except Exception as e:
    print(f"❌ Cannot list templates: {e}")

print("\n" + "=" * 50)
print("Verification complete!")

# Summary
print("\n📋 Summary:")
print("- Main Sheet ID:", MAIN_SHEET_ID)
print("- Agent Sheet ID:", AGENT_SHEET_ID)
print("- Parent Folder ID:", PARENT_FOLDER_ID)
print("- Templates Folder ID:", TEMPLATES_FOLDER_ID)

# Clean up temporary files
try:
    os.remove('/Users/patsimmons/client-coding/GreenWatt_Clean_Repo/run_verify.sh')
    os.remove('/Users/patsimmons/client-coding/GreenWatt_Clean_Repo/run_verification.py')
except:
    pass