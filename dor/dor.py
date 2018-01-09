#!/usr/bin/env python

"""
DOR Driver interface class, v2
"""

import os
import sys
import string
import re
import subprocess
import signal
import threading
from time import sleep

import nicknames

MAXCARDS = 8
MAXPAIRS = 4
DOMLABELS = ['A', 'B']

DEVPATH = "/dev"
DEV_BLOCKSIZE = 4092

DOMAPP_REQUEST_ID  = bytearray(b'\x01\x0a\x00\x00\x0d\x0a\x00\x00')
DOMAPP_ID_RESPONSE = bytearray(b'\x01\x0a\x00\x0c\x0d\x0a\x00\x01')
DOMAPP_ID_RESPONSE_LEN = 20

#--------------------------------------------------------------------------

class DOMStateThread(threading.Thread):
    def __init__(self, dom):
        threading.Thread.__init__(self)
        self.dom = dom
        self.state = "busy"

    def __str__(self):
        return self.dom.cwd()+" "+self.state

    def run(self):
        self.state = self.dom.state()

#--------------------------------------------------------------------------

class DOR:

    def __init__(self, prefix=os.path.join("/", "proc", "driver", "domhub")):
        self.prefix = prefix
        self.nicks = nicknames.Nicknames()
        self.scan()

    def __getitem__(self, key):
        for p in self.cards:
            if p.id == key:
                return p
        return None
            
    def path(self):
        return self.prefix

    def scan(self):
        self.cards = [ ]
        for i in xrange(MAXCARDS):
            c = Card(i, self)
            if os.path.exists(c.path()):
                self.cards.append(c)

    def getDOM(self, cwd):
        try:
            c = int(cwd[0])
            w = int(cwd[1])
            d = cwd[2].upper()
            return self[c][w][d]
        except:
            return None

    def getAllCWDs():
        """Return a list of all possible DOM CWDs on a hub"""
        return ["%01d%01d%s" % (card, pair, dom)
                for card in xrange(MAXCARDS)
                for pair in xrange(MAXPAIRS)
                for dom in DOMLABELS]

    def getAllDOMs(self):
        self.scan()
        return [d for c in self.cards
                for w in c.pairs
                for d in w.doms]

    def getPluggedDOMs(self):
        try:
            doms = [d for d in self.getAllDOMs() if d.pair.isPlugged()]
        except IOError:
            doms = []
        return doms
    
    def getCommunicatingDOMs(self):
        try:
            doms = [d for d in self.getAllDOMs() if d.isCommunicating()]
        except IOError:
            doms = []
        return doms

    def getDOMStates(self, doms):
        s = {}
        # Create threads for each DOM to check
        threads = []
        for dom in doms:
            t = DOMStateThread(dom)
            t.start()
            threads.append(t)

         # Join, but using a timeout for busy DOMs
        for t in threads:
            t.join(3)
            s[t.dom.cwd()] = t.state

        return s

class Card:
    """A class/struct to hold information about a DOR card.
    """
    def __init__(self, id, driver):
        self.id    = id
        self.driver = driver
        self.pairs = [ ]
        self.scan()
        
    def __int__(self):
        return self.id

    def __getitem__(self, key):
        for p in self.pairs:
            if p.id == key:
                return p
        return None

    def path(self):        
        return os.path.join(self.driver.path(), "card%d" % self.id)

    def scan(self):
        for i in xrange(MAXPAIRS):
            p = WirePair(i, self)
            if os.path.exists(p.path()):
                self.pairs.append(p)
                
    def fpgaRegs(self):
        f = file(os.path.join(self.path(), "fpga"),"r")
        return f.read()

    def revision(self):
        f = file(os.path.join(self.path(), "rev"),"r")
        return int(f.read())

    def serial(self):
        f = file(os.path.join(self.path(), "test-log"))
        m = re.compile("Serial number: (\S+)").match(f.read())
        if m is None: return ""
        return m.group(1)


class WirePair:
    """A class/struct to hold information about a DOR card.
    """
    MAXDOMS = 2
    def __init__(self, id, card):
        self.id    = id
        self.doms = [ ]
        self.card = card
        self.scan()
        
    def __int__(self):
        return self.id

    def __getitem__(self, key):
        for p in self.doms:
            if p.id == key:
                return p
        return None

    def path(self):        
        return os.path.join(self.card.path(), "pair%d" % self.id)

    def scan(self):
        for i in xrange(WirePair.MAXDOMS):
            d = DOM(DOMLABELS[i], self)
            if os.path.exists(d.path()):
                self.doms.append(d)

    def current(self):
        f = file(os.path.join(self.path(), "current"))        
        m = re.compile(".+ current is (\d+) mA").match(f.read())
        if m is None: return -1
        return int(m.group(1))        

    def voltage(self):
        f = file(os.path.join(self.path(), "voltage"))
        m = re.compile(".+ voltage is ([0-9.]+) Volts").match(f.read())
        if m is None: return -1
        return float(m.group(1))        

    def isPlugged(self):
        f = file(os.path.join(self.path(), "is-plugged"))
        s = f.read()
        return (len(s) > 0) and (s.find("not") < 0)

    def isPowered(self):
        f = file(os.path.join(self.path(), "pwr"))
        return (f.read().find("on") >= 0)    

    def pwrCheck(self):
        f = file(os.path.join(self.path(), "pwr_check"))
        return PwrCheck(f.read().rstrip())


class DOM:
    """ Class to interface with DOMs in the DOR driver tree """
    def __init__(self, id, pair):
        self.id = id.upper()
        self.pair = pair
        self.card = pair.card
        self.f = None

    def path(self):        
        return os.path.join(self.pair.path(), "dom"+self.id)

    def dev(self):
        return DEVPATH+"/dhc%dw%dd%s" % (self.card, self.pair, self.id)

    def isCommunicating(self):
        f = file(os.path.join(self.path(), "is-communicating"))
        s = f.read()
        return (len(s) > 0) and (s.find("NOT") < 0)

    def isNotConfigboot(self):
        f = file(os.path.join(self.path(), "is-not-configboot"))
        s = f.read()
        return (len(s) > 0) and (s.find("is out") >= 0)
        
    def mbid(self):
        f = file(os.path.join(self.path(), "id"))
        m = re.compile(".+ ID is ([0-9a-f]+)").match(f.read())
        if m is not None:
            return m.group(1)

    def cwd(self):
        return "%s%s%s" % (self.pair.card.id, self.pair.id, self.id)

    def commStats(self):
        f = file(os.path.join(self.path(), "comstat"))
        return CommStats(f.read())

    def pos(self):
        nicks = self.pair.card.driver.nicks
        mbid = self.mbid()
        if (nicks is not None) and (mbid is not None):
            return nicks.getDOMPosition(mbid)        

    def omkey(self):
        p = self.pos()
        if p is not None:
            return "%d-%d" % (p[0], p[1])
        else:
            return "-"

    def name(self):
        nicks = self.pair.card.driver.nicks
        mbid = self.mbid()
        if (nicks is not None) and (mbid is not None):
            return nicks.getDOMName(mbid)
        else:
            return "-"        

    def prodID(self):
        nicks = self.pair.card.driver.nicks
        mbid = self.mbid()
        if (nicks is not None) and (mbid is not None):
            return nicks.getDOMID(mbid)
        else:
            return "-"

    def quad(self):
        '''Return (by convention only) patch panel quad for this CWD'''
        return self.card.id*2 + self.pair.id/2 + 2

    def port(self):
        '''Network port with default dtsx settings'''
        p = 5001 + (self.card.id*8) + (self.pair.id*2)
        if (self.id == 'A'):
            p += 1
        return p

    def write(self, d):
        os.write(self.f, d)

    def read(self):
        done = False
        resp = ""
        sleep(0.2)
        while not done:
            try:
                resp += os.read(self.f, DEV_BLOCKSIZE)
                sleep(0.1)
            except:
                done = True
        return resp

    def open(self):
        if self.f is None:
            try:
                self.f = os.open(self.dev(), os.O_RDWR | os.O_NONBLOCK)
            except OSError:
                self.f = None
        
    def close(self):
        if self.f is not None:
            os.close(self.f)
        self.f = None

    def state(self):
        state = "unknown"
        if not self.isCommunicating():
            return "nocomm"

        self.open()
        if self.f is None:
            return "error"

        self.write(DOMAPP_REQUEST_ID)
        resp = self.read()

        # Check for correct domapp response
        if (len(resp) == DOMAPP_ID_RESPONSE_LEN) and \
                (bytearray(resp[0:8]) == DOMAPP_ID_RESPONSE):
            state = "domapp"
        else:
            # Now check for iceboot / configboot
            self.write('\r')
            resp = self.read()
            if "> " in resp:
                state = "iceboot"
            elif "# " in resp:
                state = "configboot"

        self.close()
        return state

class InvalidPwrCheckException(Exception):
    pass

class PwrCheck:
    """
    Class to parse and store wire pair power check string
    """
    PCPAT = """Card\s*(\d)\s*pair\s*(\d)\s*pwr check:\s*\
plugged\((\w+)\)\s*current\((\w+),\s*(\w+)\)\s*voltage\((\w+),\s*(\w+)\)"""    

    def __init__(self, txt):
        if txt is None:
            raise InvalidPwrCheckException('No string argument supplied!')
        self.text = txt
        m = re.search(PwrCheck.PCPAT, txt)
        if not m:
            raise InvalidPwrCheckException('Invalid pwrcheck text! "%s"' % txt)
        groups = list(m.groups())
        self.card = int(groups.pop(0))
        self.pair = int(groups.pop(0))
        self.plugged = (groups.pop(0) == 'ok')
        self.current_lo_ok = (groups.pop(0) == 'ok')
        self.current_hi_ok = (groups.pop(0) == 'ok')
        self.voltage_lo_ok = (groups.pop(0) == 'ok')
        self.voltage_hi_ok = (groups.pop(0) == 'ok')
        self.ok = self.plugged and \
                  self.current_lo_ok and self.current_hi_ok and \
                  self.voltage_lo_ok and self.voltage_hi_ok
        
class InvalidComstatException(Exception):
    pass

class CommStats:
    """
    Class to parse and store comstat values and to highlight changes in same
    """
    # TEMP FIX ME: NACKQ can be negative from the driver, this is a bug in 
    # dor-driver
    CSPAT = """(?msx)\
/dev/dhc(\d)w(\d)d(\w)\s*
RX:\s*(\d+)B,\s*MSGS=(\d+)\s*NINQ=(\d+)\s*PKTS=(\d+)\s*ACKS=(\d+)\s*
\s*BADPKT=(\d+)\s*BADHDR=(\d+)\s*BADSEQ=(\d+)\s*NCTRL=(\d+)\s*NCI=(\d+)\s*NIC=(\d+)\s*
TX:\s*(\d+)B,\s*MSGS=(\d+)\s*NOUTQ=(\d+)\s*RESENT=(\d+)\s*PKTS=(\d+)\s*ACKS=(\d+)\s*
NACKQ=(-?\d+)\s*NRETXB=(\d+)\s*RETXB_BYTES=(\d+)\s*NRETXQ=(\d+)\s*NCTRL=(\d+)\s*NCI=(\d+)\s*NIC=(\d+)\s*
NCONNECTS=(\d+)\s*NHDWRTIMEOUTS=(\d+)\s*OPEN=(\S+)\s*CONNECTED=(\S+)\s*
RXFIFO=(.+?)\ TXFIFO=(.+?)\ DOM_RXFIFO=(\S+)"""
    
    def __init__(self, txt):
        if txt is None:
            raise InvalidComstatException('No string argument supplied!')
        m = re.search(CommStats.CSPAT, txt)
        if not m:
            raise InvalidComstatException('Invalid comstats text!  "%s"' % txt)
        groups = list(m.groups())
        self.card = int(groups.pop(0))
        self.pair = int(groups.pop(0))
        self.dom = groups.pop(0)
        self.rxbytes = long(groups.pop(0))
        self.rxmsgs = long(groups.pop(0))
        self.inq = int(groups.pop(0))
        self.rxpkts = long(groups.pop(0))
        self.rxacks = long(groups.pop(0))
        self.badpkt = int(groups.pop(0))
        self.badhdr = int(groups.pop(0))
        self.badseq = int(groups.pop(0))
        self.rxctrl = int(groups.pop(0))
        self.rxci = long(groups.pop(0))
        self.rxic = long(groups.pop(0))
        self.txbytes = long(groups.pop(0))
        self.txmsgs = long(groups.pop(0))
        self.outq = int(groups.pop(0))
        self.resent = int(groups.pop(0))
        self.txpkts = long(groups.pop(0))
        self.txacks = long(groups.pop(0))
        self.nackq = int(groups.pop(0))
        self.nretxb = int(groups.pop(0))
        self.retxb_bytes = int(groups.pop(0))
        self.nretxq = int(groups.pop(0))
        self.nctrl = int(groups.pop(0))
        self.txci = long(groups.pop(0))
        self.txic = long(groups.pop(0))
        self.nconnects = int(groups.pop(0))
        self.hwtimeouts = int(groups.pop(0))
        self.open = (groups.pop(0)=='true') and True or False
        self.connected = (groups.pop(0)=='true') and True or False
        self.rxfifo = groups.pop(0)
        self.txfifo = groups.pop(0)
        self.dom_rxfifo = groups.pop(0)
