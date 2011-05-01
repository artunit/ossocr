#!/usr/bin/python

# some common conversions
# most effective seems to be radius 50, amount 10, threshold 0
# convert -unsharp 2x1.5+2.0+1.0 -resize 200% -density 300x300
# convert -unsharp 10x1.5+2.0+1.0 -resize 200% -density 300x300 -type Grayscale test.jpg new.jpg
# convert -density 300x300 -type Grayscale test.pdf test.jpg

from array import array
import Image, TiffImagePlugin
import os, tempfile

import pygtk
pygtk.require("2.0")
import gtk

import matplotlib
matplotlib.rcParams["interactive"] = 1
matplotlib.use('TkAgg') # Qt4Agg

from pylab import *
import traceback
import tesseract

import Image

# import resource 
# resource.setrlimit(resource.RLIMIT_DATA,(2e9,2e9))

import sys,os,re,glob
import ocrolib
from ocrolib import plotutils
from ocrolib import hocr
from ocrolib import common

ion()
hold(False)

IS_VALID = re.compile('[a-z|A-Z|0-9|\.|\'|\"|\s]')
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

def ocr2coords(ocrresult, baseX, baseY, scale, height):
    xmlfrag = ""
    word = ""
    words = ocrresult.split('\n')
    xl = yl = xr = yr = 0
    for letter in words:
        chars = letter.split()
        # print "-> %s %d %d" % (letter, len(letter),len(chars))
        if len(chars) == 5:
            try:
                charStr = "%s" % chars[0]
                charTest = re.search(IS_VALID, charStr)
                if charTest:
                    char = unicode(charStr, "utf-8")
                    x0 = int(chars[1])
                    y0 = int(chars[2])
                    x1 = int(chars[3])
                    y1 = int(chars[4])
                    # print "%s - %d,%d,%d,%d" % (char,x0,y0,x1,y1)
                    charWidth = y1 - y0
                    if xl == 0 and xr == 0:
                        xmlfrag += ("%d %d charWidth %d %d\n" % (y0,y1,charWidth,height))
                        xmlfrag += ("%d %d baseX x0\n" % (baseX,x0))
                        xl = round((baseX + x0)/scale)
                        yl = (height - y0) - charWidth
                        xmlfrag += ("%d %d baseY y0\n" % (baseY,y0))
                        yl = round((baseY + yl)/scale)
                    xr = round((baseX + x1)/scale)
                    yr = (height - y1) + charWidth
                    yr = round((baseY + y1)/scale)
                    # xmlfrag += ("%s - %d,%d,%d,%d\n" % (char,x0,y0,x1,y1))
                    word += char
            except:
                traceback.print_exc()
                pass
        else:
            if len(word) > 0:
                xmlfrag += ("<word x1=\"%d\" y1=\"%d\">\n%s\n<ends x2=\"%d\" y2=\"%d\"/>\n</word>\n" % 
                    (xl,yl,word,xr,yr))
                word = ""
            xl = yl = xr = yr = 0

    return xmlfrag

def alert(*args):
    sys.stderr.write(" ".join([str(x) for x in args]))
    sys.stderr.write("\n")

from optparse import OptionParser
prefix = "/usr/local/share/ocropus/models/"
parser = OptionParser(usage="""
%prog [options] image1 image2 ...

Recognize pages using built-in OCRopus components.  This first
uses the page cleaner, then the page segmenter, then the line
recognizers, and finally the language model.

The following components take files as arguments, and those files
are loaded in various ways.

--linerec -- line recognizer (.pymodel, .cmodel, or .model)
--fst -- language model (OpenFST language model dump)

If you want to see what's going on, run ocropus-pages with the "-d" option
("-D" for continuous output, but this slows down recognition significantly).
With the "-L" option, you also see each text line as it's being recognized.

(For even more insight into what is going on during recognition, use the
ocropus-showpsegs and ocropus-showlrecs commands.)

Advanced Usage:

You can choose from a number of components for the different
processing stages.  See the output of "ocropus components" for your
choices.

Possible choices are:

--clean (ICleanupGray) -- binarization, denoising, deskewing
--pseg (ISegmentPage) -- page segmentation
--ticlass (ITextImageSegmentation) -- text/image segmentation (off by default)

For each component, you can pass additional parameters.  For example,
--clean StandardPreprocessing:rmbig_minaspect=0.1 uses an instance of
StandardPreprocessing for cleanup and sets its rmbig_minaspect
parameter to 0.1.  You can see a list of all the parameters with
"ocropus params StandardPreprocessing".

Instead of component names, you can also pass the names of
constructors of Python classes for each of those components, as in
"--clean my.CleanupPage:threshold=0.3" or "--clean
my.CleanupPage(0.3)".  This will import the "my" package and then call
the constructor.
""")

# additions
parser.add_option("-s","--scale",help="scale for resize",default=SCALE)
parser.add_option("-l","--language",help="language for OCR",default="eng")
parser.add_option("-r","--region",help="region for page",default="lines")
parser.add_option("-c","--coords",help="write coordinates in XML",action="store_true")
parser.add_option("-o","--output",help="specify output file",default="ocr.txt")

# original
parser.add_option("-C","--clean",help="page cleaner",default="StandardPreprocessing")
parser.add_option("-P","--pseg",help="line segmenter",default="SegmentPageByRAST")
parser.add_option("-T","--ticlass",help="text image segmenter",default=None)
parser.add_option("-m","--linerec",help="linerec model",default=prefix+"default.model")
parser.add_option("-f","--fst",help="fst langmod",default=prefix+"default.fst")
parser.add_option("-w","--lweight",help="weight for the language model",type="float",default=1.0)
parser.add_option("-v","--verbose",help="verbose",action="store_true")
parser.add_option("-x","--hocr",help="output XHTML+hOCR",action="store_true")
parser.add_option("-p","--plain",help="output plain text",action="store_true")
parser.add_option("-i","--dpi",help="resolution in dpi",default=200,type=int)
parser.add_option("-S","--silent",action="store_true",help="disable warnings")
parser.add_option("-B","--beam",help="size of beam in beam search",type="int",default=1000)

(options,args) = parser.parse_args()

if len(args)==0:
    parser.print_help()
    sys.exit(0)

SCALE = int(options.scale)

filelist = []

img = Image.open(args[0])
width, height = img.size

if SCALE > 1:
    print "sizing %s from %d x %d to %d x %d" % (args[0], width, height, (width *SCALE), (height * SCALE))

#options are BICUBIC, NEAREST, BILINEAR, and ANTIALIAS
img = img.resize((width * SCALE, height * SCALE), Image.BICUBIC)

# we work from temporary file in PNG format
imgtemp = tempfile.NamedTemporaryFile()
img.save(imgtemp.name,"PNG")

filelist.append(args[0])

# FIXME add language model weights
assert options.lweight==1.0,"other language model weights not implemented yet"


# Create/load the various recognition components.  Note that you can pass parameters
# to any of these using the syntax documented under ocrolib.make_component.

# The preprocessor: removes noise, performs page deskewing, and other cleanup.
preproc = ocrolib.make_IBinarize(options.clean)

# The page segmenter.
segmenter = ocrolib.make_ISegmentPage(options.pseg)

# The line recognizer.  Note that this is loaded, not instantiated.
# You can pass x.model, x.cmodel, and x.pymodel, which loads a C++
# line recognizer, a C++ character recognizer, or a pickled Python line
# recognizer respectively.
linerec = ocrolib.load_linerec(options.linerec)
alert("[note]","line recognizer:",linerec)

# The language model, loaded from disk.
lmodel = ocrolib.OcroFST()
lmodel.load(options.fst)

# The text/image segmenter, if given.
ticlass = None
if options.ticlass is not None:
    ticlass = ocrolib.make_ITextImageClassification(options.ticlass)

file = open(options.output, 'w')

# Now start the output of coord info
if options.coords:
    coordsfile = open("coords.xml", 'w')
    coordsheader(coordsfile)

# Now start the output with printing the hOCR header if hOCR output has been requested.
if options.hocr:
    print hocr.header()

# Iterate through the pages specified by the argument.  Since this can be somewhat tricky
# with TIFF files, we use the page_iterator abstraction that takes care of all the special
# cases.  But basically, this just gives us one gray image after another, plus the file name.
pageno = 0


for page_gray,pagefile in ocrolib.page_iterator(filelist):

    pageno += 1
    sys.stderr.write("[note] *** %d %s ***\n"%(pageno,pagefile))

    # Output geometric page information.
    # FIXME add: bbox, ppageno
    if options.hocr: 
        print "<div class='ocr_page' id='page_%d' ppageno='%d' image='%s'>"% \
            (pageno,pageno,pagefile)

    # Perform cleanup and binarization of the page.
    page_bin,page_gray = preproc.binarize(page_gray)

    if not options.silent:
        if ocrolib.quick_check_page_components(page_bin,dpi=options.dpi)<0.5:
            continue

    # Black out images in the binary page image.
    # This will cause images to be treated as non-text blocks
    # by the page segmenter.
    if ticlass is not None:
        ocrolib.blackout_images(page_bin,ticlass)

    # Perform page segmentation into text columns and text lines.
    page_seg = segmenter.segment(page_bin)

    # Now iterate through the text lines of the page, in reading order.
    # We use the RegionExtractor utility class for that.  The page_seg image
    # is just an RGB image, see http://docs.google.com/Doc?id=dfxcv4vc_92c8xxp7
    regions = ocrolib.RegionExtractor()
    if options.region.find("column"):
        regions.setPageColumns(page_seg)
    elif options.region.find("para"):
        regions.setPageParagraphs(page_seg)
    else:
        regions.setPageLines(page_seg)
    #regions.setPageLines(page_seg)

    # If there are too many text lines, probably something went wrong with the
    # page segmentation. (FIXME: make this more flexible)
    # if regions.length()>150:
    if regions.length()>10000:
        alert("[error] too many lines (%d), probably bad input; skipping"%regions.length())
        continue

    alert("[note]",pagefile,"lines:",regions.length())
    api=tesseract.TessBaseAPI()
    api.SetOutputName("outputName")
    #api.Init(".","eng",tesseract.OEM_DEFAULT)
    api.Init(".",options.language,tesseract.OEM_DEFAULT)
    api.SetPageSegMode(tesseract.PSM_AUTO);
    #mainIm = Image.open("np.png")
    mainIm = Image.open(imgtemp.name)

    for i in range(1,regions.length()):
        line = regions.extract(page_bin,i,1) # might use page_gray
        if ocrolib.quick_check_line_components(line,dpi=options.dpi)<0.5:
            continue

        # print "tmp%d=%d %d %d %d"% (i,regions.x0(i),regions.y0(i),regions.x1(i),regions.y1(i))

        x0 = regions.x0(i) * SCALE
        y0 = regions.y0(i) * SCALE
        x1 = regions.x1(i) * SCALE
        y1 = regions.y1(i) * SCALE

        box = (x0,y0,x1,y1)
        smBox = mainIm.crop(box)
        smBox.save(imgtemp.name + str(i) + ".tif","TIFF")

        # you can save the regions in individual files
        # smBox.save(str(x0) + "-" + str(y0) + "," + str(x1) + "-" + str(y1) + "-tmp" + str(i) + ".tif","TIFF")
        imgHeight = y1 - y0

        # this is where tesseract is invoked
        result=tesseract.ProcessPagesWrapper(imgtemp.name + str(i) + ".tif",api) + ""
        result = result.replace("\n","")
        result = result.replace("\t","")
        result = result.strip()
        if len(result) > 0:
            # print "%d - TIF Result= %s" % (len(result),result)
            '''
            file.write("%d %d %d %d: %s\n" % (round(regions.x0(i)/SCALE),
                round(regions.y0(i)/SCALE),round(regions.x1(i)/SCALE),
                round(regions.y1(i)/SCALE), result))
            '''
            file.write("%s\n"%result)
            # result=tesseract.ExtractResultsWrapper(api) + ""
            if options.coords:
                result=ocr2coords(tesseract.ExtractResultsWrapper(api), (regions.x0(i) * SCALE), 
                    (regions.y0(i) * SCALE), SCALE, imgHeight)
                coordsfile.write(result);

        try:
            os.unlink(imgtemp.name + str(i) + ".tif")
        except: pass

    # Close off the DIV for the page.
    if options.hocr:
        print "</div>"

file.close()
            
if options.coords:
    coordsfile.close()

if options.hocr:
    print hocr.footer()
