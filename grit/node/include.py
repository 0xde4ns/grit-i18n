#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Handling of the <include> element.
"""

import os

import grit.format.html_inline
import grit.format.rc_header
import grit.format.rc

from grit.node import base
from grit import util

class IncludeNode(base.Node):
  """An <include> element."""
  def __init__(self):
    super(IncludeNode, self).__init__()

    # Cache flattened data so that we don't flatten the same file
    # multiple times.
    self._flattened_data = None
    # Also keep track of the last filename we flattened to, so we can
    # avoid doing it more than once.
    self._last_flat_filename = None

  def _IsValidChild(self, child):
    return False

  def _GetFlattenedData(self, allow_external_script=False):
    if not self._flattened_data:
      filename = self.ToRealPath(self.GetInputPath())
      self._flattened_data = (
          grit.format.html_inline.InlineToString(filename, self,
              allow_external_script=allow_external_script))
    return self._flattened_data

  def MandatoryAttributes(self):
    return ['name', 'type', 'file']

  def DefaultAttributes(self):
    return {'translateable' : 'true',
            'generateid': 'true',
            'filenameonly': 'false',
            'mkoutput': 'false',
            'flattenhtml': 'false',
            'allowexternalscript': 'false',
            'relativepath': 'false',
           }

  def ItemFormatter(self, t):
    if t == 'rc_header':
      return grit.format.rc_header.Item()
    elif (t in ['rc_all', 'rc_translateable', 'rc_nontranslateable'] and
          self.SatisfiesOutputCondition()):
      return grit.format.rc.RcInclude(self.attrs['type'].upper(),
                                      self.attrs['filenameonly'] == 'true',
                                      self.attrs['relativepath'] == 'true',
                                      self.attrs['flattenhtml'] == 'true')
    elif t == 'resource_map_source':
      from grit.format import resource_map
      return resource_map.SourceInclude()
    elif t == 'resource_file_map_source':
      from grit.format import resource_map
      return resource_map.SourceFileInclude()
    else:
      return super(IncludeNode, self).ItemFormatter(t)

  def FileForLanguage(self, lang, output_dir):
    """Returns the file for the specified language.  This allows us to return
    different files for different language variants of the include file.
    """
    return self.ToRealPath(self.GetInputPath())

  def GetDataPackPair(self, lang, encoding):
    """Returns a (id, string) pair that represents the resource id and raw
    bytes of the data.  This is used to generate the data pack data file.
    """
    from grit.format import rc_header
    id_map = rc_header.Item.tids_
    id = id_map[self.GetTextualIds()[0]]
    if self.attrs['flattenhtml'] == 'true':
      allow_external_script = self.attrs['allowexternalscript'] == 'true'
      data = self._GetFlattenedData(allow_external_script=allow_external_script)
    else:
      filename = self.ToRealPath(self.GetInputPath())
      data = util.ReadFile(filename, util.BINARY)

    # Include does not care about the encoding, because it only returns binary
    # data.
    return id, data

  def Process(self, output_dir):
    """Rewrite file references to be base64 encoded data URLs.  The new file
    will be written to output_dir and the name of the new file is returned."""
    filename = self.ToRealPath(self.GetInputPath())
    flat_filename = os.path.join(output_dir,
        self.attrs['name'] + '_' + os.path.basename(filename))

    if self._last_flat_filename == flat_filename:
      return

    with open(flat_filename, 'wb') as outfile:
      outfile.write(self._GetFlattenedData())

    self._last_flat_filename = flat_filename
    return os.path.basename(flat_filename)

  def GetHtmlResourceFilenames(self):
    """Returns a set of all filenames inlined by this file."""
    allow_external_script = self.attrs['allowexternalscript'] == 'true'
    return grit.format.html_inline.GetResourceFilenames(
         self.ToRealPath(self.GetInputPath()),
         allow_external_script=allow_external_script)

  @staticmethod
  def Construct(parent, name, type, file, translateable=True,
                filenameonly=False, mkoutput=False, relativepath=False):
    """Creates a new node which is a child of 'parent', with attributes set
    by parameters of the same name.
    """
    # Convert types to appropriate strings
    translateable = util.BoolToString(translateable)
    filenameonly = util.BoolToString(filenameonly)
    mkoutput = util.BoolToString(mkoutput)
    relativepath = util.BoolToString(relativepath)

    node = IncludeNode()
    node.StartParsing('include', parent)
    node.HandleAttribute('name', name)
    node.HandleAttribute('type', type)
    node.HandleAttribute('file', file)
    node.HandleAttribute('translateable', translateable)
    node.HandleAttribute('filenameonly', filenameonly)
    node.HandleAttribute('mkoutput', mkoutput)
    node.HandleAttribute('relativepath', relativepath)
    node.EndParsing()
    return node
