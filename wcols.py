#!/usr/bin/env python

"""
wcols.py - get white block coordinates from an image
           for identifying columns.

- art rhyno <http://projectconifer.ca/>

(c) Copyright GNU General Public License (GPL)
"""

"""
This represents a quick attempt to identify 
white blocks. Basically an image with a black
and white palette is converted into an array
of 1s and 0s. For example:

[[1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1], 
 [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 
 [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 
 [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1], 
 [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1], 
 [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1]]

We start at the top left and look for 1s,
then go down the side of the array and
limit the width of the column to the widest
point it can be without running into a 0
on the right. We store the column info
based on this, and then zero out the entry.

So for the array above, the first column
is defined for a 1 pixel wide and 6 pixel
long block. The entry is then zeroed out 
and the array becomes:

[[0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1], 
 [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 
 [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 
 [0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1], 
 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1], 
 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1]]

And so on. This works but it doesn't calculate
the maximum line definitions, which might
be more useful in some cases. You could reverse
the orientation of the array to look for blocks
with the greatest width rather than the greatest
height. A slant in the image can cause a bunch of 
small lines to be defined rather than a continuous 
sequence.

I wanted an output format similar to that used
by the Line Segment Identifier
<http://www.ipol.im/pub/algo/gjmr_line_segment_detector/>
which works great for black lines. I don't calculate
the angle and NFA in this approach, this method is
probably too simplistic for these calculations.

My image set is too slanted for this to be useful
but it might give an option for a better aligned
collection.
"""

import sys
import Image

# model for the column information
class column:
    def __init__(self, x0, y0, width, height):
        self.x0 = x0
        self.y0 = y0
        self.width = width
        self.height = height

file = sys.argv[1]

# open image
pic = Image.open( file )
imgdata = pic.load()

# get dimensions
row_size, col_size = pic.size

# only looking for one colour (white)
w_colour = 255

# fill with zeros
pixels = [[0 for x in xrange(col_size)] for x in xrange(row_size)] 

# columns will hold our candidates for columns
columns = []

# mark all white pixels with 1
for i in range(row_size):
        for j in range(col_size):
                if imgdata[i,j] == w_colour:
                   pixels[i][j] = 1

# now work through array
for i in range(row_size):
    for j in range(col_size):
        if pixels[i][j] == 1:
           width = 0
           r_width = col_size - j
           r_height = row_size - i
 
           # we look for 1s across image
           for r in range(i,row_size):
               if pixels[r][j] == 1:
                  for c in range(j,j + r_width):
                      if pixels[r][c] == 1:
                         width = width + 1
                      else:
                         break
                      r_width = width
                  width = 0
               else:
                  # we skip out if we run out of 1s
                  r_height = r - i
                  break
               offset = 0

           # collect column candidates
           columns.append(column(i,j,r_width,r_height))

           # zero out columns we already have
           for h in range(i,i + r_height):
               for w in range(j,j + r_width):
                   pixels[h][w] = 0

           # uncomment this if you want to see the resulting array
           # print "pixels now", pixels
           

# we want to go from left to right, top to bottom in output
columns = sorted(columns, key=lambda seg:(seg.y0))
columns = sorted(columns, key=lambda seg:(seg.x0))

# this is the LSD format, scale is useful if you are resizing for the OCR
SCALE = 1
for col in columns:
    print "%d %d %d %d %d 0 0" % (col.x0 * SCALE,col.y0 * SCALE,(col.x0 + col.height) * 
           SCALE,(col.y0 + col.width) * SCALE,col.width * col.height * SCALE)

