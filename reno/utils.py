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
import subprocess

from reno import defaults


def get_notes_dir(args):
    "Return the path to the release notes directory."
    return os.path.join(args.relnotesdir, defaults.NOTES_SUBDIR)


def get_random_string(nbytes=8):
    "Return a fixed-length random string"
    try:
        # NOTE(dhellmann): Not all systems support urandom(). When it
        # is supported, it returns a str() but under Python 3 we need
        # to give a byte string to hexlify() so convert back and forth
        # through utf-8.
        rand_bytes_bstring = os.urandom(nbytes).encode('utf-8')
        val = binascii.hexlify(rand_bytes_bstring).decode('utf-8')
    except Exception as e:
        print('ERROR: %s' % e)
        val = ''.join('%02x' % random.randrange(256)
                      for i in range(nbytes))
    return val


def check_output(*args, **kwds):
    "Unicode-aware wrapper for subprocess.check_output"
    raw = subprocess.check_output(*args, **kwds)
    return raw.decode('utf-8')
