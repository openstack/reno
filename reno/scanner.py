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

import collections
import glob
import os.path
import re
import subprocess

_TAG_PAT = re.compile('tag: ([\d\.]+)')


def _get_current_version(reporoot):
    """Return the current version of the repository.

    If the repo appears to contain a python project, use setup.py to
    get the version so pbr (if used) can do its thing. Otherwise, use
    git describe.

    """
    if os.path.exists(os.path.join(reporoot, 'setup.py')):
        cmd = ['python', 'setup.py', '--version']
        result = subprocess.check_output(cmd, cwd=reporoot).strip()
    else:
        cmd = ['git', 'describe', '--tags']
        try:
            result = subprocess.check_output(cmd, cwd=reporoot).strip()
        except subprocess.CalledProcessError:
            # This probably means there are no tags.
            result = '0.0.0'
    return result


# TODO(dhellmann): Add branch arg?
def get_notes_by_version(reporoot, notesdir):

    """Return an OrderedDict mapping versions to lists of notes files.

    The versions are presented in reverse chronological order.

    Notes files are associated with the earliest version for which
    they were available, regardless of whether they changed later.
    """

    versions = []
    earliest_seen = collections.OrderedDict()

    # Determine the current version, which might be an unreleased or dev
    # version.
    current_version = _get_current_version(reporoot)

    # FIXME(dhellmann): This might need to be more line-oriented for
    # longer histories.
    history_results = subprocess.check_output(
        ['git', 'log', '--pretty=%x00%H %d', '--name-only', '--', notesdir],
        cwd=reporoot,
    )
    history = history_results.split('\x00')
    current_version = current_version
    for h in history:
        h = h.strip()
        if not h:
            continue

        hlines = h.splitlines()

        # The first line of the block will include the SHA and may
        # include tags, the other lines are filenames.
        tags = _TAG_PAT.findall(hlines[0])
        filenames = hlines[2:]

        # If there are no tags in this block, assume the most recently
        # seen version.
        if not tags:
            tags = [current_version]
        else:
            current_version = tags[0]

        # Remember each version we have seen.
        if current_version not in versions:
            versions.append(current_version)

        # Remember the files seen, using their prefix as a unique id.
        for f in filenames:
            # Updated as older tags are found, handling edits to release
            # notes.
            prefix = os.path.basename(f)[:16]
            earliest_seen[prefix] = tags[0]

    # Invert earliest_seen to make a list of notes files for each
    # version.
    files_and_tags = collections.OrderedDict()
    for v in versions:
        files_and_tags[v] = []
    # Produce a list of the actual files present in the repository. If
    # a note is removed, this step should let us ignore it.
    for prefix, version in earliest_seen.items():
        filenames = glob.glob(
            os.path.join(reporoot, notesdir, prefix + '*.yaml')
        )
        files_and_tags[version].extend(filenames)
    for version, filenames in files_and_tags.items():
        files_and_tags[version] = list(reversed(filenames))

    return files_and_tags
