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

import os

from reno import utils


_TEMPLATE = """\
---
prelude: >
    Replace this text with content to appear at the
    top of the section for this release.
features:
  - List new features here, or remove this section.
issues:
  - List known issues here, or remove this section.
upgrade:
  - List upgrade notes here, or remove this section.
critical:
  - Add critical notes here, or remove this section.
security:
  - Add security notes here, or remove this section.
fixes:
  - Add normal bug fixes here, or remove this section.
other:
  - Add other notes here, or remove this section.
"""


def _pick_note_file_name(notesdir, slug):
    "Pick a unique name in notesdir."
    for i in range(50):
        newid = utils.get_random_string()
        notefilename = os.path.join(notesdir, '%s-%s.yaml' % (slug, newid))
        if not os.path.exists(notefilename):
            return notefilename
    else:
        raise ValueError(
            'Unable to generate unique random filename '
            'in %s after 50 tries' % notesdir,
        )


def _make_note_file(filename):
    notesdir = os.path.dirname(filename)
    if not os.path.exists(notesdir):
        os.makedirs(notesdir)
    with open(filename, 'w') as f:
        f.write(_TEMPLATE)


def create_cmd(args):
    "Create a new release note file from the template."
    notesdir = utils.get_notes_dir(args)
    # NOTE(dhellmann): There is a short race window where we might try
    # to pick a name that does not exist, then overwrite the file if
    # it is created before we try to write it. This isn't a problem
    # because this command is expected to be run by one developer in
    # their local git tree, and so there should not be any concurrency
    # concern.
    slug = args.slug.replace(' ', '-')
    filename = _pick_note_file_name(notesdir, slug)
    _make_note_file(filename)
    print('Created new notes file in %s' % filename)
    return
