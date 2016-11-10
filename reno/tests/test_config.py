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

import fixtures

from reno import config
from reno import main
from reno.tests import base

import mock


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
        actual = {
            o: getattr(c, o)
            for o in config.Config._OPTS.keys()
        }
        self.assertEqual(config.Config._OPTS, actual)

    def test_override(self):
        c = config.Config(self.tempdir.path)
        c.override(
            collapse_pre_releases=False,
        )
        actual = {
            o: getattr(c, o)
            for o in config.Config._OPTS.keys()
        }
        expected = {}
        expected.update(config.Config._OPTS)
        expected['collapse_pre_releases'] = False
        self.assertEqual(expected, actual)

    def test_override_multiple(self):
        c = config.Config(self.tempdir.path)
        c.override(
            notesdir='value1',
        )
        c.override(
            notesdir='value2',
        )
        actual = {
            o: getattr(c, o)
            for o in config.Config._OPTS.keys()
        }
        expected = {}
        expected.update(config.Config._OPTS)
        expected['notesdir'] = 'value2'
        self.assertEqual(expected, actual)

    def test_load_file_not_present(self):
        with mock.patch.object(config.LOG, 'info') as logger:
            config.Config(self.tempdir.path)
            self.assertEqual(1, logger.call_count)

    def test_load_file(self):
        rn_path = self.tempdir.join('releasenotes')
        os.mkdir(rn_path)
        config_path = self.tempdir.join('releasenotes/' +
                                        config.Config._FILENAME)
        with open(config_path, 'w') as fd:
            fd.write(self.EXAMPLE_CONFIG)
        self.addCleanup(os.unlink, config_path)
        c = config.Config(self.tempdir.path)
        self.assertEqual(False, c.collapse_pre_releases)

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
            o: getattr(c, o)
            for o in config.Config._OPTS.keys()
        }
        self.assertEqual(config.Config._OPTS, actual)

    def test_override_from_parsed_args(self):
        c = self._run_override_from_parsed_args([
            '--no-collapse-pre-releases',
        ])
        actual = {
            o: getattr(c, o)
            for o in config.Config._OPTS.keys()
        }
        expected = {}
        expected.update(config.Config._OPTS)
        expected['collapse_pre_releases'] = False
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
        self.assertEqual(config._TEMPLATE, self.c.template)
        self.c.override(template='i-am-a-template')
        self.assertEqual('i-am-a-template', self.c.template)
