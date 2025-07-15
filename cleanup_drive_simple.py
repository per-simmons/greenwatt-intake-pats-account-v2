#!/usr/bin/env python3
"""
Google Drive Storage Cleanup Script - Simple Version
Removes test folders from main directory only
"""

import os
import json
from services.google_drive_service import GoogleDriveService
from dotenv import load_dotenv

load_dotenv()

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
drive_service = GoogleDriveService(
    service_account_info=SERVICE_ACCOUNT_INFO,
    parent_folder_id=os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')
)

def is_jason_pritchard_file(filename):
    """Check if file is associated with Jason Pritchard or Agent ID 0000"""
    jason_keywords = ['jason pritchard', 'pritchard', 'agent_0000', '0000_']
    filename_lower = filename.lower()
    return any(keyword in filename_lower for keyword in jason_keywords)

def main():
    print("\n🔍 Google Drive Cleanup - Simple Version")
    print("=" * 50)
    
    # Get items in main folder only
    print(f"\n📂 Fetching items from main folder...")
    items = drive_service.list_files()
    
    if not items:
        print("❌ No items found")
        return
    
    print(f"✅ Found {len(items)} items\n")
    
    # Filter out Jason Pritchard items
    deletable_items = []
    preserved_items = []
    
    for item in items:
        if is_jason_pritchard_file(item['name']):
            preserved_items.append(item)
        else:
            deletable_items.append(item)
    
    print(f"📊 Summary:")
    print(f"   Total items: {len(items)}")
    print(f"   Jason Pritchard items (preserved): {len(preserved_items)}")
    print(f"   Items to delete: {len(deletable_items)}")
    
    if not deletable_items:
        print("\n✅ No test items to delete!")
        return
    
    # Show first 20 items to delete
    print(f"\n📋 Items to delete (showing first 20):")
    for i, item in enumerate(deletable_items[:20]):
        print(f"   {i+1}. {item['name']}")
    
    if len(deletable_items) > 20:
        print(f"   ... and {len(deletable_items) - 20} more")
    
    # Delete items
    print(f"\n🗑️  Deleting {len(deletable_items)} items...")
    deleted = 0
    failed = 0
    
    for i, item in enumerate(deletable_items):
        try:
            if drive_service.delete_file(item['id']):
                deleted += 1
                if deleted % 10 == 0:
                    print(f"   Progress: {deleted}/{len(deletable_items)} deleted")
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"   Error: {item['name']} - {str(e)[:50]}")
    
    print(f"\n✅ Complete!")
    print(f"   Deleted: {deleted}")
    print(f"   Failed: {failed}")
    print(f"   Preserved: {len(preserved_items)}")

if __name__ == "__main__":
    main()