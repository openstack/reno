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

import glob
import logging
import os.path

from reno import loader
from reno import scanner

LOG = logging.getLogger(__name__)


def lint_cmd(args, conf):
    "Check some common mistakes"
    LOG.debug('starting lint')
    notesdir = os.path.join(conf.reporoot, conf.notespath)
    notes = glob.glob(os.path.join(notesdir, '*.yaml'))

    error = 0
    load = loader.Loader(conf, ignore_cache=True)

    allowed_section_names = ['prelude'] + [s[0] for s in conf.sections]

    uids = {}
    for f in notes:
        LOG.debug('examining %s', f)
        uid = scanner._get_unique_id(f)
        uids.setdefault(uid, []).append(f)

        content = load.parse_note_file(f, None)
        for section_name in content.keys():
            if section_name not in allowed_section_names:
                LOG.warning('unrecognized section name %s in %s',
                            section_name, f)
                error = 1

    for uid, names in sorted(uids.items()):
        if len(names) > 1:
            LOG.warning('UID collision: %s', names)
            error = 1

    return error
