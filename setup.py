#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='domhub-tools-python',
      version='1.4.3',
      description='IceCube DOMHub Monitoring',
      author='John Kelley',
      author_email='jkelley@icecube.wisc.edu',
      url='http://icecube.wisc.edu',
      test_suite="tests",
      scripts=['bin/hubmoni.py', 'bin/domstate.py', 'bin/status.py'],
      packages=find_packages()
      )
