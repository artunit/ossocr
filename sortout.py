#!/usr/bin/python

"""
sortout.py - take hadoop output and create derivative files
- art rhyno <http://projectconifer.ca/>

(c) Copyright GNU General Public License (GPL)
"""

import sys
from copy import deepcopy

class hOCR_Column:
    def __init__(self, paras, x0, y0, x1, y1):
        self.hocr_paras = paras
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

class hOCR_Para:
    def __init__(self, lines, x0, y0, x1, y1):
        self.hocr_lines = lines
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

class hOCR_Line:
    def __init__(self, words, x0, y0, x1, y1):
        self.hocr_words = words
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
        self.dup = 0

class OCR_Char:
    def __init__(self, ochar, x0, y0, x1, y1):
        self.ocr_char = ochar
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.xgap = abs(self.x1 - self.x0)

class box_Entry:
    def __init__(self, box_str):
        tmp = box_str.split('_', 4)
        self.x0 = int(tmp[0])
        self.y0 = int(tmp[1])
        self.x1 = int(tmp[2])
        self.y1 = int(tmp[3])

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
            if para.x0 >= 0 and para.y0 >= 0 and para.x1 >= 0 and para.y1 >= 0:
               para_count += 1
               hocr_file.write("<p class=\'ocr_par\' dir=\'ltr\' id=\'par_%d\' " % (para_count))
               hocr_file.write("title=\"bbox %d %d %d %d\">\n" % (para.x0,para.y0,para.x1,para.y1))
               for line in para.hocr_lines:
                    if line.x0 >= 0 and line.y0 >= 0 and line.x1 >=0 and line.y1 >= 0:
                       line_count += 1
                       hocr_file.write("<span class=\'ocr_line\' id=\'line_%d\' " % (line_count))
                       hocr_file.write("title=\"bbox %d %d %d %d\">\n" % (line.x0,line.y0,line.x1,line.y1))
                       for idx, word in enumerate(line.hocr_words):
                           if word.x0 >=0 and word.y0 >= 0 and word.x1 >= 0 and word.y1 >= 0:
                              word_count += 1
                              hocr_file.write("<span class=\'ocr_word\' id=\'word_%d\' " % (word_count))
                              hocr_file.write("title=\"bbox %d %d %d %d\">" % (word.x0,word.y0,word.x1,word.y1))
                              hocr_file.write("%s</span>\n" % (word.hocr_word))
                              if idx < len(line.hocr_words) - 1:
                                 word_count += 1
                                 hocr_file.write("<span class=\'ocr_word\' id=\'word_%d\' " % (word_count))
                                 hocr_file.write("title=\"bbox %d %d %d %d\">" % (word.x1+1,word.y0,
                                   line.hocr_words[idx+1].x0-1,word.y1))
                                 hocr_file.write(" </span>\n")
                       hocr_file.write("</span>\n")
               hocr_file.write("</p>\n")
    hocr_file.write("</div>\n")
    hocrfooter(hocr_file)

def deDupChars(ocr_chars):
    uniq_chars = []
    box_info = []
    i = -1
    for ocr_char in ocr_chars:
        unique = True
        if ocr_char.x0 == -1:
           if ocr_char.y0 == -1:
              if ocr_char.x1 == -1:
                 if ocr_char.y1 == -1:
                    unique = False
                    box_info.append(box_Entry(ocr_char.ocr_char))
        if i > 0 and unique is True:
           if ocr_char.x0 in range(ocr_chars[i].x0 - 1, ocr_chars[i].x0 + 1):
              if ocr_char.y0 == range(ocr_chars[i].y0 - 1, ocr_chars[i].y0 + 1):
                 if ocr_char.x1 == range(ocr_chars[i].x1 - 1, ocr_chars[i].x1 + 1):
                    if ocr_char.y1 == range(ocr_chars[i].y1 - 1, ocr_chars[i].y1 + 1):
                       unique = False
        if unique is True:
           uniq_chars.append(ocr_char)
        i += 1
    return uniq_chars, box_info

def deDupWords(ocr_words):
    non_uniq_words = []
    non_uniq_words_hocr = []
    num_words = len(ocr_words)
    last_box = (0,0,0,0)
    for idx, ocr_word in enumerate(ocr_words):
        if idx > 0 and (idx + 1) < num_words and len(ocr_word.hocr_word.strip()) > 0:
           num = idx - 1
           if ocr_word.x0 in range(ocr_words[num].x0-2,ocr_words[num].x0+2):
              if ocr_word.y0 in range(ocr_words[num].y0-2,ocr_words[num].y0+2):
                 if ocr_word.x1 in range(ocr_words[num].x1-2,ocr_words[num].x1+2):
                    if ocr_word.y1 in range(ocr_words[num].y1-2,ocr_words[num].y1+2):
                       this_box = ocr_word.x0 + ocr_word.y0 + ocr_word.x1 + ocr_word.y1
                       if (this_box + 10) >= last_box or (this_box - 10) <= last_box:
                          if len(ocr_words[num].hocr_word) < len(ocr_word.hocr_word):
                             non_uniq_words.append(ocr_word)
                             non_uniq_words_hocr.append(hOCR_Word(ocr_word.hocr_word,ocr_word.x0,ocr_word.y0,ocr_word.x1,ocr_word.y1))
                          else:
                             non_uniq_words.append(ocr_words[num])
                             non_uniq_words_hocr.append(hOCR_Word(ocr_words[num].hocr_word,ocr_words[num].x0,ocr_words[num].y0,ocr_words[num].x1,ocr_words[num].y1))
                          non_uniq_words[len(non_uniq_words) -1].dup = 1
                          non_uniq_words_hocr[len(non_uniq_words_hocr) -1].dup = 1
                          last_box = ocr_word.x0+ocr_word.y0+ocr_word.x1+ocr_word.y1
    #we need two copies
    return non_uniq_words, non_uniq_words_hocr

def checkForDups(check_word,non_unique_words):
    dup = False
    for ocr_word in non_unique_words:
        if ocr_word.x0 in range(check_word.x0-2,check_word.x0+2):
           if ocr_word.y0 in range(check_word.y0-2,check_word.y0+2):
              if ocr_word.x1 in range(check_word.x1-2,check_word.x1+2):
                 if ocr_word.y1 in range(check_word.y1-2,check_word.y1+2):
                    if ocr_word.dup > 0:
                       if ocr_word.dup == 1:
                          dup = False
                       else:
                          dup = True
                       ocr_word.dup += 1
                       break

    return dup
          
def sortOutOcr(stub,img_type,inocr_chars,inocr_words,width,height):
    line_gap = int(options.line)
          
    hocr_columns = []
    pg_cols = []


    xml_file = None
    box_file = None
    hocr_file = None
          
    ocr_chars = sorted(inocr_chars, key=lambda seg:seg.y0)
    ocr_chars = sorted(ocr_chars, key=lambda seg:seg.x0)
    ocr_chars, pg_cols = deDupChars(ocr_chars)

    if len(pg_cols) > 0:
       pg_cols = sorted(pg_cols, key=lambda seg:(seg.x1, seg.y1))
    else:
       pg_cols.append(box_Entry("0_0_%d_%d"%(width,height)))

    #sort from top to bottom of image
    ocr_words = sorted(inocr_words, key=lambda seg:(seg.y0, seg.x0, seg.y1, seg.x1))
    non_unique_words, non_unique_words_hocr = deDupWords(ocr_words)
    ocr_words = inocr_words

    if len(ocr_chars) > 0:
       xml_file = open(stub + ".xml", 'w')
       xmlheader(xml_file)
       for pg_col in pg_cols:
           for ocr_word in ocr_words:
               if len(ocr_word.hocr_word.strip()) > 0:
                  if ocr_word.x0 >= pg_col.x0 and ocr_word.y0 >= pg_col.y0:
                     if ocr_word.x1 <= pg_col.x1 and ocr_word.y1 <= pg_col.y1:
                        if checkForDups(ocr_word,non_unique_words) is False:
                           xml_file.write("<word> x1=\"%d\" y1=\"%d\">\n" % (ocr_word.x0,ocr_word.y0))
                           xml_file.write("%s\n" % (ocr_word.hocr_word))
                           xml_file.write("<ends x2=\"%d\" y2=\"%d\"/>\n" % (ocr_word.x1,ocr_word.y1))
                           xml_file.write("</word>\n")
       xmlfooter(xml_file)
       xml_file.close()

       if options.box is True:
          box_file = open(stub + ".box", 'w') 
       
          for pg_col in pg_cols:
              for ocr_char in ocr_chars:
                  if ocr_char.x0 >= pg_col.x0 and ocr_char.y0 >= pg_col.y0:
                     if ocr_char.x1 <= pg_col.x1 and ocr_char.y1 <= pg_col.y1:
                        out_line = ("%s %d %d %d %d 0\n" % (ocr_char.ocr_char,
                           ocr_char.x0,ocr_char.y0,ocr_char.x1,ocr_char.y1))
                        box_file.write(out_line)
          box_file.close()

       if options.hocr is True:
          hocr_file = open(stub + ".html", 'w')

          for pg_col in pg_cols:

              x0 = y0 = x1 = y1 = 0
              tcx0 = tcy0 = tcx1 = tcy1 = 0
              line_left_x = line_left_y = 0
              para_left_x = para_left_y = 0
              column_left_x = column_left_y = 0
              column_right_x = column_right_y = 0
              hocr_paras = [] 
              hocr_lines = []
              hocr_words = []
              last_word = ""

              for ocr_word in ocr_words:
                  if (len(ocr_word.hocr_word.strip()) > 0 and ocr_word.x0 >= pg_col.x0 
                     and ocr_word.y0 >= pg_col.y0
                  ):
                     if ocr_word.x1 <= pg_col.x1 and ocr_word.y1 <= pg_col.y1:
                        if (checkForDups(ocr_word,non_unique_words_hocr) is False and 
                            ocr_word.x0 >=0 and ocr_word.y0 >=0 and 
                            ocr_word.x1 >= 0 and ocr_word.y1 >= 0
                           ):
                           if x0 == 0 and y0 == 0:
                              line_left_x = ocr_word.x0
                              line_left_y = ocr_word.y0
                           if para_left_x == 0 and para_left_y == 0:
                              para_left_x = line_left_x
                              para_left_y = line_left_y
                           if column_left_x == 0 and column_left_y == 0:
                              column_left_x = para_left_x
                              column_left_y = para_left_y 
                              column_right_x = ocr_word.x1
                              column_right_y = ocr_word.y1
                           x0 = ocr_word.x0
                           y0 = ocr_word.y0
                           x1 = ocr_word.x1
                           y1 = ocr_word.y1
                           hocr_word = ocr_word.hocr_word

                           if (last_word.endswith(".") and 
                              ((x0 < tcx0 and x0 > 0) or y0 > (tcy1 + line_gap))
                              ): 
                              if len(hocr_words) > 0:
                                 hocr_lines.append(hOCR_Line(hocr_words,line_left_x,line_left_y,tcx1,tcy1))
                                 hocr_words = []
                              if len(hocr_lines) > 0:
                                 hocr_paras.append(hOCR_Para(hocr_lines,para_left_x,para_left_y,tcx1,tcy1))
                                 hocr_lines = []
                              para_left_x = x0
                              para_left_y = y0
                              tcx1 = x1
                              tcy1 = y1
                           elif (x0 < tcx0 and x0 > 0) or y0 > (tcy1 + line_gap):
                              if len(hocr_words) > 0:
                                 hocr_lines.append(hOCR_Line(hocr_words,line_left_x,line_left_y,tcx1,tcy1))
                                 hocr_words = []
                              line_left_x = x0
                              line_left_y = y0
                              tcx1 = x1
                              tcy1 = y1
                           if x0 < para_left_x and x0 > 0:
                              para_left_x = x0
                           if y0 < para_left_y and y0 > 0:
                              para_left_y = y0
                           if x0 < line_left_x and x0 > 0:
                              line_left_x = x0
                           if y0 < line_left_y and y0 > 0:
                              line_left_y = y0

                           hocr_words.append(ocr_word)
                           last_word = hocr_word
                           tcx0 = x0
                           tcy0 = y0
                           if x1 > tcx1:
                              tcx1 = x1
                           if y1 > tcy1:
                              tcy1 = y1
                           if x0 < column_left_x and x0 > 0:
                              column_left_x = x0
                           if y0 < column_left_y and y0 > 0:
                              column_left_y = y0
                           if x1 > column_right_x:
                              column_right_x = x1
                           if y1 > column_right_y:
                              column_right_y = y1
       
              if len(hocr_words) > 0:
                 hocr_lines.append(hOCR_Line(hocr_words,line_left_x,line_left_y,tcx1,tcy1))
              if len(hocr_lines) > 0:
                 hocr_paras.append(hOCR_Para(hocr_lines,para_left_x,para_left_y,tcx1,tcy1))
              if len(hocr_paras) > 0:
                 hocr_columns.append(hOCR_Column(hocr_paras,column_left_x,column_left_y, column_right_x,column_right_y))

          if len(hocr_columns) > 0:
             writehOcr(stub + "." + img_type,0,0,width,height,hocr_columns,hocr_file)

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
parser.add_option("-l","--line",help="line gap",default=25)
parser.add_option("-o","--hocr",help="write hOCR",default=True)
parser.add_option("-s","--space",help="add space",default=True)

(options,args) = parser.parse_args()

# initialize
x0 = y0 = x1 = y1 = 0
is_space = last_char_space = is_char = is_word = False
last_file = None

ocr_columns = []
ocr_paras = []
ocr_lines = []
ocr_words = []
ocr_chars = []

file = open(options.file, 'r')

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
    file_str = file_parts[0]

    #if the file is a URL, get name after last slash
    if file_str.startswith('http'):
       last_slash = file_str.rfind('/')
       if last_slash > -1:
          last_slash+=1
          file_str = file_str[last_slash:]
    stub, img_type = file_str.split(".",1)

    if stub != last_file:
       width = int(file_parts[1])
       height = int(file_parts[2])

       if last_file != "@@@":
          sortOutOcr(stub,img_type,ocr_chars,ocr_words,width,height)
          ocr_words = ocr_chars = []

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
       
    is_space = False
    if (x0 + y0 + x1 + y1) == 0:
       is_space = True

    if is_char is True and not is_space:
       ocr_chars.append(OCR_Char(utf_char_or_word,x0,y0,x1,y1))

    if len(utf_char_or_word) > 0 and is_word is True and len(utf_char_or_word.strip()) > 0:
       ocr_words.append(hOCR_Word(utf_char_or_word,x0,y0,x1,y1))

    if (x0 + y0 + x1 + y1) > 0:
       tcx0 = x0
       tcy0 = y0
       tcx1 = x1
       tcy1 = y1

    last_file = stub
       
if len(ocr_chars) > 0 and len(file_parts) > 2:
   sortOutOcr(stub,img_type,ocr_chars,ocr_words,width,height)
