# GreenWatt Automation - Complete Render Deployment Guide

## 🎯 Project Overview

Your **GreenWatt Automation** project is a sophisticated Flask-based web application that processes utility bills using Google Vision OCR, generates PDFs with signature placement, and manages customer data through Google Sheets and Drive integration. The system includes SMS/email notifications and handles sensitive document processing.

Use the Render MCP server you have access to to deploy this application.

## 📋 Pre-Deployment Checklist

### ✅ Files Already Prepared
- ✅ `requirements.txt` - All Python dependencies listed
- ✅ `render.yaml` - Basic deployment configuration
- ✅ `app.py` - Main Flask application with Gunicorn-ready structure
- ✅ `.env.example` - Template for environment variables
- ✅ Complete services architecture in `/services/` directory

### ⚠️ Critical Deployment Considerations

## 🔧 Environment Variables & Secrets

Your application requires **19 critical environment variables**. Here's what needs to be configured in Render:

### **Google Cloud Platform**
```bash
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}  # Large JSON credential
GOOGLE_SHEETS_ID=11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o
GOOGLE_AGENT_SHEETS_ID=1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I
GOOGLE_DRIVE_PARENT_FOLDER_ID=1i1SAHRnrgA-eWKgaZaShwF3zzOqewO3W
GOOGLE_DRIVE_TEMPLATES_FOLDER_ID=1YPUFTwKP5uzOMTKp1OZcWuwCeZA2nFqE
```

### **SMS & Communication**
```bash
TWILIO_ACCOUNT_SID=AC_your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_FROM_NUMBER=+1234567890  # ⚠️ Needs real Twilio number
TWILIO_INTERNAL_NUMBERS=+1234567890,+1987654321  # ⚠️ Needs real team numbers
SENDGRID_API_KEY=SG.your_sendgrid_api_key_here
```

### **Email Configuration**
```bash
EMAIL_FROM=greenwatt.intake@gmail.com
EMAIL_TO=greenwatt.intake@gmail.com,pat@persimmons.studio
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### **AI & Application**
```bash
OPENAI_API_KEY=sk-proj-your_openai_api_key_here
PORT=5000
FLASK_ENV=production
PYTHON_VERSION=3.11.0
```


## 🔧 Ignore any SMS implementation right now 

### **Phone Numbers for SMS (Client Dependent)**
The Twilio configuration shows placeholder phone numbers that will be updated when the client is ready:
- `TWILIO_FROM_NUMBER=+1234567890` ← **Will be updated by client**
- `TWILIO_INTERNAL_NUMBERS=+1234567890,+1987654321` ← **Will be updated by client**

**Note:** SMS functionality is gracefully handled - the app won't crash if SMS isn't fully configured.

## 📁 File System & Storage Challenges

### **Ephemeral File System Issue**
Render uses **ephemeral file systems** - uploaded files are **deleted on redeployment**:

```python
# Current problematic pattern in app.py:
app.config['UPLOAD_FOLDER'] = 'uploads'  # ⚠️ Will be wiped on redeploy
os.makedirs('temp', exist_ok=True)        # ⚠️ Will be wiped on redeploy
```

### **Solution: Direct Google Drive Upload**
Your app already implements this correctly by:
1. ✅ Temporarily saving uploads to local disk
2. ✅ Immediately uploading to Google Drive  
3. ✅ Deleting local files after processing

```python
# Good pattern already implemented:
file.save(filepath)                    # Temp save
drive_service.upload_file(...)         # Upload to Drive
os.remove(filepath)                    # Clean up immediately
```

## 🔧 Render Configuration

### **Update render.yaml**
Your current `render.yaml` needs these additions:

```yaml
services:
  - type: web
    name: greenwatt-intake-system
    runtime: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app --bind 0.0.0.0:$PORT --workers 1"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: PORT
        value: 5000
      # All other environment variables marked as sync: false (secrets)
      - key: GOOGLE_SERVICE_ACCOUNT_JSON
        sync: false
      - key: SENDGRID_API_KEY  # ← ADD THIS
        sync: false
      # ... (add all environment variables from above)
```

### **Service Account JSON Challenge**
The `GOOGLE_SERVICE_ACCOUNT_JSON` is a **large multi-line JSON string**. In Render:
1. **Copy the entire JSON** from your `.env` file
2. **Paste as single line** in Render environment variables
3. **Ensure no line breaks** are introduced

## 🏗️ Build Commands & Dependencies

### **Python Dependencies**
Your `requirements.txt` is comprehensive and includes:
- ✅ Flask + CORS
- ✅ Google Cloud libraries (Vision, Sheets, Drive)
- ✅ PDF processing (ReportLab, PyPDF, PDF2Image)
- ✅ Image processing (Pillow, OpenCV)
- ✅ Communication (Twilio, SendGrid)
- ✅ Production server (Gunicorn)

### **System Dependencies**
Some packages may need system libraries:
- `opencv-python` might need additional system packages
- `pdf2image` requires **poppler-utils** for PDF conversion

**Potential solution**: Add a custom build script if needed:
```bash
# In build command:
apt-get update && apt-get install -y poppler-utils && pip install -r requirements.txt
```

## 📡 Webhook Configuration

### **SMS Webhook Endpoint**
Your app has SMS webhook handling at `/sms-webhook`. You'll need to:

1. **Deploy to Render first** to get your URL
2. **Configure Twilio webhook** to point to: `https://your-app.onrender.com/sms-webhook`
3. **Ensure HTTPS** (Render provides this automatically)

## 🔍 Testing Strategy

### **Pre-Deploy Testing**
Your app includes excellent test endpoints:
- `/test-ocr` - Google Vision OCR testing
- `/test-sendgrid-email` - Email notification testing  
- `/test-sms-sending` - SMS functionality testing
- `/test-end-to-end` - Complete workflow testing

### **Post-Deploy Verification**
1. **Access test endpoints** on Render URL
2. **Verify Google Cloud connectivity**
3. **Test file upload → OCR → PDF generation → Drive upload**
4. **Confirm SMS and email notifications**

## 🚀 Deployment Commands for Claude

When you're ready to deploy with the Render MCP server, tell Claude:

```
"Deploy my GreenWatt Flask application to Render from the GitHub repository at [your-repo-url]. 

Key configuration:
- Python 3.11 runtime
- Build command: pip install -r requirements.txt  
- Start command: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
- Set environment variables from my .env file (I'll provide the values)
- This is a Flask web service that handles file uploads and PDF processing

The app is ready to deploy - it has proper Gunicorn configuration and all dependencies listed."
```

## ⚠️ Security Notes

### **Exposed Secrets**
Your `.env` file contains **live production credentials**:
- Real Google service account private key
- Live Twilio credentials  
- OpenAI API key with billing

**Recommendation**: Rotate these keys after deployment and use Render's secret management.

### **Webhook Security**
Your SMS webhook includes signature validation - ensure this works on Render's HTTPS endpoints.

## 🎯 Action Items Summary

1. **✅ Ready to deploy** - Core application is deployment-ready
2. **🔑 Add SendGrid API key** to environment variables
3. **📞 Update Twilio phone numbers** with real values
4. **🔐 Configure all environment variables** in Render dashboard
5. **🌐 Update webhook URLs** after deployment
6. **🧪 Test all integrations** using built-in test endpoints

Your application is well-architected for cloud deployment and follows best practices for file handling, environment variable management, and service integration. The main work is configuration rather than code changes!