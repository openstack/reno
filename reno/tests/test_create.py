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

import fixtures
import mock

from reno import create
from reno.tests import base


class TestPickFileName(base.TestCase):

    @mock.patch('os.path.exists')
    def test_not_random_enough(self, exists):
        exists.return_value = True
        self.assertRaises(
            ValueError,
            create._pick_note_file_name,
            'somepath',
            'someslug',
        )

    @mock.patch('os.path.exists')
    def test_random_enough(self, exists):
        exists.return_value = False
        result = create._pick_note_file_name('somepath', 'someslug')
        self.assertIn('somepath', result)
        self.assertIn('someslug', result)


class TestCreate(base.TestCase):

    def setUp(self):
        super(TestCreate, self).setUp()
        self.tmpdir = self.useFixture(fixtures.TempDir()).path

    def test_create_from_template(self):
        filename = create._pick_note_file_name(self.tmpdir, 'theslug')
        create._make_note_file(filename, 'i-am-a-template')
        with open(filename, 'r') as f:
            body = f.read()
        self.assertEqual('i-am-a-template', body)

    def test_edit(self):
        self.useFixture(fixtures.EnvironmentVariable('EDITOR', 'myeditor'))
        with mock.patch('subprocess.call') as call_mock:
            self.assertTrue(create._edit_file('somepath'))
            call_mock.assert_called_once_with(['myeditor', 'somepath'])

    def test_edit_without_editor_env_var(self):
        self.useFixture(fixtures.EnvironmentVariable('EDITOR'))
        with mock.patch('subprocess.call') as call_mock:
            self.assertFalse(create._edit_file('somepath'))
            call_mock.assert_not_called()
