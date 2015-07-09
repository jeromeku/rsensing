#!/usr/bin/env python
import sys,math
r = float(sys.argv[1])*math.pi/180
s = math.sin(r)
print 'Hello World! sin(%f)=%f'%(r,s)