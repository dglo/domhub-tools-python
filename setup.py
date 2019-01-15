#!/usr/bin/env python

from setuptools import setup, find_packages

# Workaround for Python multiprocessing atexit bug
try:
    import multiprocessing
except ImportError:
    pass

setup(name='domhub-tools-python',
      version='1.7.1',
      description='IceCube DOMHub Monitoring',
      author='John Kelley',
      author_email='jkelley@icecube.wisc.edu',
      url='http://icecube.wisc.edu',
      test_suite="tests",
      scripts=['bin/hubmoni.py', 'bin/domstate.py', 'bin/status.py', 'bin/flasher.py'],
      packages=find_packages(exclude=["tests"])
      )
