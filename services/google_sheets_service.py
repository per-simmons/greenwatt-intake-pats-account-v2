from google.oauth2 import service_account
from googleapiclient.discovery import build
from cachetools import TTLCache

class GoogleSheetsService:
    def __init__(self, service_account_info, spreadsheet_id, agent_spreadsheet_id=None):
        self.credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.spreadsheet_id = spreadsheet_id
        self.agent_spreadsheet_id = agent_spreadsheet_id or spreadsheet_id
        
        # 15-minute cache for sheet lookups
        self.cache = TTLCache(maxsize=32, ttl=900)
        
        # Column indexes for formatting (0-based) - Updated for POID (OCR) and Service Address (OCR) columns
        self.MONTHLY_USAGE_COL = 16   # Column Q - kWh format (+1 for new POID (OCR) column)
        self.ANNUAL_USAGE_COL = 17    # Column R - kWh format (+1 for new POID (OCR) column)
        
    def create_headers_if_needed(self):
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
            'POID (Form)',
            'POID (OCR)',
            'Monthly Usage (OCR)',
            'Annual Usage (OCR)',
            'Agent ID',
            'Agent Name',
            'Service Address (OCR)',
            'POA ID',
            'Utility Bill Link',
            'POA Link',
            'Agreement Link',
            'Terms & Conditions Link'
        ]
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='A1:Z1'
            ).execute()
            
            existing_values = result.get('values', [])
            
            if not existing_values or len(existing_values[0]) < len(headers):
                body = {
                    'values': [headers]
                }
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range='A1:Z1',
                    valueInputOption='RAW',
                    body=body
                ).execute()
                
                request_body = {
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
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=request_body
                ).execute()
                
        except Exception as e:
            print(f"Error creating headers: {e}")
            
    def append_row(self, data):
        try:
            self.create_headers_if_needed()
            
            body = {
                'values': [data]
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='A:Z',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            # Format the newly added row
            if 'updates' in result and 'updatedRange' in result['updates']:
                updated_range = result['updates']['updatedRange']
                # Extract row number from range like "Sheet1!A2:Z2"
                import re
                row_match = re.search(r'!A(\d+):Z\d+', updated_range)
                if row_match:
                    row_number = int(row_match.group(1))
                    
                    # Format the entire row with white background, black text
                    self._format_data_row(row_number)
                    
                    # Apply kWh formatting to usage columns if they have values
                    if len(data) > self.MONTHLY_USAGE_COL and data[self.MONTHLY_USAGE_COL]:
                        self._format_kwh_column(row_number, self.MONTHLY_USAGE_COL)
                    if len(data) > self.ANNUAL_USAGE_COL and data[self.ANNUAL_USAGE_COL]:
                        self._format_kwh_column(row_number, self.ANNUAL_USAGE_COL)
            
            return result
        except Exception as e:
            print(f"Error appending row: {e}")
            raise
    
    def _format_data_row(self, row_number):
        """Format a data row with white background and black text"""
        format_request = {
            'requests': [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row_number - 1,
                        'endRowIndex': row_number
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 1.0,
                                'green': 1.0,
                                'blue': 1.0
                            },
                            'textFormat': {
                                'foregroundColor': {
                                    'red': 0.0,
                                    'green': 0.0,
                                    'blue': 0.0
                                },
                                'bold': False,
                                'fontSize': 10
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
        }
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=format_request
        ).execute()
    
    def _format_currency_column(self, row_number, col_index):
        """Apply currency formatting to a specific cell"""
        currency_request = {
            'requests': [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row_number - 1,
                        'endRowIndex': row_number,
                        'startColumnIndex': col_index,
                        'endColumnIndex': col_index + 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'numberFormat': {
                                'type': 'CURRENCY',
                                'pattern': '$#,##0.00'
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.numberFormat'
                }
            }]
        }
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=currency_request
        ).execute()
    
    def _format_kwh_column(self, row_number, col_index):
        """Apply kWh number formatting to a specific cell"""
        kwh_request = {
            'requests': [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row_number - 1,
                        'endRowIndex': row_number,
                        'startColumnIndex': col_index,
                        'endColumnIndex': col_index + 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'numberFormat': {
                                'type': 'NUMBER',
                                'pattern': '#,##0" kWh"'
                            }
                        }
                    },
                    'fields': 'userEnteredFormat.numberFormat'
                }
            }]
        }
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=kwh_request
        ).execute()
            
    def get_all_data(self):
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='A:Z'
            ).execute()
            
            return result.get('values', [])
        except Exception as e:
            print(f"Error getting data: {e}")
            return []
    
    def get_agent_name(self, agent_id):
        """Look up agent name from agent ID using Agents sheet"""
        cache_key = f"agent_{agent_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Hardcoded fallback for specific agent IDs
        hardcoded_agents = {
            "0000": "Jason Pritchard"
        }
        
        if agent_id in hardcoded_agents:
            agent_name = hardcoded_agents[agent_id]
            self.cache[cache_key] = agent_name
            print(f"Found agent {agent_id} -> {agent_name} (hardcoded)")
            return agent_name
            
        try:
            # Try both sheet name variations and column arrangements
            sheet_ranges = ["Agents!A:B", "Sheet1!A:B"]
            
            for sheet_range in sheet_ranges:
                try:
                    rows = self.service.spreadsheets().values().get(
                        spreadsheetId=self.agent_spreadsheet_id,
                        range=sheet_range
                    ).execute().get("values", [])
                    
                    if not rows or len(rows) < 2:
                        continue
                    
                    # Skip header row and check column arrangement
                    header = rows[0] if len(rows[0]) >= 2 else []
                    data_rows = rows[1:]
                    
                    # Determine column order based on header
                    if len(header) >= 2:
                        if "ID" in header[0] or "id" in header[0].lower():
                            # Column A is ID, Column B is Name
                            lookup = {r[0]: r[1] for r in data_rows if len(r) >= 2}
                        else:
                            # Column A is Name, Column B is ID (reversed)
                            lookup = {r[1]: r[0] for r in data_rows if len(r) >= 2}
                    else:
                        # No clear header, try both arrangements
                        # First try: A=ID, B=Name
                        lookup_standard = {r[0]: r[1] for r in data_rows if len(r) >= 2}
                        # Second try: A=Name, B=ID 
                        lookup_reversed = {r[1]: r[0] for r in data_rows if len(r) >= 2}
                        
                        # Test which arrangement works by checking if agent_id exists
                        if agent_id in lookup_standard:
                            lookup = lookup_standard
                        elif agent_id in lookup_reversed:
                            lookup = lookup_reversed
                        else:
                            lookup = lookup_standard  # Default fallback
                    
                    agent_name = lookup.get(agent_id, "Unknown")
                    
                    # Cache the result if found
                    if agent_name != "Unknown":
                        self.cache[cache_key] = agent_name
                        print(f"Found agent {agent_id} -> {agent_name} in {sheet_range}")
                        return agent_name
                        
                except Exception as sheet_error:
                    print(f"Failed to access {sheet_range}: {sheet_error}")
                    continue
            
            # If we get here, agent not found in any sheet
            print(f"Agent {agent_id} not found in any sheet")
            self.cache[cache_key] = "Unknown"
            return "Unknown"
            
        except Exception as e:
            print(f"Error looking up agent name for {agent_id}: {e}")
            return "Unknown"
    
    def get_active_utilities(self):
        """Get list of active utilities from Utilities sheet"""
        cache_key = "active_utilities"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            rows = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="Utilities!A:B"
            ).execute().get("values", [])
            
            # Get utilities marked as TRUE (skip header)
            utilities = [r[0] for r in rows[1:] if len(r) >= 2 and r[1].strip().upper() == "TRUE"]
            
            # Cache the result
            self.cache[cache_key] = utilities
            return utilities
            
        except Exception as e:
            print(f"Error getting active utilities: {e}")
            # Fallback to hardcoded list
            return ["National Grid", "NYSEG", "RG&E"]
    
    def get_active_developers(self):
        """Get list of active developers from Developer_Mapping sheet"""
        cache_key = "active_developers"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            rows = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="Developer_Mapping"
            ).execute().get("values", [])
            
            # Get unique developers (skip header)
            developers = list(set([r[0] for r in rows[1:] if len(r) >= 3]))
            
            # Cache the result
            self.cache[cache_key] = developers
            return developers
            
        except Exception as e:
            print(f"Error getting active developers: {e}")
            # Fallback to hardcoded list
            return ["Meadow Energy", "Solar Simplified"]
    
    def get_developer_agreement(self, developer, utility, account_type):
        """Get agreement filename based on developer, utility, and account type"""
        cache_key = f"agreement_{developer}_{utility}_{account_type}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            rows = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="Developer_Mapping"
            ).execute().get("values", [])
            
            # For Mass Market [Residential] account type, prioritize Mass Market template
            if account_type == "Mass Market [Residential]":
                # First pass: Look for Mass Market template for this developer
                for row in rows[1:]:
                    if len(row) >= 3:
                        row_developer = row[0].strip()
                        row_utility = row[1].strip()
                        row_filename = row[2].strip()
                        
                        if row_developer == developer and row_utility == "Mass Market":
                            print(f"Using Mass Market template for {developer}: {row_filename}")
                            self.cache[cache_key] = row_filename
                            return row_filename
            
            # Second pass or non-Mass Market: Look for exact developer + utility match
            for row in rows[1:]:
                if len(row) >= 3:
                    row_developer = row[0].strip()
                    row_utility = row[1].strip()
                    row_filename = row[2].strip()
                    
                    if row_developer == developer and row_utility == utility:
                        self.cache[cache_key] = row_filename
                        return row_filename
            
            # No match found
            print(f"No agreement found for {developer} + {utility} + {account_type}")
            return None
            
        except Exception as e:
            print(f"Error getting developer agreement: {e}")
            return None
    
    def setup_required_tabs(self):
        """Create required tabs if they don't exist and populate with initial data"""
        try:
            # Get current sheet info
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            existing_sheets = [sheet['properties']['title'] for sheet in sheet_metadata['sheets']]
            
            requests = []
            
            # Create Utilities tab if it doesn't exist
            if 'Utilities' not in existing_sheets:
                requests.append({
                    'addSheet': {
                        'properties': {
                            'title': 'Utilities'
                        }
                    }
                })
            
            # Create Developer_Mapping tab if it doesn't exist
            if 'Developer_Mapping' not in existing_sheets:
                requests.append({
                    'addSheet': {
                        'properties': {
                            'title': 'Developer_Mapping'
                        }
                    }
                })
            
            # Execute sheet creation requests
            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                print("Created missing tabs")
            
            # Populate Utilities tab with initial data
            utilities_data = [
                ['utility_name', 'active_flag'],
                ['National Grid', 'TRUE'],
                ['NYSEG', 'TRUE'],
                ['RG&E', 'TRUE'],
                ['Orange & Rockland', 'FALSE'],
                ['Central Hudson', 'FALSE'],
                ['ConEd', 'FALSE']
            ]
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range='Utilities!A1:B7',
                valueInputOption='RAW',
                body={'values': utilities_data}
            ).execute()
            
            # Populate Developer_Mapping tab with initial data
            developer_mapping_data = [
                ['developer_name', 'utility_name', 'file_name'],
                ['Meadow Energy', 'National Grid', 'Meadow-National-Grid-Commercial-UCB-Agreement.pdf'],
                ['Meadow Energy', 'NYSEG', 'Meadow-NYSEG-Commercial-UCB-Agreement.pdf'],
                ['Meadow Energy', 'RG&E', 'Meadow-RGE-Commercial-UCB-Agreement.pdf'],
                ['Meadow Energy', 'Mass Market', 'Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf'],
                ['Solar Simplified', 'National Grid', 'Solar-Simplified-National-Grid-Commercial-UCB-Agreement.pdf'],
                ['Solar Simplified', 'NYSEG', 'Solar-Simplified-NYSEG-Commercial-UCB-Agreement.pdf'],
                ['Solar Simplified', 'RG&E', 'Solar-Simplified-RGE-Commercial-UCB-Agreement.pdf'],
                ['Solar Simplified', 'Mass Market', 'Form-Subscription-Agreement-Mass Market UCB-Solar-Simplified-January 2023-002.pdf']
            ]
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range='Developer_Mapping!A1:C9',
                valueInputOption='RAW',
                body={'values': developer_mapping_data}
            ).execute()
            
            print("Populated initial data in new tabs")
            
        except Exception as e:
            print(f"Error setting up required tabs: {e}")
    
    def clear_cache(self):
        """Clear the lookup cache"""
        self.cache.clear()