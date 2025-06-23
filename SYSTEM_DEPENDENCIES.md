# System Dependencies

This document lists all system-level (non-Python) dependencies required for the GreenWatt Intake System.

## Required System Packages

### poppler-utils
- **Required by**: pdf2image Python package
- **Purpose**: PDF rendering and conversion to images for OCR processing
- **Installation**: `apt-get install -y poppler-utils`
- **Used in**: `services/vision_ocr_service.py` for converting PDFs to images before sending to Google Vision API

## Installation on Different Platforms

### Production (Render.com)
Already configured in `render.yaml`:
```yaml
buildCommand: "apt-get update && apt-get install -y poppler-utils && pip install -r requirements.txt"
```

### Local Development (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

### Local Development (macOS)
```bash
brew install poppler
```

### Local Development (Windows)
1. Download poppler for Windows from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract and add the `bin/` folder to your PATH
3. Or set the environment variable: `PDF2IMAGE_POPPLER_PATH=C:\path\to\poppler\bin`

## Verification

To verify poppler is installed correctly:
```bash
# Check if pdftoppm is available (used by pdf2image)
which pdftoppm

# Test PDF to image conversion
pdftoppm -h
```

## Troubleshooting

### "No module named 'pdf2image'" Error
- Ensure `pdf2image==1.16.3` is in requirements.txt
- Run `pip install pdf2image`

### "Unable to get page count. Is poppler installed?" Error
- Install poppler-utils system package as shown above
- Verify pdftoppm is in PATH

### OCR Returns Empty Results
- Check Render logs for "Fallback PDF processing error"
- Verify both pdf2image and poppler-utils are properly installed
- Check that the PDF file is not corrupted or password-protected