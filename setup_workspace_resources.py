#!/usr/bin/env python3
"""
Setup script for new Google Workspace resources
Populates empty Google Sheets with proper structure and initial data
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
sheets_service = service_manager.get_sheets_service()

def setup_main_intake_sheet(sheet_id):
    """Setup the main intake log sheet with 25 columns and required tabs"""
    print(f"\n📋 Setting up Main Intake Sheet: {sheet_id}")
    
    # 1. Set up the main Submissions sheet headers
    headers = [
        'Unique ID',
        'Submission Date',
        'Business Entity Name',
        'Account Name',
        'Contact Name',
        'Title',
        'Phone',
        'Email',
        'Service Address',
        'Developer Assigned',
        'Account Type',
        'Utility Provider (Form)',
        'Utility Name (OCR)',
        'Account Number (OCR)',
        'POID',
        'Monthly Usage (OCR)',
        'Annual Usage (OCR)',
        'Agent ID',
        'Agent Name',
        'POA ID',
        'Utility Bill Link',
        'POA Link',
        'Agreement Link',
        'Terms & Conditions Link',
        'CDG Enrollment Status'
    ]
    
    # Update headers
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='A1:Y1',
        valueInputOption='RAW',
        body={'values': [headers]}
    ).execute()
    print("✅ Headers created")
    
    # 2. Format the header row (green background, white text)
    format_request = {
        'requests': [{
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {
                            'red': 0.17,
                            'green': 0.33,
                            'blue': 0.19
                        },
                        'horizontalAlignment': 'CENTER',
                        'textFormat': {
                            'foregroundColor': {
                                'red': 1.0,
                                'green': 1.0,
                                'blue': 1.0
                            },
                            'fontSize': 11,
                            'bold': True
                        }
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
            }
        }]
    }
    
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body=format_request
    ).execute()
    print("✅ Header formatting applied")
    
    # 3. Create Utilities tab
    try:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': 'Utilities'
                        }
                    }
                }]
            }
        ).execute()
        print("✅ Utilities tab created")
    except Exception as e:
        print("⚠️  Utilities tab might already exist")
    
    # Populate Utilities tab
    utilities_data = [
        ['utility_name', 'active_flag'],
        ['National Grid', 'TRUE'],
        ['NYSEG', 'TRUE'],
        ['RG&E', 'TRUE'],
        ['Orange & Rockland', 'FALSE'],
        ['Central Hudson', 'FALSE'],
        ['ConEd', 'FALSE']
    ]
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='Utilities!A1:B7',
        valueInputOption='RAW',
        body={'values': utilities_data}
    ).execute()
    print("✅ Utilities data populated")
    
    # 4. Create Developer_Mapping tab
    try:
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': 'Developer_Mapping'
                        }
                    }
                }]
            }
        ).execute()
        print("✅ Developer_Mapping tab created")
    except Exception as e:
        print("⚠️  Developer_Mapping tab might already exist")
    
    # Populate Developer_Mapping tab (Meadow Energy only for now)
    developer_mapping_data = [
        ['developer_name', 'utility_name', 'file_name'],
        ['Meadow Energy', 'National Grid', 'Meadow-National-Grid-Commercial-UCB-Agreement.pdf'],
        ['Meadow Energy', 'NYSEG', 'Meadow-NYSEG-Commercial-UCB-Agreement.pdf'],
        ['Meadow Energy', 'RG&E', 'Meadow-RGE-Commercial-UCB-Agreement.pdf'],
        ['Meadow Energy', 'Mass Market', 'Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf']
    ]
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='Developer_Mapping!A1:C5',
        valueInputOption='RAW',
        body={'values': developer_mapping_data}
    ).execute()
    print("✅ Developer_Mapping data populated")
    
    print("✅ Main intake sheet setup complete!")

def setup_agent_sheet(sheet_id):
    """Setup the agent ID mapping sheet"""
    print(f"\n👥 Setting up Agent Sheet: {sheet_id}")
    
    # 1. Set up headers (columns A-G)
    headers = [
        'Agent ID',      # Column A
        'Agent Name',    # Column B
        'Region',        # Column C
        'Agent Email',   # Column D
        'Status',        # Column E
        'Notes',         # Column F
        'Sales Manager Email'  # Column G
    ]
    
    # Update headers
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='A1:G1',
        valueInputOption='RAW',
        body={'values': [headers]}
    ).execute()
    print("✅ Headers created")
    
    # 2. Format the header row
    format_request = {
        'requests': [{
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {
                            'red': 0.17,
                            'green': 0.33,
                            'blue': 0.19
                        },
                        'horizontalAlignment': 'CENTER',
                        'textFormat': {
                            'foregroundColor': {
                                'red': 1.0,
                                'green': 1.0,
                                'blue': 1.0
                            },
                            'fontSize': 11,
                            'bold': True
                        }
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
            }
        }]
    }
    
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body=format_request
    ).execute()
    print("✅ Header formatting applied")
    
    # 3. Add sample agent data
    agent_data = [
        ['0000', 'Jason Pritchard', 'All', 'jason@greenwattusa.com', 'Active', 'Owner', 'jason@greenwattusa.com'],
        ['0001', 'Pat Simmons (Testing)', 'Test', 'pat.testing@example.com', 'Test', 'Testing Only', 'pat.testing@example.com'],
        ['0002', 'Sample Agent', 'Northeast', '', 'Active', '', ''],
        ['0003', 'Another Agent', 'Northeast', '', 'Active', '', '']
    ]
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='A2:G5',
        valueInputOption='RAW',
        body={'values': agent_data}
    ).execute()
    print("✅ Sample agent data populated")
    
    print("✅ Agent sheet setup complete!")

def main():
    print("\n🚀 Google Workspace Resource Setup Script")
    print("=" * 50)
    print("\nThis script will set up your new Google Workspace resources.")
    print("\nPlease provide the IDs of your new (empty) resources:")
    
    # Get resource IDs from user
    main_sheet_id = input("\n📊 Main Intake Sheet ID: ").strip()
    agent_sheet_id = input("👥 Agent ID Sheet ID: ").strip()
    
    if not main_sheet_id or not agent_sheet_id:
        print("\n❌ Error: Both sheet IDs are required!")
        return
    
    print("\n🔧 Starting setup...")
    
    try:
        # Setup main intake sheet
        setup_main_intake_sheet(main_sheet_id)
        
        # Setup agent sheet
        setup_agent_sheet(agent_sheet_id)
        
        print("\n✅ All resources setup complete!")
        print("\n📝 Next steps:")
        print("1. Update your environment variables in Render.com:")
        print(f"   GOOGLE_SHEETS_ID={main_sheet_id}")
        print(f"   GOOGLE_AGENT_SHEETS_ID={agent_sheet_id}")
        print("   (Don't forget to also update the Drive folder IDs)")
        print("\n2. Share both sheets with the service account:")
        print("   greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com")
        print("   (Give Editor permission)")
        print("\n3. Test the system with a form submission")
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        print("\nPlease check:")
        print("1. The sheet IDs are correct")
        print("2. The service account has edit access to both sheets")
        print("3. Your service account credentials are valid")

if __name__ == "__main__":
    main()