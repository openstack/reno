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
import logging
import os
import os.path
import random
import subprocess

LOG = logging.getLogger(__name__)


def get_random_string(nbytes: int = 8) -> str:
    """Return a fixed-length random string

    :rtype: str
    """
    try:
        # NOTE(dhellmann): Not all systems support urandom().
        # hexlify returns binary, decode to convert to str.
        val = binascii.hexlify(os.urandom(nbytes)).decode('utf-8')
    except Exception as e:
        print('ERROR, perhaps urandom is not supported: %s' % e)
        val = ''.join('%02x' % random.randrange(256) for i in range(nbytes))
    return val


def check_output(*args: str, cwd: str | None = None) -> str:
    """Unicode-aware wrapper for subprocess.check_output"""
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
    )
    output, errors = process.communicate()
    retcode = process.poll()
    if errors:
        LOG.debug('ran: %s', ' '.join(args))
        LOG.debug('returned: %s', retcode)
        LOG.debug('error output: %s', errors.rstrip())
        LOG.debug('regular output: %s', output.rstrip())
    if retcode:
        LOG.debug('raising error')
        raise subprocess.CalledProcessError(
            retcode,
            args,
            output=output,
        )
    assert output is not None
    return output.decode('utf-8')
