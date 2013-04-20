//This is scribo/src/contest/hdlac-2011/content_in_hdoc_hdlac.cc
//using almost verbatim - want to produce PAGE files from python
//directly - see Olena licensing below

// Copyright (C) 2010, 2011 EPITA Research and Development Laboratory
// (LRDE)
//
// This file is part of Olena.
//
// Olena is free software: you can redistribute it and/or modify it under
// the terms of the GNU General Public License as published by the Free
// Software Foundation, version 2 of the License.
//
// Olena is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Olena.  If not, see <http://www.gnu.org/licenses/>.
//
// As a special exception, you may use this file as part of a free
// software project without restriction.  Specifically, if other files
// instantiate templates or use macros or inline functions from this
// file, or you compile this file and link it with other files to produce
// an executable, this file does not by itself cause the resulting
// executable to be covered by the GNU General Public License.  This
// exception does not however invalidate any other reasons why the
// executable file might be covered by the GNU General Public License.

# define SCRIBO_NOCR

#include "config.h"
#include <libgen.h>
#include <fstream>
#include <iostream>

#include <mln/core/image/image2d.hh>

#include <mln/io/magick/load.hh>

#include <scribo/toolchain/content_in_hdoc.hh>
#include <scribo/toolchain/text_in_doc_preprocess.hh>

#include <scribo/core/document.hh>

#include <scribo/debug/usage.hh>
#include <scribo/debug/logger.hh>

#include <scribo/preprocessing/crop_without_localization.hh>
#include <scribo/preprocessing/crop.hh>

#include <scribo/io/xml/save.hh>
#include <scribo/io/img/save.hh>


#include <mln/core/alias/neighb2d.hh>
#include <mln/labeling/compute.hh>
#include <mln/labeling/foreground.hh>
#include <mln/util/timer.hh>

float xmlPage(char* input_tif, char* output_xml)
{
  using namespace scribo;
  using namespace mln;

  //Magick::InitializeMagick("./content_in_hdoc_hdlac");
  Magick::InitializeMagick("xmlPage");

  mln::util::timer t;
  t.start();

  typedef image2d<scribo::def::lbl_type> L;
  image2d<value::rgb8> input;
  mln::io::magick::load(input, input_tif);

  // Preprocess document
  image2d<bool> input_preproc;
  {
    input_preproc = toolchain::text_in_doc_preprocess(input, false, 0, 0.34);

    {
      typedef scribo::def::lbl_type V;
      V nlabels;
      image2d<V> lbl = labeling::foreground(input_preproc, c8(), nlabels);
      mln::util::array<box2d>
	bbox = labeling::compute(accu::shape::bbox<point2d>(), lbl, nlabels);

      const box2d& b = input.domain();
      for_all_ncomponents(e, nlabels)
	if (bbox(e).pmin().row() == b.pmin().row()
	    || bbox(e).pmax().row() == b.pmax().row()
	    || bbox(e).pmin().col() == b.pmin().col()
	    || bbox(e).pmax().col() == b.pmax().col())
	  data::fill(((input_preproc | bbox(e)).rw() | (pw::value(lbl) == pw::cst(e))).rw(), false);
    }
  }

  bool denoise = 1;
  std::string language = "";
  bool find_line_seps = true;
  bool find_whitespace_seps = true;

  document<L>
    doc = scribo::toolchain::content_in_hdoc(input, input_preproc, denoise,
					     find_line_seps, find_whitespace_seps,
					     !language.empty(), language);

  doc.set_filename(basename(input_tif));

  scribo::io::xml::save(doc, output_xml, scribo::io::xml::Page);

  //Should return something to calling environment
  return t.read();
}
