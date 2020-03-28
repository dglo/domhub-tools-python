#!/usr/bin/env python
#
# Parse old testdaq hubConfig.dat into useful a JSON dict
#
from __future__ import print_function
import json

f = open("hubConfig.dat", "r")
hubConfig = {}
for line in f.readlines():

    vals = line.split()

    if len(vals) == 5 or len(vals) == 6:
        hostname = vals[0]
        nDOR = int(vals[1])
        nQuad = int(vals[2])
        nComm = int(vals[3])
        nIceboot = int(vals[4])
        #print hostname, nDOR, nQuad, nComm, nIceboot
        
        # Parse and split hostname
        if hostname.strip().startswith('#'):
            continue

        cluster = ""
        try:
            cluster,machine = hostname.split('-')
        except:
            pass
        if cluster != "sps" and cluster != "spts":
            machine = hostname
            cluster = "other"

        # Parse any exceptions
        waive = []
        if len(vals) == 6:
            for w in vals[5].split(';'):
                if w != "":
                    try:
                        waive.append(w.split("-")[0])
                    except:
                        pass
                
                
        
        # Put everything into a dict
        if cluster not in hubConfig:
            hubConfig[cluster] = {}
            
        hubConfig[cluster][machine] = {"dor":nDOR,
                                       "quad":nQuad,
                                       "comm":nComm,
                                       "iceboot":nIceboot,
                                       "waive":waive
                                       }

f.close()
print(json.dumps(hubConfig, sort_keys=True, indent=4, separators=(',', ': ')))

fout = open("hubConfig.json", "wb")
json.dump(hubConfig, fout, sort_keys=True, indent=4, separators=(',', ': '))
fout.close()
