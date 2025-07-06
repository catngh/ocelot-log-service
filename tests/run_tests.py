#!/usr/bin/env python3
"""
Test runner script for ocelot-log-service.
"""
import pytest
import sys
import os

if __name__ == "__main__":
    # Add the project root to PYTHONPATH to allow imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Run pytest with arguments passed from command line
    args = sys.argv[1:] if len(sys.argv) > 1 else ['tests/unit']
    
    sys.exit(pytest.main(args)) 