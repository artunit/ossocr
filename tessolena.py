#!/usr/bin/env python
"""
tessolena.py - work with hocr format from tesseract and page format
from olena to segment image and snag coordinates
- art rhyno, conifer/hackforge/ourdigitalworld
"""

from array import array
from itertools import combinations
from lxml import etree
from subprocess import call
from xml.etree import ElementTree as ET
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

import copy,sys,os,re,glob
import cStringIO
import Image
import os, tempfile
import traceback
import unicodedata

#where to create temporary files
TEMP_DIR = "/tmp/"

#path to invoke olena
OLENA_EXE = "/usr/local/bin/content_in_hdoc_hdlac"

#path to invoke tesseract
TESSERACT_EXE = "/usr/local/bin/tesseract"

#box scale - some images benefit from scaling for OCR
BOX_SCALE = 1

#minimum number of pixels in height to bother with a box
BOX_THRESHOLD = 10

#number of pixels to add to box region for breathing room
LINE_GAP = 5

#namespace used by olena for PAGE
OLENA_NAMESPACE = 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-03-19'

#namespace used by xhtml (normally) as per hocr
HTML_NAMESPACE = 'http://www.w3.org/1999/xhtml'

"""
page_square - a box on the image
"""
class page_square:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = int(x0)
        self.y0 = int(y0)
        self.x1 = int(x1)
        self.y1 = int(y1)

"""
page_entry - coordinates word on image
"""
class word_entry:
    def __init__(self, x0, y0, x1, y1, word_text):
        self.x0 = int(x0)
        self.y0 = int(y0)
        self.x1 = int(x1)
        self.y1 = int(y1)
        self.word_text = word_text

""" start the xml output """
def coordsheader(coordfile):
    coordfile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    coordfile.write("<words>\n")

""" check for valid XML file """
def parsefile(file):
    parser = make_parser()
    parser.setContentHandler(ContentHandler())
    parser.parse(file)

""" pull together squares from PAGE file """
def sortOutPAGE(PAGEfile,elemName):
    img_squares = []
    tree = ET.ElementTree(file=PAGEfile)
    for elem in tree.iterfind('.//{%s}%s' % (OLENA_NAMESPACE,elemName)):
        for coordElem in elem.iterfind('{%s}Coords' % OLENA_NAMESPACE):
            x0 = 0
            y0 = 0
            x1 = 0
            y1 = 0

            for pointElem in coordElem.iterfind('{%s}Point' % OLENA_NAMESPACE):
                this_x = int(pointElem.attrib['x'])
                this_y = int(pointElem.attrib['y'])

                if this_x < x0 or x0 == 0:
                    x0 = this_x
                if this_y < y0 or y0 == 0:
                   y0 = this_y
                if this_x > x1:
                   x1 = this_x
                if this_y > y1:
                   y1 = this_y
            #print x0,y0,x1,y1
            img_squares.append(page_square(x0,y0,x1,y1))

    return img_squares

""" burrow in to return text node """
def elemWalk(inelem):
    thiselem = inelem
    #word may be bolded, italized, etc...
    for node in thiselem:
        if node.text is not None:
           return node.text
        else:
           return elemWalk(node)
    return ''

""" sort out HOCR results """
def sortOutHocrResult(hocrfile,coordsfile,img_x0,img_y0,scale,line_gap):
    tree = ET.ElementTree(file=hocrfile)
    for elem in tree.iterfind('.//{%s}%s' % (HTML_NAMESPACE,'span')):
        if 'class' in elem.attrib:
           class_name = elem.attrib['class']
           if class_name == 'ocrx_word':
              elem_val = ''
              if elem.text is not None:
                 elem_val = elem.text
              else:
                 elem_val = elemWalk(elem)

              word_val = ''
              elem_val = elem_val.replace(">","&gt;")
              elem_val = elem_val.replace("<","&lt;")
              for char in elem_val:
                 #drop anything that can't be encoded
                 try:
                    char = char.encode('utf-8',errors='strict')
                 except:
                    char = ''
                 word_val += char
                 
              if len(word_val) > 0:
                 bbox_info = elem.attrib['title']
                 bbox_info = bbox_info.replace(';',' ')
                 bbox_info = bbox_info.split(' ')
                 #print "%s - %s %s %s %s" % (word_val,bbox_info[1],bbox_info[2],bbox_info[3],bbox_info[4])
                 hx0 = round((int(bbox_info[1]) + img_x0)/scale)
                 hy0 = round((int(bbox_info[2]) + img_y0)/scale)
                 hx1 = round((int(bbox_info[3]) + img_x0)/scale)
                 hy1 = round((int(bbox_info[4]) + img_y0)/scale)
                 coordsfile.write("<word x1=\"%d\" y1=\"%d\">\n%s\n<ends x2=\"%d\" y2=\"%d\"/>\n</word>\n" %
                    (hx0,hy0,word_val,hx1,hy1))

from optparse import OptionParser

parser = OptionParser(usage="""
%prog [options] 

Possible choices are:

--box_threshold -- smallest height for box
--coords -- file for word coordinate information
--file -- specify input file
--language -- tesseract language code
--line_gap -- extra pixels for olena boxes
--result -- file for text results
--scale -- resize image for OCR processing
--write_boxes -- keep olena boxes around

""")

# options
parser.add_option("-b","--box_threshold",help="smallest height for box",default=BOX_THRESHOLD)
parser.add_option("-c","--coords",help="write coordinates in XML",default="coords.xml")
parser.add_option("-f","--file",help="input file",default="page.tif")
parser.add_option("-l","--language",help="language for OCR",default="eng")
parser.add_option("-g","--line_gap",help="specify gap value for",default=LINE_GAP)
parser.add_option("-r","--result",help="text results file",default="page.txt")
parser.add_option("-s","--scale",help="resize squares for OCR",default=BOX_SCALE)
parser.add_option("-w","--write_boxes",help="write olena boxes",default=False)

(options,args) = parser.parse_args()

img = Image.open(options.file)
width, height = img.size

"""
olena's scribo_viewer uses base name for examining regions, so 
follow same convention 
"""
img_name = options.file.split('.')
img_base = img_name[0]
print "img_base", img_base

return_code = -1
pg_squares = []
       
coordsfile = open(options.coords, 'w')
coordsheader(coordsfile)

if OLENA_EXE is not None:
    cmd_line = "%s %s %s" % (OLENA_EXE, options.file, img_base + '.xml')
    print "executing olena with: %s" % cmd_line
    return_code = call(cmd_line, shell=True)

if os.path.isfile(img_base + ".xml") and return_code >= 0:

       tmp_squares = []

       parsefile(img_base + ".xml")
       pg_squares = sortOutPAGE(img_base + ".xml","TextRegion")

       #if you wanted to include other regions, you would do this for example
       #pg_squares.extend(sortOutPAGE(img_base + ".xml","ImageRegion"))

       #sort from bottom to top
       tmp_squares = sorted(pg_squares, key=lambda seg: seg.y0)
       #now sort from left to right
       pg_squares = sorted(tmp_squares, key=lambda seg: seg.x0)
elif OLENA_EXE is not None:
       print "bummer, olena didn't work"

       
#if olena can't identify any regions, or olena is not used, then process the entire image
if len(pg_squares) == 0:
    pg_squares.append(page_square(0,0,width,height))
       
i = 1
for square in pg_squares:
    x0 = square.x0
    y0 = square.y0
    x1 = square.x1
    y1 = square.y1

    tmpimgname = "%d_%d_%d_%d.png" % (x0,y0,x1,y1)
    if (square.y1 - square.y0) > options.box_threshold:

              
        #usually want a wee bit of breathing room with pixels
        x0 -= options.line_gap
        if x0 < 0:
            x0 = 0
        y0 -= options.line_gap
        if y0 < 0:
            y0 = 0
        x1 += options.line_gap
        #this should never happen but just in case...
        if x0 > width:
            x0 = width 
        if x1 > width: 
            x1 = width 
        y1 += options.line_gap
        if y1 > height: 
            y1 = height 

        pg_box = (x0,y0,x1,y1)
        region = img.crop(pg_box)

        bx_width, bx_height = region.size
        if options.scale > 1:
            region = region.resize((bx_width * options.scale, bx_height * options.scale), Image.BICUBIC)
        region.save(tmpimgname,"PNG")
                 
        ocrtemp= tempfile.NamedTemporaryFile()
        cmd_line = "%s %s %s -l %s hocr" % (TESSERACT_EXE,tmpimgname,ocrtemp.name,options.language)
        print "%d of %d, executing tesseract with: %s" % (i,len(pg_squares),cmd_line)
        i = i + 1
        code = call(cmd_line, shell=True)

        sortOutHocrResult(ocrtemp.name + ".hocr",coordsfile,round(x0),round(y0),options.scale,options.line_gap)
        ocrtemp.close()

        if os.path.isfile(ocrtemp.name + '.hocr'):
             os.remove(ocrtemp.name + '.hocr')

        if not options.write_boxes:
            if os.path.isfile(tmpimgname):
                os.remove(tmpimgname)

coordsfile.write("</words>\n")
coordsfile.close()
