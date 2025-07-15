#!/usr/bin/env python3
"""
Clean up orphaned files (files with no parent folder) owned by service account
These files are consuming storage but not visible in the main folder structure
"""

import os
import json
from services.google_service_manager import GoogleServiceManager
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

# Initialize service
service_manager = GoogleServiceManager()
service_manager.initialize(SERVICE_ACCOUNT_INFO)
drive_service = service_manager.get_drive_service()

def format_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if not size_bytes:
        return "0 B"
    
    size_bytes = int(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def is_jason_pritchard_file(filename):
    """Check if file is associated with Jason Pritchard or Agent ID 0000"""
    jason_keywords = ['jason pritchard', 'pritchard', 'agent_0000', '0000_']
    filename_lower = filename.lower()
    return any(keyword in filename_lower for keyword in jason_keywords)

def main():
    print("\n🔍 Cleaning Orphaned Files")
    print("=" * 50)
    
    # Find all files without parents (orphaned)
    print("\n📋 Finding orphaned files...")
    
    orphaned_files = []
    page_token = None
    
    try:
        while True:
            # Query for files with no parents
            response = drive_service.files().list(
                q="trashed=false and 'me' in owners",
                pageSize=100,
                fields="nextPageToken, files(id, name, size, mimeType, createdTime, parents)",
                pageToken=page_token
            ).execute()
            
            items = response.get('files', [])
            
            # Filter for orphaned files (no parents or empty parents list)
            for item in items:
                parents = item.get('parents', [])
                if not parents and item.get('mimeType') != 'application/vnd.google-apps.folder':
                    orphaned_files.append(item)
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
    except Exception as e:
        print(f"❌ Error searching Drive: {e}")
        return
    
    if not orphaned_files:
        print("✅ No orphaned files found!")
        return
    
    # Analyze orphaned files
    total_size = 0
    deletable_files = []
    preserved_files = []
    
    for file in orphaned_files:
        size = int(file.get('size', 0))
        total_size += size
        
        if is_jason_pritchard_file(file['name']):
            preserved_files.append(file)
        else:
            deletable_files.append(file)
    
    print(f"\n📊 Orphaned Files Analysis:")
    print(f"   Total orphaned files: {len(orphaned_files)}")
    print(f"   Total size: {format_file_size(total_size)}")
    print(f"   Files to delete: {len(deletable_files)}")
    print(f"   Jason Pritchard files (preserved): {len(preserved_files)}")
    
    # Show files to delete
    if deletable_files:
        print(f"\n📄 Orphaned files to delete:")
        sorted_files = sorted(deletable_files, key=lambda x: int(x.get('size', 0)), reverse=True)
        for i, file in enumerate(sorted_files):
            size = format_file_size(file.get('size', 0))
            created = file.get('createdTime', 'Unknown')
            print(f"   {i+1}. {file['name']} ({size}) - Created: {created}")
    
    if not deletable_files:
        print("\n✅ No deletable orphaned files!")
        return
    
    # Delete orphaned files
    print(f"\n🗑️  Permanently deleting {len(deletable_files)} orphaned files...")
    deleted = 0
    failed = 0
    
    for i, file in enumerate(deletable_files):
        try:
            # Permanently delete
            drive_service.files().delete(fileId=file['id']).execute()
            deleted += 1
            print(f"   ✅ Deleted: {file['name']}")
        except Exception as e:
            failed += 1
            print(f"   ❌ Failed: {file['name']} - {str(e)[:50]}")
    
    # Empty trash to free space
    print("\n🗑️  Emptying trash...")
    try:
        drive_service.files().emptyTrash().execute()
        print("✅ Trash emptied")
    except:
        pass
    
    print(f"\n✅ Cleanup Complete!")
    print(f"   Deleted: {deleted}")
    print(f"   Failed: {failed}")
    print(f"   Space freed: ~{format_file_size(sum(int(f.get('size', 0)) for f in deletable_files))}")

if __name__ == "__main__":
    main()