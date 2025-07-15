#!/usr/bin/env python3
"""
Google Drive Storage Cleanup Script - Automated Version
Removes test files to free up service account storage space
Preserves files associated with Jason Pritchard (Agent ID 0000)
"""

import os
import json
from datetime import datetime
from services.google_drive_service import GoogleDriveService
from dotenv import load_dotenv

load_dotenv()

# Load service account credentials from environment variable or file
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if SERVICE_ACCOUNT_JSON:
    SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)
else:
    # Fallback to file for local development
    try:
        with open('upwork-greenwatt-drive-sheets-3be108764560.json', 'r') as f:
            SERVICE_ACCOUNT_INFO = json.load(f)
    except FileNotFoundError:
        raise Exception("Service account credentials not found. Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable.")

# Initialize services
drive_service = GoogleDriveService(
    service_account_info=SERVICE_ACCOUNT_INFO,
    parent_folder_id=os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')
)

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
    jason_keywords = [
        'jason pritchard',
        'pritchard jason',
        'agent_0000',
        'agent-0000',
        'ag0000',
        'ag-0000',
        '0000_'
    ]
    
    filename_lower = filename.lower()
    return any(keyword in filename_lower for keyword in jason_keywords)

def list_all_files_recursive(drive_service, folder_id, path=""):
    """Recursively list all files and folders"""
    all_items = []
    
    # Get items in current folder
    items = drive_service.list_files(folder_id=folder_id)
    
    for item in items:
        item['path'] = path + "/" + item['name'] if path else item['name']
        all_items.append(item)
        
        # If it's a folder, recurse into it
        if item.get('mimeType') == 'application/vnd.google-apps.folder':
            subfolder_items = list_all_files_recursive(drive_service, item['id'], item['path'])
            all_items.extend(subfolder_items)
    
    return all_items

def main():
    print("\n🔍 Google Drive Storage Cleanup Script (Automated)")
    print("=" * 50)
    
    # Get all files in the parent folder and subfolders
    print(f"\n📂 Fetching files from folder: {os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')}")
    print("   Note: This may take a moment as we scan all subfolders...")
    
    all_items = list_all_files_recursive(drive_service, os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID'))
    
    if not all_items:
        print("❌ No files found or error accessing folder")
        return
    
    print(f"✅ Found {len(all_items)} total items (files and folders)\n")
    
    # Separate files from folders and categorize
    jason_items = []
    test_items = []
    folders_to_delete = []
    files_to_delete = []
    total_file_size = 0
    test_file_size = 0
    
    for item in all_items:
        is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'
        file_size = int(item.get('size', 0))
        
        if not is_folder:
            total_file_size += file_size
        
        if is_jason_pritchard_file(item['name']):
            jason_items.append(item)
        else:
            test_items.append(item)
            if is_folder:
                folders_to_delete.append(item)
            else:
                files_to_delete.append(item)
                test_file_size += file_size
    
    # Display summary
    print(f"📊 Storage Summary:")
    print(f"   Total items: {len(all_items)}")
    print(f"   Total file size: {format_file_size(total_file_size)}")
    print(f"   Jason Pritchard items: {len(jason_items)} (preserved)")
    print(f"   Test folders to delete: {len(folders_to_delete)}")
    print(f"   Test files to delete: {len(files_to_delete)}")
    print(f"   Test files size: {format_file_size(test_file_size)}")
    print(f"   Potential space to free: {format_file_size(test_file_size)}\n")
    
    # Show sample of items to be deleted
    if test_items:
        print("📋 Sample of items to be deleted (first 10):")
        for i, item in enumerate(test_items[:10]):
            is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'
            type_str = "📁 Folder" if is_folder else "📄 File"
            file_size = format_file_size(item.get('size', 0)) if not is_folder else "N/A"
            created = item.get('createdTime', 'Unknown')
            print(f"   {i+1}. {type_str} {item['path']} ({file_size})")
        
        if len(test_items) > 10:
            print(f"   ... and {len(test_items) - 10} more items")
    
    # Auto-proceed with deletion
    print(f"\n🗑️  Auto-deleting {len(test_items)} test items...")
    deleted_count = 0
    failed_count = 0
    
    # Delete files first, then folders (to handle nested structures)
    all_deletable = files_to_delete + folders_to_delete
    
    for i, item in enumerate(all_deletable):
        try:
            item_type = "folder" if item.get('mimeType') == 'application/vnd.google-apps.folder' else "file"
            if drive_service.delete_file(item['id']):
                deleted_count += 1
                if (i + 1) % 10 == 0:
                    print(f"   Deleted {i + 1}/{len(all_deletable)} items...")
            else:
                failed_count += 1
                print(f"   ❌ Failed to delete {item_type}: {item['name']}")
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Error deleting {item['name']}: {e}")
    
    # Final summary
    print(f"\n✅ Cleanup Complete!")
    print(f"   Items deleted: {deleted_count}")
    print(f"   Failed deletions: {failed_count}")
    print(f"   Space freed: ~{format_file_size(test_file_size)}")
    print(f"   Jason Pritchard items preserved: {len(jason_items)}")

if __name__ == "__main__":
    main()