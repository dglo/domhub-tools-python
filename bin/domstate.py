#!/usr/bin/env python
#
# domstate
#
# Figure out the DOM state non-destructively
#

from __future__ import print_function
import sys
import dor

def main(): 
    # Get command line arguments
    if len(sys.argv) != 2:
        print("Usage: %s CWD|all" % sys.argv[0])
        sys.exit(0)

    cwdArg = sys.argv[1].upper()
    if len(cwdArg) != 3:
        print("Error: unknown CWD",sys.argv[1])
        sys.exit(-1)

    # DOR interface
    dorDriver = dor.DOR()

    states = {}
    doms = []
    # Parse which CWDs to check (only can be communicating DOMs)
    if cwdArg.lower() == "all":
        doms = dorDriver.getCommunicatingDOMs()
    else:
        dom = dorDriver.getDOM(cwdArg)        
        if dom is None:
            states[cwdArg] = "noplug"
        else:
            doms = [dom]

    if doms:
        states = dorDriver.getDOMStates(doms)

    for cwd in sorted(states.keys()):
        print(cwd,states[cwd])

if __name__ == "__main__":
    main()
