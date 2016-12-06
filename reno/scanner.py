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

from dulwich import refs
from dulwich import repo

from reno import utils

LOG = logging.getLogger(__name__)


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


class RenoRepo(repo.Repo):

    def _get_file_from_tree(self, filename, tree):
        "Given a tree object, traverse it to find the file."
        try:
            if os.sep in filename:
                # The tree entry will only have a single level of the
                # directory name, so if we have a / in our filename we
                # know we're going to have to keep traversing the
                # tree.
                prefix, _, trailing = filename.partition(os.sep)
                mode, subtree_sha = tree[prefix.encode('utf-8')]
                subtree = self[subtree_sha]
                return self._get_file_from_tree(trailing, subtree)
            else:
                # The tree entry will point to the blob with the
                # contents of the file.
                mode, file_blob_sha = tree[filename.encode('utf-8')]
                file_blob = self[file_blob_sha]
                return file_blob.data
        except KeyError:
            # Some part of the filename wasn't found, so the file is
            # not present. Return the sentinel value.
            return None

    def get_file_at_commit(self, filename, sha):
        "Return the contents of the file if it exists at the commit, or None."
        # Get the tree associated with the commit identified by the
        # input SHA, then look through the items in the tree to find
        # the one with the path matching the filename. Take the
        # associated SHA from the tree and get the file contents from
        # the repository.
        commit = self[sha.encode('ascii')]
        tree = self[commit.tree]
        return self._get_file_from_tree(filename, tree)


class Scanner(object):

    def __init__(self, conf):
        self.conf = conf
        self.reporoot = self.conf.reporoot
        self._repo = RenoRepo(self.reporoot)
        self._load_tags()

    def _load_tags(self):
        self._all_tags = {
            k.partition(b'/tags/')[-1].decode('utf-8'): v
            for k, v in self._repo.get_refs().items()
            if k.startswith(b'refs/tags/')
        }
        self._shas_to_tags = {}
        for tag, tag_sha in self._all_tags.items():
            # The tag has its own SHA, but the tag refers to the commit and
            # that's the SHA we'll see when we scan commits on a branch.
            tag_obj = self._repo[tag_sha]
            tagged_sha = tag_obj.object[1]
            self._shas_to_tags.setdefault(tagged_sha, []).append(tag)

    def _get_walker_for_branch(self, branch):
        if branch:
            branch_ref = b'refs/heads/' + branch.encode('utf-8')
            if not refs.check_ref_format(branch_ref):
                raise ValueError(
                    '{!r} does not look like a valid branch reference'.format(
                        branch_ref))
            branch_head = self._repo.refs[branch_ref]
        else:
            branch_head = self._repo.refs[b'HEAD']
        return self._repo.get_walker(branch_head)

    def _get_tags_on_branch(self, branch, with_count=False):
        "Return a list of tag names on the given branch."
        results = []
        count = 0
        for c in self._get_walker_for_branch(branch):
            # shas_to_tags has encoded versions of the shas
            # but the commit object gives us a decoded version
            sha = c.commit.sha().hexdigest().encode('ascii')
            if sha in self._shas_to_tags:
                if with_count and count and not results:
                    val = '{}-{}'.format(self._shas_to_tags[sha][0], count)
                    results.append(val)
                else:
                    results.extend(self._shas_to_tags[sha])
            else:
                count += 1
        return results

    def _get_current_version(self, branch=None):
        "Return the current version of the repository, like git describe."
        tags = self._get_tags_on_branch(branch, with_count=True)
        if not tags:
            # Never tagged.
            return '0.0.0'
        return tags[0]

    def _get_branch_base(self, branch):
        "Return the tag at base of the branch."
        # Based on
        # http://stackoverflow.com/questions/1527234/finding-a-branch-point-with-git
        # git rev-list $(git rev-list --first-parent \
        #   ^origin/stable/newton master | tail -n1)^^!
        #
        # Determine the list of commits accessible from the branch we are
        # supposed to be scanning, but not on master.
        cmd = [
            'git',
            'rev-list',
            '--first-parent',
            branch,  # on the branch
            '^master',  # not on master
        ]
        try:
            LOG.debug(' '.join(cmd))
            parents = utils.check_output(cmd, cwd=self.reporoot).strip()
            if not parents:
                # There are no commits on the branch, yet, so we can use
                # our current-version logic.
                return self._get_current_version(branch)
        except subprocess.CalledProcessError as e:
            LOG.warning('failed to retrieve branch base: %s [%s]',
                        e, e.output.strip())
            return None
        parent = parents.splitlines()[-1]
        LOG.debug('parent = %r', parent)
        # Now get the previous commit, which should be the one we tagged
        # to create the branch.
        cmd = [
            'git',
            'rev-list',
            '{}^^!'.format(parent),
        ]
        try:
            sha = utils.check_output(cmd, cwd=self.reporoot).strip()
            LOG.debug('sha = %r', sha)
        except subprocess.CalledProcessError as e:
            LOG.warning('failed to retrieve branch base: %s [%s]',
                        e, e.output.strip())
            return None
        # Now get the tag for that commit.
        cmd = [
            'git',
            'describe',
            '--abbrev=0',
            sha,
        ]
        try:
            return utils.check_output(cmd, cwd=self.reporoot).strip()
        except subprocess.CalledProcessError as e:
            LOG.warning('failed to retrieve branch base: %s [%s]',
                        e, e.output.strip())
            return None

    def get_file_at_commit(self, filename, sha):
        "Return the contents of the file if it exists at the commit, or None."
        return self._repo.get_file_at_commit(filename, sha)

    def _file_exists_at_commit(self, filename, sha):
        "Return true if the file exists at the given commit."
        return bool(self.get_file_at_commit(filename, sha))

    def get_notes_by_version(self):
        """Return an OrderedDict mapping versions to lists of notes files.

        The versions are presented in reverse chronological order.

        Notes files are associated with the earliest version for which
        they were available, regardless of whether they changed later.

        :param reporoot: Path to the root of the git repository.
        :type reporoot: str
        """

        reporoot = self.reporoot
        notesdir = self.conf.notespath
        branch = self.conf.branch
        earliest_version = self.conf.earliest_version
        collapse_pre_releases = self.conf.collapse_pre_releases
        stop_at_branch_base = self.conf.stop_at_branch_base

        LOG.debug('scanning %s/%s (branch=%s)' % (reporoot, notesdir, branch))

        # If the user has not told us where to stop, try to work it out
        # for ourselves. If branch is set and is not "master", then we
        # want to stop at the base of the branch.
        if (stop_at_branch_base and
                (not earliest_version) and branch and (branch != 'master')):
            LOG.debug('determining earliest_version from branch')
            earliest_version = self._get_branch_base(branch)
            if earliest_version and collapse_pre_releases:
                if PRE_RELEASE_RE.search(earliest_version):
                    # The earliest version won't actually be the pre-release
                    # that might have been tagged when the branch was created,
                    # but the final version. Strip the pre-release portion of
                    # the version number.
                    earliest_version = '.'.join(
                        earliest_version.split('.')[:-1]
                    )
        LOG.debug('using earliest_version = %r', earliest_version)

        # Determine all of the tags known on the branch, in their date
        # order. We scan the commit history in topological order to ensure
        # we have the commits in the right version, so we might encounter
        # the tags in a different order during that phase.
        versions_by_date = self._get_tags_on_branch(branch)
        LOG.debug('versions by date %r' % (versions_by_date,))
        versions = []
        earliest_seen = collections.OrderedDict()

        # Determine the current version, which might be an unreleased or
        # dev version if there are unreleased commits at the head of the
        # branch in question. Since the version may not already be known,
        # make sure it is in the list of versions by date. And since it is
        # the most recent version, go ahead and insert it at the front of
        # the list.
        current_version = self._get_current_version(branch)
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
                    LOG.warning('found and ignored extra file %s', f)

            # If there are no tags in this block, assume the most recently
            # seen version.
            if not tags:
                tags = [current_version]
            else:
                current_version = tags[0]
                LOG.debug('%s has tags %s (%r), '
                          'updating current version to %s' %
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
                elif self._file_exists_at_commit(f, sha):
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
