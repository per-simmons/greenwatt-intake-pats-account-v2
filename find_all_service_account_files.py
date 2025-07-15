#!/usr/bin/env python3
"""
Find ALL files owned by the service account across entire Google Drive
This helps identify where the 15GB storage is being consumed
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
    print("\n🔍 Finding ALL files owned by service account")
    print("=" * 50)
    
    # Query for ALL items owned by the service account (not just in specific folder)
    print("\n📋 Searching entire Google Drive...")
    
    all_items = []
    page_token = None
    
    try:
        while True:
            # No parent restriction - find ALL files owned by this service account
            response = drive_service.files().list(
                q="trashed=false",
                pageSize=100,
                fields="nextPageToken, files(id, name, size, mimeType, createdTime, parents, owners)",
                pageToken=page_token
            ).execute()
            
            items = response.get('files', [])
            all_items.extend(items)
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
            
            print(f"   Found {len(all_items)} items so far...")
                
    except Exception as e:
        print(f"❌ Error searching Drive: {e}")
        return
    
    if not all_items:
        print("✅ No files found!")
        return
    
    # Analyze all items
    total_size = 0
    files = []
    folders = []
    files_by_location = {}
    
    for item in all_items:
        is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'
        size = int(item.get('size', 0))
        parents = item.get('parents', ['No parent'])
        
        if is_folder:
            folders.append(item)
        else:
            files.append(item)
            total_size += size
            
            # Track by parent folder
            parent_id = parents[0] if parents else 'No parent'
            if parent_id not in files_by_location:
                files_by_location[parent_id] = {'files': [], 'size': 0}
            files_by_location[parent_id]['files'].append(item)
            files_by_location[parent_id]['size'] += size
    
    print(f"\n📊 Service Account Storage Analysis:")
    print(f"   Total items found: {len(all_items)}")
    print(f"   Files: {len(files)}")
    print(f"   Folders: {len(folders)}")
    print(f"   Total storage used: {format_file_size(total_size)}")
    
    # Show largest files
    if files:
        print(f"\n📄 Largest files (top 20):")
        sorted_files = sorted(files, key=lambda x: int(x.get('size', 0)), reverse=True)
        for i, file in enumerate(sorted_files[:20]):
            size = format_file_size(file.get('size', 0))
            parent = file.get('parents', ['Unknown'])[0]
            print(f"   {i+1}. {file['name']} ({size}) - Parent: {parent}")
    
    # Show storage by location
    print(f"\n📁 Storage by parent folder:")
    sorted_locations = sorted(files_by_location.items(), 
                            key=lambda x: x[1]['size'], reverse=True)
    
    for parent_id, info in sorted_locations[:10]:
        size = format_file_size(info['size'])
        count = len(info['files'])
        print(f"   Folder {parent_id}: {count} files, {size}")
        
        # Try to get folder name
        if parent_id != 'No parent':
            try:
                folder = drive_service.files().get(fileId=parent_id, fields='name').execute()
                print(f"      Name: {folder.get('name', 'Unknown')}")
            except:
                pass
    
    # Show target folder info
    target_folder_id = os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID')
    if target_folder_id in files_by_location:
        info = files_by_location[target_folder_id]
        print(f"\n📂 Target folder ({target_folder_id}):")
        print(f"   Files: {len(info['files'])}")
        print(f"   Size: {format_file_size(info['size'])}")

if __name__ == "__main__":
    main()