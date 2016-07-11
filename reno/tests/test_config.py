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
from reno import defaults
from reno.tests import base


class TestConfig(base.TestCase):
    EXAMPLE_CONFIG = """
branch: master
collapse_pre_releases: false
earliest_version: true
"""

    def setUp(self):
        super(TestConfig, self).setUp()
        # Temporary directory to store our config
        self.tempdir = self.useFixture(fixtures.TempDir())

        # Argument parser and parsed arguments for our config function
        parser = argparse.ArgumentParser()
        parser.add_argument('--branch')
        parser.add_argument('--collapse-pre-releases')
        parser.add_argument('--earliest-version')
        self.args = parser.parse_args([])
        self.args.relnotesdir = self.tempdir.path

        config_path = self.tempdir.join(defaults.RELEASE_NOTES_CONFIG_FILENAME)

        with open(config_path, 'w') as fd:
            fd.write(self.EXAMPLE_CONFIG)

        self.addCleanup(os.unlink, config_path)
        self.config_path = config_path

    def test_applies_relevant_config_values(self):
        """Verify that our config function overrides default values."""
        config.parse_config_into(self.args)
        del self.args._config
        expected_value = {
            'relnotesdir': self.tempdir.path,
            'branch': 'master',
            'collapse_pre_releases': False,
            'earliest_version': True,
        }
        self.assertDictEqual(expected_value, vars(self.args))

    def test_does_not_add_extra_options(self):
        """Show that earliest_version is not set when missing."""
        del self.args.earliest_version
        self.assertEqual(0, getattr(self.args, 'earliest_version', 0))

        config.parse_config_into(self.args)
        del self.args._config
        expected_value = {
            'relnotesdir': self.tempdir.path,
            'branch': 'master',
            'collapse_pre_releases': False,
        }

        self.assertDictEqual(expected_value, vars(self.args))

    def test_get_congfig_path(self):
        """Show that we generate the path appropriately."""
        self.assertEqual('releasenotes/config.yml',
                         config.get_config_path('releasenotes'))

    def test_read_config_shortcircuits(self):
        """Verify we don't try to open a non-existent file."""
        self.assertDictEqual({},
                             config.read_config('fake/path/to/config.yml'))

    def test_read_config(self):
        """Verify we read and parse the config file specified if it exists."""
        self.assertDictEqual({'branch': 'master',
                              'collapse_pre_releases': False,
                              'earliest_version': True},
                             config.read_config(self.config_path))
