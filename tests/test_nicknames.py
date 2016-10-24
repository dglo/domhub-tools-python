#!/usr/bin/env python
import unittest
import os
import nicknames

class NicknamesTests(unittest.TestCase):

    # 778fa3a8e2bf UL9P6630 Albino_Shouting_Gorilla (84, 27)
    PREFIX = os.path.dirname(os.path.abspath(__file__))+"/../resources/"
    
    def setUp(self):
        self.nicks = nicknames.Nicknames(nicknameFile=NicknamesTests.PREFIX+"nicknames.txt")

    def testName(self):
        self.failUnless((self.nicks.getDOMName('778fa3a8e2bf') == "Albino_Shouting_Gorilla") and
                        (self.nicks.getDOMName('deadbeefdead') == None))

    def testPosition(self):
        self.failUnless((self.nicks.getDOMPosition('778fa3a8e2bf') == (84, 27)) and
                        (self.nicks.getDOMPosition('deadbeefdead') == None))

    def testDOMID(self):
        self.failUnless((self.nicks.getDOMID('778fa3a8e2bf') == 'UL9P6630') and
                        (self.nicks.getDOMID('deadbeefdead') == None))        

    def testFindMBID(self):
        self.failUnless((self.nicks.findMBID('778fa3a8e2bf') == '778fa3a8e2bf') and
                        (self.nicks.findMBID((84, 27)) == '778fa3a8e2bf') and
                        (self.nicks.findMBID('Albino_Shouting_Gorilla') == '778fa3a8e2bf') and
                        (self.nicks.findMBID('UL9P6630') == '778fa3a8e2bf') and
                        (self.nicks.findMBID('garbage') == None))

    def testException(self):
        try:
            bogus = nicknames.Nicknames(nicknameFile="bogus.txt")
        except nicknames.NicknamesException:
            return
        self.fail()

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(NicknamesTests)

def main():
    unittest.TextTestRunner(verbosity=2).run(suite())

if __name__ == '__main__':
    main()
