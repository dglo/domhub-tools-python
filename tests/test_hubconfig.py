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
        self.failUnless(hub["comm"] == 60 and
                        hub["dor"] == 8 and
                        hub["iceboot"] == 60 and
                        hub["quad"] == 15)

    def testHostCluster(self):
        host,cluster = hubmonitools.getHostCluster(hostname='access.icecube.southpole.usap.gov')
        self.failUnless(host == 'access' and cluster=='sps')

        host,cluster = hubmonitools.getHostCluster(hostname='ichub21.spts.icecube.wisc.edu')
        self.failUnless(host == 'ichub21' and cluster=='spts')

        host,cluster = hubmonitools.getHostCluster(hostname='access.sptsn.icecube.wisc.edu')
        self.failUnless(host == 'access' and cluster=='spts')

    def testHubs(self):
        hubs = self.conf.hubs("spts")
        self.failUnless("ichub21" in hubs)

    def testWaives(self):
        self.failUnless(self.conf.isWaived("ichub09", "sps", 1, 3) and not
                        self.conf.isWaived("ichub13", "sps", 2, 2))        

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HubConfigTests)

def main():
    unittest.TextTestRunner(verbosity=2).run(suite())

if __name__ == '__main__':
    main()
    

