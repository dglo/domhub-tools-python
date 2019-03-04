#!/usr/bin/env python

import unittest
import math
import dor
import os
import zmq
import threading
import subprocess
import json
import time
import hubmonitools

# Dummy LiveControl ZMQ listener on localhost
class ServerThread(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PULL)
        self.socket.bind("tcp://*:%s" % port)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.keepAlive = True
        self.data = []
        
    def run(self):
        while self.keepAlive:            
            socks = dict(self.poller.poll(100)) 
            if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                msg = self.socket.recv()
                self.data.append(json.loads(msg))

# HubMoni tests
class HubMoniTests(unittest.TestCase):
    CONFIGFILE = os.path.dirname(os.path.abspath(__file__))+"/hubmoni.config"
    ROOTDIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__))+"/..")

    def setUp(self):
        self.config = hubmonitools.HubMoniConfig(HubMoniTests.CONFIGFILE)
        server = ServerThread(self.config.ZMQ_PORT)
        server.start()
        time.sleep(1)

        # Launch hubmoni
        # Hack to fix up PYTHONPATH
        cmd = ["export PYTHONPATH=%s ; ./bin/hubmoni -c %s" % 
               (HubMoniTests.ROOTDIR, HubMoniTests.CONFIGFILE) ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             cwd=HubMoniTests.ROOTDIR, shell=True)
        if p:
            stdout, stderr = p.communicate()

        self.data = server.data
        server.keepAlive = False
        # Wait for thread to exit
        time.sleep(2)
        
    def testHubMoniAlert(self):
        # The moniDOMs tests validate the main content
        # Here we just check that they are sent via ZMQ and
        # some of the configuration options
        alerts = [a for a in self.data if a["varname"] == "alert"]
        self.failUnless(len(alerts) == 1)
        a = alerts[0]
        # The test config file should override this
        self.failUnless((a["value"]["notifies"][0]["receiver"] == "bogus@bogus.com") and
                        (a["value"]["pages"]) and
                        (a["service"] == "hubmoni"))

    def testHubMoniRecord(self):
        # Check that we received the correct number of records
        # moniDOMs tests validate the content
        pwrstat_recs = [r for r in self.data if "pwrstat" in r["varname"]]
        comstat_recs = [r for r in self.data if "comstat" in r["varname"]]
        cabling_recs = [r for r in self.data if "cabling" in r["varname"]]
        self.failUnless((len(pwrstat_recs) == (self.config.MAX_LOOP_CNT*2)) and
                        (len(comstat_recs) == (self.config.MAX_LOOP_CNT-1)*4) and
                        (len(cabling_recs) == (self.config.MAX_LOOP_CNT)))

class HubMoniPauseTests(unittest.TestCase):

    def setUp(self):
        # Pause hubmoni
        cmd = ["export PYTHONPATH=%s ; ./bin/hubmoni -c %s -p 1" % 
               (HubMoniTests.ROOTDIR, HubMoniTests.CONFIGFILE) ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             cwd=HubMoniTests.ROOTDIR, shell=True)

        self.config = hubmonitools.HubMoniConfig(HubMoniTests.CONFIGFILE)
        server = ServerThread(self.config.ZMQ_PORT)
        server.start()
        time.sleep(1)

        # Launch hubmoni
        # Hack to fix up PYTHONPATH
        cmd = ["export PYTHONPATH=%s ; ./bin/hubmoni -c %s" % 
               (HubMoniTests.ROOTDIR, HubMoniTests.CONFIGFILE) ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             cwd=HubMoniTests.ROOTDIR, shell=True)
        if p:
            stdout, stderr = p.communicate()

        self.data = server.data
        server.keepAlive = False
        # Wait for thread to exit
        time.sleep(2)

    def tearDown(self):
        # Remove any existing pause file
        try:
            os.unlink("/tmp/hubmoni.pause")
        except:
            pass

    def testPausedAlert(self):
        alerts = [a for a in self.data if a["varname"] == "alert"]
        self.failUnless(len(alerts) == 0)

class HubMoniModeTests(unittest.TestCase):
    CONFIGFILE = os.path.dirname(os.path.abspath(__file__))+"/hubmoni.config"
    ROOTDIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__))+"/..")

    def setUp(self):
        self.config = hubmonitools.HubMoniConfig(HubMoniTests.CONFIGFILE)
        server = ServerThread(self.config.ZMQ_PORT)
        server.start()
        time.sleep(1)

        # Launch hubmoni
        # Hack to fix up PYTHONPATH
        cmd = ["export PYTHONPATH=%s ; ./bin/hubmoni -c %s -s -v" % 
               (HubMoniTests.ROOTDIR, HubMoniTests.CONFIGFILE) ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             cwd=HubMoniTests.ROOTDIR, shell=True)
        if p:
            stdout, stderr = p.communicate()

        self.data = server.data
        self.stdout = stdout

        server.keepAlive = False
        # Wait for thread to exit
        time.sleep(2)
        
    def testHubMoniRecord(self):
        # We are in simulate and verbose mode, meaning the output
        # should be on stdout but not in the ZMQ data
        self.failUnless(len(self.data) == 0)
        # Don't fully parse the not-quite JSON stdout
        # Just make sure it's got stuff in it
        self.failUnless(("pwrstat" in self.stdout) and
                        ("comstat" in self.stdout) and
                        ("cabling" in self.stdout))
