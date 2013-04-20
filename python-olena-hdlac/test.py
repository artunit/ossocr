#!/usr/bin/env python
import olena_hdlac
import ctypes
import os

test = olena_hdlac.xmlPage("eurotext.tif","eurotext.xml")
print "timer for eurotext.xml reports: ", test
