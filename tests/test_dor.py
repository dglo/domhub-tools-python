#!/usr/bin/env python

import unittest
import math
import dor
import os

class DORTests(unittest.TestCase):

    PREFIX = os.path.dirname(os.path.abspath(__file__))+"/../resources/ichub29_proc"

    def setUp(self):
        self.dor = dor.DOR(DORTests.PREFIX)

    def testBadPath(self):
        self.dor = dor.DOR("/bogus/mcbogus/")
        self.failUnless((self.dor.getCommunicatingDOMs() == []) and (self.dor.getPluggedDOMs() == []))
        
    def testCardScan(self):
        self.failUnless(len(self.dor.cards) == 2)

    def testPairScan(self):
        self.failUnless((len(self.dor.cards[0].pairs) == 4) and
                        (len(self.dor.cards[1].pairs) == 4))

    def testDOMScan(self):
        # Don't need to be exhaustive here
        self.failUnless((len(self.dor.cards[1].pairs[0].doms) == 2) and
                        (len(self.dor.cards[0].pairs[2].doms) == 2))

    def testAllCommunicating(self):
        cwds = [d.cwd() for d in self.dor.getCommunicatingDOMs()]
        cwds.sort()
        self.failUnless(cwds == ['00A', '00B', '01A', '01B'])
        
    def testCurrent(self):
        cur = self.dor.cards[0].pairs[1].current()       
        self.failUnless(cur == 101)

    def testVoltage(self):
        v = self.dor.cards[0].pairs[0].voltage()
        self.failUnless(math.fabs(v-89.124) < 0.001)

    def testIsPlugged(self):
        self.failUnless(self.dor.cards[0].pairs[1].isPlugged() and not self.dor.cards[1].pairs[3].isPlugged())

    def testIsPowered(self):
        self.failUnless(self.dor.cards[0].pairs[1].isPowered() and not self.dor.cards[1].pairs[3].isPowered())

    def testIsCommunicating(self):
        doms = [self.dor.getDOM('00A'), self.dor.getDOM('10B'), self.dor.getDOM('70A')]
        self.failUnless(doms[0].isCommunicating() and not doms[1].isCommunicating() and doms[2] is None)

    def testCommStats(self):
        cs = self.dor.getDOM('00A').commStats()
        cs1 = self.dor.getDOM('01A').commStats()
        self.failUnless((cs.rxbytes == 26288504) and (cs.nretxb == 0) and
                        (cs1.txacks == 26566) and (cs1.rxacks == 478))

    def testPwrCheck(self):
        pc = self.dor.cards[0].pairs[0].pwrCheck()
        self.failUnless((pc.card == 0) and (pc.pair == 0) and pc.plugged and
                        pc.current_lo_ok and pc.current_hi_ok and
                        pc.voltage_lo_ok and pc.voltage_hi_ok and pc.ok)

        pc = self.dor.cards[0].pairs[1].pwrCheck()
        self.failUnless((pc.card == 0) and (pc.pair == 1) and pc.plugged and
                        not pc.current_lo_ok and pc.current_hi_ok and
                        pc.voltage_lo_ok and pc.voltage_hi_ok and not pc.ok)

    def testPosition(self):
        dom = self.dor.getDOM('00A')
        self.assertEqual(dom.pos(), (2029, 2))

    def testDevice(self):
        dom = self.dor.getDOM('01B')
        self.assertEqual(dom.dev(), "/dev/dhc0w1dB")

    def testDORSerial(self):
        c = self.dor.cards[1]
        self.failUnless(c.serial() == 'R1B0628D05')

    def testNicknames(self):
        dom = self.dor.getDOM('00A')
        self.failUnless((dom.name() == 'Santa_Fe') and
                        (dom.omkey() == '2029-2') and
                        (dom.prodID() == 'TP5P0955'))

    def testFPGA(self):
        fpgastr = '''FPGA registers:
CTRL  0x40000000
GSTAT 0x030029c2
DSTAT 0x000010f0
TTSIC 0x0000ffff
RTSIC 0x000000ff
INTEN 0x00010000
DOMS  0x00000000
MRAR  0x00000000
MRTC  0x00000000
MWAR  0x00000000
MWTC  0x00000000
CURL  0xe19e8c14
DCUR  0x00000000
FLASH 0xff2e031c
DOMC  0x00000000
CERR  0x00000000
DCREV 0x00000024
FREV  0x09010471
'''
        self.assertEqual(self.dor.cards[1].fpgaRegs(), fpgastr)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DORTests)
    
def main():
    unittest.TextTestRunner(verbosity=2).run(suite())

if __name__ == '__main__':
    main()

