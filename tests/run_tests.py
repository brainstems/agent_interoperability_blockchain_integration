"""
Test runner for the infrastructure crew tests.
"""

import pytest
import logging
import os
import sys

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Set asyncio fixture scope to function and configure pytest
    pytest.main([
        "-v", 
        "-s", 
        "--tb=short",
        "--asyncio-mode=strict",
        "--asyncio-default-fixture-loop-scope=function",
        "--pythonpath=/Users/erichillerbrand/agent_blockchain-integration-main",
        "tests/unit/"
    ])
