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

import collections
from unittest import mock

import fixtures
import textwrap


from reno import cache
from reno import config
from reno.tests import base


class TestCache(base.TestCase):

    scanner_output = [
        collections.OrderedDict([  # master
            ('0.0.0', [('note1', 'shaA')]),
            ('1.0.0', [('note2', 'shaB'), ('note3', 'shaC')]),
        ]),
        collections.OrderedDict([  # stable/1.0
            ('1.0.1', [('note4', 'shaD')]),
        ]),
    ]

    note_bodies = {
        'note1': textwrap.dedent("""
        prelude: >
          This is the prelude.
        """),
        'note2': textwrap.dedent("""
        issues:
          - This is the first issue.
          - This is the second issue.
        """),
        'note3': textwrap.dedent("""
        features:
          - We added a feature!
        """),
        'note4': textwrap.dedent("""
        fixes:
          - We fixed all the bugs!
        """),
    }

    def _get_note_body(self, filename, sha):
        return self.note_bodies.get(filename, '')

    def _get_dates(self):
        return {'1.0.0': 1547874431}

    def setUp(self):
        super(TestCache, self).setUp()
        self.useFixture(
            fixtures.MockPatch('reno.scanner.Scanner.get_file_at_commit',
                               new=self._get_note_body)
        )
        self.useFixture(
            fixtures.MockPatch('reno.scanner.Scanner.get_version_dates',
                               new=self._get_dates)
        )
        self.c = config.Config('.')

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    @mock.patch('reno.scanner.Scanner.get_series_branches')
    def test_build_cache_db(self, mock_get_branches, mock_get_notes):
        mock_get_notes.side_effect = self.scanner_output
        mock_get_branches.return_value = ['stable/1.0']
        expected = {
            'dates': [{'version': '1.0.0', 'date': 1547874431}],
            'notes': [
                {'version': '0.0.0',
                 'files': [('note1', 'shaA')]},
                {'version': '1.0.0',
                 'files': [('note2', 'shaB'), ('note3', 'shaC')]},
                {'version': '1.0.1',
                 'files': [('note4', 'shaD')]},
            ],
            'file-contents': {
                'note1': {
                    'prelude': 'This is the prelude.\n',
                },
                'note2': {
                    'issues': [
                        'This is the first issue.',
                        'This is the second issue.',
                    ],
                },
                'note3': {
                    'features': ['We added a feature!'],
                },
                'note4': {
                    'fixes': ['We fixed all the bugs!'],
                },
            },
        }

        db = cache.build_cache_db(
            self.c,
            versions_to_include=[],
        )

        mock_get_branches.assert_called_once()
        mock_get_notes.assert_has_calls([
            mock.call(None), mock.call('stable/1.0')])
        self.assertEqual(expected, db)
