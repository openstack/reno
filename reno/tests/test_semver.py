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


from reno import config
from reno import semver
from reno.tests import base


class TestSemVer(base.TestCase):

    note_bodies = {
        'none': textwrap.dedent("""
        prelude: >
          This should not cause any version update.
        """),
        'major': textwrap.dedent("""
        upgrade:
          - This should cause a major version update.
        """),
        'minor': textwrap.dedent("""
        features:
          - This should cause a minor version update.
        """),
        'patch': textwrap.dedent("""
        fixes:
          - This should cause a patch version update.
        """),
    }

    def _get_note_body(self, filename, sha):
        return self.note_bodies.get(filename, '')

    def _get_dates(self):
        return {'1.0.0': 1547874431}

    def setUp(self):
        super(TestSemVer, self).setUp()
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
    def test_same(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('1.1.1', []),
        ])
        expected = '1.1.1'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_same_with_note(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('1.1.1', [('none', 'shaA')]),
        ])
        expected = '1.1.1'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_major_working_copy(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('*working-copy*', [('major', 'shaA')]),
            ('1.1.1', []),
        ])
        expected = '2.0.0'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_major_working_and_post_release(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('*working-copy*', [('none', 'shaA')]),
            ('1.1.1-1', [('major', 'shaA')]),
        ])
        expected = '2.0.0'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_major_post_release(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('1.1.1-1', [('major', 'shaA')]),
        ])
        expected = '2.0.0'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_minor_working_copy(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('*working-copy*', [('minor', 'shaA')]),
            ('1.1.1', []),
        ])
        expected = '1.2.0'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_minor_working_and_post_release(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('*working-copy*', [('none', 'shaA')]),
            ('1.1.1-1', [('minor', 'shaA')]),
        ])
        expected = '1.2.0'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_minor_post_release(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('1.1.1-1', [('minor', 'shaA')]),
        ])
        expected = '1.2.0'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_patch_working_copy(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('*working-copy*', [('patch', 'shaA')]),
            ('1.1.1', []),
        ])
        expected = '1.1.2'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_patch_working_and_post_release(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('*working-copy*', [('none', 'shaA')]),
            ('1.1.1-1', [('patch', 'shaA')]),
        ])
        expected = '1.1.2'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)

    @mock.patch('reno.scanner.Scanner.get_notes_by_version')
    def test_patch_post_release(self, mock_get_notes):
        mock_get_notes.return_value = collections.OrderedDict([
            ('1.1.1-1', [('patch', 'shaA')]),
        ])
        expected = '1.1.2'
        actual = semver.compute_next_version(self.c)
        self.assertEqual(expected, actual)
