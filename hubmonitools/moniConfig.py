import os
import json

class HubMoniConfig(dict):
    """Class containing hubmoni configuration variables.
    Configuration file is a JSON dict."""
    DEFAULTS = {
        # Monitoring message service name
        "MONI_SERVICE":"hubmoni",

        # Monitoring message priority level
        "MONI_PRIORITY" : 3,

        # Monitoring message version number
        "MONI_VERSION" : 2,

        # Alert service name
        "ALERT_SERVICE" : "hubmoni",

        # Alert e-mail notification list
        "ALERT_NOTIFIES" : [],

        # Alert message priority level
        "ALERT_PRIORITY" : 1,

        # Alert pages WOs or not
        "ALERT_PAGES" : False,

        # Hub configuration file
        "HUBCONFIG" : os.environ['HOME']+"/hubConfig.json",

        # DOR procfile prefix
        "DOR_PREFIX" : "/proc/driver/domhub",
        
        # Default monitoring period, in seconds
        "MONI_PERIOD" : 120,

        # Default monitoring reporting period, in seconds
        "MONI_REPORT_PERIOD" : 3600,

        # How long to wait before reattempting 
        # socket connection, in seconds
        "SOCKET_WAIT" : 60,

        # Default ZMQ listener for reporting
        "ZMQ_HOSTNAME" : "expcont",
        "ZMQ_PORT" : 6668,
        
        # Grace period for alert after reboot, seconds
        "ALERT_GRACE_PERIOD" : 600,

        # In simulation mode, how many times to report
        # records before exiting
        "MAX_SIMLOOP_CNT" : 2
        }
        
    def __init__(self, configFile=None):
        """Initialize object with default configuration values and
        update with anything found in the JSON configuration file"""
        dict.__init__(self, HubMoniConfig.DEFAULTS)
        if configFile is not None:
            with open(configFile) as f:                
                fixed_json = ''.join(line for line in f if not line.startswith('#'))
                userConfig = json.loads(fixed_json)
                self.update(userConfig)

    def __getattr__(self, attr):
        """Syntactic sugar; access configuration items as attributes"""
        return self[attr]

    def __setattr__(self, attr, value):
        """Syntactic sugar; set configuration items as attributes"""        
        self[attr] = value
