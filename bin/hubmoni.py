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
import pkg_resources

import dor
import hubmonitools

#-------------------------------------------------------------------
# Hubmoni internal file locations
PIDFILE = "/tmp/hubmoni.pid"
LOGFILE = "/tmp/hubmoni.log"
PAUSEFILE = "/tmp/hubmoni.pause"

# Default hubmoni configuration file
HUBMONICONFIG = os.environ['HOME']+"/hubmoni.config"

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

def getUptime():
    uptime = -1
    try:
        with open("/proc/uptime", "r") as f:
            vals = f.readline().split()
            uptime = float(vals[0])
    except IOError:
        pass
    return uptime

def getVersion():
    # Would be nice not to hard-code package name here
    return pkg_resources.get_distribution('domhub-tools-python').version

#-------------------------------------------------------------------
# Alert pause file handling

def createPauseFile(pause_time):
    with open(PAUSEFILE, "w") as f:
        pause_to = datetime.datetime.now()+datetime.timedelta(minutes=pause_time)
        f.write(datetime.datetime.strftime(pause_to, "%Y-%m-%d %H:%M:%S.%f"))
    return

def checkPauseFile():
    paused = False
    if os.path.isfile(PAUSEFILE):
        with open(PAUSEFILE, "r") as f:
            pause_to_str = f.readline()
        pause_to = datetime.datetime.strptime(pause_to_str, "%Y-%m-%d %H:%M:%S.%f")
        paused = (datetime.datetime.now() < pause_to)
    return paused

#-------------------------------------------------------------------
def main():

    # Parse command line arguments
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="config_file",
                      help="configuration file", default=HUBMONICONFIG)
    parser.add_option("-s", "--simulate", action="store_true", dest="simulate",
                      help="simulation mode (don't send ZMQ)", default=False)
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="print monitoring records to STDOUT", default=False)
    parser.add_option("-p", "--pause",  type="int", dest="pause_time",
                      help="pause alerts for <#> minutes")
    (options, args) = parser.parse_args()

    # Read configuration file
    config = hubmonitools.HubMoniConfig(options.config_file)

    # Command-line only options
    simulate = options.simulate
    verbose = options.verbose

    # Check that pause time is sane
    pause_time = options.pause_time
    if (pause_time is not None) and (pause_time < 0) or (pause_time > config.MAX_PAUSE_TIME):
        sys.stderr.write("Error: pause time must be between 0 and %d minutes, exiting.\n" \
                             % pause_time)
        sys.exit(-1)
    
    #-------------------------------------------------------------------
    # Before starting monitoring, create a PID file so we only run this once
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

    # If we're already running, check to see if the user has requested 
    # that we pause alerts for a certain time
    if is_running:
        if pause_time is None:
            if verbose:
                sys.stderr.write("%s appears to be running already, exiting.\n" % sys.argv[0])
        else:
            # Create pause file
            sys.stdout.write("Pausing alerts for %d minutes...\n" % pause_time)
            createPauseFile(pause_time)
        sys.exit(0)
    else:
        if pause_time is None:
            file(PIDFILE, 'w').write(pid)
        else:
            sys.stderr.write("Pause requested but %s not running, existing.\n" % sys.argv[0])
            sys.exit(-1)
    
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
    # Log startup message
    logger.info("hubmoni %s" % getVersion())
    
    #-------------------------------------------------------------------
    # Try to open the 0mq socket to the moni listener
    context = zmq.Context()
    s = context.socket(zmq.PUSH)
    addr = "tcp://%s:%d" % (config.ZMQ_HOSTNAME, config.ZMQ_PORT)
    if not simulate or not verbose:
        keepConnecting(s,addr,logger)
    else:
        logger.info("SIMULATION MODE: data sent only if verbose=False")

    # Register SIGINT to exit
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))
    
    # DOR driver interface
    dorDriver = dor.DOR(prefix = config.DOR_PREFIX)
    # Check that we've at least got some cables plugged in
    if (len(dorDriver.getAllDOMs()) == 0):
        logger.error("no DOMs found at all; exiting!")
        sys.exit(-1)    

    # Configuration file for hub alerts
    if not os.path.isfile(config.HUBCONFIG):
        logger.error("Couldn't open hub configuration file %s; exiting!" % config.HUBCONFIG)
        sys.exit(-1)

    hubconfig = hubmonitools.HubConfig(config.HUBCONFIG)
    if not simulate:
        hub,cluster = hubmonitools.getHostCluster()
    else:
        hub,cluster = hubmonitools.getHostCluster("ichub29.spts.icecube.wisc.edu")
    
    #-------------------------------------------------------------------
    # Loop forever, looking for communicating DOMs and reporting moni records    
    lastSentTime = datetime.datetime.utcnow()
    mDOMs = {}
    mDOMsPrev = {}
    activeAlerts = []
    newAlerts = []
    simLoop = 0
    
    while True:
        commDOMs = dorDriver.getCommunicatingDOMs()
        if not commDOMs:
            logger.warn("no communicating DOMs; will keep trying");

        # Get a new monitoring snapshot for all communicating DOMs
        # Exclude DOMs in configboot, we can't reliably identify them
        for dom in commDOMs:
            if dom.isNotConfigboot():
                mDOMs[dom.cwd()] = hubmonitools.moniDOMs.HubMoniDOM(dom, hub)
            else:
                logger.warn("DOM %s appears to be in configboot, skipping" % dom.cwd())

        # Should we sending alerts?
        paused = checkPauseFile()
        uptime = getUptime()        
        sendAlerts = not paused and ((uptime < 0) or (uptime > config.ALERT_GRACE_PERIOD))

        # Check for any alert conditions
        try:
            newAlerts = hubmonitools.moniDOMs.moniAlerts(config, dorDriver, hubconfig, hub, cluster)
        except AttributeError:
            logger.error("Malformed alerts... driver unloaded?!")

        # Clear alerts that have gone away
        for alert in activeAlerts:
            if alert not in newAlerts:
                activeAlerts.remove(alert)

        # Send new alerts that are not active
        for alert in newAlerts:
            if alert not in activeAlerts:
                if sendAlerts:
                    if verbose:
                        print alert
                    if not simulate or not verbose:
                        try:
                            s.send_json(alert, flags=zmq.NOBLOCK)
                            logger.info("sent %dB moni alert" % (len(json.dumps(alert))))
                        except zmq.ZMQError:
                            logger.error("couldn't send JSON to socket.", exc_info=sys.exc_info())
                            keepConnecting(s,addr,logger)
                        
                    activeAlerts.append(alert)
                else:
                    logger.warn("moni alert detected but not sent (paused)")

        # If it's time, create the monitoring records and send them
        td = datetime.datetime.utcnow() - lastSentTime
        secSinceLastMoni = td.seconds + (td.days * 24 * 3600)
        if (secSinceLastMoni >= config.MONI_REPORT_PERIOD):

            # Construct monitoring records and send them
            recs = []
            try:
                recs = hubmonitools.moniDOMs.moniRecords(config, mDOMs, mDOMsPrev) 
            except AttributeError:
                logger.error("Malformed moni records... driver unloaded?!")
            
            for rec in recs:
                if verbose:
                    print rec

                if not simulate or not verbose:
                    try:
                        s.send_json(rec, flags=zmq.NOBLOCK)
                        logger.info("sent %dB moni record" % (len(json.dumps(rec))))
                    except zmq.ZMQError:
                        logger.error("couldn't send JSON to socket.", exc_info=sys.exc_info())
                        keepConnecting(s,addr,logger)
                    
            # Keep track of previous snapshot since some quantities
            # are a difference between the two
            mDOMsPrev = mDOMs
            mDOMs = {}
            lastSentTime = datetime.datetime.utcnow()

            if simulate:
                simLoop += 1
                if simLoop == config.MAX_SIMLOOP_CNT:
                    sys.exit(0)

        time.sleep(config.MONI_PERIOD)

if __name__ == "__main__":
    main()
    
