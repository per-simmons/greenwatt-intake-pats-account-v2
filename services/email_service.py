import os
import ssl
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_notification_email(agent_name, customer_name, utility, signed_date, annual_usage):
    """
    Send notification email to internal team using SendGrid API.
    Sends to up to 3 team members with professional HTML formatting.
    """
    try:
        # Handle SSL verification for development environments
        # This fixes "SSL: CERTIFICATE_VERIFY_FAILED" errors in corporate/dev environments
        if os.getenv('DISABLE_SSL_VERIFICATION', 'false').lower() == 'true':
            print("⚠️  SSL verification disabled for development environment")
            # Create unverified SSL context for development
            ssl._create_default_https_context = ssl._create_unverified_context
        
        # SendGrid configuration
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            print("Warning: SENDGRID_API_KEY not configured - skipping email notification")
            return False
        
        # Email recipients - internal team members
        internal_emails = [
            "greenwatt.intake@gmail.com"   # Primary intake email
        ]
        
        # Professional HTML email template with GreenWatt branding
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 20px auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #2c5530 0%, #4a7c59 100%); color: white; padding: 30px 20px; text-align: center; }}
                .header h2 {{ margin: 0; font-size: 24px; font-weight: 600; }}
                .header .subtitle {{ margin: 5px 0 0 0; font-size: 14px; opacity: 0.9; }}
                .content {{ padding: 30px 20px; }}
                .info-grid {{ display: grid; gap: 15px; }}
                .info-row {{ background-color: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #2c5530; }}
                .label {{ font-weight: 600; color: #2c5530; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }}
                .value {{ color: #333; font-size: 16px; font-weight: 500; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef; }}
                .footer p {{ margin: 0; font-size: 12px; color: #6c757d; }}
                .logo {{ font-size: 18px; font-weight: 700; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🌱 GreenWatt USA</div>
                    <h2>New Customer Submission</h2>
                    <p class="subtitle">Community Solar Intake System</p>
                </div>
                <div class="content">
                    <div class="info-grid">
                        <div class="info-row">
                            <div class="label">Field Agent</div>
                            <div class="value">{agent_name}</div>
                        </div>
                        <div class="info-row">
                            <div class="label">Customer Name</div>
                            <div class="value">{customer_name}</div>
                        </div>
                        <div class="info-row">
                            <div class="label">Utility Provider</div>
                            <div class="value">{utility}</div>
                        </div>
                        <div class="info-row">
                            <div class="label">Submission Date</div>
                            <div class="value">{signed_date}</div>
                        </div>
                        <div class="info-row">
                            <div class="label">Annual Usage</div>
                            <div class="value">{annual_usage:,} kWh/year</div>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    <p>📊 Check the Google Sheets dashboard for complete submission details</p>
                    <p>🔗 Documents automatically stored in Google Drive</p>
                    <p style="margin-top: 10px; color: #adb5bd;">Automated notification from GreenWatt Intake System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        🌱 GreenWatt USA - New Customer Submission
        
        Field Agent: {agent_name}
        Customer Name: {customer_name}
        Utility Provider: {utility}
        Submission Date: {signed_date}
        Annual Usage: {annual_usage:,} kWh/year
        
        📊 Check the Google Sheets dashboard for complete details
        🔗 Documents automatically stored in Google Drive
        
        Automated notification from GreenWatt Intake System
        """
        
        # Create SendGrid message - use verified sender identity
        message = Mail(
            from_email='greenwatt.intake@gmail.com',  # Use verified sender
            to_emails=internal_emails,
            subject=f'🌱 New Submission: {customer_name} ({utility})',
            html_content=html_content,
            plain_text_content=text_content
        )
        
        # Send email via SendGrid
        sg = SendGridAPIClient(api_key=api_key)
        response = sg.send(message)
        
        print(f"✅ Email notification sent successfully via SendGrid")
        print(f"   Recipients: {', '.join(internal_emails)}")
        print(f"   Status Code: {response.status_code}")
        print(f"   Customer: {customer_name} ({utility})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error sending SendGrid email: {e}")
        return False

def send_sendgrid_test_email():
    """
    Test function to verify SendGrid configuration.
    Call this during development to test email sending.
    """
    try:
        # Handle SSL verification for development environments
        if os.getenv('DISABLE_SSL_VERIFICATION', 'false').lower() == 'true':
            print("⚠️  SSL verification disabled for development environment")
            ssl._create_default_https_context = ssl._create_unverified_context
            
        test_data = {
            'agent_name': 'Test Agent',
            'customer_name': 'Test Customer', 
            'utility': 'National Grid',
            'signed_date': datetime.now().strftime('%m/%d/%Y'),
            'annual_usage': 12500
        }
        
        result = send_notification_email(**test_data)
        if result:
            print("✅ SendGrid test email sent successfully!")
        else:
            print("❌ SendGrid test email failed")
        return result
        
    except Exception as e:
        print(f"❌ SendGrid test error: {e}")
        return False