from google.oauth2 import service_account
from googleapiclient.discovery import build
import threading

class GoogleServiceManager:
    """
    Singleton manager for Google API services to prevent memory exhaustion.
    This ensures we only create one instance of each Google service API client,
    saving ~200MB of memory per duplicate service.
    """
    _instance = None
    _lock = threading.Lock()
    _sheets_service = None
    _drive_service = None
    _credentials = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, service_account_info):
        """Initialize with service account credentials"""
        if not self._credentials:
            self._credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            print("✅ GoogleServiceManager initialized with credentials")
    
    def get_sheets_service(self):
        """Get or create the Google Sheets service instance"""
        if not self._sheets_service:
            if not self._credentials:
                raise ValueError("GoogleServiceManager not initialized. Call initialize() first.")
            
            print("🔄 Creating Google Sheets service instance...")
            self._sheets_service = build('sheets', 'v4', credentials=self._credentials)
            print("✅ Google Sheets service created")
        
        return self._sheets_service
    
    def get_drive_service(self):
        """Get or create the Google Drive service instance"""
        if not self._drive_service:
            if not self._credentials:
                raise ValueError("GoogleServiceManager not initialized. Call initialize() first.")
            
            print("🔄 Creating Google Drive service instance...")
            self._drive_service = build('drive', 'v3', credentials=self._credentials)
            print("✅ Google Drive service created")
        
        return self._drive_service
    
    def get_memory_usage(self):
        """Get current memory usage statistics"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent()
        }
    
    def log_memory_status(self, operation=""):
        """Log current memory usage"""
        memory = self.get_memory_usage()
        print(f"📊 Memory Usage {operation}: {memory['rss_mb']:.1f}MB ({memory['percent']:.1f}%)")
        return memory