#!/usr/bin/env python3
"""
Standalone entry point for Q that can be run directly.
This avoids relative import issues when running without installation.
"""

import sys
import os

# Add the current directory to Python path so we can import the q package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main function
from q.cli import main

if __name__ == '__main__':
    main()