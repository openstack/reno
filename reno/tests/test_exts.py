# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import textwrap

from reno._exts import show_reno_config
from reno import config
from reno.tests import base


class TestMultiLineString(base.TestCase):

    def test_no_indent(self):
        input = textwrap.dedent("""\
        The notes subdirectory within the relnotesdir where the
        notes live.
        """)
        expected = '\n'.join([
            'The notes subdirectory within the relnotesdir where the',
            'notes live.',
        ])
        actual = '\n'.join(show_reno_config._multi_line_string(input))
        self.assertEqual(expected, actual)

    def test_with_indent(self):
        input = textwrap.dedent("""\
        The notes subdirectory within the relnotesdir where the
        notes live.
        """)
        expected = '\n'.join([
            '  The notes subdirectory within the relnotesdir where the',
            '  notes live.',
        ])
        actual = '\n'.join(show_reno_config._multi_line_string(input, '  '))
        self.assertEqual(expected, actual)

    def test_first_line_blank(self):
        input = textwrap.dedent("""
        The notes subdirectory within the relnotesdir where the
        notes live.
        """)
        expected = '\n'.join([
            '  The notes subdirectory within the relnotesdir where the',
            '  notes live.',
        ])
        actual = '\n'.join(show_reno_config._multi_line_string(input, '  '))
        self.assertEqual(expected, actual)


class TestFormatOptionHelp(base.TestCase):

    def test_simple_default(self):
        opt = config.Opt(
            'notesdir', 'path/to/notes',
            textwrap.dedent("""\
            The notes subdirectory within the relnotesdir where the
            notes live.
            """),
        )
        actual = '\n'.join(show_reno_config._format_option_help([opt]))
        expected = textwrap.dedent("""\
        ``notesdir``
          The notes subdirectory within the relnotesdir where the
          notes live.

          Defaults to ``'path/to/notes'``
        """)
        self.assertEqual(expected, actual)

    def test_bool_default(self):
        opt = config.Opt(
            'collapse_pre_releases', True,
            textwrap.dedent("""\
            Should pre-release versions be merged into the final release
            of the same number (1.0.0.0a1 notes appear under 1.0.0).
            """),
        )
        actual = '\n'.join(show_reno_config._format_option_help([opt]))
        expected = textwrap.dedent("""\
        ``collapse_pre_releases``
          Should pre-release versions be merged into the final release
          of the same number (1.0.0.0a1 notes appear under 1.0.0).

          Defaults to ``True``
        """)
        self.assertEqual(expected, actual)

    def test_multiline_default(self):
        opt = config.Opt(
            'release_tag_re',
            textwrap.dedent('''\
            ((?:[\\d.ab]|rc)+)  # digits, a, b, and rc cover regular and
                               # pre-releases
            '''),
            textwrap.dedent("""\
            The regex pattern used to match the repo tags representing a
            valid release version. The pattern is compiled with the
            verbose and unicode flags enabled.
            """),
        )
        actual = '\n'.join(show_reno_config._format_option_help([opt]))
        expected = textwrap.dedent("""\
        ``release_tag_re``
          The regex pattern used to match the repo tags representing a
          valid release version. The pattern is compiled with the
          verbose and unicode flags enabled.

          Defaults to

          ::

            ((?:[\\d.ab]|rc)+)  # digits, a, b, and rc cover regular and
                               # pre-releases
        """)
        self.assertEqual(expected, actual)
