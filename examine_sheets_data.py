#!/usr/bin/env python3
"""
Examine raw Google Sheets data to debug why Orange & Rockland isn't showing
"""
import os
import json
from dotenv import load_dotenv
from services.google_sheets_service import GoogleSheetsService

load_dotenv()

def examine_sheets_data():
    print("🔍 Examining Raw Google Sheets Data")
    print("=" * 50)
    
    # Load service account credentials
    SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if SERVICE_ACCOUNT_JSON:
        SERVICE_ACCOUNT_INFO = json.loads(SERVICE_ACCOUNT_JSON)
    else:
        try:
            with open('upwork-greenwatt-drive-sheets-3be108764560.json', 'r') as f:
                SERVICE_ACCOUNT_INFO = json.load(f)
        except FileNotFoundError:
            print("❌ Service account credentials not found")
            return
    
    dynamic_sheets_id = os.getenv('DYNAMIC_GOOGLE_SHEETS_ID')
    print(f"📊 Dynamic Sheets ID: {dynamic_sheets_id}")
    
    try:
        # Create dynamic sheets service
        dynamic_sheets_service = GoogleSheetsService(
            SERVICE_ACCOUNT_INFO,
            dynamic_sheets_id,
            os.getenv('GOOGLE_AGENT_SHEETS_ID')
        )
        
        # Get raw data from Utilities tab
        print("\n📋 Raw data from Utilities tab:")
        print("=" * 30)
        
        rows = dynamic_sheets_service.service.spreadsheets().values().get(
            spreadsheetId=dynamic_sheets_id,
            range="Utilities!A:B"
        ).execute().get("values", [])
        
        if not rows:
            print("❌ No data found in Utilities tab")
            return
        
        print(f"Found {len(rows)} rows:")
        for i, row in enumerate(rows):
            if len(row) >= 2:
                utility_name = row[0]
                active_flag = row[1]
                print(f"Row {i}: '{utility_name}' | '{active_flag}'")
                
                # Check for Orange & Rockland specifically
                if "orange" in utility_name.lower() and "rockland" in utility_name.lower():
                    print(f"  🎯 FOUND Orange & Rockland variant: '{utility_name}'")
                    print(f"     Active flag: '{active_flag}' (type: {type(active_flag)})")
                    print(f"     Equals 'TRUE'? {active_flag.strip().upper() == 'TRUE'}")
            else:
                print(f"Row {i}: {row} (incomplete)")
        
        print("\n" + "=" * 30)
        
        # Test the get_active_utilities logic manually
        print("\n🔍 Testing get_active_utilities logic:")
        utilities = [r[0] for r in rows[1:] if len(r) >= 2 and r[1].strip().upper() == "TRUE"]
        print(f"Filtered utilities: {utilities}")
        
        # Check for exact matches
        print("\n🔍 Checking for exact string matches:")
        test_strings = ["Orange & Rockland", "Orange &amp; Rockland", "Orange and Rockland", "Orange & Rockland "]
        for test_string in test_strings:
            found = any(row[0] == test_string for row in rows[1:] if len(row) >= 2)
            print(f"  '{test_string}': {'✅ Found' if found else '❌ Not found'}")
        
    except Exception as e:
        print(f"❌ Error examining sheets data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    examine_sheets_data()