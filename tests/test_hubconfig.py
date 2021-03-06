#!/usr/bin/env python

import unittest
import math
import os
import hubmonitools

class HubConfigTests(unittest.TestCase):

    CONFIGFILE = os.path.dirname(os.path.abspath(__file__))+"/../resources/hubConfig.json"

    def setUp(self):
        self.conf = hubmonitools.HubConfig(HubConfigTests.CONFIGFILE)
        
    def testDOMCounts(self):
        hub = self.conf.getHub("ichub04", cluster="sps")
        self.assertTrue(hub["comm"] == 60 and
                        hub["dor"] == 8 and
                        hub["iceboot"] == 60 and
                        hub["quad"] == 15)

    def testHostCluster(self):
        host,cluster = hubmonitools.getHostCluster(hostname='access.icecube.southpole.usap.gov')
        self.assertTrue(host == 'access' and cluster=='sps')

        host,cluster = hubmonitools.getHostCluster(hostname='ichub21.spts.icecube.wisc.edu')
        self.assertTrue(host == 'ichub21' and cluster=='spts')

        host,cluster = hubmonitools.getHostCluster(hostname='access.sptsn.icecube.wisc.edu')
        self.assertTrue(host == 'access' and cluster=='spts')

    def testHubs(self):
        hubs = self.conf.hubs("spts")
        self.assertTrue("ichub21" in hubs)

    def testWaives(self):
        self.assertTrue(self.conf.isWaived("ichub07", "sps", 4, 1) and 
                        self.conf.isWaived("ichub07", "sps", 5, 2) and not
                        self.conf.isWaived("ichub13", "sps", 2, 2))        

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HubConfigTests)

def main():
    unittest.TextTestRunner(verbosity=2).run(suite())

if __name__ == '__main__':
    main()
    

