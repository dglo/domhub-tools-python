import subprocess
import json

class HubConfig(dict):
    """Class containing DOR/DOM configuration for various hubs and waivers
    for certain driver error conditions.  Loads a JSON dictionary."""
    def __init__(self, hubConfigFile=None):
        """Initialize the object with the JSON dictionary in hubConfigFile"""
        dict.__init__(self)
        if hubConfigFile is not None:
            self.load(hubConfigFile)
            
    def load(self, filename):
        """Load a JSON file containing configuration for each DOMHub"""
        with open(filename) as file:
            data = json.load(file)            
            for hub in data:
                self[hub] = data[hub]

    def getHub(self, hub, cluster="other"):
        """Return dict containing configuration for a particular hub"""
        return self[cluster][hub]
        
    def isWaived(self, hub, cluster, card, pair):
        """Check to see if a particular card and pair on a hub is waived"""
        waiveStr = "c%dp%d" % (card, pair)
        return waiveStr in self[cluster][hub]["waive"]
    
    def hubs(self, cluster):
        """Return a list of hubs in a particular cluster"""
        return self[cluster].keys()


def getHostCluster(hostname=None):
    """Get the short hostname (assumes we're on *nix or BSD or similar)"""
    """as well as the cluster (sps, spts, or other)"""
    host = ""
    cluster = ""
    if hostname is None:
        cmd = ["hostname"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p:
            stdout, stderr = p.communicate()
            hostname = stdout
            
    address = hostname.split('.')
    host = address[0].rstrip()
    if (len(address) > 1) and (address[1] in ["sps", "spts", "sptsn"]):
        if address[1]=='sptsn':
            cluster='spts'
        else:
            cluster = address[1]
    else:
        cluster = "other"
    return host, cluster
