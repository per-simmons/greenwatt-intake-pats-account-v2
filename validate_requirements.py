#!/usr/bin/env python3
"""
Validate that all Python imports in the codebase have corresponding entries in requirements.txt
"""

import os
import re
import ast

def get_imports_from_file(filepath):
    """Extract all import statements from a Python file"""
    imports = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filepath)
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    # Get the base module name
                    base_module = name.name.split('.')[0]
                    imports.add(base_module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get the base module name
                    base_module = node.module.split('.')[0]
                    imports.add(base_module)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    
    return imports

def get_all_imports(directory='.'):
    """Get all imports from all Python files in directory"""
    all_imports = set()
    
    for root, dirs, files in os.walk(directory):
        # Skip virtual environments and cache directories
        dirs[:] = [d for d in dirs if d not in ['venv', 'env', '__pycache__', '.git', 'temp']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                imports = get_imports_from_file(filepath)
                all_imports.update(imports)
    
    return all_imports

def get_requirements_packages():
    """Get all packages from requirements.txt"""
    packages = set()
    
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before any version specifier)
                    package = re.split('[<>=!]', line)[0].strip()
                    # Convert package names to import names (some differ)
                    package_map = {
                        'pillow': 'PIL',
                        'opencv-python-headless': 'cv2',
                        'python-dotenv': 'dotenv',
                        'google-auth': 'google',
                        'google-auth-httplib2': 'httplib2',
                        'google-api-python-client': 'googleapiclient',
                        'google-cloud-vision': 'google',
                        'pdfplumber': 'pdfplumber',
                        'pdf2image': 'pdf2image',
                        'flask-cors': 'flask_cors',
                        'pytz': 'pytz',
                        'pypdf': 'pypdf',
                        'pymupdf': 'fitz',
                        'cachetools': 'cachetools',
                        'reportlab': 'reportlab',
                        'twilio': 'twilio',
                        'sendgrid': 'sendgrid',
                        'numpy': 'numpy',
                        'werkzeug': 'werkzeug',
                        'flask': 'flask',
                        'openai': 'openai',
                        'gunicorn': 'gunicorn'
                    }
                    
                    # Add both the package name and its import name
                    packages.add(package.lower())
                    if package.lower() in package_map:
                        packages.add(package_map[package.lower()])
    
    return packages

def main():
    """Main validation function"""
    print("🔍 Validating Python requirements...\n")
    
    # Get all imports
    all_imports = get_all_imports()
    
    # Get packages from requirements.txt
    req_packages = get_requirements_packages()
    
    # Standard library modules to ignore
    stdlib_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'io', 're', 'ast',
        'threading', 'subprocess', 'uuid', 'base64', 'traceback',
        'typing', 'collections', 'itertools', 'functools', 'pathlib',
        'shutil', 'tempfile', 'contextlib', 'warnings', 'copy',
        'math', 'random', 'string', 'hashlib', 'hmac', 'secrets',
        'urllib', 'http', 'email', 'csv', 'xml', 'html', 'ftplib',
        'unittest', 'doctest', 'pdb', 'logging', 'argparse',
        'configparser', 'sqlite3', 'queue', 'socket', 'ssl',
        'struct', 'binascii', 'codecs', 'locale', 'glob',
        'fnmatch', 'linecache', 'pickle', 'copyreg', 'types',
        'importlib', 'pkgutil', 'platform', 'errno', 'gc',
        'weakref', 'atexit', 'abc', 'asyncio', 'concurrent',
        'multiprocessing', 'signal', 'select', 'selectors',
        'statistics', 'decimal', 'fractions', 'numbers',
        'cmath', 'array', 'bisect', 'heapq', 'zlib', 'gzip',
        'bz2', 'lzma', 'zipfile', 'tarfile', 'fileinput',
        'filecmp', 'calendar', 'textwrap', 'unicodedata',
        'pprint', 'enum', 'graphlib', 'dataclasses'
    }
    
    # Local modules to ignore (from this project)
    local_modules = {
        'services', 'app', 'test_ocr_debug', 'verify_production_config',
        'validate_requirements'
    }
    
    # Filter out standard library and local modules
    third_party_imports = all_imports - stdlib_modules - local_modules
    
    # Check for missing packages
    missing_from_requirements = []
    for imp in sorted(third_party_imports):
        # Check if the import or its base name is in requirements
        if imp.lower() not in req_packages and imp not in req_packages:
            missing_from_requirements.append(imp)
    
    # Report results
    if missing_from_requirements:
        print("❌ Found imports without corresponding requirements.txt entries:\n")
        for imp in missing_from_requirements:
            print(f"   - {imp}")
        print(f"\n⚠️  Total missing: {len(missing_from_requirements)}")
    else:
        print("✅ All imports have corresponding entries in requirements.txt")
    
    print(f"\n📊 Summary:")
    print(f"   - Total unique imports found: {len(all_imports)}")
    print(f"   - Third-party imports: {len(third_party_imports)}")
    print(f"   - Packages in requirements.txt: {len(req_packages)}")
    
    # Special check for pdf2image
    if 'pdf2image' in third_party_imports:
        if 'pdf2image' in req_packages:
            print("\n✅ pdf2image is properly listed in requirements.txt")
        else:
            print("\n❌ pdf2image is used but NOT in requirements.txt!")

if __name__ == "__main__":
    main()