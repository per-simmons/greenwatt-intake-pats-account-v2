#!/usr/bin/env python3
"""
Verify the PRODUCTION folder IDs are actually Shared Drives
This uses the IDs that should be in Render production
"""

import os
import json
from services.google_service_manager import GoogleServiceManager

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

print("🔍 Verifying PRODUCTION Folder IDs (from Render environment)")
print("=" * 60)

# PRODUCTION folder IDs from the migration document
production_folders = {
    "Parent Folder (Signed Docs)": "12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj",
    "Templates Folder": "1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS"
}

for name, folder_id in production_folders.items():
    print(f"\n📁 Checking {name}: {folder_id}")
    
    try:
        # Get folder metadata with Shared Drive support
        folder = drive_service.files().get(
            fileId=folder_id,
            supportsAllDrives=True,
            fields='id,name,mimeType,parents,driveId,capabilities,permissions'
        ).execute()
        
        print(f"✅ Found: {folder['name']}")
        print(f"   Type: {folder['mimeType']}")
        
        if 'driveId' in folder:
            print(f"   ✅ IN SHARED DRIVE: {folder['driveId']}")
            print(f"   ✅ Can add children: {folder.get('capabilities', {}).get('canAddChildren', False)}")
        else:
            print(f"   ❌ NOT IN SHARED DRIVE - In My Drive/personal folder")
            
        # Check permissions
        if 'permissions' in folder:
            print("   Permissions:")
            for perm in folder['permissions']:
                email = perm.get('emailAddress', perm.get('displayName', 'Unknown'))
                print(f"     - {email}: {perm['role']}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if "not found" in str(e).lower():
            print("   ⚠️  Folder does not exist or service account has no access")

print("\n" + "=" * 60)
print("🔍 CRITICAL CHECK SUMMARY:")
print("If these folders are NOT in Shared Drives, the app will fail in production!")
print("If they ARE in Shared Drives, then the fix should work correctly.")