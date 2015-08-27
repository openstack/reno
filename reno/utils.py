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

import binascii
import os
import os.path
import random


def get_notes_dir(args):
    "Return the path to the release notes directory."
    return os.path.join(args.relnotesdir, 'notes')


def get_random_string(nbytes=8):
    "Return a fixed-length random string"
    try:
        # NOTE(dhellmann): Not all systems support urandom().
        val = os.urandom(nbytes)
    except Exception:
        val = ''.join(chr(random.randrange(256)) for i in range(nbytes))
    return binascii.hexlify(val)
