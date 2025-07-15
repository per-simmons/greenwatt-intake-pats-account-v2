#!/usr/bin/env python3
"""
Google Drive Storage Cleanup Script - Comprehensive Version
Properly deletes FILES (not just folders) to free up storage quota
Includes option to permanently delete (bypass trash)
"""

import os
import json
from datetime import datetime
from googleapiclient.errors import HttpError
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

# Initialize service manager and get drive service
service_manager = GoogleServiceManager()
service_manager.initialize(SERVICE_ACCOUNT_INFO)
drive_service = service_manager.get_drive_service()

PARENT_FOLDER_ID = os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')

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

def get_all_files_recursive(service, folder_id, path="", depth=0):
    """Recursively get all files and folders with proper error handling"""
    all_items = []
    
    # Prevent infinite recursion
    if depth > 10:
        print(f"⚠️  Max depth reached at: {path}")
        return all_items
    
    try:
        page_token = None
        
        while True:
            # Query for all items in the folder
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=100,
                fields="nextPageToken, files(id, name, size, mimeType, createdTime, parents)",
                pageToken=page_token
            ).execute()
            
            items = response.get('files', [])
            
            for item in items:
                item['path'] = os.path.join(path, item['name'])
                item['depth'] = depth
                all_items.append(item)
                
                # If it's a folder, recurse
                if item.get('mimeType') == 'application/vnd.google-apps.folder':
                    print(f"   📁 Scanning folder: {item['path']}")
                    sub_items = get_all_files_recursive(service, item['id'], item['path'], depth + 1)
                    all_items.extend(sub_items)
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
    except HttpError as error:
        print(f"❌ Error accessing {path}: {error}")
    
    return all_items

def permanently_delete_file(service, file_id, file_name):
    """Permanently delete a file (bypass trash)"""
    try:
        # First try to delete normally
        service.files().delete(fileId=file_id).execute()
        
        # Then empty it from trash to free space immediately
        try:
            service.files().emptyTrash().execute()
        except:
            # If we can't empty all trash, at least the file is deleted
            pass
            
        return True
    except HttpError as error:
        if error.resp.status == 404:
            # File already deleted
            return True
        print(f"❌ Error deleting {file_name}: {error}")
        return False

def main():
    print("\n🔍 Google Drive Comprehensive Cleanup")
    print("=" * 50)
    print("⚠️  This will PERMANENTLY delete files to free storage quota")
    print("=" * 50)
    
    # Get ALL items recursively
    print(f"\n📂 Scanning ALL folders and files recursively...")
    print(f"   Starting from folder: {PARENT_FOLDER_ID}")
    
    all_items = get_all_files_recursive(drive_service, PARENT_FOLDER_ID)
    
    if not all_items:
        print("❌ No items found")
        return
    
    print(f"\n✅ Found {len(all_items)} total items")
    
    # Separate and analyze
    files = []
    folders = []
    jason_items = []
    deletable_files = []
    deletable_folders = []
    total_size = 0
    deletable_size = 0
    
    for item in all_items:
        is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'
        size = int(item.get('size', 0))
        
        if is_folder:
            folders.append(item)
        else:
            files.append(item)
            total_size += size
        
        if is_jason_pritchard_file(item['name']):
            jason_items.append(item)
        else:
            if is_folder:
                deletable_folders.append(item)
            else:
                deletable_files.append(item)
                deletable_size += size
    
    # Display analysis
    print(f"\n📊 Storage Analysis:")
    print(f"   Total files: {len(files)}")
    print(f"   Total folders: {len(folders)}")
    print(f"   Total file size: {format_file_size(total_size)}")
    print(f"   ")
    print(f"   Jason Pritchard items (preserved): {len(jason_items)}")
    print(f"   Deletable files: {len(deletable_files)}")
    print(f"   Deletable folders: {len(deletable_folders)}")
    print(f"   Space to free: {format_file_size(deletable_size)}")
    
    # Show largest files
    if deletable_files:
        sorted_files = sorted(deletable_files, key=lambda x: int(x.get('size', 0)), reverse=True)
        print(f"\n📄 Largest files to delete:")
        for i, file in enumerate(sorted_files[:10]):
            size = format_file_size(file.get('size', 0))
            print(f"   {i+1}. {file['name']} ({size}) - {file['path']}")
    
    if not deletable_files and not deletable_folders:
        print("\n✅ No deletable items found!")
        return
    
    # Confirm deletion
    print(f"\n⚠️  Ready to PERMANENTLY delete:")
    print(f"   - {len(deletable_files)} files ({format_file_size(deletable_size)})")
    print(f"   - {len(deletable_folders)} folders")
    
    # Auto-proceed for automation
    print("\n🗑️  Starting permanent deletion...")
    
    # Delete files first (they hold the actual storage)
    deleted_files = 0
    failed_files = 0
    
    print(f"\n📄 Deleting {len(deletable_files)} files...")
    for i, file in enumerate(deletable_files):
        if permanently_delete_file(drive_service, file['id'], file['name']):
            deleted_files += 1
            if (i + 1) % 10 == 0:
                print(f"   Progress: {i + 1}/{len(deletable_files)} files deleted")
        else:
            failed_files += 1
    
    # Then delete folders (now empty)
    deleted_folders = 0
    failed_folders = 0
    
    print(f"\n📁 Deleting {len(deletable_folders)} folders...")
    # Sort by depth (deepest first) to avoid deleting parent before children
    sorted_folders = sorted(deletable_folders, key=lambda x: x['depth'], reverse=True)
    
    for i, folder in enumerate(sorted_folders):
        if permanently_delete_file(drive_service, folder['id'], folder['name']):
            deleted_folders += 1
            if (i + 1) % 10 == 0:
                print(f"   Progress: {i + 1}/{len(sorted_folders)} folders deleted")
        else:
            failed_folders += 1
    
    # Empty trash to ensure space is freed
    print("\n🗑️  Emptying trash to free space immediately...")
    try:
        drive_service.files().emptyTrash().execute()
        print("✅ Trash emptied successfully")
    except Exception as e:
        print(f"⚠️  Could not empty entire trash: {e}")
    
    # Final summary
    print(f"\n✅ Cleanup Complete!")
    print(f"   Files deleted: {deleted_files}/{len(deletable_files)}")
    print(f"   Folders deleted: {deleted_folders}/{len(deletable_folders)}")
    print(f"   Failed deletions: {failed_files + failed_folders}")
    print(f"   Space freed: ~{format_file_size(deletable_size)}")
    print(f"   Jason Pritchard items preserved: {len(jason_items)}")

if __name__ == "__main__":
    main()