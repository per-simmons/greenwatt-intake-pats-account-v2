from google.cloud import vision
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
                            full_text += page_text + "\n"
                            
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
                        full_text += page_text + "\n"
                        
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
