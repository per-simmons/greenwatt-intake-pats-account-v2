import openai
import json
import os

# Set OpenAI API key (check environment variable on every call)
def _ensure_openai_key():
    if not openai.api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            openai.api_key = api_key
        else:
            raise Exception("OpenAI API key not found in environment variable OPENAI_API_KEY")

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
        # Clean up OCR text first
        cleaned_text = normalize_ocr_text(raw_ocr_text)
        prompt = """You are extracting fields from raw OCR text of US utility bills.
Return JSON with *exactly* these keys:

utility_name      – String
customer_name     – String
account_number    – String
poid              – String (may be empty)
monthly_usage_kwh – Integer (no commas)
  
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

• POID = first 6–12-digit sequence after "POID" or "Point ID".

• monthly_usage_kwh = Find the ENERGY CONSUMPTION in kWh (kilowatt-hours) for this billing period:
  - Look for numbers followed by "kWh" that represent electricity consumed
  - Search near "kWh Used", "Energy Usage", "Consumption", "kWh This Period"
  - Look in usage tables or consumption summaries
  - If only daily averages shown (like "12.67 kWh/Day"), multiply by 30 for monthly estimate
  - This is ENERGY consumed, NOT dollar amounts
  - Return as integer (round if decimal, strip commas)

If a field isn't present, return an empty string.
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
        
        # POID
        final_data['poid'] = parsed_data.get('poid', '')
        
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
        
        return final_data
        
    except Exception as e:
        print(f"LLM parsing error: {e}")
        # Raise error instead of returning empty data
        raise Exception(f"LLM parsing failed: {str(e)}")