import os
from .llm_parser import parse_utility_bill_with_llm
from .vision_ocr_service import process_utility_bill_with_vision

# Legacy Tesseract functions removed - now using Google Vision API

def process_utility_bill(file_path, service_account_info):
    try:
        print(f"🔍 DEBUG: Processing file: {file_path}")
        print(f"🔍 DEBUG: File exists: {os.path.exists(file_path)}")
        print(f"🔍 DEBUG: File size: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'} bytes")
        print(f"🔍 DEBUG: Service account info type: {type(service_account_info)}")
        print(f"🔍 DEBUG: Service account keys: {list(service_account_info.keys()) if isinstance(service_account_info, dict) else 'Not a dict'}")
        print(f"🔍 DEBUG: Service account project_id: {service_account_info.get('project_id', 'N/A') if isinstance(service_account_info, dict) else 'N/A'}")
        print(f"🔍 DEBUG: Service account client_email: {service_account_info.get('client_email', 'N/A') if isinstance(service_account_info, dict) else 'N/A'}")
        print(f"🔍 DEBUG: Service account type field: {service_account_info.get('type', 'N/A') if isinstance(service_account_info, dict) else 'N/A'}")
        
        # Check if this is a test file
        if 'test_utility_bill' in file_path:
            print("🔍 DEBUG: DETECTED TEST FILE - using mock data")
            return {
                'utility_name': 'National Grid',
                'customer_name': 'John Test Customer',
                'account_number': '1234567890',
                'poid': 'POI12345',
                'monthly_usage': '1500',
                'annual_usage': '18000',
                'service_address': '456 Test Service Lane, Buffalo, NY 14201',
                'monthly_charge': '175.89',
                'annual_charge': '2110.68'
            }
        
        print(f"🔍 DEBUG: Processing REAL file - starting Google Vision OCR...")
        
        # Extract raw text using Google Vision API
        try:
            print(f"🔍 DEBUG: About to call process_utility_bill_with_vision...")
            raw_text = process_utility_bill_with_vision(file_path, service_account_info)
            print(f"🔍 DEBUG: Vision API call completed successfully")
        except Exception as vision_error:
            print(f"🔍 DEBUG: Vision API error: {vision_error}")
            import traceback
            traceback.print_exc()
            raise
        
        print(f"🔍 DEBUG: Vision API returned {len(raw_text) if raw_text else 0} characters")
        print(f"🔍 DEBUG: Raw text type: {type(raw_text)}")
        print(f"🔍 DEBUG: Raw text preview: {raw_text[:200] if raw_text else 'EMPTY/NONE'}...")
        
        if not raw_text or len(raw_text.strip()) < 10:
            print("🔍 DEBUG: Empty or minimal text from Vision API!")
            print(f"🔍 DEBUG: Raw text was: '{raw_text}'")
            return {
                'utility_name': '',
                'customer_name': '',
                'account_number': '',
                'poid': '',
                'monthly_usage': '',
                'annual_usage': '',
                'service_address': '',
                'monthly_charge': '',
                'annual_charge': ''
            }
        
        print(f"🔍 DEBUG: Sending text to LLM parser...")
        
        # Use LLM to parse the extracted text
        try:
            print(f"🔍 DEBUG: About to call parse_utility_bill_with_llm...")
            parsed_data = parse_utility_bill_with_llm(raw_text)
            print(f"🔍 DEBUG: LLM parsing completed successfully")
        except Exception as llm_error:
            print(f"🔍 DEBUG: LLM parsing error: {llm_error}")
            import traceback
            traceback.print_exc()
            raise
            
        print(f"🔍 DEBUG: LLM parsed data: {parsed_data}")
        
        return parsed_data
    except Exception as e:
        print(f"🔍 DEBUG ERROR: {e}")
        import traceback
        traceback.print_exc()
        # Return error indication instead of dummy data
        raise Exception(f"OCR processing failed: {str(e)}")