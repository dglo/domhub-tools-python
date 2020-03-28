#!/usr/bin/env python
#
# nicknames.py
#

# Grab DOM positions, names, and DOM id out of the nicknames file
# Return various dictionaries keyed on mainboard ID
#
from __future__ import print_function
import sys
import os

NICKPATHS = ["./resources", "/mnt/data/testdaq", ".", os.environ['HOME']]
NICKFILE = "nicknames.txt"

class NicknamesException(Exception): pass

class Nicknames:
    
    def __init__(self, nicknameFile=NICKFILE):
        self.posDict = {}
        self.idDict = {}
        self.nameDict = {}
        self.initializeDicts(nicknameFile)
        
    def initializeDicts(self, filename):
        f = None
        for path in NICKPATHS:
            try:
                f = open(os.path.join(path, filename), "r")
                break
            except EnvironmentError:
                pass

        if f is None:
            raise NicknamesException("Couldn't find nicknames file for MBID mapping.")

        # Skip header
        f.readline() 
        for line in f.readlines():
            vals = line.split()
            if len(vals) >= 4:
                mbid = vals[0]
                name = vals[2]
                pos = vals[3]
                id = vals[1]
                self.nameDict[mbid] = name.strip()
                self.idDict[mbid] = id
                (string, dom) = pos.split("-")
                try:
                    self.posDict[mbid] = ( int(string), int(dom) )
                except:
                    pass
        f.close()
        
    def getDOMPosition(self, mbid):
        if mbid in self.posDict:
            return self.posDict[mbid]
        else:
            return None

    def getDOMName(self, mbid):
        if mbid in self.nameDict:
            return self.nameDict[mbid]
        else:
            return None
    
    def getDOMID(self, mbid):        
        if mbid in self.idDict:
            return self.idDict[mbid]
        else:
            return None
        
    def findMBID(self, dom):
        # Is this a mainboard ID already?
        if dom in self.nameDict:
            return dom
        for mbid in self.nameDict:
            if dom == self.nameDict[mbid]:
                return mbid
            if (mbid in self.posDict) and (dom == self.posDict[mbid]):
                return mbid    
            if (mbid in self.idDict) and (dom == self.idDict[mbid]):
                return mbid
        return None

def main():    
    if len(sys.argv) != 2:
        print("Usage: %s <dom>" % sys.argv[0])
        sys.exit(0)
    dom = sys.argv[1]
    nicks = Nicknames()
    mbid = nicks.findMBID(dom)
    if mbid is not None:
        print(mbid, nicks.getDOMID(mbid), nicks.getDOMName(mbid), nicks.getDOMPosition(mbid))
    
if __name__ == "__main__":
    main()

    
