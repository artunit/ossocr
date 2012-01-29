#!/usr/bin/python

# some common conversions if not using wavelet
# most effective seems to be radius 50, amount 10, threshold 0 
# convert -unsharp 2x1.5+2.0+1.0 -resize 200% -density 300x300
# convert -unsharp 10x1.5+2.0+1.0 -resize 200% -density 300x300 -type Grayscale test.jpg new.jpg
# convert -density 300x300 -type Grayscale test.pdf test.jpg

from array import array
import json, os, tempfile
import tesseract
import traceback
import Image
import sys,os,re,glob
import urllib
import cStringIO

TEMP_DIR = "/tmp/"
SCALE    = 1
IS_VALID = re.compile('[a-z|A-Z|0-9|\.|\'|\"|\s]')
IS_STOP  = re.compile('[\.|,|;|\s]')

def coordsheader(coordfile):
    coordfile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    coordfile.write("<words>\n")

def ocr2coords(scale, height, coordsin, coordsfile):
    """ Pull together coordinate information in XML format """

    char = word = ""
    x0 = y0 = x1 = y1 = 0
    tcx0 = tcy0 = tcx1 = tcy1 = 0
    xl = yl = xr = yr = 0
    adj_y = 0

    infile = open(coordsin,"r")
    for line in infile:
        #print line
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

                #adjust for proportional font
                if adj_y > tcy1:
                    y1 = height - adj_y
                if adj_y == 0:
                    y1 = height - tcy1

                #print "adj_y is now %d - tcy1 %d" % (adj_y,tcy1)
                adj_y = tcy1

        if len(word) == 0:
            x0 = tcx0
            y0 = tcy0
            x1 = tcx1
            adj_y = 0

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
            tcy1 = 0

        if not stopChar and len(entries) == 5:
           xl = round(tcx0/scale)
           xr = round(tcx1/scale)
           yl = round(tcy0/scale)
           yr = round(tcy1/scale)

    if len(word) > 0:
        coordsfile.write("<word x1=\"%d\" y1=\"%d\">\n%s\n<ends x2=\"%d\" y2=\"%d\"/>\n</word>\n" %
            (x0,y1,word,xr,yl))

def ocr2hadoop(filename, scale, height, coordsin):
    """ Pull together coordinate information in Hadoop stream-friendly format """

    char_cnt = 0
    line_cnt = 0
    char = word = ""
    x0 = y0 = x1 = y1 = 0
    tcx0 = tcy0 = tcx1 = tcy1 = 0
    xl = yl = xr = yr = 0
    adj_y = 0

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

                #adjust for proportional font
                if adj_y > tcy1:
                    y1 = height - adj_y
                if adj_y == 0:
                    y1 = height - tcy1

                adj_y = tcy1

        if len(word) == 0:
            x0 = tcx0
            y0 = tcy0
            x1 = tcx1
            adj_y = 0

        if len(entries) == 5 and not stopChar:
            word += char
            char_cnt = char_cnt + 1

        if (len(entries) == 4 or stopChar) and len(word) > 0:

            x0 = round(x0/scale)
            y0 = round(y0/scale)
            x1 = round(x1/scale)
            y1 = round(y1/scale)

            #note that we swap Y values because of changing the orientation
            if x0 >= 0 and y0 >=0 and x1 >=0 and y1 >=0:
                    print "%ld\t%s_%06d\t%s\t%d\t%d\t%d\t%d" % (char_cnt,filename,line_cnt,word,x0,y1,xr,yl)
                    line_cnt = line_cnt + 1
            word = ""

        if not stopChar and len(entries) == 5:
           xl = round(tcx0/scale)
           xr = round(tcx1/scale)
           yl = round(tcy0/scale)
           yr = round(tcy1/scale)

    if len(word) > 0:
        print "%ld\t%s_%06d\t%s\t%d\t%d\t%d\t%d" % (char_cnt,filename,line_cnt,word,x0,y1,xr,yl)


def alert(*args):
    sys.stderr.write(" ".join([str(x) for x in args]))
    sys.stderr.write("\n")

from optparse import OptionParser

parser = OptionParser(usage="""
%prog [options] image1 

Possible choices are:

--file -- specify input file, use for standalone, non-hadoop processing
--hadoop -- default, coordinate information written out for streaming
--scale -- resize image for OCR processing
--language -- tesseract language code
--coords -- write coordinate information
--output -- specify output file, defaults to ocr.txt

""")


# options
parser.add_option("-f","--file",help="input file",default=None)
parser.add_option("-s","--scale",help="scale for resize",default=SCALE)
parser.add_option("-l","--language",help="language for OCR",default="eng")
parser.add_option("-c","--coords",help="write coordinates in XML",default=False)
parser.add_option("-g","--hadoop",help="write coordinates information in hadoop grid format",default=True)
parser.add_option("-o","--output",help="specify output file",default="ocr.txt")

(options,args) = parser.parse_args()

img_source = None

if options.file:
    img_source = [options.file]
else:
    img_source = sys.stdin

for img_name in img_source:
    img_name = img_name.rstrip()

    SCALE = int(options.scale)

    #hadoop is very strange about this, works much better if using temp directory
    if options.file:
        img = Image.open(img_name)
    else:
        #used for S3 buckets with AWS
        if img_name.startswith('http'):
            file = urllib.urlopen(img_name)
            imgStrIO = cStringIO.StringIO(file.read()) # constructs a StringIO holding the image
            img = Image.open(imgStrIO)
        else:
            img = Image.open(TEMP_DIR + img_name)

    width, height = img.size

    if SCALE > 1 and not options.hadoop:
    	print "sizing %s from %d x %d to %d x %d" % (args[0], width, height, (width *SCALE), (height * SCALE))

    #options are BICUBIC, NEAREST, BILINEAR, and ANTIALIAS
    img = img.resize((width * SCALE, height * SCALE), Image.BICUBIC)

    # we work from temporary file in TIFF format
    imgtemp = tempfile.NamedTemporaryFile()
    img.save(imgtemp.name,"TIFF")

    file = None

    if options.file:
        file = open(options.output, 'w')

    # Now start the output of coord info
    if options.coords:
        options.hadoop = False
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

    if len(result) > 0:
        # print "%d - TIF Result= %s" % (len(result),result)
        if not options.hadoop:
            file.write("%s\n"%result)

        if options.coords or options.hadoop:
            coordtemp = tempfile.NamedTemporaryFile()
            result = tesseract.ExtractResultsWrapper(api, coordtemp.name)
            #print "len", result
            if options.coords:
                 ocr2coords(SCALE, height * SCALE, coordtemp.name, coordsfile)
            else:
                 ocr2hadoop(img_name, SCALE, height * SCALE, coordtemp.name)

    if options.file:
        file.close()
            
if options.coords:
    coordsfile.write("</words>\n")
    coordsfile.close()
