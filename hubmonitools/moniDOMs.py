import datetime
import json
import dor

class HubMoniDOM(object):
    """Class containing increment of monitoring data from one
    DOM on a hub.  """
    def __init__(self, dom, hub):
        self.dom = dom
        self.hub = hub
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

    def __init__(self, config, quantity, countQty):
        self.valid = True
        self.countQty = countQty
        dict.__init__(self,
                      { "service" : config.MONI_SERVICE,
                        "varname" : quantity,
                        "prio" : config.MONI_PRIORITY,
                        "time" : datetime.datetime.utcnow().__str__(),                        
                        })
        if countQty:
            self["value"] = {"counts": {},
                             "version" : config.MONI_VERSION }
        else: 
            self["value"] = {"value": {},
                             "version" : config.MONI_VERSION }

    def setDOMValue(self, omkey, val):
        if self.countQty:
            self["value"]["counts"][omkey] = val
        else:
            self["value"]["value"][omkey] = val

    def getDOMValue(self, omkey):
        if self.countQty:
            return self["value"]["counts"][omkey]
        else:
            return self["value"]["value"][omkey]

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=4, separators=(',', ': '))
    
class HubMoniAlert(dict):
    def __init__(self, config, hub, cluster, alert_txt=None, alert_desc=None):
        dict.__init__(self,
                      { "service" : config.ALERT_SERVICE,
                        "varname" : "alert",
                        "t" : datetime.datetime.utcnow().__str__(),
                        "prio" : config.ALERT_PRIORITY,
                        "value" : { "pages"     : config.ALERT_PAGES,
                                    "vars"      : { "hub" : hub, "cluster" : cluster },
                                    "notifies"  : []
                                    }
                        })
        if alert_txt is not None and alert_desc is not None:
            self.setAlert(config.ALERT_NOTIFIES, alert_txt, alert_desc)

    def setAlert(self, notifies, alert_txt, alert_desc):
        """Set the alert text and description (other fields are common)"""
        self["value"]["condition"] = alert_txt
        self["value"]["desc"] = alert_desc
        for receiver in notifies:
            self["value"]["notifies"].append({"receiver": receiver,
                                              "notifies_header": "HubMoni alert: " + alert_txt,
                                              "notifies_txt": alert_desc })        

    def appendAlert(self, alert_desc):
        """Append description to the alert if it's not already included"""
        if alert_desc not in self["value"]["desc"]:
            self["value"]["desc"] += alert_desc
            for idx,receiver in enumerate(self["value"]["notifies"]):
                self["value"]["notifies"][idx]["notifies_txt"] += alert_desc
            
    def __eq__(self, other):
        """Overide equals for alert equivalence."""
        if type(self) is type(other):
            return ((self["value"]["condition"] == other["value"]["condition"]) and
                    (self["value"]["vars"]["hub"] == other["value"]["vars"]["hub"]) and
                    (self["value"]["vars"]["cluster"] == other["value"]["vars"]["cluster"]))
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=4, separators=(',', ': '))

def moniAlerts(config, dor, hubConfig, hub, cluster):
    """Send user alerts to I3Live for problematic conditions"""
    conf = hubConfig.getHub(hub, cluster)

    alerts = []

    # Check number of DOR cards
    if (len(dor.cards) != conf["dor"]):
        alert_txt = "%s: unexpected number of DOR cards" % hub
        alert_desc = "%s-%s: expected %d DOR cards, found %d" % \
            (cluster, hub, conf["dor"], len(dor.cards))
        alert = HubMoniAlert(config, hub, cluster, alert_txt=alert_txt, alert_desc=alert_desc)
        alerts.append(alert)
        
    # Check number of communicating DOMs
    if (len(dor.getCommunicatingDOMs()) != conf["comm"]):
        alert_txt = "%s: unexpected number of DOMs" % hub
        alert_desc = "%s-%s: expected %d communicating DOMs, found %d" % \
            (cluster, hub, conf["comm"], len(dor.getCommunicatingDOMs()))
        alert = HubMoniAlert(config, hub, cluster, alert_txt=alert_txt, alert_desc=alert_desc)        
        alerts.append(alert)

    # Check DOR-driver pwr_check conditions (vs. waivers)
    pwrFail = False
    for dom in dor.getPluggedDOMs():
        moni = HubMoniDOM(dom, hub)
        # All power check failures are equivalent at the moment
        if not moni.pwrcheck.ok and not hubConfig.isWaived(hub, cluster, int(dom.card), int(dom.pair)):
            if not pwrFail:
                alert_txt = "%s: DOM power check failure" % hub
                alert_desc = "%s-%s: " % (cluster, hub)
                alert_desc += moni.pwrcheck.text
                alert = HubMoniAlert(config, hub, cluster, alert_txt=alert_txt, alert_desc=alert_desc)
                pwrFail = True
            else:
                alert.appendAlert(moni.pwrcheck.text)
    if pwrFail:
        alerts.append(alert)

    return alerts

def moniRecords(config, moniDOMs, moniDOMsPrev):
    """Construct the JSON monitoring records from the monitoring snapshots"""

    # JSON monitoring message headers
    MONI_QUANTITIES = ["dom_pwrstat_voltage", "dom_pwrstat_current",
                       "dom_comstat_retx", "dom_comstat_badpkt",
                       "dom_comstat_rxbytes", "dom_comstat_txbytes",
                       "dom_cabling"]

    recs = []
    for qty in MONI_QUANTITIES:
        rec = HubMoniRecord(config, qty, countQty=("comstat" in qty))
        for cwd in moniDOMs:
            # Most recent monitoring snapshot for this DOM
            m = moniDOMs[cwd]
            rec["value"]["hub"] = m.hub
            omkey = m.dom.omkey()
            if omkey is "-":
                continue
            if (qty == "dom_pwrstat_voltage"):
                rec.setDOMValue(omkey, m.voltage)
            elif (qty == "dom_pwrstat_current"):
                rec.setDOMValue(omkey, m.current)
            elif (qty == "dom_cabling"):
                rec.setDOMValue(omkey, cwd)
                # Override priority
                rec["prio"] = 2
            elif rec.countQty:
                if cwd not in moniDOMsPrev:
                    rec.valid = False
                else:
                    cnt = 0L
                    mPrev = moniDOMsPrev[cwd]
                    if (qty == "dom_comstat_retx"):
                        cnt = m.comstat.nretxb - mPrev.comstat.nretxb
                    elif (qty == "dom_comstat_badpkt"):
                        cnt = m.comstat.badpkt - mPrev.comstat.badpkt
                    elif (qty == "dom_comstat_rxbytes"):
                        cnt = m.comstat.rxbytes - mPrev.comstat.rxbytes
                    elif (qty == "dom_comstat_txbytes"):
                        cnt = m.comstat.txbytes - mPrev.comstat.txbytes
                    # A negative count most likely means the comstats
                    # were reset underneath us
                    if (cnt < 0):
                        rec.valid = False
                    else:
                        rec.setDOMValue(omkey, cnt)
                        rec["value"]["recordingStopTime"] = m.updateTime
                        rec["value"]["recordingStartTime"] = mPrev.updateTime

        recs.append(rec)
        
    return recs


