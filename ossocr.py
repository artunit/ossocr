#!/usr/bin/env python

"""
ossocr.py - work with tesseract api for extracting coordinates in a hadoop-friendly manner
- art rhyno <http://projectconifer.ca/>

(c) Copyright GNU General Public License (GPL)
"""

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
IS_STOP  = re.compile('\s')
#IS_STOP  = re.compile('[\.|,|;|\s]')

"""
line_seg - a segment of a line
"""
class line_seg:
    def __init__(self, ident, x0, y0, x1, y1, size):
        self.ident = ident
        self.x0 = x0
        self.x1 = x1
        self.y0 = y0
        self.y1 = y1
        self.size = float(size)
        self.width = x1 - x0
        self.height = y1 - y0

"""
pg_line - a segment that has been identified as a full line
"""
class pg_line:
    def __init__(self, y0, y1):
        self.y0 = y0
        self.y1 = y1

"""
page_square - a box on the image
"""
class page_square:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = int(x0)
        self.y0 = int(y0)
        self.x1 = int(x1)
        self.y1 = int(y1)

""" start the xml output """
def coordsheader(coordfile):
    coordfile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    coordfile.write("<words>\n")

""" pull together coordinate information in file or Hadoop stream-friendly format """
def ocr2coords(filename, scale, height, coordsin, coordsfile, 
    img_width, img_height, img_x0, img_y0, pg_box, char_cnt_base, word_cnt_base
    ):

    char_cnt = char_cnt_base
    word_cnt = word_cnt_base
    char = word = ""
    x0 = y0 = x1 = y1 = 0
    coord_x0 = coord_y0 = coord_x1 = coord_y1 = 0
    tcx0 = tcy0 = tcx1 = tcy1 = 0
    xl = yl = xr = yr = 0

    infile = open(coordsin,"r")
    if pg_box and coordsfile is None:
       print "%ld\t%s_%d_%d_%010d_%015ld\t%d_%d_%d_%d\t-1\t-1\t-1\t-1" % (char_cnt,
                         filename,img_width,img_height,word_cnt,char_cnt,
                         pg_box[0],pg_box[1],pg_box[2],pg_box[3])
       char_cnt += 1
    for line in infile:
        entries = line.split()

        #drop anything that can't be encoded
        try:
            char = entries[0].encode('utf-8',errors='strict')
        except:
            char = ''

        stopChar = False

        if len(char) > 0:
            if len(entries) == 5:
               coord_x0 = round((int(entries[1]) + img_x0)/scale)
               coord_y0 = round((int(entries[4]) + img_y0)/scale)
               coord_x1 = round((int(entries[3]) + img_x0)/scale)
               coord_y1 = round((int(entries[2]) + img_y0)/scale)

               if coordsfile is None:
                  print "%ld\t%s_%d_%d_%010d_%015ld\t%s\t%d\t%d\t%d\t%d" % (char_cnt,
                     filename,img_width,img_height,
                     word_cnt,char_cnt,char, 
                     coord_x0,
                     coord_y0,
                     coord_x1,
                     coord_y1)
               char_cnt += 1

               stopChar = re.search(IS_STOP, char)
               if not stopChar:
                  tcx0 = coord_x0
                  tcy0 = coord_y0
                  tcx1 = coord_x1
                  tcy1 = coord_y1

                  #tesseract works from the bottom up for Y but we need to work from the top
                  tcy1 = height - tcy1

                  #adjust for proportional font
                  if (height - tcy0) < y0 and (height - tcy0) > 0:
                     y0 = height - tcy0
                  if y0 == 0:
                     y0 = height - tcy0

            if len(word) == 0:
               x0 = tcx0
               x1 = tcx1
               y1 = tcy1

            if len(entries) == 5 and not stopChar:
               word += char
                
            if len(entries) == 4:
               if coordsfile is None:
                    print "%ld\t%s_%d_%d_%010d_%015ld\tspace\t0\t0\t0\t0" % (char_cnt,
                         filename,img_width,img_height,word_cnt,char_cnt)
               char_cnt += 1

            if (len(entries) == 4 or stopChar) and len(word) > 0:
               x0 = round(x0/scale)
               y0 = round(y0/scale)
               x1 = round(x1/scale)
               y1 = round(y1/scale)

               if x0 >= 0 and y0 >=0 and x1 >=0 and y1 >=0:
                  if coordsfile: 
                     coordsfile.write("<word x1=\"%d\" y1=\"%d\">\n%s\n<ends x2=\"%d\" y2=\"%d\"/>\n</word>\n" %
                         (x0,y0,word,xr,yr))
                  else:
                     print "%ld\t%s_%d_%d_%010d\t%s\t%d\t%d\t%d\t%d" % (char_cnt,
                         filename,img_width,img_height,word_cnt,word,x0,y0,xr,yr)
                  y0 = 0
                  word_cnt += 1
               word = ""

            if not stopChar and len(entries) == 5:
               xr = round(tcx1/scale)
               yr = round(tcy1/scale)

    if len(word) > 0:
       if coordsfile:
          coordsfile.write("<word x1=\"%d\" y1=\"%d\">\n%s\n<ends x2=\"%d\" y2=\"%d\"/>\n</word>\n" %
               (x0,y0,word,xr,yr))
       else:
          print "%ld\t%s_%d_%d_%010d\t%s\t%d\t%d\t%d\t%d" % (char_cnt,filename,
               img_width,img_height,word_cnt,word,x0,y0,xr,yl)
    return char_cnt, word_cnt

""" utility alert function """
def alert(*args):
    sys.stderr.write(" ".join([str(x) for x in args]))
    sys.stderr.write("\n")


""" combine segs based on ident """
def sortOutSegs(lines,ident,x0,y0,x1,y1,size):
    for seg in lines:
        if seg.ident == ident:
           seg.size += size
           if x0 < seg.x0:
              seg.width += abs(seg.x0 - x0)
              seg.x0 = x0
           if y0 < seg.y0:
              seg.height += abs(seg.y0 - y0)
              seg.y0 = y0
           if x1 > seg.x0 + seg.width:
              seg.width += abs(seg.x0 - x1)
           if y1 > (seg.y0 + seg.height):
              seg.height = y1 - seg.y0
              seg.y1 = y1
           break

""" combine lines based on proximity """
def sortOutLines(lines,width,left_margin,right_margin,line_span,skip_threshold):
    i=0
    comb_lines = []
    for line in lines:
        if line.x0 < (width - left_margin) and line.x0 > right_margin:
           seg_match = False
           for seg in comb_lines:
               if abs(seg.x0 - line_span) <= line.x0 and (seg.x0 + line_span) >= line.x0: 

                  #lines may align but skip too great a distance to be considered the same
                  current_gap = 0
 
                  if line.y0 < seg.y1 and line.y1 > seg.y0:
                     current_gap = 0
                  elif seg.y0 < line.y1 and seg.y1 > seg.y0:
                     current_gap = 0
                  elif seg.y0 > line.y1:
                     current_gap = seg.y0 - line.y1
                  elif line.y0 > seg.y1:
                     current_gap = line.y0 - seg.y1
           
                  if current_gap < skip_threshold:
                     sortOutSegs(comb_lines,seg.ident,line.x0,line.y0,line.x1,line.y1,line.size)
                     seg_match = True
                     break

           if seg_match is False:
              comb_lines.append(line_seg(i,line.x0,line.y0,line.x1,line.y1,line.size))
              i+=1
    return comb_lines

""" use lines to determine page squares """
def sortOutSquares(lines,iwidth,iheight,high_ind):

    squares = []
    #add line to each side of image
    lines.append(line_seg(0,0,0,0,iheight,0))
    lines.append(line_seg(high_ind,iwidth,0,iheight,iheight,0))

    #move from bottom to top of image
    sq_lines = sorted(lines, key=lambda seg: seg.y0)
    #then put in left to right order
    sq_lines = sorted(sq_lines, key=lambda seg: seg.x0)

    #we start at the far right and move backwards
    for seg in reversed(sq_lines):
        #print "incoming-> ident: %d x0: %d y0: %d height: %d" % (seg.ident,seg.x0,seg.y0,seg.height)

        marked_lines=[]
        lowest_y = iheight
        highest_y = 0

        #now look for lines behind this line to connect square to
        for back_seg in reversed(sq_lines):
            box_y0 = back_seg.y0 
            box_y1 = back_seg.y0 + back_seg.height

            if back_seg.ident < seg.ident and (back_seg.y0 < lowest_y or box_y1 > highest_y): 
               #does the line overlap at all? no square unless it can be connected
               if (  (back_seg.y0 >= seg.y0 and (seg.y0 + seg.height) <= box_y1) or 
                     (back_seg.y0 <= seg.y0 and box_y1 >= seg.y0) or 
                     (back_seg.y0 >= seg.y0 and box_y1 <= (seg.y0 + seg.height))
                  ):

                  box_x0 = back_seg.x0
                  box_y0 = back_seg.y0

                  #box will connect at y values that meet
                  if box_y0 < seg.y0:
                     box_y0 = seg.y0
                  box_x1 = seg.x0
                  box_y1 = back_seg.y0 + back_seg.height
                  if box_y1 > (seg.y0 + seg.height):
                     box_y1 = seg.y0 + seg.height

                  #we need to deal with lines behind lines
                  overlap = seg_checked = False
                  #seg_boxes represent boxes with line coordinates
                  seg_boxes = []
                  while not seg_checked:
                        #adjust y values for existing boxes, y values of defined boxes are kept in marked_lines
	                for bounds in marked_lines:
                            if box_y0 >= bounds.y0 and box_y0 < bounds.y1 and box_y1 > bounds.y1:
                               box_y0 = bounds.y1
                            elif box_y0 <= bounds.y0 and box_y1 > bounds.y0:
                               if box_y1 > bounds.y1:
                                  seg_boxes.append(pg_line(bounds.y1,box_y1))
                               box_y1 = bounds.y0
                            elif (box_y0 >= bounds.y0 and box_y1 <= bounds.y1) or (box_y0 > box_y1):
                               overlap = True
                               break
                     
                        if not overlap and box_y1 > box_y0: 
                           marked_lines.append(pg_line(box_y0,box_y1))
                           squares.append(page_square(box_x0,box_y0,box_x1,box_y1))

                        #if a line behind completely overlaps, we are done
                        if len(seg_boxes) > 0:
                           """
                           here we have a line behind that is smaller, we have already snagged the top
                           box and now send through the actual overlap
                           """
                           box_y0 = seg_boxes[0].y0
                           box_y1 = seg_boxes[0].y1
                           seg_boxes.pop(0)
                        else:
                           seg_checked = True

                        #identify longest lines so that we don't bother with lines that completely overlap
                        if ( back_seg.y0 < lowest_y and 
                             (back_seg.y0 + back_seg.height) > highest_y
                           ):
                                  
                           lowest_y = back_seg.y0
                           highest_y = back_seg.y0 + back_seg.height
    return squares

""" look for lines from pasted-up newspapers """
def pasteUpLines(im_width,im_height,lines_file,line_gap,col_threshold,v_threshold,
                 h_threshold,l_margin,r_margin,angle_div,comb_num,skip_threshold
    ):

    x0 = y0 = x1 = y1 = 0
    lines = []

    i=0
    file = open(lines_file, 'r')
    for line in file:
        line = line.strip()
        x0, y0, x1, y1, size, angle, nfa  = line.split(' ', 7)

        if (abs(float(x1) - float(x0)) < v_threshold and 
           (abs(float(y1) - float(y0)) > h_threshold) and 
           abs(float(y1) - float(y0))/angle_div > abs(float(x1) - float(x0))
           ):

           line_x0 = float(x0)
           line_x1 = float(x1)
           if line_x0 > line_x1:
              line_x1 = line_x0
              line_x0 = float(x1)
           line_y0 = float(y0)
           line_y1 = float(y1)
           if line_y0 > line_y1:
              line_y1 = line_y0
              line_y0 = float(y1)
          
           lines.append(line_seg(i,line_x0,line_y0,line_x1,line_y1,size))
           i+=1
    file.close()

    #sort from top to bottom of image
    lines = sorted(lines, key=lambda seg:seg.y0)
    #now put in x order
    lines = sorted(lines, key=lambda seg:seg.x0)

    for n in range(0, comb_num):
        if n > 0:
           lines = sortOutLines(lines,im_width,0,0,line_gap,skip_threshold)
        else:
           lines = sortOutLines(lines,im_width,l_margin,r_margin,line_gap,skip_threshold)

    last_seg = 0
    box_x0 = 0
    box_y0 = 0
    box_x1 = 0
    box_y1 = 0

    lines = sorted(lines, key=lambda seg: seg.y0)
    lines = sorted(lines, key=lambda seg: seg.x0)

    final_lines = []
    i = len(lines)
    last_x0 = last_y0 = last_y1 = 0

    for seg in reversed(lines):
        if (seg.height > col_threshold and 
           ((seg.x0 + col_threshold) < last_x0 or 
           seg.y1 < last_y0 or seg.y0 > last_y1)
           ):

           final_lines.append(line_seg(i,seg.x0,seg.y0,seg.x1,seg.y1,seg.size))
           i-=1
           last_x0 = seg.x0
           last_y0 = seg.y0
           last_y1 = seg.y1

    return sortOutSquares(final_lines,im_width,im_height,len(lines)+1)


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
--lines -- specify lines segment file
--line_gap -- specify gap value for combining lines
--box_threshold -- smallest height for box
--col_threshold -- smallest width for column
--v_threshold -- smallest height for a line (remember that letters contain lines)
--h_threshold -- largest value allowed between x coords (otherwise is too sloped)
--l_margin -- how far out a line is valid from the left for creating box
--r_margin -- how far out a line is valid from the right for creating box
--angle_div -- value to divide difference of y coords to difference of x
--comb_num -- how many tries to combine lines
--skip_threshold -- gap that determines whether coords represent  a new line

""")

# options
parser.add_option("-f","--file",help="input file",default=None)
parser.add_option("-s","--scale",help="scale for resize",default=SCALE)
parser.add_option("-l","--language",help="language for OCR",default="eng")
parser.add_option("-c","--coords",help="write coordinates in XML",default=False)
parser.add_option("-g","--hadoop",help="write coordinates information in hadoop grid format",default=True)
parser.add_option("-o","--output",help="specify output file",default="ocr.txt")
parser.add_option("-d","--lines",help="specify lines segment file",default=None)
parser.add_option("-e","--line_gap",help="specify gap value for combining lines",default=75)
parser.add_option("-b","--box_threshold",help="smallest height for box",default=10)
parser.add_option("-u","--col_threshold",help="smallest width for column",default=200)
parser.add_option("-y","--v_threshold",help="height for a line (remember that letters contain lines)",default=50)
parser.add_option("-x","--h_threshold",help="largest value allowed between x coords (otherwise is too sloped)",default=100)
parser.add_option("-m","--l_margin",help="how far out a line is valid from the left for creating box",default=400)
parser.add_option("-r","--r_margin",help="how far out a line is valid from the right for creating box",default=100)
parser.add_option("-a","--angle_div",help="value to divide difference of y coords to difference of x",default=4)
parser.add_option("-n","--comb_num",help="how many tries to combine lines",default=2)
parser.add_option("-k","--skip_threshold",help="gap that determines whether coords represent a new line",default=100)

(options,args) = parser.parse_args()

coordsfile = img_source = None

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
    char_cnt_base = word_cnt_base = 0

    if SCALE > 1 and not options.hadoop:
    	print "sizing %s from %d x %d to %d x %d" % (args[0], width, height, (width *SCALE), (height * SCALE))

    #options are BICUBIC, NEAREST, BILINEAR, and ANTIALIAS
    img = img.resize((width * SCALE, height * SCALE), Image.BICUBIC)

    # we work from temporary file in TIFF format
    imgtemp = tempfile.NamedTemporaryFile()
    img.save(imgtemp.name,"TIFF")
    sqimgname = tmpimgname = imgtemp.name

    file = None
    pg_box = None

    pg_squares = []
    pg_squares.append(page_square(0,0,width,height))
    if options.hadoop is True or options.lines:
       img_info = img_name.split('.')
       img_base = img_info[0]
       if os.path.isfile(TEMP_DIR + img_base + ".txt"):
          pg_squares = pasteUpLines(width,height,TEMP_DIR + img_base + ".txt",
             options.line_gap,options.col_threshold,options.v_threshold,options.h_threshold,
             options.l_margin,options.r_margin,options.angle_div,options.comb_num,
             options.skip_threshold)

    api=tesseract.TessBaseAPI()
    api.SetOutputName("outputName")
    api.Init(".",options.language,tesseract.OEM_DEFAULT)
    api.SetPageSegMode(tesseract.PSM_AUTO);

    if options.file:
       file = open(options.output, 'w')


    #now start the output of coord info
    if options.coords:
       options.hadoop = False
       coordsfile = open("coords.xml", 'w')
       coordsheader(coordsfile)

    i = 0
    for square in pg_squares:
        x0 = square.x0
        y0 = square.y0
        x1 = square.x1
        y1 = square.y1
        if len(pg_squares) > 1:
           tmpimgname = "%s_%d.tif" % (sqimgname,i)
           if (square.y1 - square.y0) > options.box_threshold:
              i+=1
              x0 -= options.line_gap
              if x0 < 0:
                 x0 = 0
              y0 -= options.line_gap
              if y0 < 0:
                 y0 = 0
              x1 += options.line_gap
              if x1 > width:
                 x1 = width
              y1 += options.line_gap
              if y1 > height:
                 y1 = height
              pg_box = (x0,y0,x1,y1)
              region = img.crop(pg_box)
              region.save(tmpimgname,"TIFF")
              y0 = (height - y1) 
        else:
          x0 = 0
          y0 = 0
          x1 = 0
          y1 = 0

        result = ""
        if (square.y1 - square.y0) > options.box_threshold:
           orig_result=tesseract.ProcessPagesWrapper(tmpimgname,api) + ""
           result = orig_result.replace("\n","")
           result = result.replace("\t","")
           result = result.strip()

        if len(result) > 0:
            # print "RESULTS-------------------------------------->"
            # print "%d - Result= %s" % (len(result),result)
            # print "<--------------------------------------RESULTS"
            if not options.hadoop:
                file.write("%s\n"%result)

            coordtemp = tempfile.NamedTemporaryFile()
            result = tesseract.ExtractResultsWrapper(api, coordtemp.name, len(orig_result),"")
            #print "len", result
            char_cnt_base, word_cnt_base = ocr2coords(img_name, SCALE, height * SCALE, 
                coordtemp.name, coordsfile, width, height, round(x0), round(y0), pg_box,
                char_cnt_base, word_cnt_base)
            imgtemp.close()

        if os.path.isfile(tmpimgname):
           os.remove( tmpimgname)

    if options.file:
       file.close()
            
    if options.coords:
        coordsfile.write("</words>\n")
        coordsfile.close()
