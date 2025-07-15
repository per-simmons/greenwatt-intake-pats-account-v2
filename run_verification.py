#!/usr/bin/env python3
"""Run the verification script directly"""

import subprocess
import sys
import os

# Change to the project directory
os.chdir('/Users/patsimmons/client-coding/GreenWatt_Clean_Repo')

# Run the verification script
try:
    result = subprocess.run([sys.executable, 'verify_workspace_resources.py'], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
except Exception as e:
    print(f"Error running verification: {e}")