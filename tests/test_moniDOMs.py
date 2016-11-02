#!/usr/bin/env python

import unittest
import math
import os
import dor
from time import sleep
from datetime import datetime
import hubmonitools

# For python2.6 total_seconds()
def timedelta_total_seconds(timedelta):
    return (timedelta.microseconds + 0.0 +
            (timedelta.seconds + timedelta.days * 24 * 3600) * 10 ** 6) / 10 ** 6

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
            self.moniDOMs[dom.cwd()] = hubmonitools.HubMoniDOM(dom, self.hub)
            
    def testMoniDOMs(self):
        # Check that we have all CWDs and check 
        self.assertEqual(sorted(self.moniDOMs.keys()), ['00A', '00B', '01A', '01B'])
        m = self.moniDOMs['00B']
        self.assertEqual(m.dom.omkey(), "2029-1")
        self.assertEqual(m.current, 99)
        self.assertEqual(m.voltage, 89.124)
        self.failUnless(m.dom.isCommunicating())
        self.assertEqual(m.dom.mbid(), "ac81eee613d4")
        self.failUnless(m.pwrcheck.ok)

    def testMoniRecord(self):        
        recs = hubmonitools.moniRecords(self.moniDOMs, {})

        # Check that stats *don't* appear when there is only one record
        self.failUnless('dom_comstat_retx' not in recs)
        self.assertEqual(len(recs), 2)

        # Check hub name
        self.assertEqual(recs[0]["value"]["hub"], "ichub29")

        # Get another set of monitoring records
        commDOMs = self.dor.getCommunicatingDOMs()
        moniDOMsPrev = self.moniDOMs
        self.moniDOMs = {}
        for dom in commDOMs:
            cwd = dom.cwd()
            self.moniDOMs[cwd] = hubmonitools.HubMoniDOM(dom, self.hub)
            # Fake some bad packets
            if (cwd == "01A"):
                self.moniDOMs[cwd].comstat.badpkt += 8
            
        recs = hubmonitools.moniRecords(self.moniDOMs, moniDOMsPrev)
        self.assertEqual(len(recs), 6)

        currentRec = [r for r in recs if r["varname"] == "dom_pwrstat_current"][0]
        self.assertEqual(currentRec.getDOMValue("2029-3"), 101)

        badpktRec =  [r for r in recs if r["varname"] == "dom_comstat_badpkt"][0]
        self.assertEqual(badpktRec.getDOMValue("2029-4"), 8)

        # Get yet another set of monitoring records, check times
        sleep(5)
        moniDOMsPrev = self.moniDOMs
        self.moniDOMs = {}
        for dom in commDOMs:
            cwd = dom.cwd()
            self.moniDOMs[cwd] = hubmonitools.HubMoniDOM(dom, self.hub)
            # Fake some received bytes
            if (cwd == "00A"):
                self.moniDOMs[cwd].comstat.rxbytes += 162000000

        recs = hubmonitools.moniRecords(self.moniDOMs, moniDOMsPrev)

        throughputRec = [r for r in recs if r["varname"] == "dom_comstat_rxbytes"][0]
        starttime = datetime.strptime(throughputRec["value"]["recordingStartTime"],
                                      "%Y-%m-%d %H:%M:%S.%f")
        stoptime = datetime.strptime(throughputRec["value"]["recordingStopTime"],
                                      "%Y-%m-%d %H:%M:%S.%f")
        delta_sec = int(timedelta_total_seconds(stoptime-starttime) + 0.5)
        self.assertEqual(throughputRec.getDOMValue("2029-2"), 162000000)
        self.assertEqual(delta_sec, 5)

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

        
