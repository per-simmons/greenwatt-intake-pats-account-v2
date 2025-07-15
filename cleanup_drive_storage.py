#!/usr/bin/env python3
"""
Google Drive Storage Cleanup Script
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

def main():
    print("\n🔍 Google Drive Storage Cleanup Script")
    print("=" * 50)
    
    # Get all files in the parent folder
    print(f"\n📂 Fetching files from folder: {os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')}")
    all_files = drive_service.list_files()
    
    if not all_files:
        print("❌ No files found or error accessing folder")
        return
    
    print(f"✅ Found {len(all_files)} total files\n")
    
    # Categorize files
    jason_files = []
    test_files = []
    total_size = 0
    test_size = 0
    
    for file in all_files:
        file_size = int(file.get('size', 0))
        total_size += file_size
        
        if is_jason_pritchard_file(file['name']):
            jason_files.append(file)
        else:
            test_files.append(file)
            test_size += file_size
    
    # Display summary
    print(f"📊 Storage Summary:")
    print(f"   Total files: {len(all_files)}")
    print(f"   Total size: {format_file_size(total_size)}")
    print(f"   Jason Pritchard files: {len(jason_files)}")
    print(f"   Test files (deletable): {len(test_files)}")
    print(f"   Test files size: {format_file_size(test_size)}")
    print(f"   Potential space to free: {format_file_size(test_size)}\n")
    
    # Show sample of files to be deleted
    if test_files:
        print("📋 Sample of files to be deleted (first 10):")
        for i, file in enumerate(test_files[:10]):
            file_size = format_file_size(file.get('size', 0))
            created = file.get('createdTime', 'Unknown')
            print(f"   {i+1}. {file['name']} ({file_size}) - Created: {created}")
        
        if len(test_files) > 10:
            print(f"   ... and {len(test_files) - 10} more files")
    
    # Confirm deletion
    print(f"\n⚠️  This will delete {len(test_files)} test files and free up {format_file_size(test_size)}")
    confirmation = input("Do you want to proceed with deletion? (yes/no): ").lower().strip()
    
    if confirmation != 'yes':
        print("❌ Cleanup cancelled")
        return
    
    # Delete files
    print("\n🗑️  Deleting test files...")
    deleted_count = 0
    failed_count = 0
    
    for i, file in enumerate(test_files):
        try:
            if drive_service.delete_file(file['id']):
                deleted_count += 1
                if (i + 1) % 10 == 0:
                    print(f"   Deleted {i + 1}/{len(test_files)} files...")
            else:
                failed_count += 1
                print(f"   ❌ Failed to delete: {file['name']}")
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Error deleting {file['name']}: {e}")
    
    # Final summary
    print(f"\n✅ Cleanup Complete!")
    print(f"   Files deleted: {deleted_count}")
    print(f"   Failed deletions: {failed_count}")
    print(f"   Space freed: ~{format_file_size(test_size)}")
    print(f"   Jason Pritchard files preserved: {len(jason_files)}")

if __name__ == "__main__":
    main()