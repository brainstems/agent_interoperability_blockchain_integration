"""
Test runner for infrastructure crew tests.
"""

import pytest
import logging
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add project root to Python path
    sys.path.insert(0, project_root)
    
    # Run pytest from the root directory with specific test directories
    pytest.main(["-v", "-s", "--tb=short", "tests/unit/", "tests/integration/"])
