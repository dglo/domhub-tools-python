#!/usr/bin/env python
#
# flasher.py
#
# Simple iceboot interface to flash a DOM.
#
from __future__ import print_function
import sys
import time
import signal
import dor

# Fix me add command-line arguments
FLASHER_BRIGHTNESS = 127
FLASHER_WIDTH = 127
FLASHER_RATE_HZ = 610
FLASHER_MASK = 0xfff
FLASHER_TIME_SEC = 480

class InvalidDOMStateException(Exception):
    pass

class UnexpectedDOMResponse(Exception):
    pass

# Class for interfacing with a DOM in IceBoot
# FIX ME: make this more general and move it elsewhere
class IceBoot(object):
    PROMPT = '> '
    def __init__(self, dom):
        if dom.state() != "iceboot":
            raise InvalidDOMStateException('DOM %s is not in IceBoot!', dom.cwd())
        self.dom = dom
        self.dom.open()
        
    def send(self, s):
        self.dom.write(s+'\r')

    def expect(self, s=None):
        resp = self.dom.read().split('\r\n')
        if s is None:
            respOK = (resp[-1] == IceBoot.PROMPT) and (len(resp) == 2)
        else:
            respOK = (resp[-1] == IceBoot.PROMPT) and (resp[1] == s)
        if not respOK:
            print("DEBUG",s,resp)
            raise UnexpectedDOMResponse('Bad DOM response %s' % resp[1])
    
    def flasherSetup(self, brightness, width, mask, rate):    
        self.send("enableFB .")
        time.sleep(1)
        self.expect("0")
        self.send("%d setFBbrightness" % brightness)
        self.expect()
        self.send("%d setFBwidth" % width)
        self.expect()
        self.send("%d setFBenables" % mask)
        self.expect()
        self.send("%d setFBrate" % rate)
        self.expect()

    def flasherStart(self):
        self.send("startFBflashing")
        self.expect()

    def flasherStop(self):
        self.send("stopFBflashing")
        self.expect()

    def flasherShutdown(self):
        self.send("disableFB")
        self.expect()

#--------------
# Courtesy of StackExchange

class GracefulKiller(object):
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True

#--------------

def main(): 
    # Get command line arguments
    if len(sys.argv) < 2:
        print("Usage: %s CWD <CWD ...>" % sys.argv[0])
        sys.exit(0)

    killer = GracefulKiller()

    # Get DOR interface to the DOMs
    dorDriver = dor.DOR()
    doms = []
    cwds = set([cwd.upper() for cwd in sys.argv[1:]])
    for cwd in cwds:
        # Check that other DOM on pair is not requested
        cw = cwd[0:2]
        if cwd[2] == 'A':
            cwdOther = cw+'B'
        else:
            cwdOther = cw+'A'
        if cwdOther in cwds:
            print("Error: cannot flash both DOMs on a wire pair, exiting!")
            sys.exit(-1)

        dom = dorDriver.getDOM(cwd)
        if dom is None:
            print("Error: couldn't communicate with DOM %s, skipping!" % cwd)
        else:
            doms.append(dom)

    if len(doms) == 0:
        print("Error: no DOMs left to flash, exiting.")
        sys.exit(-1)

    # Get IceBoot interface for each DOM
    iceboots = []
    for dom in doms:
        try:
            iceboots.append(IceBoot(dom))
        except InvalidDOMStateException:
            print("Error: DOM %s is not in IceBoot, skipping!" % dom.cwd())

    # Now start the flasher action
    print("Setting up flasherboard on %d DOM(s)..." % len(iceboots))
    for ib in iceboots:
        ib.flasherSetup(FLASHER_BRIGHTNESS, FLASHER_WIDTH, FLASHER_MASK, FLASHER_RATE_HZ)
            
    print("*** FLASHING %d DOM(s) FOR %d SECONDS ***" % (len(iceboots), FLASHER_TIME_SEC))
    for ib in iceboots:
        ib.flasherStart()

    flashTime = 0
    while (flashTime < FLASHER_TIME_SEC) and not killer.kill_now:
        time.sleep(1)
        flashTime = flashTime+1

    print("Stopping flashing and shutting down flasherboard...")
    for ib in iceboots:
        ib.flasherStop()
        ib.flasherShutdown()

if __name__ == "__main__":
    main()
