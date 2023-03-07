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
import argparse
import os
from unittest import mock

import fixtures
from testtools import ExpectedException

from reno import config
from reno.config import Section
from reno import defaults
from reno import main
from reno.tests import base


def expected_options(**overrides):
    """The default config options, along with any overrides set via kwargs."""
    result = {
        o.name: (
            Section.from_raw_yaml(o.default)
            if o.name == "sections"
            else o.default
        )
        for o in config._OPTIONS
    }
    result.update(**overrides)
    return result


class TestConfig(base.TestCase):
    EXAMPLE_CONFIG = """
collapse_pre_releases: false
"""

    def setUp(self):
        super(TestConfig, self).setUp()
        # Temporary directory to store our config
        self.tempdir = self.useFixture(fixtures.TempDir())

    def test_defaults(self):
        c = config.Config(self.tempdir.path)
        actual = c.options
        self.assertEqual(expected_options(), actual)

    def test_override(self):
        c = config.Config(self.tempdir.path)
        c.override(
            collapse_pre_releases=False,
        )
        actual = c.options
        expected = expected_options(collapse_pre_releases=False)
        self.assertEqual(expected, actual)

    def test_override_multiple(self):
        c = config.Config(self.tempdir.path)
        c.override(
            notesdir='value1',
        )
        c.override(
            notesdir='value2',
        )
        actual = c.options
        expected = expected_options(notesdir='value2')
        self.assertEqual(expected, actual)

    def test_override_sections_with_subsections(self):
        c = config.Config(self.tempdir.path)
        c.override(
            sections=[
                ["features", "Features"],
                ["features_sub", "Sub", 2],
                ["features_subsub", "Subsub", 3],
                ["bugs", "Bugs"],
                ["bugs_sub", "Sub", 2],
                ["documentation", "Documentation", 1]
            ],
        )
        actual = c.options
        expected = expected_options(
            sections=[
                Section("features", "Features", section_level=1),
                Section("features_sub", "Sub", section_level=2),
                Section("features_subsub", "Subsub", section_level=3),
                Section("bugs", "Bugs", section_level=1),
                Section("bugs_sub", "Sub", section_level=2),
                Section("documentation", "Documentation", section_level=1),
            ]
        )
        self.assertEqual(expected, actual)

        # Also check data validation.
        with ExpectedException(ValueError):
            c.override(sections=[["features"]])
        with ExpectedException(ValueError):
            c.override(sections=[["features", "Features", 0]])
        with ExpectedException(ValueError):
            c.override(sections=[["features", "Features", 5]])

    def test_load_file_not_present(self):
        missing = 'reno.config.Config._report_missing_config_files'
        with mock.patch(missing) as error_handler:
            config.Config(self.tempdir.path)
            self.assertEqual(1, error_handler.call_count)

    def _test_load_file(self, config_path):
        with open(config_path, 'w') as fd:
            fd.write(self.EXAMPLE_CONFIG)
        self.addCleanup(os.unlink, config_path)
        c = config.Config(self.tempdir.path)
        self.assertEqual(False, c.collapse_pre_releases)

    def test_load_file_in_releasenotesdir(self):
        rn_path = self.tempdir.join('releasenotes')
        os.mkdir(rn_path)
        config_path = self.tempdir.join('releasenotes/config.yaml')
        self._test_load_file(config_path)

    def test_load_file_in_repodir(self):
        config_path = self.tempdir.join('reno.yaml')
        self._test_load_file(config_path)

    def test_load_file_empty(self):
        config_path = self.tempdir.join('reno.yaml')
        with open(config_path, 'w') as fd:
            fd.write('# Add reno config here')
        self.addCleanup(os.unlink, config_path)
        c = config.Config(self.tempdir.path)
        self.assertEqual(True, c.collapse_pre_releases)

    def test_get_default(self):
        d = config.Config.get_default('notesdir')
        self.assertEqual('notes', d)

    def test_get_default_unknown(self):
        self.assertRaises(
            ValueError,
            config.Config.get_default,
            'unknownopt',
        )

    def _run_override_from_parsed_args(self, argv):
        parser = argparse.ArgumentParser()
        main._build_query_arg_group(parser)
        args = parser.parse_args(argv)
        c = config.Config(self.tempdir.path)
        c.override_from_parsed_args(args)
        return c

    def test_override_from_parsed_args_empty(self):
        c = self._run_override_from_parsed_args([])
        actual = {
            o.name: getattr(c, o.name)
            for o in config._OPTIONS
        }
        self.assertEqual(expected_options(), actual)

    def test_override_from_parsed_args_boolean_false(self):
        c = self._run_override_from_parsed_args([
            '--no-collapse-pre-releases',
        ])
        actual = c.options
        expected = expected_options(collapse_pre_releases=False)
        self.assertEqual(expected, actual)

    def test_override_from_parsed_args_boolean_true(self):
        c = self._run_override_from_parsed_args([
            '--collapse-pre-releases',
        ])
        actual = c.options
        expected = expected_options(collapse_pre_releases=True)
        self.assertEqual(expected, actual)

    def test_override_from_parsed_args_string(self):
        c = self._run_override_from_parsed_args([
            '--earliest-version', '1.2.3',
        ])
        actual = c.options
        expected = expected_options(earliest_version='1.2.3')
        self.assertEqual(expected, actual)

    def test_override_from_parsed_args_ignore_non_options(self):
        parser = argparse.ArgumentParser()
        main._build_query_arg_group(parser)
        parser.add_argument('not_a_config_option')
        args = parser.parse_args(['value'])
        c = config.Config(self.tempdir.path)
        c.override_from_parsed_args(args)
        self.assertFalse(hasattr(c, 'not_a_config_option'))


class TestConfigProperties(base.TestCase):

    def setUp(self):
        super(TestConfigProperties, self).setUp()
        # Temporary directory to store our config
        self.tempdir = self.useFixture(fixtures.TempDir())
        self.c = config.Config('releasenotes')

    def test_reporoot(self):
        self.c.reporoot = 'blah//'
        self.assertEqual('blah/', self.c.reporoot)
        self.c.reporoot = 'blah'
        self.assertEqual('blah/', self.c.reporoot)

    def test_notespath(self):
        self.assertEqual('releasenotes/notes', self.c.notespath)
        self.c.override(notesdir='thenotes')
        self.assertEqual('releasenotes/thenotes', self.c.notespath)

    def test_template(self):
        template = defaults.TEMPLATE.format(defaults.PRELUDE_SECTION_NAME)
        self.assertEqual(template, self.c.template)
        self.c.override(template='i-am-a-template')
        self.assertEqual('i-am-a-template', self.c.template)

    def test_prelude_override(self):
        template = defaults.TEMPLATE.format(defaults.PRELUDE_SECTION_NAME)
        self.assertEqual(template, self.c.template)
        self.c.override(prelude_section_name='fake_prelude_name')
        expected_template = defaults.TEMPLATE.format('fake_prelude_name')
        self.assertEqual(expected_template, self.c.template)

    def test_prelude_and_template_override(self):
        template = defaults.TEMPLATE.format(defaults.PRELUDE_SECTION_NAME)
        self.assertEqual(template, self.c.template)
        self.c.override(prelude_section_name='fake_prelude_name',
                        template='i-am-a-template')
        self.assertEqual('fake_prelude_name', self.c.prelude_section_name)
        self.assertEqual('i-am-a-template', self.c.template)
