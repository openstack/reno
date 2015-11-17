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

import collections
import fnmatch
import logging
import os.path
import re
import subprocess
import sys

from reno import utils

_TAG_PAT = re.compile('tag: ([\d\.]+)')
LOG = logging.getLogger(__name__)


def _get_current_version(reporoot, branch=None):
    """Return the current version of the repository.

    If the repo appears to contain a python project, use setup.py to
    get the version so pbr (if used) can do its thing. Otherwise, use
    git describe.

    """
    cmd = ['git', 'describe', '--tags']
    if branch is not None:
        cmd.append(branch)
    try:
        result = utils.check_output(cmd, cwd=reporoot).strip()
        if '-' in result:
            # Descriptions that come after a commit look like
            # 2.0.0-1-abcde, and we want to remove the SHA value from
            # the end since we only care about the version number
            # itself, but we need to recognize that the change is
            # unreleased so keep the -1 part.
            result, dash, ignore = result.rpartition('-')
    except subprocess.CalledProcessError:
        # This probably means there are no tags.
        result = '0.0.0'
    return result


def get_file_at_commit(reporoot, filename, sha):
    "Return the contents of the file if it exists at the commit, or None."
    try:
        return utils.check_output(
            ['git', 'show', '%s:%s' % (sha, filename)],
            cwd=reporoot,
        )
    except subprocess.CalledProcessError:
        return None


def _file_exists_at_commit(reporoot, filename, sha):
    "Return true if the file exists at the given commit."
    return bool(get_file_at_commit(reporoot, filename, sha))


def _get_unique_id(filename):
    base = os.path.basename(filename)
    root, ext = os.path.splitext(base)
    uniqueid = root[-16:]
    if '-' in uniqueid:
        # This is an older file with the UUID at the beginning
        # of the name.
        uniqueid = root[:16]
    return uniqueid


# TODO(dhellmann): Add branch arg?
def get_notes_by_version(reporoot, notesdir, branch=None):
    """Return an OrderedDict mapping versions to lists of notes files.

    The versions are presented in reverse chronological order.

    Notes files are associated with the earliest version for which
    they were available, regardless of whether they changed later.
    """

    LOG.debug('scanning %s/%s (branch=%s)' % (reporoot, notesdir, branch))

    versions = []
    earliest_seen = collections.OrderedDict()

    # Determine the current version, which might be an unreleased or dev
    # version.
    current_version = _get_current_version(reporoot, branch)
    LOG.debug('current repository version: %s' % current_version)

    # Remember the most current filename for each id, to allow for
    # renames.
    last_name_by_id = {}

    # FIXME(dhellmann): This might need to be more line-oriented for
    # longer histories.
    log_cmd = ['git', 'log', '--pretty=%x00%H %d', '--name-only']
    if branch is not None:
        log_cmd.append(branch)
    LOG.debug('running %s' % ' '.join(log_cmd))
    history_results = utils.check_output(log_cmd, cwd=reporoot)
    history = history_results.split('\x00')
    current_version = current_version
    for h in history:
        h = h.strip()
        if not h:
            continue
        # print(h)

        hlines = h.splitlines()

        # The first line of the block will include the SHA and may
        # include tags, the other lines are filenames.
        sha = hlines[0].split(' ')[0]
        tags = _TAG_PAT.findall(hlines[0])
        # Filter the files based on the notes directory we were
        # given. We cannot do this in the git log command directly
        # because it means we end up skipping some of the tags if the
        # commits being tagged don't include any release note
        # files. Even if this list ends up empty, we continue doing
        # the other processing so that we record all of the known
        # versions.
        filenames = [
            f
            for f in hlines[2:]
            if fnmatch.fnmatch(f, notesdir + '/*.yaml')
        ]

        # If there are no tags in this block, assume the most recently
        # seen version.
        if not tags:
            tags = [current_version]
        else:
            current_version = tags[0]
            LOG.debug('%s has tags, updating current version to %s' %
                      (sha, current_version))

        # Remember each version we have seen.
        if current_version not in versions:
            LOG.debug('%s is a new version' % current_version)
            versions.append(current_version)

        LOG.debug('%s contains files %s' % (sha, filenames))

        # Remember the files seen, using their UUID suffix as a unique id.
        for f in filenames:
            # Updated as older tags are found, handling edits to release
            # notes.
            LOG.debug('setting earliest reference to %s to %s' %
                      (f, tags[0]))
            uniqueid = _get_unique_id(f)
            earliest_seen[uniqueid] = tags[0]
            if uniqueid in last_name_by_id:
                # We already have a filename for this id from a
                # new commit, so use that one in case the name has
                # changed.
                LOG.debug('%s was seen before' % f)
                continue
            if _file_exists_at_commit(reporoot, f, sha):
                # Remember this filename as the most recent version of
                # the unique id we have seen, in case the name
                # changed from an older commit.
                last_name_by_id[uniqueid] = (f, sha)
                LOG.debug('remembering %s as filename for %s' % (f, uniqueid))

    # Invert earliest_seen to make a list of notes files for each
    # version.
    files_and_tags = collections.OrderedDict()
    for v in versions:
        files_and_tags[v] = []
    # Produce a list of the actual files present in the repository. If
    # a note is removed, this step should let us ignore it.
    for uniqueid, version in earliest_seen.items():
        try:
            base, sha = last_name_by_id[uniqueid]
            files_and_tags[version].append((base, sha))
        except KeyError:
            # Unable to find the file again, skip it to avoid breaking
            # the build.
            print(
                '[reno] unable to find file associated '
                'with unique id %r, skipping' %
                uniqueid,
                file=sys.stderr,
            )

    # Only return the parts of files_and_tags that actually have
    # filenames associated with the versions.
    trimmed = {
        k: list(reversed(v))
        for (k, v)
        in files_and_tags.items()
        if v
    }

    return trimmed
