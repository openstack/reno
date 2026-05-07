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
import warnings

import pbr.version


def __getattr__(name: str) -> str:
    if name == '__version__':
        warnings.warn(
            "Accessing reno.__version__ is deprecated and will be "
            "removed in a future release. Use importlib.metadata instead: "
            "importlib.metadata.version('reno')",
            DeprecationWarning,
            stacklevel=2,
        )
        return pbr.version.VersionInfo('reno').version_string()
    raise AttributeError(f"module 'reno' has no attribute {name!r}")


# Configure a null logger so that if reno is used as a library by an
# application that does not configure logging there are no warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())
