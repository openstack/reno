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

from __future__ import print_function

import logging

from reno import loader

LOG = logging.getLogger(__name__)


def list_cmd(args, conf):
    "List notes files based on query arguments"
    LOG.debug('starting list')
    reporoot = conf.reporoot
    ldr = loader.Loader(conf)
    if args.version:
        versions = args.version
    else:
        versions = ldr.versions
    for version in versions:
        notefiles = ldr[version]
        print(version)
        for n, sha in notefiles:
            if n.startswith(reporoot):
                n = n[len(reporoot):]
            print('\t%s (%s)' % (n, sha))
    return
