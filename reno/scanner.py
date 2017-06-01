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
import sys

from dulwich import diff_tree
from dulwich import index as d_index
from dulwich import objects
from dulwich import porcelain
from dulwich import repo

LOG = logging.getLogger(__name__)


def _parse_version(v):
    parts = v.split('.') + ['0', '0', '0']
    result = []
    for p in parts[:3]:
        try:
            result.append(int(p))
        except ValueError:
            result.append(p)
    return result


def _get_unique_id(filename):
    base = os.path.basename(filename)
    root, ext = os.path.splitext(base)
    uniqueid = root[-16:]
    if '-' in uniqueid:
        # This is an older file with the UUID at the beginning
        # of the name.
        uniqueid = root[:16]
    return uniqueid


def _note_file(name):
    """Return bool indicating if the filename looks like a note file.

    This is used to filter the files in changes based on the notes
    directory we were given. We cannot do this in the walker directly
    because it means we end up skipping some of the tags if the
    commits being tagged don't include any release note files.

    """
    if not name:
        return False
    if fnmatch.fnmatch(name, '*.yaml'):
        return True
    else:
        LOG.info('found and ignored extra file %s', name)
    return False


def _changes_in_subdir(repo, walk_entry, subdir):
    """Iterator producing changes of interest to reno.

    The default changes() method of a WalkEntry computes all of the
    changes in the entire repo at that point. We only care about
    changes in a subdirectory, so this reimplements
    WalkeEntry.changes() with that filter in place.

    The alternative, passing paths to the TreeWalker, does not work
    because we need all of the commits in sequence so we can tell when
    the tag changes. We have to look at every commit to see if it
    either has a tag, a note file, or both.

    NOTE(dhellmann): The TreeChange entries returned as a result of
    the manipulation done by this function have the subdir prefix
    stripped.

    """
    commit = walk_entry.commit
    store = repo.object_store

    parents = walk_entry._get_parents(commit)

    if not parents:
        changes_func = diff_tree.tree_changes
        parent_subtree = None
    elif len(parents) == 1:
        changes_func = diff_tree.tree_changes
        parent_tree = repo[repo[parents[0]].tree]
        parent_subtree = repo._get_subtree(parent_tree, subdir)
        if parent_subtree:
            parent_subtree = parent_subtree.sha().hexdigest().encode('ascii')
    else:
        changes_func = diff_tree.tree_changes_for_merge
        parent_subtree = [
            repo._get_subtree(repo[repo[p].tree], subdir)
            for p in parents
        ]
        parent_subtree = [
            p.sha().hexdigest().encode('ascii')
            for p in parent_subtree
            if p
        ]
    subdir_tree = repo._get_subtree(repo[commit.tree], subdir)
    if subdir_tree:
        commit_subtree = subdir_tree.sha().hexdigest().encode('ascii')
    else:
        commit_subtree = None
    if parent_subtree == commit_subtree:
        return []
    return changes_func(store, parent_subtree, commit_subtree)


class _ChangeAggregator(object):
    """Collapse a series of changes based on uniqueness for file uids.

    The list of TreeChange instances describe changes between the old
    and new repository trees. The change has a type, and new and old
    paths and shas.

    Simple add, delete, and change operations are handled directly.

    There is a rename type, but detection of renamed files is
    incomplete so we handle that ourselves based on the UID value
    built into the filenames (under the assumption that if someone
    changes that part of the filename they want it treated as a
    different file for some reason).  If we see both an add and a
    delete for a given UID treat that as a rename.

    The SHA values returned are for the commit, rather than the blob
    values in the TreeChange objects.

    The path values in the change entries are encoded, so we return
    the decoded values to make consuming them easier.

    """

    _rename_op = set([diff_tree.CHANGE_ADD, diff_tree.CHANGE_DELETE])
    _modify_op = set([diff_tree.CHANGE_MODIFY])
    _delete_op = set([diff_tree.CHANGE_DELETE])
    _add_op = set([diff_tree.CHANGE_ADD])

    def __init__(self):
        # Track UIDs that had a duplication issue but have been
        # deleted so we know not to throw an error for them.
        self._deleted_bad_uids = set()

    def aggregate_changes(self, walk_entry, changes):
        sha = walk_entry.commit.id
        by_uid = collections.defaultdict(list)
        for ec in changes:
            if not isinstance(ec, list):
                ec = [ec]
            else:
                ec = ec
            for c in ec:
                LOG.debug('change %r', c)
                if c.type == diff_tree.CHANGE_ADD:
                    path = c.new.path.decode('utf-8') if c.new.path else None
                    if _note_file(path):
                        uid = _get_unique_id(path)
                        by_uid[uid].append((c.type, path, sha))
                    else:
                        LOG.debug('ignoring')
                elif c.type == diff_tree.CHANGE_DELETE:
                    path = c.old.path.decode('utf-8') if c.old.path else None
                    if _note_file(path):
                        uid = _get_unique_id(path)
                        by_uid[uid].append((c.type, path, sha))
                    else:
                        LOG.debug('ignoring')
                elif c.type == diff_tree.CHANGE_MODIFY:
                    path = c.new.path.decode('utf-8') if c.new.path else None
                    if _note_file(path):
                        uid = _get_unique_id(path)
                        by_uid[uid].append((c.type, path, sha))
                    else:
                        LOG.debug('ignoring')
                else:
                    raise ValueError('unhandled change type: {!r}'.format(c))

        results = []
        for uid, changes in sorted(by_uid.items()):
            if len(changes) == 1:
                results.append((uid,) + changes[0])
            else:
                types = set(c[0] for c in changes)
                if types == self._rename_op:
                    # A rename, combine the data from the add and
                    # delete entries.
                    added = [
                        c for c in changes if c[0] == diff_tree.CHANGE_ADD
                    ][0]
                    deled = [
                        c for c in changes if c[0] == diff_tree.CHANGE_DELETE
                    ][0]
                    results.append(
                        (uid, diff_tree.CHANGE_RENAME, deled[1]) + added[1:]
                    )
                elif types == self._modify_op:
                    # Merge commit with modifications to the same files in
                    # different commits.
                    for c in changes:
                        results.append((uid, diff_tree.CHANGE_MODIFY,
                                        c[1], sha))
                elif types == self._delete_op:
                    # There were multiple files in one commit using the
                    # same UID but different slugs. Treat them as
                    # different files and allow them to be deleted.
                    results.extend(
                        (uid, diff_tree.CHANGE_DELETE, c[1], sha)
                        for c in changes
                    )
                    self._deleted_bad_uids.add(uid)
                elif types == self._add_op:
                    # There were multiple files in one commit using the
                    # same UID but different slugs. Warn the user about
                    # this case and then ignore the files. We allow delete
                    # (see above) to ensure they can be cleaned up.
                    msg = ('%s: found several files in one commit (%s)'
                           ' with the same UID: %s' %
                           (uid, sha, [c[1] for c in changes]))
                    if uid not in self._deleted_bad_uids:
                        raise ValueError(msg)
                    else:
                        LOG.info(msg)
                else:
                    raise ValueError('Unrecognized changes: {!r}'.format(
                        changes))
        return results


class _ChangeTracker(object):

    def __init__(self):
        # Track the versions we have seen and the earliest version for
        # which we have seen a given note's unique id.
        self.versions = []
        self.earliest_seen = collections.OrderedDict()
        # Remember the most current filename for each id, to allow for
        # renames.
        self.last_name_by_id = {}
        # Remember uniqueids that have had files deleted.
        self.uniqueids_deleted = set()

    def _common(self, uniqueid, sha, version):
        if version not in self.versions:
            self.versions.append(version)
        # Update the "earliest" version where a UID appears
        # every time we see it, because we are scanning the
        # history in reverse order so "early" items come
        # later.
        if uniqueid in self.earliest_seen:
            LOG.debug('%s: resetting earliest reference from %s to %s for %s',
                      uniqueid, self.earliest_seen[uniqueid], version, sha)
        else:
            LOG.debug('%s: setting earliest reference to %s for %s',
                      uniqueid, version, sha)
        self.earliest_seen[uniqueid] = version

    def add(self, filename, sha, version):
        uniqueid = _get_unique_id(filename)
        self._common(uniqueid, sha, version)
        LOG.info('%s: adding %s from %s',
                 uniqueid, filename, version)

        # If we have recorded that a UID was deleted, that
        # means that was the last change made to the file and
        # we can ignore it.
        if uniqueid in self.uniqueids_deleted:
            LOG.debug(
                '%s: has already been deleted, ignoring this change',
                uniqueid,
            )
            return

        # A note is being added in this commit. If we have
        # not seen it before, it was added here and never
        # changed.
        if uniqueid not in self.last_name_by_id:
            self.last_name_by_id[uniqueid] = (filename, sha)
            LOG.info(
                '%s: new %s in commit %s',
                uniqueid, filename, sha,
            )
        else:
            LOG.debug(
                '%s: add for file we have already seen',
                uniqueid,
            )

    def rename(self, filename, sha, version):
        uniqueid = _get_unique_id(filename)
        self._common(uniqueid, sha, version)

        # If we have recorded that a UID was deleted, that
        # means that was the last change made to the file and
        # we can ignore it.
        if uniqueid in self.uniqueids_deleted:
            LOG.debug(
                '%s: has already been deleted, ignoring this change',
                uniqueid,
            )
            return

        # The file is being renamed. We may have seen it
        # before, if there were subsequent modifications,
        # so only store the name information if it is not
        # there already.
        if uniqueid not in self.last_name_by_id:
            self.last_name_by_id[uniqueid] = (filename, sha)
            LOG.info(
                '%s: update to %s in commit %s',
                uniqueid, filename, sha,
            )
        else:
            LOG.debug(
                '%s: renamed file already known with the new name',
                uniqueid,
            )

    def modify(self, filename, sha, version):
        uniqueid = _get_unique_id(filename)
        self._common(uniqueid, sha, version)

        # If we have recorded that a UID was deleted, that
        # means that was the last change made to the file and
        # we can ignore it.
        if uniqueid in self.uniqueids_deleted:
            LOG.debug(
                '%s: has already been deleted, ignoring this change',
                uniqueid,
            )
            return

        # An existing file is being modified. We may have
        # seen it before, if there were subsequent
        # modifications, so only store the name
        # information if it is not there already.
        if uniqueid not in self.last_name_by_id:
            self.last_name_by_id[uniqueid] = (filename, sha)
            LOG.info(
                '%s: update to %s in commit %s',
                uniqueid, filename, sha,
            )
        else:
            LOG.debug(
                '%s: modified file already known',
                uniqueid,
            )

    def delete(self, filename, sha, version):
        uniqueid = _get_unique_id(filename)
        self._common(uniqueid, sha, version)
        # This file is being deleted without a rename. If
        # we have already seen the UID before, that means
        # that after the file was deleted another file
        # with the same UID was added back. In that case
        # we do not want to treat it as deleted.
        #
        # Never store deleted files in last_name_by_id so
        # we can safely use all of those entries to build
        # the history data.
        if uniqueid not in self.last_name_by_id:
            self.uniqueids_deleted.add(uniqueid)
            LOG.info(
                '%s: note deleted in %s',
                uniqueid, sha,
            )
        else:
            LOG.debug(
                '%s: delete for file re-added after the delete',
                uniqueid,
            )


class RenoRepo(repo.Repo):

    # Populated by _load_tags().
    _all_tags = None
    _shas_to_tags = None

    def _get_commit_from_tag(self, tag, tag_sha):
        """Return the commit referenced by the tag and when it was tagged."""
        tag_obj = self[tag_sha]

        if isinstance(tag_obj, objects.Tag):
            # A signed tag has its own SHA, but the tag refers to
            # the commit and that's the SHA we'll see when we scan
            # commits on a branch.
            git_obj = tag_obj
            while True:
                # Tags can point to other tags, in such cases follow the chain
                # of tags until there are no more.
                child_obj = self[git_obj.object[1]]
                if isinstance(child_obj, objects.Tag):
                    git_obj = child_obj
                else:
                    break

            tagged_sha = git_obj.object[1]
            date = tag_obj.tag_time
        elif isinstance(tag_obj, objects.Commit):
            # Unsigned tags refer directly to commits. This seems
            # to especially happen when the tag definition moves
            # to the packed-refs list instead of being represented
            # by its own file.
            tagged_sha = tag_obj.id
            date = tag_obj.commit_time
        else:
            raise ValueError(
                ('Unrecognized tag object {!r} with '
                 'tag {} and SHA {!r}: {}').format(
                    tag_obj, tag, tag_sha, type(tag_obj))
            )
        return tagged_sha, date

    def _load_tags(self):
        self._all_tags = {
            k.partition(b'/tags/')[-1].decode('utf-8'): v
            for k, v in self.get_refs().items()
            if k.startswith(b'refs/tags/')
        }
        self._shas_to_tags = {}
        for tag, tag_sha in self._all_tags.items():
            tagged_sha, date = self._get_commit_from_tag(tag, tag_sha)
            self._shas_to_tags.setdefault(tagged_sha, []).append((tag, date))

    def get_tags_on_commit(self, sha):
        "Return the tag(s) on a commit, in application order."
        if self._all_tags is None:
            self._load_tags()
        tags_and_dates = self._shas_to_tags.get(sha, [])
        tags_and_dates.sort(key=lambda x: x[1])
        return [t[0] for t in tags_and_dates]

    def _get_subtree(self, tree, path):
        "Given a tree SHA and a path, return the SHA of the subtree."
        try:
            mode, tree_sha = tree.lookup_path(self.get_object,
                                              path.encode('utf-8'))
        except KeyError:
            # Some part of the path wasn't found, so the subtree is
            # not present. Return the sentinel value.
            return None
        else:
            tree = self[tree_sha]
            return tree

    def get_file_at_commit(self, filename, sha):
        """Return the contents of the file.

        If sha is None, return the working copy of the file. If the
        file cannot be read from the working dir, return None.

        If the sha is not None and the file exists at the commit,
        return the data from the stored blob. If the file does not
        exist at the commit, return None.

        """
        if sha is None:
            # Get the copy from the working directory.
            try:
                with open(os.path.join(self.path, filename), 'r') as f:
                    return f.read()
            except IOError:
                return None
        # Get the tree associated with the commit identified by the
        # input SHA, then look through the items in the tree to find
        # the one with the path matching the filename. Take the
        # associated SHA from the tree and get the file contents from
        # the repository.
        if hasattr(sha, 'encode'):
            sha = sha.encode('ascii')
        commit = self[sha]
        tree = self[commit.tree]
        try:
            mode, blob_sha = tree.lookup_path(self.get_object,
                                              filename.encode('utf-8'))
        except KeyError:
            # Some part of the filename wasn't found, so the file is
            # not present. Return the sentinel value.
            return None
        else:
            blob = self[blob_sha]
            return blob.data


class Scanner(object):

    def __init__(self, conf):
        self.conf = conf
        self.reporoot = self.conf.reporoot
        self._repo = RenoRepo(self.reporoot)
        self.release_tag_re = re.compile(
            self.conf.release_tag_re,
            flags=re.VERBOSE | re.UNICODE,
        )
        self.pre_release_tag_re = re.compile(
            self.conf.pre_release_tag_re,
            flags=re.VERBOSE | re.UNICODE,
        )
        self.branch_name_re = re.compile(
            self.conf.branch_name_re,
            flags=re.VERBOSE | re.UNICODE,
        )

    def _get_ref(self, name):
        if name:
            candidates = [
                'refs/heads/' + name,
                'refs/remotes/' + name,
                'refs/tags/' + name,
                # If a stable branch was removed, look for its EOL tag.
                'refs/tags/' + (name.rpartition('/')[-1] + '-eol'),
                # If someone is using the "short" name for a branch
                # without a local tracking branch, look to see if the
                # name exists on the 'origin' remote.
                'refs/remotes/origin/' + name,
            ]
            for ref in candidates:
                key = ref.encode('utf-8')
                if key in self._repo.refs:
                    sha = self._repo.refs[key]
                    o = self._repo[sha]
                    if isinstance(o, objects.Tag):
                        # Branches point directly to commits, but
                        # signed tags point to the signature and we
                        # need to dereference it to get to the commit.
                        sha = o.object[1]
                    return sha
            # If we end up here we didn't find any of the candidates.
            raise ValueError('Unknown reference {!r}'.format(name))
        return self._repo.refs[b'HEAD']

    def _get_walker_for_branch(self, branch):
        branch_head = self._get_ref(branch)
        return self._repo.get_walker(branch_head)

    def _get_valid_tags_on_commit(self, sha):
        return [tag for tag in self._repo.get_tags_on_commit(sha)
                if self.release_tag_re.match(tag)]

    def _get_tags_on_branch(self, branch):
        "Return a list of tag names on the given branch."
        results = []
        for c in self._get_walker_for_branch(branch):
            # shas_to_tags has encoded versions of the shas
            # but the commit object gives us a decoded version
            sha = c.commit.sha().hexdigest().encode('ascii')
            tags = self._get_valid_tags_on_commit(sha)
            results.extend(tags)
        return results

    def _get_current_version(self, branch=None):
        "Return the current version of the repository, like git describe."
        # This is similar to _get_tags_on_branch() except that it
        # counts up to where the tag appears and it returns when it
        # finds the first tagged commit (there is no need to scan the
        # rest of the branch).
        commit = self._repo[self._get_ref(branch)]
        count = 0
        while commit:
            # shas_to_tags has encoded versions of the shas
            # but the commit object gives us a decoded version
            sha = commit.sha().hexdigest().encode('ascii')
            tags = self._get_valid_tags_on_commit(sha)
            if tags:
                if count:
                    val = '{}-{}'.format(tags[-1], count)
                else:
                    val = tags[-1]
                return val
            if commit.parents:
                # Only traverse the first parent of each node.
                commit = self._repo[commit.parents[0]]
                count += 1
            else:
                commit = None
        return '0.0.0'

    def _strip_pre_release(self, tag):
        """Return tag with pre-release identifier removed if present."""
        pre_release_match = self.pre_release_tag_re.search(tag)
        if pre_release_match:
            try:
                start = pre_release_match.start('pre_release')
                end = pre_release_match.end('pre_release')
            except IndexError:
                raise ValueError(
                    ("The pre-release tag regular expression, {!r}, is missing"
                     " a group named 'pre_release'.").format(
                        self.pre_release_tag_re.pattern
                    )
                )
            else:
                stripped_tag = tag[:start] + tag[end:]
        else:
            stripped_tag = tag

        return stripped_tag

    def _get_branch_base(self, branch):
        "Return the tag at base of the branch."
        # Based on
        # http://stackoverflow.com/questions/1527234/finding-a-branch-point-with-git
        # git rev-list $(git rev-list --first-parent \
        #   ^origin/stable/newton master | tail -n1)^^!
        #
        # Build the set of all commits that appear on the master
        # branch, then scan the commits that appear on the specified
        # branch until we find something that is on both.
        master_commits = set(
            c.commit.sha().hexdigest()
            for c in self._get_walker_for_branch('master')
        )
        for c in self._get_walker_for_branch(branch):
            if c.commit.sha().hexdigest() in master_commits:
                # We got to this commit via the branch, but it is also
                # on master, so this is the base.
                tags = self._get_valid_tags_on_commit(
                    c.commit.sha().hexdigest().encode('ascii'))
                if tags:
                    return tags[-1]
                else:
                    # Naughty, naughty, branching without tagging.
                    LOG.info(
                        ('There is no tag on commit %s at the base of %s. '
                         'Branch scan short-cutting is disabled.'),
                        c.commit.sha().hexdigest(), branch)
                    return None
        return None

    def _topo_traversal(self, branch):
        """Generator that yields the branch entries in topological order.

        The topo ordering in dulwich does not match the git command line
        output, so we have our own that follows the branch being merged
        into the mainline before following the mainline. This ensures that
        tags on the mainline appear in the right place relative to the
        merge points, regardless of the commit date on the entry.

        # *   d1239b6 (HEAD -> master) Merge branch 'new-branch'
        # |\
        # | * 9478612 (new-branch) one commit on branch
        # * | 303e21d second commit on master
        # * | 0ba5186 first commit on master
        # |/
        # *   a7f573d original commit on master

        """
        head = self._get_ref(branch)

        # Map SHA values to Entry objects, because we will be traversing
        # commits not entries.
        all = {}

        children = {}

        # Populate all and children structures by traversing the
        # entire graph once. It doesn't matter what order we do this
        # the first time, since we're just recording the relationships
        # of the nodes.
        for e in self._repo.get_walker(head):
            all[e.commit.id] = e
            for p in e.commit.parents:
                children.setdefault(p, set()).add(e.commit.id)

        # Track what we have already emitted.
        emitted = set()

        # Use a deque as a stack with the nodes left to process. This
        # lets us avoid recursion, since we have no idea how deep some
        # branches might be.
        todo = collections.deque()
        todo.appendleft(head)

        ignore_null_merges = self.conf.ignore_null_merges
        if ignore_null_merges:
            LOG.debug('ignoring null-merge commits')

        while todo:
            sha = todo.popleft()
            entry = all[sha]
            null_merge = False

            # OpenStack used to use null-merges to bring final release
            # tags from stable branches back into the master
            # branch. This confuses the regular traversal because it
            # makes that stable branch appear to be part of master
            # and/or the later stable branch. When we hit one of those
            # tags, skip it and take the first parent.
            if ignore_null_merges and len(entry.commit.parents) > 1:
                # Look for tags on the 2nd and later parents. The
                # first parent is part of the branch we were
                # originally trying to traverse, and any tags on it
                # need to be kept.
                for p in entry.commit.parents[1:]:
                    t = self._get_valid_tags_on_commit(p)
                    # If we have a tag being merged in, we need to
                    # include a check to verify that this is actually
                    # a null-merge (there are no changes).
                    if t and not entry.changes():
                        LOG.debug(
                            'treating %s as a null-merge because '
                            'parent %s has tag(s) %s',
                            sha, p, t,
                        )
                        null_merge = True
                        break
                if null_merge:
                    # Make it look like the parent entries that we're
                    # going to skip have been emitted so the
                    # bookkeeping for children works properly and we
                    # can continue past the merge.
                    emitted.update(set(entry.commit.parents[1:]))
                    # Make it look like the current entry was emitted
                    # so the bookkeeping for children works properly
                    # and we can continue past the merge.
                    emitted.add(sha)
                    # Now set up the first parent so it is processed
                    # later.
                    first_parent = entry.commit.parents[0]
                    if first_parent not in todo:
                        todo.appendleft(first_parent)
                    continue

            # If a node has multiple children, it is the start point
            # for a branch that was merged back into the rest of the
            # tree. We will have already processed the merge commit
            # and are traversing either the branch that was merged in
            # or the base into which it was merged. We want to stop
            # traversing the branch that was merged in at the point
            # where the branch was created, because we are trying to
            # linearize the history. At that point, we go back to the
            # merge node and take the other parent node, which should
            # lead us back to the origin of the branch through the
            # mainline.
            unprocessed_children = [
                c
                for c in children.get(sha, set())
                if c not in emitted
            ]

            if not unprocessed_children:
                # All children have been processed. Remember that we have
                # processed this node and then emit the entry.
                emitted.add(sha)
                yield entry

                # Now put the parents on the stack from left to right
                # so they are processed right to left. If the node is
                # already on the stack, leave it to be processed in
                # the original order where it was added.
                #
                # NOTE(dhellmann): It's not clear if this is the right
                # solution, or if we should re-stack and then ignore
                # duplicate emissions at the top of this
                # loop. Checking if the item is already on the todo
                # stack isn't very expensive, since we don't expect it
                # to grow very large, but it's not clear the output
                # will be produced in the right order.
                for p in entry.commit.parents:
                    if p not in todo:
                        todo.appendleft(p)

            else:
                # Has unprocessed children.  Do not emit, and do not
                # restack, since when we get to the other child they will
                # stack it.
                pass

    def get_file_at_commit(self, filename, sha):
        "Return the contents of the file if it exists at the commit, or None."
        return self._repo.get_file_at_commit(filename, sha)

    def _file_exists_at_commit(self, filename, sha):
        "Return true if the file exists at the given commit."
        return bool(self.get_file_at_commit(filename, sha))

    def _get_series_branches(self):
        "Get branches matching the branch_name_re config option."
        refs = self._repo.get_refs()
        LOG.debug('refs %s', list(refs.keys()))
        branch_names = set()
        for r in refs.keys():
            name = None
            r = r.decode('utf-8')
            if r.startswith('refs/remotes/origin/'):
                name = r[20:]
            elif r.startswith('refs/heads/'):
                name = r[11:]
            if name and self.branch_name_re.search(name):
                branch_names.add(name)
        return list(sorted(branch_names))

    def _get_earlier_branch(self, branch):
        "Return the name of the branch created before the given branch."
        # FIXME(dhellmann): Assumes branches come in order based on
        # name. That may not be true for projects that branch based on
        # version numbers instead of names.
        if branch.startswith('origin/'):
            branch = branch[7:]
        LOG.debug('looking for the branch before %s', branch)
        branch_names = self._get_series_branches()
        if branch not in branch_names:
            LOG.debug('Could not find branch %r among %s',
                      branch, branch_names)
            return None
        LOG.debug('found branches %s', branch_names)
        current = branch_names.index(branch)
        if current == 0:
            # This is the first branch.
            LOG.debug('%s appears to be the first branch', branch)
            return None
        previous = branch_names[current - 1]
        LOG.debug('found earlier branch %s', previous)
        return previous

    def _find_scan_stop_point(self, earliest_version, versions_by_date,
                              collapse_pre_releases, branch):
        """Return the version to use to stop the scan.

        Use the list of versions_by_date to get the tag with a
        different version created *before* the branch to ensure that
        we include notes that go with that version that *is* in the
        branch.

        :param earliest_version: Version string of the earliest
            version to be included in the output.
        :param versions_by_date: List of version strings in reverse
            chronological order.
        :param collapse_pre_releases: Boolean indicating whether we are
            collapsing pre-releases or not. If false, the next tag
            is used, regardless of its version.
        :param branch: The name of the branch we are scanning.

        """
        if not earliest_version:
            return None
        earliest_parts = _parse_version(earliest_version)
        try:
            idx = versions_by_date.index(earliest_version) + 1
        except ValueError:
            # The version we were given is not present, use a full
            # scan.
            return None
        # We need to look for the previous branch's root.
        if branch and branch != 'master':
            previous_branch = self._get_earlier_branch(branch)
            if not previous_branch:
                # This was the first branch, so scan the whole
                # history.
                return None
            previous_base = self._get_branch_base(previous_branch)
            return previous_base
        is_pre_release = bool(self.pre_release_tag_re.search(earliest_version))
        if is_pre_release and not collapse_pre_releases:
            # We just take the next tag.
            return versions_by_date[idx]
        # We need to look for a different version.
        for candidate in versions_by_date[idx:]:
            parts = _parse_version(candidate)
            if parts != earliest_parts:
                # The candidate is a different version, use it.
                return candidate
        return None

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

        LOG.info('scanning %s/%s (branch=%s earliest_version=%s)',
                 reporoot.rstrip('/'), notesdir.lstrip('/'),
                 branch or '*current*', earliest_version)

        # Determine the current version, which might be an unreleased or
        # dev version if there are unreleased commits at the head of the
        # branch in question.
        current_version = self._get_current_version(branch)
        LOG.debug('current repository version: %s' % current_version)

        # Determine all of the tags known on the branch, in their date
        # order. We scan the commit history in topological order to ensure
        # we have the commits in the right version, so we might encounter
        # the tags in a different order during that phase.
        versions_by_date = self._get_tags_on_branch(branch)
        LOG.debug('versions by date %r' % (versions_by_date,))
        if earliest_version and earliest_version not in versions_by_date:
            raise ValueError(
                'earliest-version set to unknown revision {!r}'.format(
                    earliest_version))

        # If the user has told us where to stop, use that as the
        # default.
        scan_stop_tag = self._find_scan_stop_point(
            earliest_version, versions_by_date,
            collapse_pre_releases, branch)

        # If the user has not told us where to stop, try to work it
        # out for ourselves.
        if not branch and not earliest_version and stop_at_branch_base:
            # On the current branch, stop at the point where the most
            # recent branch was created, if we can find one.
            LOG.debug('working on current branch without earliest_version')
            branches = self._get_series_branches()
            if branches:
                for earlier_branch in reversed(branches):
                    LOG.debug('checking if current branch is later than %s',
                              earlier_branch)
                    scan_stop_tag = self._get_branch_base(earlier_branch)
                    if scan_stop_tag in versions_by_date:
                        LOG.info(
                            'looking at %s at base of %s to '
                            'stop scanning the current branch',
                            scan_stop_tag, earlier_branch
                        )
                        break
                else:
                    LOG.info('unable to find the previous branch base')
                    scan_stop_tag = None
                if scan_stop_tag:
                    # If there is a tag on this branch after the point
                    # where the earlier branch was created, then use that
                    # tag as the earliest version to show in the current
                    # "series". If there is no such tag, then go all the
                    # way to the base of that earlier branch.
                    try:
                        idx = versions_by_date.index(scan_stop_tag) + 1
                        earliest_version = versions_by_date[idx]
                    except ValueError:
                        # The scan_stop_tag is not in versions_by_date.
                        earliest_version = None
                    except IndexError:
                        # The idx is not in versions_by_date.
                        earliest_version = scan_stop_tag
        elif branch and stop_at_branch_base and not earliest_version:
            # If branch is set and is not "master",
            # then we want to stop at the version before the tag at the
            # base of the branch, which involves a bit of searching.
            LOG.debug('determining earliest_version from branch')
            branch_base = self._get_branch_base(branch)
            scan_stop_tag = self._find_scan_stop_point(
                branch_base, versions_by_date,
                collapse_pre_releases, branch)
            if not scan_stop_tag:
                earliest_version = branch_base
            else:
                idx = versions_by_date.index(scan_stop_tag)
                earliest_version = versions_by_date[idx - 1]
            if earliest_version and collapse_pre_releases:
                if self.pre_release_tag_re.search(earliest_version):
                    # The earliest version won't actually be the pre-release
                    # that might have been tagged when the branch was created,
                    # but the final version. Strip the pre-release portion of
                    # the version number.
                    earliest_version = self._strip_pre_release(
                        earliest_version
                    )
        if earliest_version:
            LOG.info('earliest version to include is %s', earliest_version)
        else:
            LOG.info('including entire branch history')
        if scan_stop_tag:
            LOG.info('stopping scan at %s', scan_stop_tag)

        # Since the version may not already be known, make sure it is
        # in the list of versions by date. And since it is the most
        # recent version, go ahead and insert it at the front of the
        # list.
        if current_version not in versions_by_date:
            versions_by_date.insert(0, current_version)
        versions_by_date.insert(0, '*working-copy*')

        # Track the versions we have seen and the earliest version for
        # which we have seen a given note's unique id.
        tracker = _ChangeTracker()

        # Process the local index, if we are scanning the current
        # branch.
        if not branch:
            prefix = notesdir.rstrip('/') + '/'
            index = self._repo.open_index()

            # Pretend anything known to the repo and changed but not
            # staged is part of the fake version '*working-copy*'.
            LOG.debug('scanning unstaged changes')
            for fname in d_index.get_unstaged_changes(index, self.reporoot):
                fname = fname.decode('utf-8')
                LOG.debug('found unstaged file %s', fname)
                if fname.startswith(prefix) and _note_file(fname):
                    fullpath = os.path.join(self.reporoot, fname)
                    if os.path.exists(fullpath):
                        LOG.debug('found file %s', fullpath)
                        tracker.add(fname, None, '*working-copy*')
                    else:
                        LOG.debug('deleted file %s', fullpath)
                        tracker.delete(fname, None, '*working-copy*')

            # Pretend anything in the index is part of the fake
            # version "*working-copy*".
            LOG.debug('scanning staged schanges')
            changes = porcelain.get_tree_changes(self._repo)
            for fname in changes['add']:
                fname = fname.decode('utf-8')
                if fname.startswith(prefix) and _note_file(fname):
                    tracker.add(fname, None, '*working-copy*')
            for fname in changes['modify']:
                fname = fname.decode('utf-8')
                if fname.startswith(prefix) and _note_file(fname):
                    tracker.modify(fname, None, '*working-copy*')
            for fname in changes['delete']:
                fname = fname.decode('utf-8')
                if fname.startswith(prefix) and _note_file(fname):
                    tracker.delete(fname, None, '*working-copy*')

        aggregator = _ChangeAggregator()

        # Process the git commit history.
        for counter, entry in enumerate(self._topo_traversal(branch), 1):

            sha = entry.commit.id
            tags_on_commit = self._get_valid_tags_on_commit(sha)

            LOG.debug('%06d %s %s', counter, sha, tags_on_commit)

            # If there are no tags in this block, assume the most recently
            # seen version.
            tags = tags_on_commit
            if not tags:
                tags = [current_version]
            else:
                current_version = tags_on_commit[-1]
                LOG.info('%06d %s updating current version to %s',
                         counter, sha, current_version)

            # Look for changes to notes files in this commit. The
            # change has only the basename of the path file, so we
            # need to prefix that with the notesdir before giving it
            # to the tracker.
            changes = _changes_in_subdir(self._repo, entry, notesdir)
            for change in aggregator.aggregate_changes(entry, changes):
                uniqueid = change[0]

                c_type = change[1]

                if c_type == diff_tree.CHANGE_ADD:
                    path, blob_sha = change[-2:]
                    fullpath = os.path.join(notesdir, path)
                    tracker.add(fullpath, sha, current_version)

                elif c_type == diff_tree.CHANGE_DELETE:
                    path, blob_sha = change[-2:]
                    fullpath = os.path.join(notesdir, path)
                    tracker.delete(fullpath, sha, current_version)

                elif c_type == diff_tree.CHANGE_RENAME:
                    path, blob_sha = change[-2:]
                    fullpath = os.path.join(notesdir, path)
                    tracker.rename(fullpath, sha, current_version)

                elif c_type == diff_tree.CHANGE_MODIFY:
                    path, blob_sha = change[-2:]
                    fullpath = os.path.join(notesdir, path)
                    tracker.modify(fullpath, sha, current_version)

                else:
                    raise ValueError(
                        'unknown change instructions {!r}'.format(change)
                    )

            if scan_stop_tag and scan_stop_tag in tags:
                LOG.info(
                    ('reached end of branch after %d commits at %s '
                     'with tags %s'),
                    counter, sha, tags)
                break

        # Invert earliest_seen to make a list of notes files for each
        # version.
        files_and_tags = collections.OrderedDict()
        for v in tracker.versions:
            files_and_tags[v] = []
        # Produce a list of the actual files present in the repository. If
        # a note is removed, this step should let us ignore it.
        for uniqueid, version in tracker.earliest_seen.items():
            try:
                base, sha = tracker.last_name_by_id[uniqueid]
                LOG.debug('%s: sorting %s into version %s',
                          uniqueid, base, version)
                files_and_tags[version].append((base, sha))
            except KeyError:
                # Unable to find the file again, skip it to avoid breaking
                # the build.
                msg = ('unable to find release notes file associated '
                       'with unique id %r, skipping') % uniqueid
                LOG.debug(msg)
                print(msg, file=sys.stderr)

        # Combine pre-releases into the final release, if we are told to
        # and the final release exists.
        if collapse_pre_releases:
            LOG.debug('collapsing pre-release versions into final releases')
            collapsing = files_and_tags
            files_and_tags = collections.OrderedDict()
            for ov in versions_by_date:
                if ov not in collapsing:
                    # We don't need to collapse this one because there are
                    # no notes attached to it.
                    continue
                pre_release_match = self.pre_release_tag_re.search(ov)
                LOG.debug('checking %r', ov)
                if pre_release_match:
                    # Remove the trailing pre-release part of the version
                    # from the string.
                    canonical_ver = self._strip_pre_release(ov)
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

        LOG.debug('files_and_tags %s',
                  {k: len(v) for k, v in files_and_tags.items()})
        # Only return the parts of files_and_tags that actually have
        # filenames associated with the versions.
        LOG.debug('trimming')
        trimmed = collections.OrderedDict()
        for ov in versions_by_date:
            if not files_and_tags.get(ov):
                continue
            LOG.debug('keeping %s', ov)
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
                LOG.debug('stopping trimming at %s', earliest_version)
                break

        LOG.debug(
            'found %d versions and %d files',
            len(trimmed.keys()), sum(len(ov) for ov in trimmed.values()),
        )
        return trimmed
