#!/usr/bin/env python
import unittest
import sys
import os

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import test cases
from tests.test_auth import AuthTestCase

if __name__ == '__main__':
    # Create a test loader
    loader = unittest.TestLoader()
    
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(loader.loadTestsFromTestCase(AuthTestCase))
    
    # Run the test suite
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return non-zero exit code if tests failed
    sys.exit(not result.wasSuccessful()) 