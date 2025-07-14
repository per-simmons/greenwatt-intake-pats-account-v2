import os
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from datetime import datetime

class SMSService:
    def __init__(self):
        # Get Twilio credentials from environment
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_FROM_NUMBER')
        self.internal_numbers = os.getenv('TWILIO_INTERNAL_NUMBERS', '').split(',')
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            print("Warning: Twilio credentials not fully configured")
            self.client = None
            self.validator = None
        else:
            self.client = Client(self.account_sid, self.auth_token)
            self.validator = RequestValidator(self.auth_token)
    
    def send_customer_verification_sms(self, customer_phone, customer_name):
        """Send verification SMS to customer asking to confirm participation"""
        if not self.client:
            print("SMS service not configured - skipping customer verification SMS")
            return False
            
        try:
            # Format phone number
            phone = self._format_phone_number(customer_phone)
            
            message_body = f"""
Hello {customer_name},

Thank you for your interest in GreenWatt USA's Community Solar program!

Please reply Y to confirm your participation in our Community Distributed Generation (CDG) bill credit program, which guarantees up to 10% savings off your electricity bill.

Reply N if you do not wish to participate at this time.

Your response helps us finalize your enrollment.

Best regards,
GreenWatt USA Team
            """.strip()
            
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_number,
                to=phone
            )
            
            print(f"Customer verification SMS sent to {phone}: {message.sid}")
            return {
                'success': True,
                'message_sid': message.sid,
                'timestamp': datetime.now().isoformat(),
                'phone': phone
            }
            
        except Exception as e:
            print(f"Error sending customer verification SMS: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def send_internal_notification_sms(self, submission_data):
        """Send notification SMS to internal team about new submission"""
        if not self.client or not self.internal_numbers:
            print("SMS service not configured - skipping internal notification SMS")
            return False
            
        results = []
        
        for phone in self.internal_numbers:
            if not phone.strip():
                continue
                
            try:
                formatted_phone = self._format_phone_number(phone.strip())
                
                message_body = f"""
NEW GREENWATT SUBMISSION

Customer: {submission_data.get('customer_name', 'N/A')}
Agent: {submission_data.get('agent_name', 'N/A')}
Utility: {submission_data.get('utility', 'N/A')}
Usage: {submission_data.get('annual_usage', 'N/A')} kWh/year

Submitted: {submission_data.get('submission_date', 'N/A')}

Check Google Sheets for full details.
                """.strip()
                
                message = self.client.messages.create(
                    body=message_body,
                    from_=self.from_number,
                    to=formatted_phone
                )
                
                results.append({
                    'success': True,
                    'phone': formatted_phone,
                    'message_sid': message.sid
                })
                
                print(f"Internal notification SMS sent to {formatted_phone}: {message.sid}")
                
            except Exception as e:
                print(f"Error sending internal SMS to {phone}: {e}")
                results.append({
                    'success': False,
                    'phone': phone,
                    'error': str(e)
                })
        
        return results
    
    def _format_phone_number(self, phone):
        """Format phone number to E.164 format"""
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        # Add +1 if it's a 10-digit US number
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        else:
            # Return as-is if already formatted or international
            return phone
    
    def parse_customer_response(self, message_body):
        """Parse customer SMS response to determine Y/N"""
        response = message_body.strip().upper()
        
        # Positive responses
        if response in ['Y', 'YES', 'CONFIRM', 'OK', 'OKAY', 'ACCEPT']:
            return 'Y'
        # Negative responses  
        elif response in ['N', 'NO', 'DECLINE', 'CANCEL', 'OPT OUT', 'OPTOUT']:
            return 'N'
        else:
            return 'INVALID'
    
    def log_customer_response(self, customer_phone, response, message_sid=None):
        """Log customer response for tracking"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'phone': customer_phone,
            'response': response,
            'message_sid': message_sid
        }
        
        print(f"Customer response logged: {log_entry}")
        return log_entry
    
    def validate_webhook_signature(self, request_url, post_params, twilio_signature):
        """
        Validate that the webhook request is actually from Twilio
        Returns True if valid, False otherwise
        """
        if not self.validator:
            print("Warning: Twilio validator not configured - skipping signature validation")
            return True  # Allow in development if not configured
            
        try:
            is_valid = self.validator.validate(
                request_url,
                post_params,
                twilio_signature
            )
            
            if not is_valid:
                print("⚠️  Invalid Twilio webhook signature detected!")
                
            return is_valid
            
        except Exception as e:
            print(f"Error validating Twilio webhook signature: {e}")
            return False
    
    def process_webhook_response(self, webhook_data):
        """
        Process incoming Twilio webhook data for customer SMS responses
        Returns structured response data
        """
        try:
            # Extract key information from Twilio webhook
            from_number = webhook_data.get('From', '')
            message_body = webhook_data.get('Body', '').strip()
            message_sid = webhook_data.get('MessageSid', '')
            account_sid = webhook_data.get('AccountSid', '')
            
            # Parse the customer response (Y/N)
            parsed_response = self.parse_customer_response(message_body)
            
            response_data = {
                'phone_number': from_number,
                'message_body': message_body,
                'parsed_response': parsed_response,
                'message_sid': message_sid,
                'account_sid': account_sid,
                'timestamp': datetime.now().isoformat(),
                'status': 'received'
            }
            
            print(f"📱 SMS Response Processed: {from_number} → {parsed_response}")
            return response_data
            
        except Exception as e:
            print(f"Error processing webhook response: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }