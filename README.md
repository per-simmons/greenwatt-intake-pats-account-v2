# GreenWatt Automation System

A full-stack Flask web application for automated intake and document processing for community solar programs.

## 🚀 Quick Deploy to Render.com

This repository is ready for immediate deployment to Render.com:

1. **Fork this repository** or use it directly
2. **Connect to Render.com** and create a new Web Service
3. **Configure environment variables** (see deployment guide below)
4. **Deploy** - the app will automatically start with Gunicorn

## Features

- 📝 **Web form** for field agent data entry with dynamic dropdowns
- 🔍 **OCR processing** using Google Cloud Vision API + OpenAI GPT-3.5
- 📄 **PDF generation** with pixel-perfect signature placement
- ☁️ **Google Drive integration** for organized document storage
- 📊 **Google Sheets integration** for comprehensive data logging
- 📧 **Email notifications** via SendGrid for team alerts
- 📱 **SMS integration** via Twilio for customer verification
- 🏗️ **Production ready** with Gunicorn WSGI server

## Deployment Ready

- ✅ **render.yaml** configured for Render.com
- ✅ **requirements.txt** with all dependencies
- ✅ **Gunicorn WSGI server** for production
- ✅ **Environment variable** based configuration
- ✅ **SSL certificate** compatibility (works on Render)

## 🔧 Environment Variables Required

Configure these environment variables in Render.com dashboard:

### **Google Cloud Platform**
```bash
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}  # Full JSON credential
GOOGLE_SHEETS_ID=11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o
GOOGLE_AGENT_SHEETS_ID=1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I
GOOGLE_DRIVE_PARENT_FOLDER_ID=1i1SAHRnrgA-eWKgaZaShwF3zzOqewO3W
GOOGLE_DRIVE_TEMPLATES_FOLDER_ID=1YPUFTwKP5uzOMTKp1OZcWuwCeZA2nFqE
```

### **Email & SMS**
```bash
SENDGRID_API_KEY=SG.your_sendgrid_api_key_here
EMAIL_FROM=greenwatt.intake@gmail.com
EMAIL_TO=greenwatt.intake@gmail.com,pat@persimmons.studio
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
TWILIO_ACCOUNT_SID=AC_your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_FROM_NUMBER=+1234567890  # Needs real Twilio number
TWILIO_INTERNAL_NUMBERS=+1234567890,+1987654321  # Team numbers
```

### **AI & App Configuration**
```bash
OPENAI_API_KEY=sk-proj-your_openai_api_key_here
PORT=5000
FLASK_ENV=production
PYTHON_VERSION=3.11.0
```

## 📦 Local Development

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env` file

3. Run development server:
```bash
python app.py
```

The application will start on `http://localhost:5000`

## Running the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Usage

1. Open the web interface at `http://localhost:5000`
2. Fill out all required fields in the form
3. Upload a utility bill (JPEG, PNG, or PDF)
4. Check the POA agreement checkbox
5. Submit the form

The system will:
- Extract data from the utility bill using OCR
- Generate two PDF contracts
- Upload all documents to Google Drive
- Log the submission in Google Sheets
- Send email notifications to the configured recipients

## Project Structure

```
.
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration
├── templates/            # HTML templates
│   └── index.html       # Main form page
├── static/              # Static assets
│   ├── css/
│   │   └── style.css   # Styling
│   └── js/
│       └── main.js     # Frontend JavaScript
├── services/            # Backend services
│   ├── ocr_service.py          # OCR processing
│   ├── pdf_generator.py        # PDF generation
│   ├── google_drive_service.py # Google Drive integration
│   ├── google_sheets_service.py # Google Sheets integration
│   └── email_service.py        # Email notifications
├── uploads/             # Temporary file uploads
└── temp/               # Temporary processing files
```

## Developer Notes

- The system includes 3 example developer templates (A, B, C) with different terms
- POID is required for NYSEG and RG&E utilities only
- Agent IDs are mapped to names in `app.py` (AG001-AG004)
- All uploaded files are deleted after processing
- Google Drive folders are created with naming convention: `YYYY-MM-DD_CustomerName_Utility`

## Troubleshooting

1. **OCR not working**: Ensure Tesseract is installed and in your PATH
2. **Google API errors**: Verify service account has proper permissions
3. **Email not sending**: Check SMTP configuration in `.env`
4. **File upload errors**: Ensure `uploads/` and `temp/` directories exist with write permissions