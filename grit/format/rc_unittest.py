#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

'''Unit tests for grit.format.rc'''

import os
import re
import sys
if __name__ == '__main__':
  sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), '../..'))

import tempfile
import unittest
import StringIO

from grit import grd_reader
from grit import util
from grit.tool import build

class DummyOutput(object):
  def __init__(self, type, language, file = 'hello.gif'):
    self.type = type
    self.language = language
    self.file = file
  def GetType(self):
    return self.type
  def GetLanguage(self):
    return self.language
  def GetOutputFilename(self):
    return self.file

class FormatRcUnittest(unittest.TestCase):
  def testMessages(self):
    root = grd_reader.Parse(StringIO.StringIO('''
      <messages>
          <message name="IDS_BTN_GO" desc="Button text" meaning="verb">Go!</message>
          <message name="IDS_GREETING" desc="Printed to greet the currently logged in user">
            Hello <ph name="USERNAME">%s<ex>Joi</ex></ph>, how are you doing today?
          </message>
          <message name="BONGO" desc="Flippo nippo">
            Howdie "Mr. Elephant", how are you doing?   \'\'\'
          </message>
          <message name="IDS_WITH_LINEBREAKS">
Good day sir,
I am a bee
Sting sting
          </message>
      </messages>
      '''), flexible_root = True)
    util.FixRootForUnittest(root)

    buf = StringIO.StringIO()
    build.RcBuilder.ProcessNode(root, DummyOutput('rc_all', 'en'), buf)
    output = buf.getvalue()
    self.failUnless(output.strip() == u'''
STRINGTABLE
BEGIN
  IDS_BTN_GO      "Go!"
  IDS_GREETING    "Hello %s, how are you doing today?"
  BONGO           "Howdie ""Mr. Elephant"", how are you doing?   "
  IDS_WITH_LINEBREAKS "Good day sir,\\nI am a bee\\nSting sting"
END'''.strip())


  def testRcSection(self):
    root = grd_reader.Parse(StringIO.StringIO('''
      <structures>
          <structure type="menu" name="IDC_KLONKMENU" file="grit\\testdata\klonk.rc" encoding="utf-16" />
          <structure type="dialog" name="IDD_ABOUTBOX" file="grit\\testdata\klonk.rc" encoding="utf-16" />
          <structure type="version" name="VS_VERSION_INFO" file="grit\\testdata\klonk.rc" encoding="utf-16" />
      </structures>'''), flexible_root = True)
    util.FixRootForUnittest(root)
    root.RunGatherers(recursive = True)

    buf = StringIO.StringIO()
    build.RcBuilder.ProcessNode(root, DummyOutput('rc_all', 'en'), buf)
    output = buf.getvalue().strip()
    expected = u'''
IDC_KLONKMENU MENU
BEGIN
    POPUP "&File"
    BEGIN
        MENUITEM "E&xit",                       IDM_EXIT
        MENUITEM "This be ""Klonk"" me like",   ID_FILE_THISBE
        POPUP "gonk"
        BEGIN
            MENUITEM "Klonk && is [good]",           ID_GONK_KLONKIS
        END
    END
    POPUP "&Help"
    BEGIN
        MENUITEM "&About ...",                  IDM_ABOUT
    END
END

IDD_ABOUTBOX DIALOGEX 22, 17, 230, 75
STYLE DS_SETFONT | DS_MODALFRAME | WS_CAPTION | WS_SYSMENU
CAPTION "About"
FONT 8, "System", 0, 0, 0x0
BEGIN
    ICON            IDI_KLONK,IDC_MYICON,14,9,20,20
    LTEXT           "klonk Version ""yibbee"" 1.0",IDC_STATIC,49,10,119,8,
                    SS_NOPREFIX
    LTEXT           "Copyright (C) 2005",IDC_STATIC,49,20,119,8
    DEFPUSHBUTTON   "OK",IDOK,195,6,30,11,WS_GROUP
    CONTROL         "Jack ""Black"" Daniels",IDC_RADIO1,"Button",
                    BS_AUTORADIOBUTTON,46,51,84,10
END

VS_VERSION_INFO VERSIONINFO
 FILEVERSION 1,0,0,1
 PRODUCTVERSION 1,0,0,1
 FILEFLAGSMASK 0x17L
#ifdef _DEBUG
 FILEFLAGS 0x1L
#else
 FILEFLAGS 0x0L
#endif
 FILEOS 0x4L
 FILETYPE 0x1L
 FILESUBTYPE 0x0L
BEGIN
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "040904b0"
        BEGIN
            VALUE "FileDescription", "klonk Application"
            VALUE "FileVersion", "1, 0, 0, 1"
            VALUE "InternalName", "klonk"
            VALUE "LegalCopyright", "Copyright (C) 2005"
            VALUE "OriginalFilename", "klonk.exe"
            VALUE "ProductName", " klonk Application"
            VALUE "ProductVersion", "1, 0, 0, 1"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x409, 1200
    END
END'''.strip()
    for expected_line, output_line in zip(expected.split(), output.split()):
        self.assertEqual(expected_line, output_line)

  def testRcIncludeStructure(self):
    root = grd_reader.Parse(StringIO.StringIO('''
      <structures>
        <structure type="tr_html" name="IDR_HTML" file="bingo.html"/>
        <structure type="tr_html" name="IDR_HTML2" file="bingo2.html"/>
      </structures>'''), flexible_root = True)
    util.FixRootForUnittest(root, '/temp')
    # We do not run gatherers as it is not needed and wouldn't find the file

    buf = StringIO.StringIO()
    build.RcBuilder.ProcessNode(root, DummyOutput('rc_all', 'en'), buf)
    output = buf.getvalue()
    expected = (u'IDR_HTML           HTML               "%s"\n'
                u'IDR_HTML2          HTML               "%s"'
                % (util.normpath('/temp/bingo.html').replace('\\', '\\\\'),
                   util.normpath('/temp/bingo2.html').replace('\\', '\\\\')))
    # hackety hack to work on win32&lin
    output = re.sub('"[c-zC-Z]:', '"', output)
    self.failUnless(output.strip() == expected)

  def testRcIncludeFile(self):
    root = grd_reader.Parse(StringIO.StringIO('''
      <includes>
        <include type="TXT" name="TEXT_ONE" file="bingo.txt"/>
        <include type="TXT" name="TEXT_TWO" file="bingo2.txt"  filenameonly="true" />
      </includes>'''), flexible_root = True)
    util.FixRootForUnittest(root, '/temp')

    buf = StringIO.StringIO()
    build.RcBuilder.ProcessNode(root, DummyOutput('rc_all', 'en'), buf)
    output = buf.getvalue()
    expected = (u'TEXT_ONE           TXT                "%s"\n'
                u'TEXT_TWO           TXT                "%s"'
                % (util.normpath('/temp/bingo.txt').replace('\\', '\\\\'),
                   'bingo2.txt'))
    # hackety hack to work on win32&lin
    output = re.sub('"[c-zC-Z]:', '"', output)
    self.failUnless(output.strip() == expected)

  def testRcIncludeFlattenedHtmlFile(self):
    input_file = util.PathFromRoot('grit/testdata/include_test.html')
    output_file = '%s/HTML_FILE1_include_test.html' % tempfile.gettempdir()
    root = grd_reader.Parse(StringIO.StringIO('''
      <includes>
        <include name="HTML_FILE1" flattenhtml="true" file="%s" type="BINDATA" />
      </includes>''' % input_file), flexible_root = True)
    util.FixRootForUnittest(root, '.')

    buf = StringIO.StringIO()
    build.RcBuilder.ProcessNode(root, DummyOutput('rc_all', 'en', output_file),
                                buf)
    output = buf.getvalue()

    expected = u'HTML_FILE1         BINDATA            "HTML_FILE1_include_test.html"'
    # hackety hack to work on win32&lin
    output = re.sub('"[c-zC-Z]:', '"', output)
    self.failUnless(output.strip() == expected)

    file_contents = util.ReadFile(output_file, util.RAW_TEXT)

    # Check for the content added by the <include> tag.
    self.failUnless(file_contents.find('Hello Include!') != -1)
    # Check for the content that was removed by if tag.
    self.failUnless(file_contents.find('should be removed') == -1)
    # Check for the content that was kept in place by if.
    self.failUnless(file_contents.find('should be kept') != -1)
    self.failUnless(file_contents.find('in the middle...') != -1)
    self.failUnless(file_contents.find('at the end...') != -1)
    # Check for nested content that was kept
    self.failUnless(file_contents.find('nested true should be kept') != -1)
    self.failUnless(file_contents.find('silbing true should be kept') != -1)
    # Check for removed "<if>" and "</if>" tags.
    self.failUnless(file_contents.find('<if expr=') == -1)
    self.failUnless(file_contents.find('</if>') == -1)


  def testStructureNodeOutputfile(self):
    input_file = util.PathFromRoot('grit/testdata/simple.html')
    root = grd_reader.Parse(StringIO.StringIO(
      '<structure type="tr_html" name="IDR_HTML" file="%s" />' %input_file),
      flexible_root = True)
    util.FixRootForUnittest(root, '.')
    # We must run the gatherers since we'll be wanting the translation of the
    # file.  The file exists in the location pointed to.
    root.RunGatherers(recursive=True)

    output_dir = tempfile.gettempdir()
    en_file = root.FileForLanguage('en', output_dir)
    self.failUnless(en_file == input_file)
    fr_file = root.FileForLanguage('fr', output_dir)
    self.failUnless(fr_file == os.path.join(output_dir, 'fr_simple.html'))

    contents = util.ReadFile(fr_file, util.RAW_TEXT)

    self.failUnless(contents.find('<p>') != -1)  # should contain the markup
    self.failUnless(contents.find('Hello!') == -1)  # should be translated


  def testChromeHtmlNodeOutputfile(self):
    input_file = util.PathFromRoot('grit/testdata/chrome_html.html')
    output_file = '%s/HTML_FILE1_chrome_html.html' % tempfile.gettempdir()
    root = grd_reader.Parse(StringIO.StringIO(
        '<structure type="chrome_html" name="HTML_FILE1" file="%s" flattenhtml="true" />' %
        input_file), flexible_root = True)
    util.FixRootForUnittest(root, '.')
    # We must run the gatherers since we'll be wanting the chrome_html output.
    # The file exists in the location pointed to.
    root.RunGatherers(recursive=True)

    buf = StringIO.StringIO()
    build.RcBuilder.ProcessNode(root, DummyOutput('rc_all', 'en', output_file),
                                buf)
    output = buf.getvalue()
    expected = u'HTML_FILE1         HTML               "HTML_FILE1_chrome_html.html"'
    # hackety hack to work on win32&lin
    output = re.sub('"[c-zC-Z]:', '"', output)
    self.failUnless(output.strip() == expected)

    file_contents = util.ReadFile(output_file, util.RAW_TEXT)

    # Check for the content added by the <include> tag.
    self.failUnless(file_contents.find('Hello Include!') != -1)
    # Check for inserted -webkit-image-set.
    self.failUnless(file_contents.find('content: -webkit-image-set') != -1)


  def testSubstitutionHtml(self):
    input_file = util.PathFromRoot('grit/testdata/toolbar_about.html')
    root = grd_reader.Parse(StringIO.StringIO('''<?xml version="1.0" encoding="UTF-8"?>
      <grit latest_public_release="2" source_lang_id="en-US" current_release="3" base_dir=".">
        <release seq="1" allow_pseudo="False">
          <structures fallback_to_english="True">
            <structure type="tr_html" name="IDR_HTML" file="%s" expand_variables="true"/>
          </structures>
        </release>
      </grit>
      ''' % input_file), util.PathFromRoot('.'))
    util.FixRootForUnittest(root, '.')
    root.SetOutputLanguage('ar')
    # We must run the gatherers since we'll be wanting the translation of the
    # file.  The file exists in the location pointed to.
    root.RunGatherers(recursive=True)

    output_dir = tempfile.gettempdir()
    import grit.node.structure
    structure = root.GetChildrenOfType(grit.node.structure.StructureNode)[0]
    ar_file = structure.FileForLanguage('ar', output_dir)
    self.failUnless(ar_file == os.path.join(output_dir,
                                            'ar_toolbar_about.html'))

    contents = util.ReadFile(ar_file, util.RAW_TEXT)

    self.failUnless(contents.find('dir="RTL"') != -1)


  def testFallbackToEnglish(self):
    root = grd_reader.Parse(StringIO.StringIO('''<?xml version="1.0" encoding="UTF-8"?>
      <grit latest_public_release="2" source_lang_id="en-US" current_release="3" base_dir=".">
        <release seq="1" allow_pseudo="False">
          <structures fallback_to_english="True">
            <structure type="dialog" name="IDD_ABOUTBOX" file="grit\\testdata\klonk.rc" encoding="utf-16" />
          </structures>
        </release>
      </grit>'''), util.PathFromRoot('.'))
    util.FixRootForUnittest(root)
    root.SetOutputLanguage('en')
    root.RunGatherers(recursive = True)

    node = root.GetNodeById("IDD_ABOUTBOX")
    formatter = node.ItemFormatter('rc_all')
    output = formatter.Format(node, 'bingobongo')
    self.failUnless(output.strip() == '''IDD_ABOUTBOX DIALOGEX 22, 17, 230, 75
STYLE DS_SETFONT | DS_MODALFRAME | WS_CAPTION | WS_SYSMENU
CAPTION "About"
FONT 8, "System", 0, 0, 0x0
BEGIN
    ICON            IDI_KLONK,IDC_MYICON,14,9,20,20
    LTEXT           "klonk Version ""yibbee"" 1.0",IDC_STATIC,49,10,119,8,
                    SS_NOPREFIX
    LTEXT           "Copyright (C) 2005",IDC_STATIC,49,20,119,8
    DEFPUSHBUTTON   "OK",IDOK,195,6,30,11,WS_GROUP
    CONTROL         "Jack ""Black"" Daniels",IDC_RADIO1,"Button",
                    BS_AUTORADIOBUTTON,46,51,84,10
END''')


  def testSubstitutionRc(self):
    root = grd_reader.Parse(StringIO.StringIO('''<?xml version="1.0" encoding="UTF-8"?>
    <grit latest_public_release="2" source_lang_id="en-US" current_release="3"
        base_dir=".">
        <outputs>
          <output lang="en" type="rc_all" filename="grit\\testdata\klonk_resources.rc"/>
        </outputs>

      <release seq="1" allow_pseudo="False">
        <structures>
          <structure type="menu" name="IDC_KLONKMENU"
              file="grit\\testdata\klonk.rc" encoding="utf-16"
              expand_variables="true" />
        </structures>
        <messages>
          <message name="good" sub_variable="true">
            excellent
          </message>
        </messages>
      </release>
    </grit>
    '''), util.PathFromRoot('.'))
    util.FixRootForUnittest(root)
    root.SetOutputLanguage('en')
    root.RunGatherers(recursive=True)

    buf = StringIO.StringIO()
    build.RcBuilder.ProcessNode(root, DummyOutput('rc_all', 'en'), buf)
    output = buf.getvalue()
    self.failUnless(output.strip() == '''
// Copyright (c) Google Inc. 2012
// All rights reserved.
// This file is automatically generated by GRIT.  Do not edit.

#include "resource.h"
#include <winresrc.h>
#ifdef IDC_STATIC
#undef IDC_STATIC
#endif
#define IDC_STATIC (-1)

LANGUAGE LANG_NEUTRAL, SUBLANG_NEUTRAL


IDC_KLONKMENU MENU
BEGIN
    POPUP "&File"
    BEGIN
        MENUITEM "E&xit",                       IDM_EXIT
        MENUITEM "This be ""Klonk"" me like",   ID_FILE_THISBE
        POPUP "gonk"
        BEGIN
            MENUITEM "Klonk && is excellent",           ID_GONK_KLONKIS
        END
    END
    POPUP "&Help"
    BEGIN
        MENUITEM "&About ...",                  IDM_ABOUT
    END
END

STRINGTABLE
BEGIN
  good            "excellent"
END
'''.strip())


if __name__ == '__main__':
  unittest.main()
