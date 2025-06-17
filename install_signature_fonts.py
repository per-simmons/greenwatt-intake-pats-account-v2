#!/usr/bin/env python3
"""
Font installation script for GreenWatt PDF signature system.
Downloads and installs cursive fonts for professional PDF signatures.
"""

import os
import requests
from urllib.parse import urlparse

def download_font(url, filename, fonts_dir="fonts"):
    """Download a font file from URL."""
    try:
        print(f"📥 Downloading {filename}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Ensure fonts directory exists
        os.makedirs(fonts_dir, exist_ok=True)
        
        # Write font file
        filepath = os.path.join(fonts_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        # Verify it's a real TTF file
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if header not in [b'\x00\x01\x00\x00', b'OTTO', b'true', b'typ1']:
                print(f"❌ {filename} - Invalid TTF file (got HTML redirect)")
                os.remove(filepath)
                return False
        
        print(f"✅ {filename} - Downloaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ {filename} - Download failed: {e}")
        return False

def install_signature_fonts():
    """Install all signature fonts for the PDF system."""
    
    print("🎨 GreenWatt PDF Signature Fonts Installer")
    print("=" * 50)
    
    # Font download configurations
    # Using direct GitHub links to Google Fonts repository
    fonts_to_install = [
        {
            "name": "Great Vibes",
            "filename": "GreatVibes-Regular.ttf",
            "url": "https://github.com/google/fonts/raw/main/ofl/greatvibes/GreatVibes-Regular.ttf",
            "description": "Elegant script font - recommended for signatures"
        },
        {
            "name": "Alex Brush", 
            "filename": "AlexBrush-Regular.ttf",
            "url": "https://github.com/google/fonts/raw/main/ofl/alexbrush/AlexBrush-Regular.ttf",
            "description": "Handwritten style font"
        },
        {
            "name": "Allura",
            "filename": "Allura-Regular.ttf", 
            "url": "https://github.com/google/fonts/raw/main/ofl/allura/Allura-Regular.ttf",
            "description": "Formal script font"
        },
        {
            "name": "Kaushan Script",
            "filename": "KaushanScript-Regular.ttf",
            "url": "https://github.com/google/fonts/raw/main/ofl/kaushanscript/KaushanScript-Regular.ttf", 
            "description": "Casual script font"
        }
    ]
    
    successful_downloads = 0
    
    for font_config in fonts_to_install:
        print(f"\n📋 {font_config['name']}")
        print(f"   {font_config['description']}")
        
        if download_font(font_config["url"], font_config["filename"]):
            successful_downloads += 1
    
    print(f"\n📊 Installation Summary")
    print(f"   Successfully installed: {successful_downloads}/{len(fonts_to_install)} fonts")
    
    if successful_downloads > 0:
        print(f"\n✅ Font installation completed!")
        print(f"   Fonts installed in: ./fonts/")
        print(f"   Primary signature font: Great Vibes")
        
        # Test the fonts
        test_fonts()
    else:
        print(f"\n❌ No fonts were installed successfully.")
        print(f"   Check your internet connection and try again.")
        print(f"   Falling back to Helvetica-Oblique for signatures.")

def test_fonts():
    """Test that the installed fonts work with ReportLab."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        print(f"\n🧪 Testing installed fonts with ReportLab...")
        
        fonts_dir = "fonts"
        test_fonts = [
            ("GreatVibes-Regular.ttf", "GreatVibes"),
            ("AlexBrush-Regular.ttf", "AlexBrush"),
            ("Allura-Regular.ttf", "Allura"),
            ("KaushanScript-Regular.ttf", "KaushanScript")
        ]
        
        working_fonts = []
        
        for font_file, font_name in test_fonts:
            font_path = os.path.join(fonts_dir, font_file)
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    working_fonts.append(font_name)
                    print(f"   ✅ {font_name}")
                except Exception as e:
                    print(f"   ❌ {font_name} - {e}")
            else:
                print(f"   ⚠️  {font_name} - File not found")
        
        if working_fonts:
            print(f"\n🎯 {len(working_fonts)} fonts ready for PDF signatures!")
            print(f"   Primary font: {working_fonts[0]}")
        else:
            print(f"\n⚠️  No fonts working. Will use Helvetica-Oblique fallback.")
            
    except ImportError:
        print(f"\n⚠️  ReportLab not available for testing.")
        print(f"   Install with: pip install reportlab")

if __name__ == "__main__":
    install_signature_fonts()