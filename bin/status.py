#!/usr/bin/env python
#
# Print table of DOM status
#
# J. Kelley
# WIPAC 2016
#

import sys
import dor
from hubmonitools import hubConfig

#-----------------------------------------------------------

class DOMSummary(dict):
    '''Helper object for DOM summary information and formatting'''
    ''' should be an OrderedDict, sad Python 2.6'''
    def __init__(self, dom, state=None):
        self['DOR'] = dom.cwd()
        self['Port'] = dom.port()
        self['Qud'] = "Q_"+str(dom.quad())
        self['DORserial#'] = dom.pair.card.serial()
        if dom.isCommunicating():
            self['Stat'] = 'COMM'
        else:
            self['Stat'] = ''
        self['Pos'] = dom.omkey()
        self['Name'] = dom.name()
        self['MBID'] = dom.mbid()
        self['DOMID'] = dom.prodID()
        self['Curr'] = str(dom.pair.current())+" mA"
        self['Volts'] = str(int(dom.pair.voltage()+0.5))+"V"
        if state is not None:
            self['State'] = state

        # Formatting stuff
        # DOR Port Qud DORserial# Stat Pos      NAME                       MBID      DOMID    Curr  Volts
        # 30B 5025 Q_8 R1B0621D05 COMM -        Radish                 0f9cff64d691 UP4P0286  68 mA  89V
        self.orderedKeys = ['DOR','Port','Qud','DORserial#','Stat','Pos','Name','MBID',
                            'DOMID','Curr','Volts']
        if 'State' in self:
            self.orderedKeys.append('State')

        self.format = {'DOR':'{0: <4}',
                       'Port':'{0: <5}',
                       'Qud':'{0: <4}',
                       'DORserial#':'{0: <11}',
                       'Stat':'{0: <5}',
                       'Pos':'{0: <9}',
                       'Name':'{0: <23}',
                       'MBID':'{0: ^12}',
                       'DOMID':'{0: ^11}',
                       'Curr':'{0: <6}',
                       'Volts':'{0: ^6}',
                       'State':'{0: >7}'}

    def __str__(self):        
        s = ""
        for k in self.orderedKeys:
            fmt = self.format[k]
            s += fmt.format(self[k])
        return s
    
    def headers(self):
        s = ""
        for k in self.orderedKeys:
            fmt = self.format[k]
            s += fmt.format(k)
        return s

    def __cmp__(self, other):
        return self['Port'].__cmp__(other['Port'])

#-----------------------------------------------------------

dorDriver = dor.DOR()

quick = (len(sys.argv) > 1) and (sys.argv[1] == '-q')

# Header info
#-------------------------------------------------------------------------------
#TCUBE SUMMARY:

print "-"*80
(host,cluster) = hubConfig.getHostCluster()
print "%s SUMMARY:\n" % host.upper()


states = None
doms = dorDriver.getPluggedDOMs()
if not quick:
    states = dorDriver.getDOMStates(doms)

# Get the DOM summaries
summaries = []
for dom in doms:
    if not quick:
        summary = DOMSummary(dom, state=states[dom.cwd()])
    else:
        summary = DOMSummary(dom)
    summaries.append(summary)

# Print the DOM summaries, sorted in string order
headers = False
for summary in sorted(summaries):
    if not headers:
        print summary.headers()
        headers = True
    print summary

# Print a summary line
countStr = "communicating %d DOMs; " % len(dorDriver.getCommunicatingDOMs())
if not quick:
    for state in set(states.values()):
        cnt = len([cwd for cwd in states if states[cwd] == state])
        countStr += "%s %d DOMs; " % (state, cnt)

print ""
print countStr
print "-"*80


#30B 5025 Q_8 R1B0621D05 COMM -        Radish                 0f9cff64d691 UP4P0286  68 mA  89V
