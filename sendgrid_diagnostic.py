#!/usr/bin/env python3
"""
SendGrid Diagnostic Script
Tests SendGrid API connectivity and sender verification
"""

import os
import requests
import json

def test_sendgrid_api():
    """Test SendGrid API directly"""
    api_key = os.getenv('SENDGRID_API_KEY')
    
    print("=== SendGrid API Diagnostic ===")
    
    if not api_key:
        print("❌ SENDGRID_API_KEY environment variable not set")
        return False
        
    print(f"API Key: {api_key[:10]}...")
    
    # Test 1: Check API key validity
    print("\n1. Testing API Key Validity...")
    try:
        response = requests.get(
            "https://api.sendgrid.com/v3/user/account",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Account Type: {data.get('type', 'Unknown')}")
            print(f"   ✅ API Key is valid")
        else:
            print(f"   ❌ API Key invalid: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ API Error: {e}")
        return False
    
    # Test 2: Check sender verification
    print("\n2. Checking Sender Verification...")
    try:
        response = requests.get(
            "https://api.sendgrid.com/v3/verified_senders",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            senders = response.json()
            print(f"   Found {len(senders.get('results', []))} verified senders:")
            for sender in senders.get('results', []):
                print(f"     - {sender.get('from_email')} (verified: {sender.get('verified')})")
        else:
            print(f"   ❌ Failed to get senders: {response.text}")
    except Exception as e:
        print(f"   ❌ Sender check error: {e}")
    
    # Test 3: Send actual test email
    print("\n3. Sending Test Email...")
    try:
        email_data = {
            "personalizations": [
                {
                    "to": [
                        {"email": "greenwatt.intake@gmail.com"}
                    ],
                    "subject": "🧪 SendGrid Diagnostic Test"
                }
            ],
            "from": {
                "email": "greenwatt.intake@gmail.com",
                "name": "GreenWatt Diagnostic"
            },
            "content": [
                {
                    "type": "text/html",
                    "value": """
                    <html>
                    <body>
                        <h2>🧪 SendGrid Diagnostic Test</h2>
                        <p>This is a diagnostic test email from the GreenWatt system.</p>
                        <p><strong>Time:</strong> {timestamp}</p>
                        <p><strong>Test:</strong> Direct SendGrid API call</p>
                        <p>If you receive this, SendGrid is working correctly!</p>
                    </body>
                    </html>
                    """.replace("{timestamp}", "2025-06-19")
                }
            ]
        }
        
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            data=json.dumps(email_data)
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 202:
            print("   ✅ Email sent successfully!")
            print("   📧 Check your inbox for the test email")
        else:
            print(f"   ❌ Email failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Email send error: {e}")
    
    # Test 4: Check rate limits and quotas
    print("\n4. Checking Account Status...")
    try:
        response = requests.get(
            "https://api.sendgrid.com/v3/user/credits",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        if response.status_code == 200:
            credits = response.json()
            print(f"   Credits remaining: {credits.get('remain', 'Unknown')}")
            print(f"   Credits used: {credits.get('used', 'Unknown')}")
        else:
            print(f"   Credit check failed: {response.status_code}")
    except Exception as e:
        print(f"   Credit check error: {e}")

if __name__ == "__main__":
    test_sendgrid_api()