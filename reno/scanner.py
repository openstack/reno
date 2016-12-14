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


# The git log output from _get_tags_on_branch() looks like this sample
# from the openstack/nova repository for git 1.9.1:
#
# git log --simplify-by-decoration --pretty="%d"
# (HEAD, origin/master, origin/HEAD, gerrit/master, master)
# (apu/master)
# (tag: 13.0.0.0b1)
# (tag: 12.0.0.0rc3, tag: 12.0.0)
#
# And this for git 1.7.1 (RHEL):
#
# $ git log --simplify-by-decoration --pretty="%d"
# (HEAD, origin/master, origin/HEAD, master)
# (tag: 13.0.0.0b1)
# (tag: 12.0.0.0rc3, tag: 12.0.0)
# (tag: 12.0.0.0rc2)
# (tag: 2015.1.0rc3, tag: 2015.1.0)
# ...
# (tag: folsom-2)
# (tag: folsom-1)
# (essex-1)
# (diablo-2)
# (diablo-1)
# (2011.2)
#
# The difference in the tags with "tag:" and without appears to be
# caused by some being annotated and others not.
#
# So we might have multiple tags on a given commit, and we might have
# lines that have no tags or are completely blank, and we might have
# "tag:" or not. This pattern is used to find the tag entries on each
# line, ignoring tags that don't look like version numbers.
TAG_RE = re.compile('''
    (?:[(]|tag:\s)  # look for tag: prefix and drop
    ((?:[\d.ab]|rc)+)  # digits, a, b, and rc cover regular and pre-releases
    [,)]  # possible trailing comma or closing paren
''', flags=re.VERBOSE | re.UNICODE)
PRE_RELEASE_RE = re.compile('''
    \.(\d+(?:[ab]|rc)+\d*)$
''', flags=re.VERBOSE | re.UNICODE)


def _branch_or_eol_tag(reporoot, branch):
    "If a stable branch is deleted, convert the name to the eol tag."
    branch_results = utils.check_output(
        ['git', 'branch', '--list', '-a'],
        cwd=reporoot,
    )
    branches = []
    for line in branch_results.splitlines():
        # Clean up whitespace and the * marking the "current" branch.
        line = line.strip().lstrip('*').strip()
        if line.startswith('remotes/'):
            line = line[8:]
        branches.append(line)
    if branch in branches:
        return branch
    return branch.rpartition('/')[-1] + '-eol'


def _get_version_tags_on_branch(reporoot, branch):
    """Return tags from the branch, in date order.

    Need to get the list of tags in the right order, because the topo
    search breaks the date ordering. Use git to ask for the tags in
    order, rather than trying to sort them, because many repositories
    have "non-standard" tags or have renumbered projects (from
    date-based to SemVer), for which sorting would require complex
    logic.

    """
    tags = []
    tag_cmd = [
        'git', 'log',
        '--simplify-by-decoration',
        '--pretty="%d"',
    ]
    if branch:
        tag_cmd.append(_branch_or_eol_tag(reporoot, branch))
    LOG.debug('running %s' % ' '.join(tag_cmd))
    tag_results = utils.check_output(tag_cmd, cwd=reporoot)
    LOG.debug(tag_results)
    for line in tag_results.splitlines():
        LOG.debug('line %r' % line)
        for match in TAG_RE.findall(line):
            tags.append(match)
    return tags


def get_notes_by_version(reporoot, notesdir, branch=None,
                         collapse_pre_releases=True,
                         earliest_version=None):
    """Return an OrderedDict mapping versions to lists of notes files.

    The versions are presented in reverse chronological order.

    Notes files are associated with the earliest version for which
    they were available, regardless of whether they changed later.

    :param reporoot: Path to the root of the git repository.
    :type reporoot: str
    :param notesdir: The directory under *reporoot* with the release notes.
    :type notesdir: str
    :param branch: The name of the branch to scan. Defaults to current.
    :type branch: str
    :param collapse_pre_releases: When true, merge pre-release versions
        into the final release, if it is present.
    :type collapse_pre_releases: bool
    """

    LOG.debug('scanning %s/%s (branch=%s)' % (reporoot, notesdir, branch))

    # Determine all of the tags known on the branch, in their date
    # order. We scan the commit history in topological order to ensure
    # we have the commits in the right version, so we might encounter
    # the tags in a different order during that phase.
    versions_by_date = _get_version_tags_on_branch(reporoot, branch)
    LOG.debug('versions by date %r' % (versions_by_date,))
    versions = []
    earliest_seen = collections.OrderedDict()

    # Determine the current version, which might be an unreleased or
    # dev version if there are unreleased commits at the head of the
    # branch in question. Since the version may not already be known,
    # make sure it is in the list of versions by date. And since it is
    # the most recent version, go ahead and insert it at the front of
    # the list.
    current_version = _get_current_version(reporoot, branch)
    LOG.debug('current repository version: %s' % current_version)
    if current_version not in versions_by_date:
        LOG.debug('adding %s to versions by date' % current_version)
        versions_by_date.insert(0, current_version)

    # Remember the most current filename for each id, to allow for
    # renames.
    last_name_by_id = {}

    # Remember uniqueids that have had files deleted.
    uniqueids_deleted = collections.defaultdict(set)

    # FIXME(dhellmann): This might need to be more line-oriented for
    # longer histories.
    log_cmd = [
        'git', 'log',
        '--topo-order',  # force traversal order rather than date order
        '--pretty=%x00%H %d',  # output contents in parsable format
        '--name-only'  # only include the names of the files in the patch
    ]
    if branch is not None:
        log_cmd.append(_branch_or_eol_tag(reporoot, branch))
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
        tags = TAG_RE.findall(hlines[0])
        # Filter the files based on the notes directory we were
        # given. We cannot do this in the git log command directly
        # because it means we end up skipping some of the tags if the
        # commits being tagged don't include any release note
        # files. Even if this list ends up empty, we continue doing
        # the other processing so that we record all of the known
        # versions.
        filenames = []
        for f in hlines[2:]:
            if fnmatch.fnmatch(f, notesdir + '/*.yaml'):
                filenames.append(f)
            elif fnmatch.fnmatch(f, notesdir + '/*'):
                LOG.warn('found and ignored extra file %s', f)

        # If there are no tags in this block, assume the most recently
        # seen version.
        if not tags:
            tags = [current_version]
        else:
            current_version = tags[0]
            LOG.debug('%s has tags %s (%r), updating current version to %s' %
                      (sha, tags, hlines[0], current_version))

        # Remember each version we have seen.
        if current_version not in versions:
            LOG.debug('%s is a new version' % current_version)
            versions.append(current_version)

        LOG.debug('%s contains files %s' % (sha, filenames))

        # Remember the files seen, using their UUID suffix as a unique id.
        for f in filenames:
            # Updated as older tags are found, handling edits to release
            # notes.
            uniqueid = _get_unique_id(f)
            LOG.debug('%s: found file %s',
                      uniqueid, f)
            LOG.debug('%s: setting earliest reference to %s' %
                      (uniqueid, tags[0]))
            earliest_seen[uniqueid] = tags[0]
            if uniqueid in last_name_by_id:
                # We already have a filename for this id from a
                # new commit, so use that one in case the name has
                # changed.
                LOG.debug('%s: was seen before in %s',
                          uniqueid, last_name_by_id[uniqueid])
                continue
            elif _file_exists_at_commit(reporoot, f, sha):
                LOG.debug('%s: looking for %s in deleted files %s',
                          uniqueid, f, uniqueids_deleted[uniqueid])
                if f in uniqueids_deleted[uniqueid]:
                    # The file exists in the commit, but was deleted
                    # later in the history.
                    LOG.debug('%s: skipping deleted file %s',
                              uniqueid, f)
                else:
                    # Remember this filename as the most recent version of
                    # the unique id we have seen, in case the name
                    # changed from an older commit.
                    last_name_by_id[uniqueid] = (f, sha)
                    LOG.debug('%s: remembering %s as filename',
                              uniqueid, f)
            else:
                # Track files that have been deleted. The rename logic
                # above checks for repeated references to files that
                # are deleted later, and the inversion logic below
                # checks for any remaining values and skips those
                # entries.
                LOG.debug('%s: saw a file that no longer exists',
                          uniqueid)
                uniqueids_deleted[uniqueid].add(f)
                LOG.debug('%s: deleted files %s',
                          uniqueid, uniqueids_deleted[uniqueid])

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
            if base in uniqueids_deleted.get(uniqueid, set()):
                LOG.debug('skipping deleted note %s' % uniqueid)
                continue
            files_and_tags[version].append((base, sha))
        except KeyError:
            # Unable to find the file again, skip it to avoid breaking
            # the build.
            msg = ('[reno] unable to find file associated '
                   'with unique id %r, skipping') % uniqueid
            LOG.debug(msg)
            print(msg, file=sys.stderr)

    # Combine pre-releases into the final release, if we are told to
    # and the final release exists.
    if collapse_pre_releases:
        collapsing = files_and_tags
        files_and_tags = collections.OrderedDict()
        for ov in versions_by_date:
            if ov not in collapsing:
                # We don't need to collapse this one because there are
                # no notes attached to it.
                continue
            pre_release_match = PRE_RELEASE_RE.search(ov)
            LOG.debug('checking %r', ov)
            if pre_release_match:
                # Remove the trailing pre-release part of the version
                # from the string.
                pre_rel_str = pre_release_match.groups()[0]
                canonical_ver = ov[:-len(pre_rel_str)].rstrip('.')
                if canonical_ver not in versions_by_date:
                    # This canonical version was never tagged, so we
                    # do not want to collapse the pre-releases. Reset
                    # to the original version.
                    canonical_ver = ov
                else:
                    LOG.debug('combining into %r', canonical_ver)
            else:
                canonical_ver = ov
            if canonical_ver not in files_and_tags:
                files_and_tags[canonical_ver] = []
            files_and_tags[canonical_ver].extend(collapsing[ov])

    # Only return the parts of files_and_tags that actually have
    # filenames associated with the versions.
    trimmed = collections.OrderedDict()
    for ov in versions_by_date:
        if not files_and_tags.get(ov):
            continue
        # Sort the notes associated with the version so they are in a
        # deterministic order, to avoid having the same data result in
        # different output depending on random factors. Earlier
        # versions of the scanner assumed the notes were recorded in
        # chronological order based on the commit date, but with the
        # change to use topological sorting that is no longer
        # necessarily true. We want the notes to always show up in the
        # same order, but it doesn't really matter what order that is,
        # so just sort based on the unique id.
        trimmed[ov] = sorted(files_and_tags[ov])
        # If we have been told to stop at a version, we can do that
        # now.
        if earliest_version and ov == earliest_version:
            break

    LOG.debug('[reno] found %d versions and %d files',
              len(trimmed.keys()), sum(len(ov) for ov in trimmed.values()))
    return trimmed
