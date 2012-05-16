#!/usr/bin/python

import sys

class hOCR_Column:
    def __init__(self, paras, x0, y0, x1, y1):
        self.hocr_paras = paras[:]
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

class hOCR_Para:
    def __init__(self, lines, x0, y0, x1, y1):
        self.hocr_lines = lines[:]
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

class hOCR_Line:
    def __init__(self, words, x0, y0, x1, y1):
        self.hocr_words = words[:]
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

class hOCR_Word:
    def __init__(self, word, x0, y0, x1, y1):
        self.hocr_word = word
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

def hocrheader(hocrfile):
    hocrfile.write("<!DOCTYPE html PUBLIC ")
    hocrfile.write("\"-//W3C//DTD HTML 4.01 Transitional//EN\" ")
    hocrfile.write("\"http://www.w3.org/TR/html4/loose.dtd\">\n")
    hocrfile.write("<html>\n")
    hocrfile.write("<head>\n")
    hocrfile.write("<title></title>\n")
    hocrfile.write("<meta http-equiv=\"Content-Type\" content=\"text/html;charset=utf-8\" />\n")
    hocrfile.write("<meta name=\"ocr-system\" content=\"tesseract\"/>\n")
    hocrfile.write("</head>\n")
    hocrfile.write("<body>\n")

def hocrfooter(hocrfile):
    hocrfile.write("</body>\n")
    hocrfile.write("</html>\n")

def xmlheader(xmlfile):
    xmlfile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    xmlfile.write("<words>\n")

def xmlfooter(xmlfile):
    xmlfile.write("</words>")

def writehOcr(pgname,page_x0,page_y0,page_x1,page_y1,columns,hocr_file):
    word_count = line_count = column_count = para_count = 0
    hocrheader(hocr_file)
    hocr_file.write("<div class=\'ocr_page\' id=\'page_1\' ")
    hocr_file.write("title=\'image \"%s\"; bbox %d %d %d %d\'>\n" % (
                   pgname,page_x0,page_y0,page_x1,page_y1))
    for column in columns:
        column_count += 1
        hocr_file.write("<div class=\'ocr_carea\' id=\'block_%d_%d\' " % (column_count,column_count))
        hocr_file.write("title=\"bbox %d %d %d %d\">\n" % (column.x0,column.y0,column.x1,column.y1))
        for para in column.hocr_paras:
            para_count += 1
            hocr_file.write("<p class=\'ocr_par\' dir=\'ltr\' id=\'par_%d\' " % (para_count))
            hocr_file.write("title=\"bbox %d %d %d %d\">\n" % (para.x0,para.y0,para.x1,para.y1))
            for line in para.hocr_lines:
                line_count += 1
                hocr_file.write("<span class=\'ocr_line\' id=\'line_%d\' " % (line_count))
                hocr_file.write("title=\"bbox %d %d %d %d\">\n" % (line.x0,line.y0,line.x1,line.y1))
                for word in line.hocr_words:
                    word_count += 1
                    hocr_file.write("<span class=\'ocr_word\' id=\'word_%d\' " % (word_count))
                    hocr_file.write("title=\"bbox %d %d %d %d\">" % (word.x0,word.y0,word.x1,word.y1))
                    hocr_file.write("%s</span>\n" % (word.hocr_word))
                hocr_file.write("</span>\n")
            hocr_file.write("</p>\n")
    hocr_file.write("</div>\n")
    hocrfooter(hocr_file)

from optparse import OptionParser

parser = OptionParser(usage="""
%prog [options] 

Possible choices are:

--file -- specify input file
--xml -- write XML file
--box -- write box file
--column -- pixel gap to define column
--line -- pixel gap to define line
--hocr -- write hOCR file
--space -- map spaces to words

""")

# options
parser.add_option("-f","--file",help="input file",default="page.txt")
parser.add_option("-x","--xml",help="write xml",default=True)
parser.add_option("-b","--box",help="write box",default=True)
parser.add_option("-c","--column",help="column gap",default=100)
parser.add_option("-l","--line",help="line gap",default=25)
parser.add_option("-o","--hocr",help="write hOCR",default=True)
parser.add_option("-s","--space",help="add space",default=True)

(options,args) = parser.parse_args()

# initialize
x0 = y0 = x1 = y1 = 0
tcx0 = tcy0 = tcx1 = tcy1 = 0
line_left_x = line_left_y = 0
para_left_x = para_left_y = 0
column_left_x = column_left_y = 0
is_space = is_char = is_word = False
line_gap = int(options.line)
column_gap = int(options.column)
last_file = None

ocr_columns = []
ocr_paras = []
ocr_lines = []
ocr_words = []

file = open(options.file, 'r')

xml_file = None
box_file = None
hocr_file = None
stub = img_type = ""
last_file = "@@@"
   
for line in file:
    line = line.strip()
    fileinfo, char_or_word, x0, y0, x1, y1 = line.split(' ', 6)
       
    utf_char_or_word = None
    try:
        utf_char_or_word = char_or_word.encode('utf-8',errors='strict')
    except:
        utf_char_or_word = ''

    file_parts = fileinfo.split('_')
    #print "file", file_parts[0]
    stub, img_type = file_parts[0].split(".",1)
    #print "%s %s" % (stub,img_type)

    if stub != last_file:
       width = int(file_parts[1])
       height = int(file_parts[2])

       if last_file != "@@@":
          xmlfooter(xml_file)
          xml_file.close()
       xml_file = open(stub + ".xml", 'w')
       xmlheader(xml_file)

       if options.box:
          if last_file != "@@@":
             box_file.close()
          box_file = open(stub + ".box", 'w') 

       if options.hocr is True:
          if last_file != "@@@":
             writehOcr(stub + "." + img_type,0,0,width,height,ocr_columns,hocr_file)
             hocr_file.close()
          hocr_file = open(stub + ".html", 'w')

    if len(file_parts) == 5:
       is_char = True
       is_word = False
    else:
       is_char = False
       is_word = True

    x0 = int(x0)
    y0 = hocr_y0 = int(y0)
    x1 = int(x1)
    y1 = hocr_y1 = int(y1)
       
    if (x0 + y0 + x1 + y1) == 0:
       is_space = True

    #change the orientation for hocr with characters
    if is_char is True and hocr_y1 > 0:
       hocr_y0 = height - y1
       hocr_y1 = height - y0

    if is_word is True and len(utf_char_or_word) > 0:
       xml_file.write("<word> x1=\"%d\" y1=\"%d\">\n" % (x0,y0))
       xml_file.write("%s\n" % (utf_char_or_word))
       xml_file.write("<ends x2=\"%d\" y2=\"%d\"/>\n" % (x1,y1))
       xml_file.write("</word>\n")

    if options.hocr is True and len(utf_char_or_word) > 0 and is_word:
       ocr_words.append(hOCR_Word(utf_char_or_word,x0,y0,x1,y1))

    if options.hocr is True and options.space is True and len(utf_char_or_word) > 0 and is_char is True:
       if is_space is True and tcx1 > 0 and x0 > tcx1:
          ocr_words.append(hOCR_Word(" ",(x0 - (x0 - tcx1) + 1),tcy0,(x0 - 1),tcy1))
          is_space = False
       
    if options.box is True and len(utf_char_or_word) > 0 and is_char is True and not is_space:
       out_line = ("%s %d %d %d %d 0\n" % (utf_char_or_word,x0,y0,x1,y1))
       box_file.write(out_line)

    if is_char is True:
       # we don't want extra spaces at the end of empty lines
       if hocr_y0 > tcx0 and tcy1 > 0:
          is_space = False

       # need to check if the current line if further away OR has jumped back for new column
       if (hocr_y1 > (tcy1 + line_gap) or (hocr_y1 + line_gap) < tcy1) and len(ocr_words) > 0:
          if (x0 + y0 + x1 + y1) > 0:
             ocr_lines.append(hOCR_Line(ocr_words,line_left_x,line_left_y,tcx1,tcy1))
             line_left_x = x0
             line_left_y = hocr_y0
             if line_left_x < para_left_x:
                para_left_x = column_left_x = line_left_x
             last_word = ""
             if len(ocr_words) > 0:
                last_word = ocr_words[len(ocr_words) - 1].hocr_word
             ocr_words = []
             
             # if utf_char_or_word.isupper() and (last_word.endswith(".") or (hocr_y1 + line_gap) < tcy1): 
             if utf_char_or_word.isupper() and (last_word.endswith(".") or hocr_y1 > (tcy1 + line_gap)): 
                ocr_paras.append(hOCR_Para(ocr_lines,para_left_x,para_left_y,tcx1,tcy1))
                para_left_x = x0
                para_left_y = hocr_y0
                if para_left_x < column_left_x:
                   column_left_x = para_left_x
                ocr_lines = []
       
             # again, checking for gap or start of new column
             if (hocr_y1 > (tcy1 + column_gap) or (hocr_y1 + column_gap) < tcy1) and len(ocr_paras) > 0:
                ocr_columns.append(hOCR_Column(ocr_paras,column_left_x,column_left_y,tcx1,tcy1))
                column_left_x = x0
                column_left_y = hocr_y0
                ocr_paras = []

       if (x0 + y0 + x1 + y1) > 0:
          tcx0 = x0
          tcy0 = hocr_y0
          tcx1 = x1
          tcy1 = hocr_y1

       if last_file != stub:
          #snag leftovers
          if len(ocr_words) > 0:
             ocr_lines.append(hOCR_Line(ocr_words,line_left_x,line_left_y,tcx1,tcy1))
          if len(ocr_lines) > 0:
             ocr_paras.append(hOCR_Para(ocr_lines,para_left_x,para_left_y,tcx1,tcy1))
          if len(ocr_paras) > 0:
             ocr_columns.append(hOCR_Column(ocr_paras,column_left_x,column_left_y,tcx1,tcy1))

       last_file = stub
       
if len(ocr_words) > 0:
   ocr_lines.append(hOCR_Line(ocr_words,line_left_x,line_left_y,tcx1,tcy1))
if len(ocr_lines) > 0:
   ocr_paras.append(hOCR_Para(ocr_lines,para_left_x,para_left_y,tcx1,tcy1))
if len(ocr_paras) > 0:
   ocr_columns.append(hOCR_Column(ocr_paras,column_left_x,column_left_y,tcx1,tcy1))
   if options.hocr is True:
      writehOcr(stub + "." + img_type,0,0,width,height,ocr_columns,hocr_file)

if options.box is True:
   if last_file != "@@@":
       box_file.close()
if options.hocr is True:
   if last_file != "@@@":
      hocr_file.close()
   
if last_file != "@@@":
   xmlfooter(xml_file)
   xml_file.close()
