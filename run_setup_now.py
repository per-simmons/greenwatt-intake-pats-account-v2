#!/usr/bin/env python3
"""Direct execution of setup"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the setup
from setup_workspace_resources_auto import main

if __name__ == "__main__":
    main()