#!/usr/bin/env python3
"""
Verify service account has access to Shared Drive folders
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

print("🔍 Verifying Shared Drive Access")
print("=" * 60)

# Test folder IDs
folders_to_check = {
    "Parent Folder": "12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj",
    "Templates Folder": "1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS"
}

for name, folder_id in folders_to_check.items():
    print(f"\n📁 Checking {name}: {folder_id}")
    
    try:
        # Try to get folder metadata with Shared Drive support
        folder = drive_service.files().get(
            fileId=folder_id,
            supportsAllDrives=True,  # IMPORTANT: This flag is needed for Shared Drives
            fields='id,name,mimeType,permissions,driveId,capabilities'
        ).execute()
        
        print(f"✅ Found: {folder['name']}")
        print(f"   Type: {folder['mimeType']}")
        
        if 'driveId' in folder:
            print(f"   ✅ In Shared Drive: {folder['driveId']}")
        else:
            print(f"   ❌ NOT in Shared Drive - in My Drive")
        
        # Check permissions
        if 'permissions' in folder:
            print("   Permissions:")
            for perm in folder['permissions']:
                print(f"     - {perm.get('emailAddress', 'Unknown')}: {perm['role']}")
        
        # Check capabilities
        caps = folder.get('capabilities', {})
        print(f"   Can add children: {caps.get('canAddChildren', False)}")
        print(f"   Can edit: {caps.get('canEdit', False)}")
        
        # Try to list files in the folder
        print("\n   Testing file listing...")
        files = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields='files(id,name)'
        ).execute()
        
        file_count = len(files.get('files', []))
        print(f"   ✅ Can list files: Found {file_count} files")
        
        # Try to create a test file
        print("\n   Testing file creation...")
        test_metadata = {
            'name': 'test_permission_check.txt',
            'parents': [folder_id],
            'mimeType': 'text/plain'
        }
        
        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(b'Test content', mimetype='text/plain')
        
        test_file = drive_service.files().create(
            body=test_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields='id,name'
        ).execute()
        
        print(f"   ✅ Can create files: Created {test_file['name']} (ID: {test_file['id']})")
        
        # Clean up test file
        drive_service.files().delete(
            fileId=test_file['id'],
            supportsAllDrives=True
        ).execute()
        print("   ✅ Cleaned up test file")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
        # Check if it's a scope issue
        if "insufficient" in str(e).lower():
            print("\n⚠️  This might be a scope issue. The service account needs:")
            print("   - https://www.googleapis.com/auth/drive scope")
            print("   - Content Manager role in the Shared Drive")
        
        # Check if it's the supportsAllDrives issue
        if "not found" in str(e).lower():
            print("\n⚠️  The folder might be in a Shared Drive but the API call")
            print("   is missing the 'supportsAllDrives=True' parameter")
            print("   This needs to be added to the GoogleDriveService class")

print("\n" + "=" * 60)
print("🔧 SOLUTION:")
print("1. Make sure the service account is added to the Shared Drive")
print("   (not just the folders) with 'Content Manager' role")
print("2. The GoogleDriveService class needs to be updated to support")
print("   Shared Drives by adding 'supportsAllDrives=True' to all API calls")