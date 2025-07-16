from cachetools import TTLCache
from .google_service_manager import GoogleServiceManager

class GoogleSheetsService:
    def __init__(self, service_account_info=None, spreadsheet_id=None, agent_spreadsheet_id=None, dynamic_spreadsheet_id=None):
        # Use the singleton service manager
        self.service_manager = GoogleServiceManager()
        
        # Initialize the service manager if credentials provided
        if service_account_info:
            self.service_manager.initialize(service_account_info)
        
        # Get the shared sheets service
        self.service = self.service_manager.get_sheets_service()
        
        # Store multiple spreadsheet IDs
        self.spreadsheet_id = spreadsheet_id  # Main logging sheet
        self.agent_spreadsheet_id = agent_spreadsheet_id or spreadsheet_id
        self.dynamic_spreadsheet_id = dynamic_spreadsheet_id  # Dynamic form data sheet
        
        # INCREASED cache size for better performance (was 16, now 100)
        self.cache = TTLCache(maxsize=100, ttl=600)
        
        # Column indexes for formatting (0-based) - Updated after removing form columns
        self.MONTHLY_USAGE_COL = 15   # Column P - kWh format (shifted left by 2)
        self.ANNUAL_USAGE_COL = 16    # Column Q - kWh format (shifted left by 2)
        
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
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='A1:Y1'
            ).execute()
            
            existing_values = result.get('values', [])
            
            # Force update headers if they don't match exactly
            if not existing_values or existing_values[0] != headers:
                print(f"Updating headers: Current has {len(existing_values[0]) if existing_values else 0} columns, need {len(headers)} columns")
                body = {
                    'values': [headers]
                }
                
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range='A1:Y1',
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
                range='A:Y',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            # Format the newly added row
            if 'updates' in result and 'updatedRange' in result['updates']:
                updated_range = result['updates']['updatedRange']
                # Extract row number from range like "Sheet1!A2:Y2"
                import re
                row_match = re.search(r'!A(\d+):Y\d+', updated_range)
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
                range='A:Y'
            ).execute()
            
            return result.get('values', [])
        except Exception as e:
            print(f"Error getting data: {e}")
            return []
    
    def get_agent_name(self, agent_id):
        """Look up agent name from agent ID using Agents sheet"""
        # For backward compatibility, get full info and return just the name
        agent_info = self.get_agent_info(agent_id)
        return agent_info.get('name', 'Unknown')
    
    def get_agent_info(self, agent_id):
        """Look up agent information from agent ID using Agents sheet
        Returns dict with: name, email, sales_manager_email
        """
        cache_key = f"agent_info_{agent_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Hardcoded fallback for specific agent IDs
        hardcoded_agents = {
            "0000": {
                "name": "Jason Pritchard",
                "email": "jason@greenwattusa.com",
                "sales_manager_email": "jason@greenwattusa.com"
            },
            "0001": {
                "name": "Pat Simmons (Testing)",
                "email": "pat.testing@example.com",
                "sales_manager_email": "pat.testing@example.com"
            }
        }
        
        if agent_id in hardcoded_agents:
            agent_info = hardcoded_agents[agent_id]
            self.cache[cache_key] = agent_info
            print(f"Found agent {agent_id} -> {agent_info['name']} (hardcoded)")
            return agent_info
            
        try:
            # Try both sheet name variations - now getting columns A through G
            sheet_ranges = ["Agents!A:G", "Sheet1!A:G"]
            
            for sheet_range in sheet_ranges:
                try:
                    rows = self.service.spreadsheets().values().get(
                        spreadsheetId=self.agent_spreadsheet_id,
                        range=sheet_range
                    ).execute().get("values", [])
                    
                    if not rows or len(rows) < 2:
                        continue
                    
                    # Skip header row
                    if len(rows) < 2:
                        continue
                    
                    data_rows = rows[1:]
                    
                    # Look for the agent by ID in column A
                    for row in data_rows:
                        if len(row) >= 1 and row[0] == agent_id:
                            # Found the agent, extract info from columns
                            agent_info = {
                                "name": row[1] if len(row) > 1 else "Unknown",
                                "email": row[3] if len(row) > 3 else "",  # Column D (index 3)
                                "sales_manager_email": row[6] if len(row) > 6 else ""  # Column G (index 6)
                            }
                            
                            # Cache the result
                            self.cache[cache_key] = agent_info
                            print(f"Found agent {agent_id} -> {agent_info['name']} with email {agent_info['email']}")
                            return agent_info
                        
                except Exception as sheet_error:
                    print(f"Failed to access {sheet_range}: {sheet_error}")
                    continue
            
            # If we get here, agent not found in any sheet
            print(f"Agent {agent_id} not found in any sheet")
            agent_info = {
                "name": "Unknown",
                "email": "",
                "sales_manager_email": ""
            }
            self.cache[cache_key] = agent_info
            return agent_info
            
        except Exception as e:
            print(f"Error looking up agent name for {agent_id}: {e}")
            return {
                "name": "Unknown",
                "email": "",
                "sales_manager_email": ""
            }
    
    def get_active_utilities(self):
        """Get list of active utilities from Utilities sheet"""
        cache_key = "active_utilities"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            # Use dynamic spreadsheet ID if available, otherwise fall back to main
            sheet_id = self.dynamic_spreadsheet_id or self.spreadsheet_id
            rows = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
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
            # Use dynamic spreadsheet ID if available, otherwise fall back to main
            sheet_id = self.dynamic_spreadsheet_id or self.spreadsheet_id
            rows = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
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
            # Use dynamic spreadsheet ID if available, otherwise fall back to main
            sheet_id = self.dynamic_spreadsheet_id or self.spreadsheet_id
            rows = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
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
    
    def force_update_headers(self):
        """Force update headers to new 25-column structure (one-time fix)"""
        try:
            headers = [
                'Unique ID',
                'Submission Date',
                'Business Entity Name',
                'Account Name',
                'Contact Name',
                'Title',
                'Phone',
                'Email',
                'Service Address',  # Column I - from OCR only
                'Developer Assigned',
                'Account Type',
                'Utility Provider (Form)',
                'Utility Name (OCR)',
                'Account Number (OCR)',
                'POID',  # Column O - from OCR only
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
            
            # Clear the entire first row first
            clear_request = {
                'requests': [{
                    'updateCells': {
                        'range': {
                            'sheetId': 0,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 25  # Clear up to column Y
                        },
                        'fields': 'userEnteredValue'
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=clear_request
            ).execute()
            
            # Now set the new headers
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range='A1:Y1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print("✅ Successfully force-updated headers to new 25-column structure")
            
            # Apply formatting
            self._format_header_row()
            
        except Exception as e:
            print(f"❌ Error force-updating headers: {e}")
            raise
    
    def _format_header_row(self):
        """Format the header row with green background and white text"""
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
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=format_request
        ).execute()

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
    
    def get_all_developer_mappings(self):
        """Get all developer mappings for testing/display purposes"""
        try:
            rows = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="Developer_Mapping!A:C"
            ).execute().get('values', [])
            
            if not rows:
                return []
            
            # Skip header row and return as list of dictionaries
            mappings = []
            for row in rows[1:]:
                if len(row) >= 3:
                    mappings.append({
                        'developer_name': row[0].strip(),
                        'utility_name': row[1].strip(),
                        'file_name': row[2].strip()
                    })
            
            return mappings
            
        except Exception as e:
            print(f"Error getting all developer mappings: {e}")
            return []
    
    def clear_cache(self):
        """Clear the lookup cache"""
        self.cache.clear()
    
    def log_sms_sent(self, row_index):
        """Update CDG Enrollment Status when SMS is sent"""
        try:
            # Update column Y (CDG Enrollment Status) to PENDING when SMS is sent
            body = {
                'values': [['PENDING']]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'Y{row_index}',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ CDG Enrollment Status set to PENDING for row {row_index}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating enrollment status: {e}")
            return False
    
    def log_sms_response(self, phone, response):
        """Find row by phone number and update CDG Enrollment Status"""
        try:
            # Get all data to find the row with matching phone number
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='A:Y'
            ).execute()
            
            values = result.get('values', [])
            
            # Phone number is in column G (index 6)
            row_found = False
            for idx, row in enumerate(values):
                if idx == 0:  # Skip header row
                    continue
                    
                # Check if this row has the matching phone number in column G
                if len(row) > 6 and row[6] == phone:
                    row_number = idx + 1  # Convert to 1-based index
                    
                    # Determine enrollment status based on response
                    if response.upper() in ['Y', 'YES']:
                        status = 'ENROLLED'
                    elif response.upper() in ['N', 'NO']:
                        status = 'DECLINED'
                    else:
                        status = f'INVALID: {response}'
                    
                    # Update column Y (CDG Enrollment Status)
                    body = {
                        'values': [[status]]
                    }
                    
                    result = self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f'Y{row_number}',
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    
                    print(f"✅ CDG Enrollment Status updated for row {row_number}: {phone} → {status}")
                    row_found = True
                    break
            
            if not row_found:
                print(f"⚠️  No matching row found for phone number: {phone}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Error logging SMS response: {e}")
            return False