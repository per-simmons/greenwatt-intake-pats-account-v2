#!/usr/bin/env python3
"""Execute setup directly"""
import os
import json
import sys

# Navigate to correct directory
os.chdir('/Users/patsimmons/client-coding/GreenWatt_Clean_Repo')

# Add to path
sys.path.insert(0, os.getcwd())

# Now execute the setup
exec(open('setup_workspace_resources_auto.py').read())