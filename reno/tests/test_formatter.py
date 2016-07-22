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

import mock

from reno import config
from reno import formatter
from reno import loader
from reno.tests import base


class TestFormatter(base.TestCase):

    scanner_output = {
        '0.0.0': [('note1', 'shaA')],
        '1.0.0': [('note2', 'shaB'), ('note3', 'shaC')],
    }

    versions = ['0.0.0', '1.0.0']

    note_bodies = {
        'note1': {
            'prelude': 'This is the prelude.',
        },
        'note2': {
            'issues': [
                'This is the first issue.',
                'This is the second issue.',
            ],
        },
        'note3': {
            'features': [
                'We added a feature!',
            ],
            'upgrade': None,
        },
    }

    def _get_note_body(self, reporoot, filename, sha):
        return self.note_bodies.get(filename, '')

    def setUp(self):
        super(TestFormatter, self).setUp()

        def _load(ldr):
            ldr._scanner_output = self.scanner_output
            ldr._cache = {
                'file-contents': self.note_bodies
            }

        self.c = config.Config('reporoot')

        with mock.patch('reno.loader.Loader._load_data', _load):
            self.ldr = loader.Loader(
                self.c,
                ignore_cache=False,
            )

    def test_with_title(self):
        result = formatter.format_report(
            loader=self.ldr,
            versions_to_include=self.versions,
            title='This is the title',
        )
        self.assertIn('This is the title', result)

    def test_versions(self):
        result = formatter.format_report(
            loader=self.ldr,
            versions_to_include=self.versions,
            title='This is the title',
        )
        self.assertIn('0.0.0\n=====', result)
        self.assertIn('1.0.0\n=====', result)

    def test_without_title(self):
        result = formatter.format_report(
            loader=self.ldr,
            versions_to_include=self.versions,
            title=None,
        )
        self.assertNotIn('This is the title', result)

    def test_section_order(self):
        result = formatter.format_report(
            loader=self.ldr,
            versions_to_include=self.versions,
            title=None,
        )
        prelude_pos = result.index('This is the prelude.')
        issues_pos = result.index('This is the first issue.')
        features_pos = result.index('We added a feature!')
        expected = [prelude_pos, features_pos, issues_pos]
        actual = list(sorted([prelude_pos, features_pos, issues_pos]))
        self.assertEqual(expected, actual)
