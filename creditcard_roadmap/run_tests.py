#!/usr/bin/env python
import unittest
import coverage
import sys
import os

# Configure code coverage
COV = coverage.coverage(
    branch=True,
    include='app/*',
    omit=[
        'app/templates/*',
        'app/static/*',
        'app/*/__init__.py'
    ]
)
COV.start()

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import the TestLoader
from unittest import TestLoader, TextTestRunner

if __name__ == '__main__':
    # Discover and run tests
    tests = TestLoader().discover('tests')
    result = TextTestRunner(verbosity=2).run(tests)
    
    # Generate coverage report
    COV.stop()
    COV.save()
    print('Coverage Summary:')
    COV.report()
    
    # Generate HTML report
    basedir = os.path.abspath(os.path.dirname(__file__))
    covdir = os.path.join(basedir, 'coverage')
    if not os.path.exists(covdir):
        os.makedirs(covdir)
    COV.html_report(directory=covdir)
    
    sys.exit(not result.wasSuccessful()) 