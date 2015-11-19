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
    top of the section for this release. All of the
    prelude content is merged together and then rendered
    separately from the items listed in other parts of
    the file, so the text needs to be worded so that
    both the prelude and the other items make sense
    when read independently. This may mean repeating
    some details. Not every release note
    requires a prelude. Usually only notes describing
    major features or adding release theme details should
    have a prelude.
features:
  - List new features here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
issues:
  - List known issues here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
upgrade:
  - List upgrade notes here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
deprecations:
  - List deprecations notes here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
critical:
  - Add critical notes here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
security:
  - Add security notes here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
fixes:
  - Add normal bug fixes here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
other:
  - Add other notes here, or remove this section.
    All of the list items in this section are combined
    when the release notes are rendered, so the text
    needs to be worded so that it does not depend on any
    information only available in another section, such
    as the prelude. This may mean repeating some details.
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
