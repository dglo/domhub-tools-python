import datetime
import json
import dor

class HubMoniDOM(object):
    """Class containing increment of monitoring data from one
    DOM on a hub.  """
    def __init__(self, dom):
        self.dom = dom
        self.updateTime = datetime.datetime.utcnow().__str__()
        if (self.dom is not None) and self.dom.pair.isPlugged():
            self.current = self.dom.pair.current()
            self.voltage = self.dom.pair.voltage()
            self.pwrcheck = self.dom.pair.pwrCheck()
            if self.dom.isCommunicating():
                self.comstat = self.dom.commStats()
                self.mbid = self.dom.mbid()

class HubMoniRecord(dict):
    """Class containing a JSON monitoring record for a particular quantity,
    including all DOMs on the hub."""    
    MONI_SERVICE = "hubmoni"    
    MONI_PRIORITY = 3
    MONI_VERSION = 2

    def __init__(self, quantity):
        dict.__init__(self,
                      { "service" : HubMoniRecord.MONI_SERVICE,
                        "varname" : quantity,
                        "prio" : HubMoniRecord.MONI_PRIORITY,
                        "time" : datetime.datetime.utcnow().__str__(),                      
                        "value" : { "value": {},
                                    "version" : HubMoniRecord.MONI_VERSION } })

    def setDOMValue(self, omkey, val):
        self["value"]["value"][omkey] = val

    def getDOMValue(self, omkey):
        return self["value"]["value"][omkey]

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=4, separators=(',', ': '))
    
class HubMoniAlert(dict):
    ALERT_NOTIFIES = "jkelley@icecube.wisc.edu"
    ALERT_PRIORITY = 1
    ALERT_PAGES = False
    ALERT_SERVICE = "hubmoni"
    
    def __init__(self, hub, cluster, alert_txt=None, alert_desc=None):
        dict.__init__(self,
                      { "service" : HubMoniAlert.ALERT_SERVICE,
                        "varname" : "alert",
                        "t" : datetime.datetime.utcnow().__str__(),
                        "prio" : HubMoniAlert.ALERT_PRIORITY,
                        "value" : { "notifies": [{"receiver": HubMoniAlert.ALERT_NOTIFIES,
                                                  # "notifies_txt": "TBD",
                                                  # "notifies_header": "TBD"
                                                  }],
                                    "pages"     : HubMoniAlert.ALERT_PAGES,
                                    "vars"      : { "hubname" : hub, "cluster" : cluster }
                                    }
                        })
        if alert_txt is not None and alert_desc is not None:
            self.setAlert(alert_txt, alert_desc)

    def setAlert(self, alert_txt, alert_desc):
        """Set the alert text and description (other fields are common)"""
        self["value"]["condition"] = alert_txt
        self["value"]["notifies"][0]["notifies_header"] = "HubMoni alert: " + alert_txt
        self["value"]["notifies"][0]["notifies_txt"] = alert_desc

    def appendAlert(self, alert_desc):
        """Append description to the alert if it's not already included"""
        if alert_desc not in self["value"]["notifies"][0]["notifies_txt"]:
            self["value"]["notifies"][0]["notifies_txt"] += alert_desc
            
    def __eq__(self, other):
        """Overide equals for alert equivalence"""
        if type(self) is type(other):
            return ((self["value"]["condition"] == other["value"]["condition"]) and
                    (self["value"]["notifies"][0]["notifies_txt"] == other["value"]["notifies"][0]["notifies_txt"]) and
                    (self["value"]["vars"]["hubname"] == other["value"]["vars"]["hubname"]) and
                    (self["value"]["vars"]["cluster"] == other["value"]["vars"]["cluster"]))
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=4, separators=(',', ': '))

def moniAlerts(dor, hubConfig, hub, cluster):
    """Send user alerts to I3Live for problematic conditions"""
    conf = hubConfig.getHub(hub, cluster)

    alerts = []

    # Check number of DOR cards
    if (len(dor.cards) != conf["dor"]):
        alert_txt = "Unexpected number of DOR cards on %s" % hub
        alert_desc = "%s: expected %d DOR cards, found %d" % (hub, conf["dor"], len(dor.cards))
        alert = HubMoniAlert(hub, cluster, alert_txt=alert_txt, alert_desc=alert_desc)
        alerts.append(alert)
        
    # Check number of communicating DOMs
    if (len(dor.getCommunicatingDOMs()) != conf["comm"]):
        alert_txt = "Unexpected number of communicating DOMs on %s" % hub
        alert_desc = "%s: expected %d communicating DOMs, found %d" % \
            (hub, conf["comm"], len(dor.getCommunicatingDOMs()))
        alert = HubMoniAlert(hub, cluster, alert_txt=alert_txt, alert_desc=alert_desc)        
        alerts.append(alert)

    # Check DOR-driver pwr_check conditions (vs. waivers)
    pwrFail = False
    for dom in dor.getPluggedDOMs():
        moni = HubMoniDOM(dom)
        # All power check failures are equivalent at the moment
        if not moni.pwrcheck.ok and not hubConfig.isWaived(hub, cluster, int(dom.card), int(dom.pair)):
            if not pwrFail:
                alert_txt = "DOM power check failure on %s" % hub
                alert_desc = "%s: " % hub
                alert_desc += moni.pwrcheck.text
                alert = HubMoniAlert(hub, cluster, alert_txt=alert_txt, alert_desc=alert_desc)
                pwrFail = True
            else:
                alert.appendAlert(moni.pwrcheck.text)
    if pwrFail:
        alerts.append(alert)

    return alerts

def moniRecords(moniDOMs):
    """Construct the JSON monitoring records from the monitoring snapshots"""

    # JSON monitoring message headers
    MONI_QUANTITIES = ["dom_pwrstat_voltage", "dom_pwrstat_current",
                       "dom_comstat_retx", "dom_comstat_badpkt"]

    recs = []
    for qty in MONI_QUANTITIES:
        qty_diff = "comstat" in qty        
        rec = HubMoniRecord(qty)
        for cwd in moniDOMs:
            moniArr = moniDOMs[cwd]
            omkey = moniArr[0].dom.omkey()
            if (qty == "dom_pwrstat_voltage"):
                rec.setDOMValue(omkey, moniArr[0].voltage)
            elif (qty == "dom_pwrstat_current"):
                rec.setDOMValue(omkey, moniArr[0].current)
            elif (qty == "dom_comstat_retx") and (len(moniArr) > 1):
                    rec.setDOMValue(omkey, moniArr[-1].comstat.nretxb - moniArr[0].comstat.nretxb)
            elif (qty == "dom_comstat_badpkt") and (len(moniArr) > 1):
                    rec.setDOMValue(omkey, moniArr[-1].comstat.badpkt - moniArr[0].comstat.badpkt)
                    
        # Quantities that report a count in a given period
        if qty_diff:
            if (len(moniArr) > 1):
                rec["value"]["recordingStopTime"] = moniArr[-1].updateTime
                rec["value"]["recordingStartTime"] = moniArr[0].updateTime
                recs.append(rec)
        else:
            recs.append(rec)
                
    return recs


