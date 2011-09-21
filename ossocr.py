#!/usr/bin/python

# some common conversions
# most effective seems to be radius 50, amount 10, threshold 0
# convert -unsharp 2x1.5+2.0+1.0 -resize 200% -density 300x300
# convert -unsharp 10x1.5+2.0+1.0 -resize 200% -density 300x300 -type Grayscale test.jpg new.jpg
# convert -density 300x300 -type Grayscale test.pdf test.jpg

from array import array
import Image, TiffImagePlugin
import json, os, tempfile

#import pygtk
#pygtk.require("2.0")
#import gtk

#import matplotlib
#matplotlib.rcParams["interactive"] = 1
#if "DISPLAY" not in os.environ: matplotlib.use('AGG')
#else: matplotlib.use('GTK')

from pylab import *
import traceback
import tesseract

import Image

import sys,os,re,glob

ion()
hold(False)

IS_VALID = re.compile('[a-z|A-Z|0-9|\.|\'|\"|\s]')
IS_STOP = re.compile('[\.|,|;|\s]')
SCALE    = 1
LZW      = "lzw"
ZIP      = "zip"
JPEG     = "jpeg"
PACKBITS = "packbits"
G3       = "g3"
G4       = "g4"
NONE     = "none"

def _save(im, fp, filename):

    # check compression mode
    try:
        compression = im.encoderinfo["compression"]
    except KeyError:
        # use standard driver
        TiffImagePlugin._save(im, fp, filename)
    else:
        # compress via temporary file
        if compression not in (LZW, ZIP, JPEG, PACKBITS, G3, G4, NONE):
            raise IOError, "unknown compression mode"
        file = tempfile.mktemp()
        im.save(file, "TIFF")
        os.system("tiffcp -c %s %s %s" % (compression, file, filename))
        try: os.unlink(file)
        except: pass

Image.register_save(TiffImagePlugin.TiffImageFile.format, _save)

def numpy2pixbuf(a):
    """Convert a numpy array to a pixbuf."""
    if len(a.shape)==3:
        data = zeros(list(a.shape),'B')
        data[:,:,:] = 255*a
        return gtk.gdk.pixbuf_new_from_array(data,gtk.gdk.COLORSPACE_RGB,8)
    elif len(a.shape)==2:
        data = zeros(list(a.shape)+[3],'B')
        data[:,:,0] = 255*a
        data[:,:,1] = 255*a
        data[:,:,2] = 255*a
        return gtk.gdk.pixbuf_new_from_array(data,gtk.gdk.COLORSPACE_RGB,8)

def coordsheader(coordfile):
    coordfile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    coordfile.write("<words>\n")

def ocr2coords(scale, height, coordsin, coordsfile):
    """ Pull together coordinate information in XML format """

    char = word = ""
    x0 = y0 = x1 = y1 = 0
    tcx0 = tcy0 = tcx1 = tcy1 = 0
    xl = yl = xr = yr = 0

    infile = open(coordsin,"r")
    for line in infile:
        entries = line.split()

        stopChar = False

        if len(entries) == 5:
            char = entries[0]

            stopChar = re.search(IS_STOP, char)
            if not stopChar:
                tcx0 = int(entries[1])
                tcy0 = int(entries[2])
                tcx1 = int(entries[3])
                tcy1 = int(entries[4])

                #tesseract works from the bottom up for Y but we need to work from the top
                tcy0 = height - tcy0
                tcy1 = height - tcy1

        if len(word) == 0:
            x0 = tcx0
            y0 = tcy0
            x1 = tcx1
            y1 = tcy1

        if len(entries) == 5 and not stopChar:
            word += char

        if (len(entries) == 4 or stopChar) and len(word) > 0:

            #print "%d: %d,%d,%d,%d -> %d"%(height,x0,y0,x1,y1,scale)
            #adjust for scale
            x0 = round(x0/scale)
            y0 = round(y0/scale)
            x1 = round(x1/scale)
            y1 = round(y1/scale)

            #note that we swap Y values because of changing the orientation
            if x0 >= 0 and y0 >=0 and x1 >=0 and y1 >=0:
                    coordsfile.write("<word x1=\"%d\" y1=\"%d\">\n%s\n<ends x2=\"%d\" y2=\"%d\"/>\n</word>\n" %
                         (x0,y1,word,xr,yl))
            word = ""

        if not stopChar and len(entries) == 5:
           xl = round(tcx0/scale)
           xr = round(tcx1/scale)
           yl = round(tcy0/scale)
           yr = round(tcy1/scale)

    if len(word) > 0:
        coordsfile.write("<word x1=\"%d\" y1=\"%d\">\n%s\n<ends x2=\"%d\" y2=\"%d\"/>\n</word>\n" %
            (x0,y1,word,xr,yl))


def alert(*args):
    sys.stderr.write(" ".join([str(x) for x in args]))
    sys.stderr.write("\n")

from optparse import OptionParser

parser = OptionParser(usage="""
%prog [options] image1 

Possible choices are:

--scale -- resize image for OCR processing
--language -- tesseract language code
--coords -- write coordinate information
--output -- specify output file, defaults to ocr.txt

""")


# options
parser.add_option("-s","--scale",help="scale for resize",default=SCALE)
parser.add_option("-l","--language",help="language for OCR",default="eng")
parser.add_option("-c","--coords",help="write coordinates in XML",action="store_true")
parser.add_option("-o","--output",help="specify output file",default="ocr.txt")

(options,args) = parser.parse_args()

if len(args)==0:
    parser.print_help()
    sys.exit(0)

SCALE = int(options.scale)

img = Image.open(args[0])
width, height = img.size

if SCALE > 1:
    print "sizing %s from %d x %d to %d x %d" % (args[0], width, height, (width *SCALE), (height * SCALE))

#options are BICUBIC, NEAREST, BILINEAR, and ANTIALIAS
img = img.resize((width * SCALE, height * SCALE), Image.BICUBIC)

# we work from temporary file in TIFF format
imgtemp = tempfile.NamedTemporaryFile()
img.save(imgtemp.name,"TIFF")

file = open(options.output, 'w')

# Now start the output of coord info
if options.coords:
    coordsfile = open("coords.xml", 'w')
    coordsheader(coordsfile)

api=tesseract.TessBaseAPI()
api.SetOutputName("outputName")
api.Init(".",options.language,tesseract.OEM_DEFAULT)
api.SetPageSegMode(tesseract.PSM_AUTO);

result=tesseract.ProcessPagesWrapper(imgtemp.name,api) + ""
        
result = result.replace("\n","")
result = result.replace("\t","")
result = result.strip()
#print "len", len(result)

if len(result) > 0:
    # print "%d - TIF Result= %s" % (len(result),result)
    file.write("%s\n"%result)

    if options.coords:
        coordtemp = tempfile.NamedTemporaryFile()
        result = tesseract.ExtractResultsWrapper(api, coordtemp.name)
        #print "len", result
        ocr2coords(SCALE, height * SCALE, coordtemp.name, coordsfile)

file.close()
            
if options.coords:
    coordsfile.write("</words>\n")
    coordsfile.close()
