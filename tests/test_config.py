#!/usr/bin/env python

import os
import unittest
import hubmonitools

class MoniConfigTests(unittest.TestCase):

    PREFIX = os.path.dirname(os.path.abspath(__file__))
    
    def testConfigDefaults(self):
        config = hubmonitools.HubMoniConfig()
        self.failUnless((config.MONI_SERVICE == "hubmoni") and
                        (config.MONI_PRIORITY == 3) and
                        (config.ALERT_SERVICE == "hubmoni") and
                        (config.ALERT_PRIORITY == 1) and
                        (config.ALERT_PAGES == False) and
                        (config.ALERT_NOTIFIES == []) and
                        (config.ZMQ_HOSTNAME == "expcont") and
                        (config.ZMQ_PORT == 6668))

    def testConfigFile(self):
        config = hubmonitools.HubMoniConfig(MoniConfigTests.PREFIX+"/hubmoni.config")
        # Make sure defaults are still there
        self.failUnless((config.MONI_SERVICE == "hubmoni") and
                        (config.ALERT_SERVICE == "hubmoni"))
        # Check overrides
        self.failUnless((config.ALERT_PAGES == True) and
                        (config.ALERT_NOTIFIES == ["bogus@bogus.com"]))
        
