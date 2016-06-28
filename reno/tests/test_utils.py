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
import six

from reno.tests import base
from reno import utils


class TestGetRandomString(base.TestCase):

    @mock.patch('random.randrange')
    @mock.patch('os.urandom')
    def test_no_urandom(self, urandom, randrange):
        urandom.side_effect = Exception('cannot use this')
        randrange.return_value = ord('a')
        actual = utils.get_random_string()
        expected = '61' * 8  # hex for ord('a')
        self.assertIsInstance(actual, six.text_type)
        self.assertEqual(expected, actual)

    @mock.patch('random.randrange')
    @mock.patch('os.urandom')
    def test_with_urandom(self, urandom, randrange):
        urandom.return_value = b'\x62' * 8
        randrange.return_value = ord('a')
        actual = utils.get_random_string()
        expected = '62' * 8  # hex for ord('b')
        self.assertIsInstance(actual, six.text_type)
        self.assertEqual(expected, actual)
