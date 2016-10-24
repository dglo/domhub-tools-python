#!/usr/bin/env python

import unittest
import math
import os
import dor
import hubmonitools

class MoniDOMTests(unittest.TestCase):

    PREFIX = os.path.dirname(os.path.abspath(__file__))+"/../resources/ichub29_proc"
    HUBADDRESS = "ichub29.spts.icecube.wisc.edu"
    HUBCONFIG = os.path.dirname(os.path.abspath(__file__))+"/../resources/hubConfig.json"
    
    def setUp(self):
        self.dor = dor.DOR(prefix=MoniDOMTests.PREFIX)

        # Configuration file for hub alerts
        self.hubconfig = hubmonitools.HubConfig(MoniDOMTests.HUBCONFIG)
        self.hub,self.cluster = hubmonitools.getHostCluster(MoniDOMTests.HUBADDRESS)

        # Get monitoring snapshot
        self.moniDOMs = {}
        commDOMs = self.dor.getCommunicatingDOMs()
        for dom in commDOMs:
            cwd = dom.cwd()
            self.moniDOMs[cwd] = [ hubmonitools.HubMoniDOM(dom) ]
            
    def testMoniDOMs(self):
        # Check that we have all CWDs and check 
        self.assertEqual(sorted(self.moniDOMs.keys()), ['00A', '00B', '01A', '01B'])
        m = self.moniDOMs['00B'][0]
        self.assertEqual(m.dom.omkey(), "2029-1")
        self.assertEqual(m.current, 99)
        self.assertEqual(m.voltage, 89.124)
        self.failUnless(m.dom.isCommunicating())
        self.assertEqual(m.dom.mbid(), "ac81eee613d4")
        self.failUnless(m.pwrcheck.ok)

    def testMoniRecord(self):        
        recs = hubmonitools.moniRecords(self.moniDOMs)

        # Check that stats *don't* appear when there is only one record
        self.failUnless('dom_comstat_retx' not in recs)
        self.assertEqual(len(recs), 2)

        # Get other set of monitoring records
        commDOMs = self.dor.getCommunicatingDOMs()        
        for dom in commDOMs:
            cwd = dom.cwd()
            self.moniDOMs[cwd].append(hubmonitools.HubMoniDOM(dom))

        recs = hubmonitools.moniRecords(self.moniDOMs)
        self.assertEqual(len(recs), 5)

        currentRec = [r for r in recs if r["varname"] == "dom_pwrstat_current"][0]
        self.assertEqual(currentRec.getDOMValue("2029-3"), 101)

        badpktRec =  [r for r in recs if r["varname"] == "dom_comstat_badpkt"][0]
        self.assertEqual(badpktRec.getDOMValue("2029-4"), 0)

        throughputRec = [r for r in recs if r["varname"] == "dom_comstat_rxbytes"][0]
        self.assertEqual(throughputRec.getDOMValue("2029-1"), 0)

    def testAlerts(self):
        alerts = hubmonitools.moniAlerts(self.dor, self.hubconfig, self.hub, self.cluster)

        # One power check failure has already been inserted into the resources tree
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["value"]["condition"], "DOM power check failure on "+self.hub)
        
        # Fake more alerts
        self.hubconfig[self.cluster][self.hub]["comm"] = 3
        alerts = hubmonitools.moniAlerts(self.dor, self.hubconfig, self.hub, self.cluster)
        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0]["value"]["condition"], "Unexpected number of communicating DOMs on "+self.hub)
        
        self.hubconfig[self.cluster][self.hub]["comm"] = 4        
        self.hubconfig[self.cluster][self.hub]["dor"] = 1
        alerts = hubmonitools.moniAlerts(self.dor, self.hubconfig, self.hub, self.cluster)
        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0]["value"]["condition"], "Unexpected number of DOR cards on "+self.hub)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MoniDOMTests)

def main():
    unittest.TextTestRunner(verbosity=2).run(suite())    

if __name__ == '__main__':
    main()

        
