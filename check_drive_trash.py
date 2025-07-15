#!/usr/bin/env python3
"""
Check Google Drive trash for files consuming storage quota
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

def main():
    print("\n🗑️  Checking Google Drive Trash")
    print("=" * 50)
    
    # Query for ALL trashed items owned by service account
    print("\n📋 Finding all trashed items...")
    
    trashed_items = []
    page_token = None
    
    try:
        while True:
            response = drive_service.files().list(
                q="trashed=true",
                pageSize=100,
                fields="nextPageToken, files(id, name, size, mimeType, trashedTime)",
                pageToken=page_token
            ).execute()
            
            items = response.get('files', [])
            trashed_items.extend(items)
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
    except Exception as e:
        print(f"❌ Error accessing trash: {e}")
        return
    
    if not trashed_items:
        print("✅ No items in trash!")
        return
    
    # Analyze trash
    total_size = 0
    files = []
    folders = []
    
    for item in trashed_items:
        is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'
        size = int(item.get('size', 0))
        
        if is_folder:
            folders.append(item)
        else:
            files.append(item)
            total_size += size
    
    print(f"\n📊 Trash Analysis:")
    print(f"   Total items in trash: {len(trashed_items)}")
    print(f"   Files: {len(files)}")
    print(f"   Folders: {len(folders)}")
    print(f"   Total size in trash: {format_file_size(total_size)}")
    
    # Show some items
    if files:
        print(f"\n📄 Files in trash (first 10):")
        sorted_files = sorted(files, key=lambda x: int(x.get('size', 0)), reverse=True)
        for i, file in enumerate(sorted_files[:10]):
            size = format_file_size(file.get('size', 0))
            print(f"   {i+1}. {file['name']} ({size})")
    
    # Empty trash
    if total_size > 0:
        print(f"\n🗑️  Emptying trash to free {format_file_size(total_size)}...")
        try:
            drive_service.files().emptyTrash().execute()
            print("✅ Trash emptied successfully!")
        except Exception as e:
            print(f"❌ Error emptying trash: {e}")

if __name__ == "__main__":
    main()