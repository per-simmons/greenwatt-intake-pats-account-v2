#!/usr/bin/env python3
"""
Comprehensive Memory Fix for GreenWatt Intake Form
Date: 2025-06-27
Author: Claude Code

This script contains all the fixes needed to resolve memory issues.
Run this to apply all fixes to the codebase.
"""

import os
import shutil
from datetime import datetime
import re

def backup_files():
    """Create backups of files we'll modify"""
    files_to_backup = [
        'app.py',
        'services/vision_ocr_service.py',
        'services/google_service_manager.py'
    ]
    
    backup_dir = f'backups/memory_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    os.makedirs(backup_dir, exist_ok=True)
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(backup_dir, os.path.basename(file)))
    
    print(f"✅ Backups created in {backup_dir}")
    return backup_dir

def fix_vision_ocr_service():
    """Fix memory leaks in vision_ocr_service.py"""
    
    new_content = '''from google.cloud import vision
from google.oauth2 import service_account
import io
import os
from PIL import Image
import time
import gc
import tempfile
import contextlib

class VisionOCRService:
    # Class-level client to reuse across requests
    _client = None
    _credentials = None
    
    def __init__(self, service_account_info):
        """Initialize Google Cloud Vision client with service account credentials"""
        if not VisionOCRService._credentials:
            VisionOCRService._credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - no longer creates/destroys clients"""
        pass
    
    @classmethod
    def _get_client(cls):
        """Get or create shared client instance"""
        if not cls._client:
            if not cls._credentials:
                raise ValueError("VisionOCRService not initialized with credentials")
            cls._client = vision.ImageAnnotatorClient(credentials=cls._credentials)
            print("✅ Created shared Vision API client")
        return cls._client
    
    def extract_text_from_image(self, image_path):
        """Extract text from image using Vision API document_text_detection"""
        try:
            print(f"🔍 VISION EXTRACT: Reading file: {image_path}")
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            print(f"🔍 VISION EXTRACT: File read successfully, {len(content)} bytes")
            
            image = vision.Image(content=content)
            client = self._get_client()
            
            print(f"🔍 VISION EXTRACT: About to call Vision API document_text_detection")
            
            # Use document_text_detection for better utility bill reading
            response = client.document_text_detection(
                image=image,
                image_context=vision.ImageContext(language_hints=["en"])
            )
            
            print(f"🔍 VISION EXTRACT: Vision API call completed")
            
            if response.error.message:
                print(f"🔍 VISION EXTRACT: Vision API returned error: {response.error.message}")
                raise Exception(f"Vision API error: {response.error.message}")
            
            print(f"🔍 VISION EXTRACT: No error in response")
            
            # Get the full text annotation
            texts = response.text_annotations
            print(f"🔍 VISION EXTRACT: Text annotations count: {len(texts) if texts else 0}")
            
            if texts:
                result_text = texts[0].description
                print(f"🔍 VISION EXTRACT: Extracted text length: {len(result_text) if result_text else 0}")
                return result_text
            else:
                print(f"🔍 VISION EXTRACT: No text annotations found")
                return ""
                
        except Exception as e:
            print(f"🔍 VISION EXTRACT ERROR: {e}")
            import traceback
            traceback.print_exc()
            return ""
        finally:
            # Force cleanup
            del content
            gc.collect()
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using Vision API - simplified approach to avoid gRPC issues"""
        try:
            # Use the simpler fallback method directly to avoid gRPC async issues
            print("Processing PDF with Vision API (image conversion method)...")
            return self._fallback_pdf_to_images(pdf_path)
            
        except Exception as e:
            print(f"Vision PDF OCR Error: {e}")
            return ""
    
    def _fallback_pdf_to_images(self, pdf_path):
        """Fallback method: convert PDF pages to images and process with Vision"""
        try:
            from pdf2image import convert_from_path
            print("Using fallback: PDF to images conversion")
            
            # Check file size before processing
            file_size = os.path.getsize(pdf_path)
            print(f"PDF file size: {file_size / (1024*1024):.1f} MB")
            
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                print("PDF file too large (>50MB), skipping conversion")
                return ""
            
            full_text = ""
            
            # Use a proper temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                print("Starting PDF conversion...")
                
                # Process one page at a time to reduce memory usage
                try:
                    # Get page count first
                    from pdf2image import pdfinfo_from_path
                    info = pdfinfo_from_path(pdf_path, poppler_path='/usr/bin')
                    page_count = info["Pages"]
                    print(f"PDF has {page_count} pages")
                    
                    # Process each page individually
                    for page_num in range(1, min(page_count + 1, 11)):  # Limit to 10 pages
                        print(f"Processing page {page_num}/{min(page_count, 10)}")
                        
                        # Convert single page
                        pages = convert_from_path(
                            pdf_path, 
                            dpi=150,  # Reduced DPI
                            first_page=page_num,
                            last_page=page_num,
                            poppler_path='/usr/bin'
                        )
                        
                        if pages:
                            page = pages[0]
                            # Save page as temporary image
                            temp_image_path = os.path.join(temp_dir, f"page_{page_num}.png")
                            page.save(temp_image_path, 'PNG')
                            
                            # Immediately close the PIL image to free memory
                            page.close()
                            del pages
                            gc.collect()
                            
                            # Extract text from this page using Vision
                            page_text = self.extract_text_from_image(temp_image_path)
                            full_text += page_text + "\\n"
                            
                            # Remove temp file immediately
                            try:
                                os.remove(temp_image_path)
                            except:
                                pass
                        
                except Exception as e:
                    print(f"Error processing PDF pages individually: {e}")
                    # Fallback to all-at-once conversion if page-by-page fails
                    pages = convert_from_path(
                        pdf_path, 
                        dpi=150,
                        poppler_path='/usr/bin'
                    )
                    print(f"Fallback: converted PDF to {len(pages)} page(s)")
                    
                    for i, page in enumerate(pages[:10]):  # Limit to 10 pages
                        print(f"Processing page {i+1}/{min(len(pages), 10)}")
                        temp_image_path = os.path.join(temp_dir, f"page_{i}.png")
                        page.save(temp_image_path, 'PNG')
                        page.close()  # Close PIL image
                        
                        page_text = self.extract_text_from_image(temp_image_path)
                        full_text += page_text + "\\n"
                        
                        try:
                            os.remove(temp_image_path)
                        except:
                            pass
                    
                    # Clean up all pages
                    for page in pages:
                        page.close()
                    del pages
                    gc.collect()
            
            print(f"PDF processing complete. Extracted {len(full_text)} characters")
            return full_text
            
        except Exception as e:
            print(f"Fallback PDF processing error: {e}")
            import traceback
            traceback.print_exc()
            return ""
        finally:
            gc.collect()

def process_utility_bill_with_vision(file_path, service_account_info):
    """Main function to process utility bill using Google Vision API"""
    try:
        print(f"🔍 VISION DEBUG: Starting Vision API processing")
        print(f"🔍 VISION DEBUG: File path: {file_path}")
        print(f"🔍 VISION DEBUG: Service account type: {service_account_info.get('type', 'N/A')}")
        print(f"🔍 VISION DEBUG: Project ID: {service_account_info.get('project_id', 'N/A')}")
        
        # Use context manager for proper cleanup
        with VisionOCRService(service_account_info) as vision_service:
            print(f"🔍 VISION DEBUG: VisionOCRService created successfully")
            
            if file_path.lower().endswith('.pdf'):
                print("Processing PDF with Google Vision API...")
                raw_text = vision_service.extract_text_from_pdf(file_path)
            else:
                print("Processing image with Google Vision API...")
                raw_text = vision_service.extract_text_from_image(file_path)
                
            print(f"🔍 VISION DEBUG: Vision API call completed")
            print(f"🔍 VISION DEBUG: Raw text type: {type(raw_text)}")
            print(f"🔍 VISION DEBUG: Raw text length: {len(raw_text) if raw_text else 0}")
        
        print("="*50)
        print("GOOGLE VISION OCR TEXT:")
        print(raw_text if raw_text else "EMPTY/NONE")
        print("="*50)
        
        return raw_text
        
    except Exception as e:
        print(f"🔍 VISION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return ""
    finally:
        gc.collect()
'''
    
    with open('services/vision_ocr_service.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed vision_ocr_service.py")

def fix_app_memory_cleanup():
    """Add more aggressive memory cleanup to app.py"""
    
    # Read current app.py
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Find the cleanup_old_sessions function and replace it
    cleanup_func = '''def cleanup_old_sessions():
    """Clean up old progress sessions more aggressively"""
    current_time = time.time()
    sessions_to_remove = []
    
    for session_id, session in progress_sessions.items():
        # Remove if older than 2 minutes OR if marked for cleanup
        cleanup_time = session.get('cleanup_time', session['start_time'] + 120)
        if current_time > cleanup_time:
            sessions_to_remove.append(session_id)
    
    # Remove old sessions
    for session_id in sessions_to_remove:
        del progress_sessions[session_id]
    
    # MORE AGGRESSIVE: Keep only 10 most recent sessions if we have more than 10
    if len(progress_sessions) > 10:
        # Sort by start time and keep only the 10 most recent
        sorted_sessions = sorted(progress_sessions.items(), 
                               key=lambda x: x[1]['start_time'], 
                               reverse=True)
        progress_sessions.clear()
        progress_sessions.update(dict(sorted_sessions[:10]))
    
    # Log memory status with more detail
    try:
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # More aggressive cleanup at lower threshold (250MB instead of 350MB)
        if memory_mb > 250:
            print(f"⚠️ High memory usage: {memory_mb:.1f}MB - forcing aggressive cleanup")
            
            # Clear ALL progress sessions if memory is critical
            if memory_mb > 300:
                print(f"🚨 CRITICAL: Clearing all {len(progress_sessions)} progress sessions")
                progress_sessions.clear()
            else:
                # Keep only 5 most recent if memory is high
                if len(progress_sessions) > 5:
                    sorted_sessions = sorted(progress_sessions.items(), 
                                           key=lambda x: x[1]['start_time'], 
                                           reverse=True)
                    progress_sessions.clear()
                    progress_sessions.update(dict(sorted_sessions[:5]))
            
            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()
            
            # Log memory after cleanup
            memory_after = process.memory_info().rss / 1024 / 1024
            print(f"📊 Memory after cleanup: {memory_after:.1f}MB (freed {memory_mb - memory_after:.1f}MB)")
    except:
        pass'''
    
    # Find and replace the cleanup_old_sessions function
    import re
    pattern = r'def cleanup_old_sessions\(\):.*?(?=\ndef|\Z)'
    content = re.sub(pattern, cleanup_func, content, flags=re.DOTALL)
    
    # Add memory monitoring to file upload endpoint
    # Find the upload endpoint and add cleanup
    upload_pattern = r'(@app\.route\(\'/upload\', methods=\[\'POST\'\]\).*?def upload\(\):)'
    upload_replacement = r'\1\n    # Pre-emptive memory cleanup before processing\n    cleanup_old_sessions()\n    gc.collect()'
    content = re.sub(upload_pattern, upload_replacement, content, flags=re.DOTALL)
    
    # Save the modified content
    with open('app.py', 'w') as f:
        f.write(content)
    
    print("✅ Updated app.py with aggressive memory cleanup")

def add_memory_monitoring_endpoint():
    """Add a memory monitoring endpoint to app.py"""
    
    endpoint_code = '''
@app.route('/memory-status')
def memory_status():
    """Endpoint to check current memory usage"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        # Get detailed memory stats
        memory_stats = {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
            'total_mb': psutil.virtual_memory().total / 1024 / 1024,
            'progress_sessions': len(progress_sessions),
            'gc_stats': gc.get_stats()
        }
        
        # Force cleanup if memory is high
        if memory_stats['rss_mb'] > 250:
            cleanup_old_sessions()
            gc.collect()
            
            # Recalculate after cleanup
            memory_info_after = process.memory_info()
            memory_stats['rss_mb_after_cleanup'] = memory_info_after.rss / 1024 / 1024
            memory_stats['cleaned'] = True
        else:
            memory_stats['cleaned'] = False
        
        return jsonify(memory_stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
'''
    
    # Append to app.py before if __name__ == '__main__':
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Find the right place to insert (before the main block)
    main_pattern = r"(if __name__ == '__main__':|# Start background cleanup thread)"
    match = re.search(main_pattern, content)
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + endpoint_code + '\n\n' + content[insert_pos:]
        
        with open('app.py', 'w') as f:
            f.write(content)
        
        print("✅ Added memory monitoring endpoint /memory-status")

def create_memory_monitor_script():
    """Create a monitoring script for production"""
    
    monitor_script = '''#!/bin/bash
# Memory monitoring script for GreenWatt Render deployment
# Run this to continuously monitor memory usage

echo "🔍 Starting memory monitor for GreenWatt service..."
echo "Press Ctrl+C to stop"

SERVICE_URL="${SERVICE_URL:-https://greenwatt-intake-clean.onrender.com}"

while true; do
    echo -n "$(date '+%Y-%m-%d %H:%M:%S') - "
    
    # Call the memory status endpoint
    response=$(curl -s "${SERVICE_URL}/memory-status" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Parse the JSON response
        rss_mb=$(echo "$response" | grep -o '"rss_mb":[0-9.]*' | cut -d: -f2)
        sessions=$(echo "$response" | grep -o '"progress_sessions":[0-9]*' | cut -d: -f2)
        cleaned=$(echo "$response" | grep -o '"cleaned":[a-z]*' | cut -d: -f2)
        
        echo "Memory: ${rss_mb}MB | Sessions: ${sessions} | Cleaned: ${cleaned}"
        
        # Alert if memory is high
        if (( $(echo "$rss_mb > 400" | bc -l) )); then
            echo "⚠️  WARNING: High memory usage detected!"
        fi
    else
        echo "❌ Failed to fetch memory status"
    fi
    
    # Wait 30 seconds before next check
    sleep 30
done
'''
    
    with open('monitor_memory.sh', 'w') as f:
        f.write(monitor_script)
    
    os.chmod('monitor_memory.sh', 0o755)
    print("✅ Created monitor_memory.sh script")

def update_render_yaml():
    """Update render.yaml with memory optimizations"""
    
    render_config = '''services:
  - type: web
    name: greenwatt-intake-clean
    runtime: python
    plan: starter
    buildCommand: |
      apt-get update && apt-get install -y poppler-utils
      pip install --upgrade pip
      pip install -r requirements.txt
      python install_signature_fonts.py
    startCommand: |
      # Use single worker and enable memory monitoring
      gunicorn app:app \
        --bind 0.0.0.0:$PORT \
        --workers 1 \
        --worker-class sync \
        --timeout 120 \
        --max-requests 50 \
        --max-requests-jitter 10 \
        --preload
    envVars:
      - key: PYTHONUNBUFFERED
        value: "1"
      - key: MALLOC_TRIM_THRESHOLD_
        value: "0"
      - key: MALLOC_MMAP_THRESHOLD_
        value: "16384"
      - key: GUNICORN_CMD_ARGS
        value: "--max-requests=50 --max-requests-jitter=10"
'''
    
    with open('render.yaml', 'w') as f:
        f.write(render_config)
    
    print("✅ Updated render.yaml with memory optimizations")

def main():
    print("🚀 Starting comprehensive memory fix for GreenWatt Intake Form")
    print("-" * 60)
    
    # Create backups
    backup_dir = backup_files()
    
    try:
        # Apply all fixes
        fix_vision_ocr_service()
        fix_app_memory_cleanup()
        add_memory_monitoring_endpoint()
        create_memory_monitor_script()
        update_render_yaml()
        
        print("-" * 60)
        print("✅ All fixes applied successfully!")
        print("\nNext steps:")
        print("1. Test locally: python app.py")
        print("2. Monitor memory: ./monitor_memory.sh")
        print("3. Commit and push to deploy")
        print(f"\nBackups saved in: {backup_dir}")
        
    except Exception as e:
        print(f"\n❌ Error applying fixes: {e}")
        print("Please check the error and try again")
        print(f"Backups are in: {backup_dir}")

if __name__ == "__main__":
    main()