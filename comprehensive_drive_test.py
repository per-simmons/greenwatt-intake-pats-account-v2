#!/usr/bin/env python3
"""
Comprehensive test script to validate ALL Google Drive operations
This ensures 100% confidence that the Shared Drive fix works
"""

import os
import json
import time
from services.google_drive_service import GoogleDriveService
from services.google_service_manager import GoogleServiceManager

# Load service account
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if SERVICE_ACCOUNT_JSON:
    SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)
else:
    with open('upwork-greenwatt-drive-sheets-3be108764560.json', 'r') as f:
        SERVICE_ACCOUNT_INFO = json.load(f)

# Initialize services
service_manager = GoogleServiceManager()
service_manager.initialize(SERVICE_ACCOUNT_INFO)
drive_api = service_manager.get_drive_service()

print("🧪 COMPREHENSIVE GOOGLE DRIVE OPERATIONS TEST")
print("=" * 80)

# Test with PRODUCTION folder IDs
PRODUCTION_PARENT_ID = "12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj"
PRODUCTION_TEMPLATES_ID = "1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS"

# Track test results
results = {
    "folder_type_check": False,
    "create_folder": False,
    "upload_file": False,
    "list_files": False,
    "get_metadata": False,
    "delete_file": False,
    "template_access": False,
    "error_messages": []
}

print("\n1️⃣ CHECKING IF FOLDERS ARE SHARED DRIVES...")
print("-" * 60)

def check_shared_drive(folder_id, folder_name):
    """Verify folder is a Shared Drive"""
    try:
        folder = drive_api.files().get(
            fileId=folder_id,
            supportsAllDrives=True,
            fields='id,name,driveId,capabilities'
        ).execute()
        
        is_shared = 'driveId' in folder
        can_add = folder.get('capabilities', {}).get('canAddChildren', False)
        
        print(f"📁 {folder_name}:")
        print(f"   ID: {folder_id}")
        print(f"   Name: {folder['name']}")
        print(f"   Is Shared Drive: {'✅ YES' if is_shared else '❌ NO'}")
        print(f"   Can add files: {'✅ YES' if can_add else '❌ NO'}")
        
        return is_shared and can_add
    except Exception as e:
        print(f"❌ Error checking {folder_name}: {str(e)}")
        results["error_messages"].append(f"Folder check failed: {str(e)}")
        return False

parent_is_shared = check_shared_drive(PRODUCTION_PARENT_ID, "Parent Folder")
templates_is_shared = check_shared_drive(PRODUCTION_TEMPLATES_ID, "Templates Folder")
results["folder_type_check"] = parent_is_shared and templates_is_shared

if not results["folder_type_check"]:
    print("\n⚠️  CRITICAL: Folders are NOT Shared Drives! Tests will likely fail.")
else:
    print("\n✅ Both folders are Shared Drives - proceeding with tests...")

# Initialize GoogleDriveService with production folder
drive_service = GoogleDriveService(SERVICE_ACCOUNT_INFO, PRODUCTION_PARENT_ID)

print("\n2️⃣ TESTING FOLDER CREATION...")
print("-" * 60)

test_folder_id = None
try:
    timestamp = int(time.time())
    test_folder_name = f"TEST_COMPREHENSIVE_{timestamp}"
    test_folder_id = drive_service.create_folder(test_folder_name)
    print(f"✅ Created folder: {test_folder_name}")
    print(f"   ID: {test_folder_id}")
    results["create_folder"] = True
except Exception as e:
    print(f"❌ Folder creation failed: {str(e)}")
    results["error_messages"].append(f"Folder creation: {str(e)}")

print("\n3️⃣ TESTING FILE UPLOAD...")
print("-" * 60)

test_file_id = None
if test_folder_id:
    try:
        # Create test file
        test_file_path = f"test_file_{timestamp}.txt"
        with open(test_file_path, 'w') as f:
            f.write(f"Comprehensive test file created at {timestamp}\n")
            f.write("This tests the Shared Drive upload functionality.")
        
        # Upload to test folder
        test_file_id = drive_service.upload_file(
            test_file_path, 
            f"test_upload_{timestamp}.txt",
            test_folder_id
        )
        print(f"✅ Uploaded file successfully")
        print(f"   ID: {test_file_id}")
        print(f"   Link: {drive_service.get_file_link(test_file_id)}")
        results["upload_file"] = True
        
        # Clean up local file
        os.remove(test_file_path)
    except Exception as e:
        print(f"❌ File upload failed: {str(e)}")
        results["error_messages"].append(f"File upload: {str(e)}")
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

print("\n4️⃣ TESTING FILE LISTING...")
print("-" * 60)

try:
    files = drive_service.list_files(test_folder_id)
    print(f"✅ Listed {len(files)} files in test folder")
    for file in files:
        print(f"   - {file['name']} (ID: {file['id']})")
    results["list_files"] = True
except Exception as e:
    print(f"❌ File listing failed: {str(e)}")
    results["error_messages"].append(f"File listing: {str(e)}")

print("\n5️⃣ TESTING FILE METADATA ACCESS...")
print("-" * 60)

if test_file_id:
    try:
        file_meta = drive_api.files().get(
            fileId=test_file_id,
            supportsAllDrives=True,
            fields='id,name,size,createdTime,permissions,capabilities'
        ).execute()
        print(f"✅ Retrieved file metadata")
        print(f"   Name: {file_meta['name']}")
        print(f"   Size: {file_meta.get('size', 'N/A')} bytes")
        print(f"   Can download: {file_meta.get('capabilities', {}).get('canDownload', False)}")
        results["get_metadata"] = True
    except Exception as e:
        print(f"❌ Metadata retrieval failed: {str(e)}")
        results["error_messages"].append(f"Metadata retrieval: {str(e)}")

print("\n6️⃣ TESTING TEMPLATE FOLDER ACCESS...")
print("-" * 60)

try:
    # List files in templates folder
    template_files = drive_api.files().list(
        q=f"'{PRODUCTION_TEMPLATES_ID}' in parents",
        pageSize=5,
        fields="files(id, name, mimeType)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    templates = template_files.get('files', [])
    print(f"✅ Found {len(templates)} templates")
    for template in templates[:3]:  # Show first 3
        print(f"   - {template['name']}")
    results["template_access"] = True
except Exception as e:
    print(f"❌ Template access failed: {str(e)}")
    results["error_messages"].append(f"Template access: {str(e)}")

print("\n7️⃣ TESTING FILE DELETION...")
print("-" * 60)

if test_file_id:
    try:
        success = drive_service.delete_file(test_file_id)
        if success:
            print(f"✅ Deleted test file successfully")
            results["delete_file"] = True
        else:
            print(f"❌ File deletion returned False")
    except Exception as e:
        print(f"❌ File deletion failed: {str(e)}")
        results["error_messages"].append(f"File deletion: {str(e)}")

print("\n8️⃣ CLEANING UP TEST FOLDER...")
print("-" * 60)

if test_folder_id:
    try:
        drive_api.files().delete(
            fileId=test_folder_id,
            supportsAllDrives=True
        ).execute()
        print("✅ Cleaned up test folder")
    except Exception as e:
        print(f"⚠️  Failed to clean up test folder: {str(e)}")

print("\n" + "=" * 80)
print("📊 TEST RESULTS SUMMARY")
print("=" * 80)

# Calculate success rate
total_tests = len([k for k in results.keys() if k != "error_messages"])
passed_tests = sum(1 for k, v in results.items() if k != "error_messages" and v)
success_rate = (passed_tests / total_tests) * 100

print(f"\nTests Passed: {passed_tests}/{total_tests} ({success_rate:.0f}%)")
print("\nDetailed Results:")
for test, passed in results.items():
    if test != "error_messages":
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test.replace('_', ' ').title()}: {status}")

if results["error_messages"]:
    print("\n❌ ERROR DETAILS:")
    for error in results["error_messages"]:
        print(f"  - {error}")

print("\n" + "=" * 80)

if success_rate == 100:
    print("✅ ALL TESTS PASSED! The Shared Drive fix is working correctly.")
    print("\n🎉 You can deploy with confidence!")
else:
    print("⚠️  SOME TESTS FAILED!")
    print("\nPossible causes:")
    print("1. The folders might not be Shared Drives")
    print("2. Service account might not have proper permissions")
    print("3. There might be additional API issues to fix")
    print("\nReview the error messages above for details.")