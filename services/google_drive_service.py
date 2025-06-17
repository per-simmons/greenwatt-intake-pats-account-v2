from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

class GoogleDriveService:
    def __init__(self, service_account_info, parent_folder_id=None):
        self.credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        self.service = build('drive', 'v3', credentials=self.credentials)
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