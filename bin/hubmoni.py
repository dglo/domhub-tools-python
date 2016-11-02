#!/usr/bin/env python
#
# DOMHub monitoring 2.0
#
# Collect DOR communications statistics and voltage/current.
#  - Monitor DOMs for changes and report to IceCube Live.
#  - Runs forever (CTRL-C to exit).
#
# John Kelley
# jkelley@icecube.wisc.edu
#-------------------------------------------------------------------

import time
import sys
import os
import re
import datetime
import signal
import atexit
import subprocess
import logging
import logging.handlers
from optparse import OptionParser
import json
import zmq

import dor
import hubmonitools

#-------------------------------------------------------------------
# Program files
PIDFILE = "/tmp/hubmoni.pid"
LOGFILE = "/tmp/hubmoni.log"

# Hub configuration file
HUBCONFIG = os.environ['HOME']+"/hubConfig.json"

# Default monitoring period, in seconds
MONI_PERIOD = 30

# Default monitoring reporting period, in seconds
MONI_REPORT_PERIOD = 3600

# How long to wait before reattempting 
# socket connection, in seconds
SOCKET_WAIT = 60

# Default ZMQ listener for reporting
ZMQ_HOSTNAME = "expcont"
ZMQ_PORT = 6668

#-------------------------------------------------------------------
def keepConnecting(s, addr, logger):
    while True:
        try:
            s.connect(addr)
        except zmq.ZMQError:
            logger.warn("couldn't connect to socket at %s" % addr)
            logger.warn("trying again in a minute...")
            time.sleep(SOCKET_WAIT)
        else:
            logger.info("Connected to ZMQ listener at %s" % addr)
            return

#-------------------------------------------------------------------
def main():

    # Parse command line arguments
    parser = OptionParser()
    parser.add_option("-H", "--host", dest = "hostname",
                      help = "monitoring listener hostname", default = ZMQ_HOSTNAME)
    parser.add_option("-p", "--port", dest = "port", type="int",
                      help = "monitoring listener port number", default = ZMQ_PORT)
    parser.add_option("-d", "--dor", dest = "dor_prefix", default = "/proc/driver/domhub",
                      help = "DOR procfile prefix")
    parser.add_option("-c", "--config", dest="hubconfig_file",
                      help="hub configuration file", default=HUBCONFIG)    
    parser.add_option("-t", "--time", dest = "moni_period", type="float",
                      help = "time between monitoring checks, in seconds", default = MONI_PERIOD)
    parser.add_option("-r", "--report", dest = "report_period", type="float",
                      help = "time between monitoring reports, in seconds", default = MONI_REPORT_PERIOD)
    parser.add_option("-s", "--simulate", action="store_true", dest="simulate",
                      help="don't send JSON data", default=False)    
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="print monitoring records to STDOUT", default=False)
    (options, args) = parser.parse_args()

    hostname = options.hostname
    port = options.port
    dor_prefix = options.dor_prefix
    simulate = options.simulate
    verbose = options.verbose
    report_period = options.report_period
    moni_period = options.moni_period
    hubconfig_file = options.hubconfig_file
    
    #-------------------------------------------------------------------
    # Before doing anything, create a PID file so we only run this once
    pid = str(os.getpid())

    is_running = False
    if os.path.isfile(PIDFILE):
        # Check if PID is still running
        oldpid = int(open(PIDFILE).read())
        try:
            os.kill(oldpid, 0)
        except OSError:
            # It must have been left lying around
            if verbose:
                sys.stderr.write("Old lockfile found but process is dead, removing.\n")
            os.unlink(PIDFILE)
        else:
            is_running = True

    if is_running:
        if verbose:
            sys.stderr.write("%s appears to be running already, exiting.\n" % sys.argv[0])
        sys.exit(0)
    else:
        file(PIDFILE, 'w').write(pid)
    
    # Register CTRL-C
    signal.signal(signal.SIGINT, lambda signal, frame: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda signal, frame: sys.exit(0))

    # Clean up at exit
    atexit.register(lambda : os.unlink(PIDFILE))

    #-------------------------------------------------------------------
    # Set up logging
    logger = logging.getLogger('hubMoniLogger')

    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Rotate through files
    handler = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=100000, backupCount=3)

    # Set formatting of log messages
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    
    # Add the handler
    logger.addHandler(handler)
    
    #-------------------------------------------------------------------
    # Try to open the 0mq socket to the moni listener
    context = zmq.Context()
    s = context.socket(zmq.PUSH)
    addr = "tcp://%s:%d" % (hostname, port)
    if not simulate:
        keepConnecting(s,addr,logger)
    else:
        logger.info("SIMULATION MODE: no data will be sent")

    # Register SIGINT to exit
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))
    
    # DOR driver interface
    dorDriver = dor.DOR(prefix = dor_prefix)
    # Check that we've at least got some cables plugged in
    if (len(dorDriver.getAllDOMs()) == 0):
        logger.error("no DOMs found at all; exiting!")
        sys.exit(-1)    

    # Configuration file for hub alerts
    if not os.path.isfile(hubconfig_file):
        logger.error("Couldn't open hub configuration file %s; exiting!" % hubconfig_file)
        sys.exit(-1)

    hubconfig = hubmonitools.HubConfig(hubconfig_file)
    if not simulate:
        hub,cluster = hubmonitools.getHostCluster()
    else:
        hub,cluster = hubmonitools.getHostCluster("ichub29.spts.icecube.wisc.edu")
    
    #-------------------------------------------------------------------
    # Loop forever, looking for communicating DOMs and reporting moni records    
    lastSentTime = datetime.datetime.utcnow()
    doms = {}
    activeAlerts = []
    
    while True:
        commDOMs = dorDriver.getCommunicatingDOMs()
        if not commDOMs:
            logger.warn("no communicating DOMs; will keep trying");

        # Get a new monitoring snapshot for all communicating DOMs
        # The latest monitoring record is at the end
        for dom in commDOMs:
            cwd = dom.cwd()
            if cwd in doms:
                doms[cwd].append(hubmonitools.moniDOMs.HubMoniDOM(dom, hub))
            else:
                doms[cwd] = [ hubmonitools.moniDOMs.HubMoniDOM(dom, hub) ]
            #print "moniDOMs[",cwd,"]:",doms[cwd]

        # Check for any alerts and send them
        newAlerts = hubmonitools.moniDOMs.moniAlerts(dorDriver, hubconfig, hub, cluster)

        # Clear alerts that have gone away
        for alert in activeAlerts:
            if alert not in newAlerts:
                activeAlerts.remove(alert)

        # Send new alerts that are not active
        for alert in newAlerts:
            if alert not in activeAlerts:
                if verbose:
                    print alert
                if not simulate:
                    try:
                        s.send_json(alert, flags=zmq.NOBLOCK)
                        logger.info("sent %dB moni alert" % (len(json.dumps(alert))))
                    except zmq.ZMQError:
                        logger.error("couldn't send JSON to socket.", exc_info=sys.exc_info())
                        keepConnecting(s,addr,logger)
                        
                activeAlerts.append(alert)

        # If it's time, create the monitoring records and send them
        td = datetime.datetime.utcnow() - lastSentTime
        secSinceLastMoni = td.seconds + (td.days * 24 * 3600)
        if (secSinceLastMoni >= report_period):

            # Construct monitoring records and send them
            recs = hubmonitools.moniDOMs.moniRecords(doms)            
            for rec in recs:
                if verbose:
                    print rec

                if not simulate:
                    try:
                        s.send_json(rec, flags=zmq.NOBLOCK)
                        logger.info("sent %dB moni record" % (len(json.dumps(rec))))
                    except zmq.ZMQError:
                        logger.error("couldn't send JSON to socket.", exc_info=sys.exc_info())
                        keepConnecting(s,addr,logger)

            
            # Shift DOM monitoring snapshot to latest
            for cwd in doms:
                doms[cwd] = doms[cwd][-1:]

            lastSentTime = datetime.datetime.utcnow()
            
        time.sleep(moni_period)

if __name__ == "__main__":
    main()
    
