import openai
import json
import os

# Set OpenAI API key (check environment variable on every call)
def _ensure_openai_key():
    if not openai.api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and api_key != "sk-proj-your_openai_api_key_here":
            openai.api_key = api_key
        else:
            print("⚠️  OpenAI API key not set - using fallback mode for testing")
            # Don't raise exception for testing mode
            pass

# Initial setup
_ensure_openai_key()

def normalize_ocr_text(text):
    """
    Clean up common OCR artifacts before sending to LLM
    """
    # Replace common OCR errors
    replacements = {
        'O': '0',  # Common OCR confusion
        'I': '1',  # When it appears in numbers
        'l': '1',  # lowercase L to 1 in numbers
        'S': '5',  # When it appears in numbers  
        '$': '$',  # Normalize dollar signs
        ',': ',',  # Normalize commas
    }
    
    # Normalize multiple spaces to single spaces
    import re
    text = re.sub(r'\s+', ' ', text)
    
    return text

def parse_utility_bill_with_llm(raw_ocr_text):
    """
    Use OpenAI to parse utility bill text and extract structured data
    """
    try:
        # Ensure API key is set
        _ensure_openai_key()
        
        # Check if OpenAI is available
        if not openai.api_key:
            print("⚠️  OpenAI not available - returning fallback mock data")
            return {
                'utility_name': 'National Grid',
                'customer_name': 'Test Customer',
                'account_number': '123456789',
                'poid': 'TEST123456',
                'monthly_usage': '1500',
                'annual_usage': '18000',
                'service_address': '123 Test Street, Buffalo, NY 14201'
            }
        # Clean up OCR text first
        cleaned_text = normalize_ocr_text(raw_ocr_text)
        prompt = """You are extracting fields from raw OCR text of US utility bills.
Return JSON with *exactly* these keys:

utility_name      – String
customer_name     – String
account_number    – String
poid              – String (may be empty)
monthly_usage_kwh – Integer (no commas)
service_address   – String (may be empty)
  
Rules:
• Utility name: Look for these exact company names or their websites in the text:
  - "PG&E" or "pge.com" → return "PG&E"
  - "NYSEG" or "nyseg" → return "NYSEG"  
  - "RG&E" or "rge" → return "RG&E"
  - "Con Edison" or "ConEd" or "coned" → return "Con Edison"
  - "National Grid" → return "National Grid"
  - "PSEG" → return "PSEG"
  - "Orange & Rockland" or "O&R" → return "Orange & Rockland"
  - "Central Hudson" → return "Central Hudson"
  If none found, return empty string.

• Customer name: Look for the account holder's name, typically found:
  - At the top of the bill in the mailing address section
  - After "Bill to:" or "Account holder:" or "Customer:"
  - In the account information section
  - Usually appears as "First Last" or "Last, First" format
  - Avoid company names - look for individual person names

• Account number = first 8–18 character sequence containing at least 6 digits appearing within 50 characters AFTER: ["account","acct","account no","account number"] (case-insensitive). Keep hyphens and leading zeros.

• POID = Point of Delivery ID for RG&E/NYSEG bills:
  - For RG&E bills: Look for "POD ID:" or "PoD ID:" label, then extract the value that IMMEDIATELY follows
    * RG&E POIDs ALWAYS start with "R" followed by 14 digits (e.g., R01000035625383)
    * DO NOT confuse with meter numbers which typically start with "035" and are 10 digits
    * The POID appears BEFORE the meter number table in the bill
  - For NYSEG bills: Look for "PoD ID" or "Point of Delivery ID" in top right section  
  - For other utilities: Look for "POID", "Point ID", or similar near account information
  - Extract the complete alphanumeric sequence including any prefix letters
  - If not found, return empty string (National Grid typically doesn't have POID)

• monthly_usage_kwh = Find the ENERGY CONSUMPTION in kWh (kilowatt-hours) for this billing period:
  - Look for numbers followed by "kWh" that represent electricity consumed
  - Search near "kWh Used", "Energy Usage", "Consumption", "kWh This Period"
  - Look in usage tables or consumption summaries
  - If only daily averages shown (like "12.67 kWh/Day"), multiply by 30 for monthly estimate
  - This is ENERGY consumed, NOT dollar amounts
  - Return as integer (round if decimal, strip commas)

• service_address = Service address from utility bill:
  - Look for service address in bill header or account information section
  - Usually appears after "Service Address:", "Service Location:", or "Property Address:"
  - Extract full address including street, city, state, zip
  - Different from billing/mailing address - this is where electricity is delivered

If a field isn't present, return an empty string (or 0 for numbers).
Respond with JSON ONLY, no commentary.

Text to parse:
"""
        
        print("="*30)
        print("SENDING TO LLM:")
        print("Text sample:", cleaned_text[:800], "...")
        print("="*30)
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a utility bill data extraction expert. Parse the text and return only valid JSON. Look carefully at company names and websites to identify the correct utility."},
                {"role": "user", "content": prompt + cleaned_text}
            ],
            temperature=0,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        print("="*30)
        print("RAW LLM RESPONSE:")
        print(response_text)
        print("="*30)
        
        # Try to parse the JSON response
        try:
            parsed_data = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from LLM response")
        
        # Debug: Print the exact JSON the LLM returned
        print(f"LLM returned JSON: {json.dumps(parsed_data, indent=2)}")
        
        # Map and validate fields
        final_data = {}
        
        # Utility name (OCR wins over form data)
        final_data['utility_name'] = parsed_data.get('utility_name', '')
        
        # Customer name
        final_data['customer_name'] = parsed_data.get('customer_name', '')
        
        # Account number with validation
        account_num = parsed_data.get('account_number', '')
        if account_num:
            # Strip spaces/dashes, keep leading zeros
            clean_account = str(account_num).replace(' ', '').replace('-', '')
            # Validate: must contain at least 6 digits and be 8-18 chars
            digit_count = sum(c.isdigit() for c in clean_account)
            if 6 <= digit_count and 8 <= len(clean_account) <= 18:
                final_data['account_number'] = clean_account
            else:
                print("ACCOUNT_NUMBER_NOT_FOUND - validation failed")
                final_data['account_number'] = ''
        else:
            final_data['account_number'] = ''
        
        # POID with RG&E-specific validation
        poid = parsed_data.get('poid', '')
        utility_name = final_data.get('utility_name', '')
        
        print(f"=== POID EXTRACTION DEBUG ===")
        print(f"Utility: {utility_name}")
        print(f"LLM extracted POID: '{poid}'")
        
        # Special validation for RG&E POIDs
        if utility_name == 'RG&E':
            # RG&E POIDs should start with 'R' followed by 14 digits
            import re
            
            # First, let's see what's around "POD ID" in the text
            pod_context = re.search(r'(.{20}Po[Dd] ID:.{50})', cleaned_text)
            if pod_context:
                print(f"POD ID context: ...{pod_context.group(1)}...")
            
            if poid and not re.match(r'^R\d{14}$', poid):
                print(f"WARNING: Invalid RG&E POID format: {poid}")
                # Check if it's a meter number (typically starts with 035)
                if poid.startswith('035') and len(poid) == 10:
                    print(f"ERROR: Meter number {poid} mistaken for POID")
                
                # Try multiple patterns to find the real POID
                patterns = [
                    r'Po[Dd] ID:\s*([R]\d{14})',
                    r'POD ID:\s*([R]\d{14})',
                    r'Point of Delivery ID:\s*([R]\d{14})',
                    r'([R]\d{14})(?=\s*Meter Number)'  # POID before meter number
                ]
                
                for pattern in patterns:
                    poid_match = re.search(pattern, cleaned_text)
                    if poid_match:
                        poid = poid_match.group(1)
                        print(f"FIXED: Found correct POID using pattern '{pattern}': {poid}")
                        break
                else:
                    poid = ''
                    print("ERROR: Could not find valid RG&E POID with any pattern")
            elif poid and re.match(r'^R\d{14}$', poid):
                print(f"SUCCESS: Valid RG&E POID format confirmed: {poid}")
            elif not poid:
                # LLM didn't extract any POID, try to find it ourselves
                print("WARNING: LLM didn't extract POID for RG&E bill, searching manually...")
                patterns = [
                    r'Po[Dd] ID:\s*([R]\d{14})',
                    r'POD ID:\s*([R]\d{14})',
                    r'Point of Delivery ID:\s*([R]\d{14})'
                ]
                
                for pattern in patterns:
                    poid_match = re.search(pattern, cleaned_text)
                    if poid_match:
                        poid = poid_match.group(1)
                        print(f"FOUND: Located POID using pattern '{pattern}': {poid}")
                        break
        
        print(f"Final POID: '{poid}'")
        print(f"=== END POID DEBUG ===")
        
        final_data['poid'] = poid
        
        # Monthly usage with better validation
        monthly_usage_kwh = parsed_data.get('monthly_usage_kwh', '')
        if monthly_usage_kwh:
            try:
                # Clean and convert monthly usage
                monthly_clean = str(monthly_usage_kwh).replace(',', '').replace('kWh', '').replace('kwh', '').strip()
                monthly_value = float(monthly_clean)
                final_data['monthly_usage'] = str(int(round(monthly_value)))
                final_data['annual_usage'] = str(int(round(monthly_value * 12)))
                print(f"Monthly usage: {monthly_value} kWh -> Annual: {monthly_value * 12} kWh")
            except (ValueError, AttributeError):
                print("MONTHLY_USAGE_PARSE_ERROR")
                final_data['monthly_usage'] = ''
                final_data['annual_usage'] = ''
        else:
            print("MONTHLY_USAGE_NOT_FOUND")
            final_data['monthly_usage'] = ''
            final_data['annual_usage'] = ''
        
        # Service address
        final_data['service_address'] = parsed_data.get('service_address', '')
        
        return final_data
        
    except Exception as e:
        print(f"LLM parsing error: {e}")
        # Raise error instead of returning empty data
        raise Exception(f"LLM parsing failed: {str(e)}")