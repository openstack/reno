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

import logging
import textwrap

import fixtures
import mock
import six
import yaml

from reno import config
from reno import loader
from reno.tests import base


class TestValidate(base.TestCase):

    scanner_output = {
        '0.0.0': [('note', 'shaA')],
    }

    versions = ['0.0.0']

    def setUp(self):
        super(TestValidate, self).setUp()
        self.logger = self.useFixture(
            fixtures.FakeLogger(
                format='%(message)s',
                level=logging.WARNING,
            )
        )
        self.c = config.Config('reporoot')

    def _make_loader(self, note_bodies):
        def _load(ldr):
            ldr._scanner_output = self.scanner_output
            ldr._cache = {
                'file-contents': {'note1': note_bodies},
            }

        with mock.patch('reno.loader.Loader._load_data', _load):
            return loader.Loader(
                self.c,
                ignore_cache=False,
            )

    def test_prelude_list(self):
        note_bodies = yaml.safe_load(textwrap.dedent('''
        prelude:
          - This is the first comment.
          - This is a second.
        '''))
        self.assertIsInstance(note_bodies['prelude'], list)
        ldr = self._make_loader(note_bodies)
        ldr.parse_note_file('note1', None)
        self.assertIn('prelude', self.logger.output)

    def test_non_prelude_single_string(self):
        note_bodies = yaml.safe_load(textwrap.dedent('''
        issues: |
          This is a single string.
        '''))
        print(type(note_bodies['issues']))
        self.assertIsInstance(note_bodies['issues'], six.string_types)
        ldr = self._make_loader(note_bodies)
        ldr.parse_note_file('note1', None)
        self.assertIn('list of strings', self.logger.output)

    def test_note_with_colon_as_dict(self):
        note_bodies = yaml.safe_load(textwrap.dedent('''
        issues:
          - This is the first issue.
          - dict: This is parsed as a dictionary.
        '''))
        self.assertIsInstance(note_bodies['issues'][-1], dict)
        ldr = self._make_loader(note_bodies)
        ldr.parse_note_file('note1', None)
        self.assertIn('dict', self.logger.output)
