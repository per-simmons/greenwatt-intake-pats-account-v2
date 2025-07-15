#!/usr/bin/env python3
"""
Check if the configured Drive folders are Shared Drives or regular folders
"""

import os
import json
from services.google_service_manager import GoogleServiceManager
from dotenv import load_dotenv

load_dotenv()

# Load service account
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if SERVICE_ACCOUNT_JSON:
    SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)
else:
    with open('upwork-greenwatt-drive-sheets-3be108764560.json', 'r') as f:
        SERVICE_ACCOUNT_INFO = json.load(f)

# Initialize service
service_manager = GoogleServiceManager()
service_manager.initialize(SERVICE_ACCOUNT_INFO)
drive_service = service_manager.get_drive_service()

def check_folder_type(folder_id, folder_name):
    """Check if a folder is in a Shared Drive or My Drive"""
    try:
        # Get folder details
        folder = drive_service.files().get(
            fileId=folder_id,
            fields='id,name,parents,driveId,capabilities'
        ).execute()
        
        print(f"\n📁 {folder_name}:")
        print(f"   ID: {folder_id}")
        print(f"   Name: {folder['name']}")
        
        if 'driveId' in folder:
            print(f"   ✅ Location: Shared Drive (ID: {folder['driveId']})")
            print(f"   ✅ Can create files: {folder.get('capabilities', {}).get('canAddChildren', False)}")
            return True
        else:
            print(f"   ❌ Location: My Drive (Personal folder)")
            print(f"   ❌ Service accounts CANNOT create files here!")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking folder: {str(e)}")
        return False

# Check both folders
print("🔍 Checking Drive folder types...")
print("=" * 60)

parent_folder_id = os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')
templates_folder_id = os.getenv('GOOGLE_DRIVE_TEMPLATES_FOLDER_ID')

parent_is_shared = check_folder_type(parent_folder_id, "Parent Folder")
templates_is_shared = check_folder_type(templates_folder_id, "Templates Folder")

print("\n" + "=" * 60)
if parent_is_shared and templates_is_shared:
    print("✅ Both folders are in Shared Drives - this should work!")
else:
    print("❌ Folders are NOT in Shared Drives!")
    print("\n🚨 TO FIX THIS:")
    print("1. Create a Shared Drive in your Workspace account")
    print("2. Create folders inside the Shared Drive")
    print("3. Share the Shared Drive with the service account")
    print("4. Update environment variables with new folder IDs")
    print("\nShared Drives are different from regular shared folders!")
    print("You need to specifically create a 'Shared Drive' (Team Drive)")