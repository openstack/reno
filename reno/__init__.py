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

import pbr.version


__version__ = pbr.version.VersionInfo(
    'reno').version_string()

# Configure a null logger so that if reno is used as a library by an
# application that does not configure logging there are no warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())
