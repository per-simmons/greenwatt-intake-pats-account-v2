from googleapiclient.http import MediaFileUpload
import os
from .google_service_manager import GoogleServiceManager

class GoogleDriveService:
    def __init__(self, service_account_info=None, parent_folder_id=None):
        # Use the singleton service manager
        self.service_manager = GoogleServiceManager()
        
        # Initialize the service manager if credentials provided
        if service_account_info:
            self.service_manager.initialize(service_account_info)
        
        # Get the shared drive service
        self.service = self.service_manager.get_drive_service()
        self.parent_folder_id = parent_folder_id
        
    def create_folder(self, folder_name, parent_id=None):
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        # Use provided parent_id, or fall back to instance parent_folder_id
        target_parent = parent_id or self.parent_folder_id
        if target_parent:
            file_metadata['parents'] = [target_parent]
            
        try:
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            
            self.service.permissions().create(
                fileId=folder_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()
            
            return folder_id
        except Exception as e:
            print(f"Error creating folder: {e}")
            raise
            
    def upload_file(self, file_path, file_name, folder_id=None):
        file_metadata = {'name': file_name}
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        mime_type = 'application/pdf' if file_path.endswith('.pdf') else 'image/jpeg'
        
        try:
            media = MediaFileUpload(file_path, mimetype=mime_type)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            
            self.service.permissions().create(
                fileId=file_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()
            
            return file_id
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise
            
    def get_file_link(self, file_id):
        return f"https://drive.google.com/file/d/{file_id}/view"
    
    def delete_file(self, file_id):
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False