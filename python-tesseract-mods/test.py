#!/usr/bin/env python
# -*- coding: utf-8 -*-
# total credit to https://code.google.com/p/python-tesseract/, small additions for coords here
import tesseract
import ctypes
import os
api = tesseract.TessBaseAPI()
api.SetOutputName("outputName");
tessdatapath = os.getenv('TESSDATA_PREFIX', '/usr/local/share')
api.Init(tessdatapath,"eng",tesseract.OEM_DEFAULT)
api.SetPageSegMode(tesseract.PSM_AUTO)
mImgFile = "eurotext.jpg"

result = tesseract.ProcessPagesFileStream(mImgFile,api)
print "result(ProcessPagesFileStream)=",result

result = tesseract.ProcessPagesRaw(mImgFile,api)
print "result(ProcessPagesRaw)",result

#x = [[' 0 0 0 0' for i in range(10)] for j in range(len(result))]

mBuffer=open(mImgFile).read()
result = tesseract.ProcessPagesBuffer(mBuffer,len(mBuffer),api)
print "result(ProcessPagesBuffer)=",result

result = tesseract.ProcessPagesWrapper(mImgFile,api)
print "result(ProcessPagesWrapper)=",result

coords = tesseract.ExtractResultsArrayWrapper(api, len(result),"^","")
coord_array = coords.split("^")
print "coords in string:"
for coord_entry in coord_array:
    print coord_entry
