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

import os
import subprocess

from reno import utils


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


def _make_note_file(filename, template, encoding=None):
    notesdir = os.path.dirname(filename)
    if not os.path.exists(notesdir):
        os.makedirs(notesdir)
    with open(filename, 'w', encoding=encoding) as f:
        f.write(template)


def _edit_file(filename):
    if 'EDITOR' not in os.environ:
        return False
    subprocess.call([os.environ['EDITOR'], filename])
    return True


def _get_user_template(template_file, encoding=None):
    if not os.path.exists(template_file):
        raise ValueError(
            'The provided template file %s doesn\'t '
            'exist' % template_file,
        )
    with open(template_file, 'r', encoding=encoding) as f:
        return f.read()


def create_cmd(args, conf):
    "Create a new release note file from the template."
    # NOTE(dhellmann): There is a short race window where we might try
    # to pick a name that does not exist, then overwrite the file if
    # it is created before we try to write it. This isn't a problem
    # because this command is expected to be run by one developer in
    # their local git tree, and so there should not be any concurrency
    # concern.
    slug = args.slug.replace(' ', '-')

    if not conf.options['allow_subdirectories'] and os.sep in slug:
        raise ValueError('Slug should not include the path separator (%s)'
                         % os.sep)

    filename = _pick_note_file_name(conf.notespath, slug)
    encoding = conf.options['encoding']
    if args.from_template:
        template = _get_user_template(args.from_template, encoding=encoding)
    else:
        template = conf.template
    _make_note_file(filename, template, encoding=encoding)
    if args.edit and not _edit_file(filename):
        print('Was unable to edit the new note. EDITOR environment variable '
              'is missing!')
    print('Created new notes file in %s' % filename)
    return
