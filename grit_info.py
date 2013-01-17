#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

'''Tool to determine inputs and outputs of a grit file.
'''

import optparse
import os
import posixpath
import sys

from grit import grd_reader
from grit import util

class WrongNumberOfArguments(Exception):
  pass


def Outputs(filename, defines, ids_file):
  grd = grd_reader.Parse(
      filename, defines=defines, tags_to_ignore=set(['messages']),
      first_ids_file=ids_file)

  target = []
  lang_folders = {}
  # Add all explicitly-specified output files
  for output in grd.GetOutputFiles():
    path = output.GetFilename()
    target.append(path)

    if path.endswith('.h'):
      path, filename = os.path.split(path)
    if output.attrs['lang']:
      lang_folders[output.attrs['lang']] = os.path.dirname(path)

  # Add all generated files, once for each output language.
  for node in grd:
    if node.name == 'structure':
      with node:
        # TODO(joi) Should remove the "if sconsdep is true" thing as it is a
        # hack - see grit/node/structure.py
        if node.HasFileForLanguage() and node.attrs['sconsdep'] == 'true':
          for lang in lang_folders:
            path = node.FileForLanguage(lang, lang_folders[lang],
                                        create_file=False,
                                        return_if_not_generated=False)
            if path:
              target.append(path)

  return [t.replace('\\', '/') for t in target]


def GritSourceFiles():
  files = []
  grit_root_dir = os.path.relpath(os.path.dirname(__file__), os.getcwd())
  for root, dirs, filenames in os.walk(grit_root_dir):
    grit_src = [os.path.join(root, f) for f in filenames
                if f.endswith('.py')]
    files.extend(grit_src)
  return sorted(files)


def Inputs(filename, defines, ids_file):
  grd = grd_reader.Parse(
      filename, debug=False, defines=defines, tags_to_ignore=set(['message']),
      first_ids_file=ids_file)
  files = set()
  for lang, ctx in grd.GetConfigurations():
    grd.SetOutputLanguage(lang or grd.GetSourceLanguage())
    grd.SetOutputContext(ctx)
    for node in grd.ActiveDescendants():
      with node:
        if (node.name == 'structure' or node.name == 'skeleton' or
            (node.name == 'file' and node.parent and
             node.parent.name == 'translations')):
          files.add(grd.ToRealPath(node.GetInputPath()))
          # If it's a flattened node, grab inlined resources too.
          if node.name == 'structure' and node.attrs['flattenhtml'] == 'true':
            node.RunPreSubstitutionGatherer()
            files.update(node.GetHtmlResourceFilenames())
        elif node.name == 'grit':
          first_ids_file = node.GetFirstIdsFile()
          if first_ids_file:
            files.add(first_ids_file)
        elif node.name == 'include':
          files.add(grd.ToRealPath(node.GetInputPath()))
          # If it's a flattened node, grab inlined resources too.
          if node.attrs['flattenhtml'] == 'true':
            files.update(node.GetHtmlResourceFilenames())
        elif node.name == 'part':
          files.add(util.normpath(os.path.join(os.path.dirname(filename),
                                               node.GetInputPath())))

  cwd = os.getcwd()
  return [os.path.relpath(f, cwd) for f in sorted(files)]


def PrintUsage():
  print 'USAGE: ./grit_info.py --inputs [-D foo] [-f resource_ids] <grd-file>'
  print ('       ./grit_info.py --outputs [-D foo] [-f resource_ids] ' +
      '<out-prefix> <grd-file>')


def DoMain(argv):
  parser = optparse.OptionParser()
  parser.add_option("--inputs", action="store_true", dest="inputs")
  parser.add_option("--outputs", action="store_true", dest="outputs")
  parser.add_option("-D", action="append", dest="defines", default=[])
  # grit build also supports '-E KEY=VALUE', support that to share command
  # line flags.
  parser.add_option("-E", action="append", dest="build_env", default=[])
  parser.add_option("-w", action="append", dest="whitelist_files", default=[])
  parser.add_option("-f", dest="ids_file",
                    default="GRIT_DIR/../gritsettings/resource_ids")

  options, args = parser.parse_args(argv)

  defines = {}
  for define in options.defines:
    name, val = util.ParseDefine(define)
    defines[name] = val

  for env_pair in options.build_env:
    (env_name, env_value) = env_pair.split('=', 1)
    os.environ[env_name] = env_value

  if options.inputs:
    if len(args) > 1:
      raise WrongNumberOfArguments("Expected 0 or 1 arguments for --inputs.")

    inputs = []
    if len(args) == 1:
      filename = args[0]
      inputs = Inputs(filename, defines, options.ids_file)

    # Add in the grit source files.  If one of these change, we want to re-run
    # grit.
    inputs.extend(GritSourceFiles())
    inputs = [f.replace('\\', '/') for f in inputs]

    if len(args) == 1:
      # Include grd file as second input (works around gyp expecting it).
      inputs.insert(1, args[0])
    if options.whitelist_files:
      inputs.extend(options.whitelist_files)
    return '\n'.join(inputs)
  elif options.outputs:
    if len(args) != 2:
      raise WrongNumberOfArguments(
          "Expected exactly 2 arguments for --outputs.")

    prefix, filename = args
    outputs = [posixpath.join(prefix, f)
               for f in Outputs(filename, defines, options.ids_file)]
    return '\n'.join(outputs)
  else:
    raise WrongNumberOfArguments("Expected --inputs or --outputs.")


def main(argv):
  if sys.version_info < (2, 6):
    print "GRIT requires Python 2.6 or later."
    return 1

  try:
    result = DoMain(argv[1:])
  except WrongNumberOfArguments, e:
    PrintUsage()
    print e
    return 1
  print result
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
