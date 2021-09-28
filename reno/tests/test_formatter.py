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

from unittest import mock

from reno import config
from reno import formatter
from reno import loader
from reno.tests import base


class TestFormatterBase(base.TestCase):

    scanner_output = {
        '0.0.0': [('note1', 'shaA')],
        '1.0.0': [('note2', 'shaB'), ('note3', 'shaC')],
    }

    versions = ['0.0.0', '1.0.0']

    def _get_note_body(self, reporoot, filename, sha):
        return self.note_bodies.get(filename, '')

    def setUp(self):
        super(TestFormatterBase, self).setUp()

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

    def tearDown(self):
        # we don't need to worry about closing this after since we're not
        # actually using a real Git repo here (see the mock above), but we'll
        # do so to enforce the contract
        self.ldr.close()
        super().tearDown()


class TestFormatter(TestFormatterBase):

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

    def test_with_title(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title='This is the title',
        )
        self.assertIn('This is the title', result)

    def test_versions(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title='This is the title',
        )
        self.assertIn('0.0.0\n=====', result)
        self.assertIn('1.0.0\n=====', result)

    def test_without_title(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title=None,
        )
        self.assertNotIn('This is the title', result)

    def test_default_section_order(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title=None,
        )
        prelude_pos = result.index('This is the prelude.')
        issues_pos = result.index('This is the first issue.')
        features_pos = result.index('We added a feature!')
        expected = [prelude_pos, features_pos, issues_pos]
        actual = list(sorted([prelude_pos, features_pos, issues_pos]))
        self.assertEqual(expected, actual)


class TestFormatterCustomSections(TestFormatterBase):
    note_bodies = {
        'note1': {
            'prelude': 'This is the prelude.',
        },
        'note2': {
            'features': [
                'This is the first feature.',
            ],
            'api': [
                'This is the API change for the first feature.',
            ],
        },
        'note3': {
            'api': [
                'This is the API change for the second feature.',
            ],
            'features': [
                'This is the second feature.',
            ],
        },
    }

    def setUp(self):
        super(TestFormatterCustomSections, self).setUp()
        self.c.override(sections=[
            ['api', 'API Changes'],
            ['features', 'New Features'],
        ])

    def test_custom_section_order(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title=None,
        )
        prelude_pos = result.index('This is the prelude.')
        api_pos = result.index('API Changes')
        features_pos = result.index('New Features')
        expected = [prelude_pos, api_pos, features_pos]
        actual = list(sorted([prelude_pos, features_pos, api_pos]))
        self.assertEqual(expected, actual)
        self.assertIn('.. _relnotes_1.0.0_API Changes:', result)


class TestFormatterCustomUnreleaseTitle(TestFormatterBase):

    note_bodies = {
        'note1': {
            'prelude': 'This is the prelude.',
        },
    }

    scanner_output = {
        '0.1.0-1': [('note1', 'shaA')],
    }

    versions = ['0.1.0-1']

    def test_with_title(self):
        self.c.override(unreleased_version_title='Not Released')
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title='This is the title',
        )
        self.assertIn('Not Released', result)
        self.assertNotIn('0.1.0-1', result)
        self.assertIn('.. _This is the title_Not Released:', result)

    def test_without_title(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title='This is the title',
        )
        self.assertIn('0.1.0-1', result)
        self.assertIn('.. _This is the title_0.1.0-1:', result)


class TestFormatterAnchors(TestFormatterBase):

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

    def test_with_title(self):
        self.c.override(unreleased_version_title='Not Released')
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title='This is the title',
        )
        self.assertIn('.. _This is the title_0.0.0:', result)
        self.assertIn('.. _This is the title_0.0.0_Prelude:', result)
        self.assertIn('.. _This is the title_1.0.0:', result)
        self.assertIn('.. _This is the title_1.0.0_Known Issues:', result)

    def test_without_title(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
        )
        self.assertIn('.. _relnotes_0.0.0:', result)
        self.assertIn('.. _relnotes_0.0.0_Prelude:', result)
        self.assertIn('.. _relnotes_1.0.0:', result)
        self.assertIn('.. _relnotes_1.0.0_Known Issues:', result)

    def test_with_branch_and_title(self):
        self.c.override(unreleased_version_title='Not Released')
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            title='This is the title',
            branch='stable/queens',
        )
        self.assertIn('.. _This is the title_0.0.0_stable_queens:', result)
        self.assertIn('.. _This is the title_0.0.0_stable_queens_Prelude:',
                      result)
        self.assertIn('.. _This is the title_1.0.0_stable_queens:', result)
        self.assertIn(
            '.. _This is the title_1.0.0_stable_queens_Known Issues:',
            result)

    def test_with_branch(self):
        result = formatter.format_report(
            loader=self.ldr,
            config=self.c,
            versions_to_include=self.versions,
            branch='stable/queens',
        )
        self.assertIn('.. _relnotes_0.0.0_stable_queens:', result)
        self.assertIn('.. _relnotes_0.0.0_stable_queens_Prelude:', result)
        self.assertIn('.. _relnotes_1.0.0_stable_queens:', result)
        self.assertIn('.. _relnotes_1.0.0_stable_queens_Known Issues:', result)
