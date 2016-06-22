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

import logging
import os.path

from reno import scanner

import six
import yaml

LOG = logging.getLogger(__name__)


def get_cache_filename(reporoot, notesdir):
    return os.path.join(reporoot, notesdir, 'reno.cache')


class Loader(object):
    "Load the release notes for a given repository."

    def __init__(self, reporoot, notesdir, branch=None,
                 collapse_pre_releases=True,
                 earliest_version=None,
                 ignore_cache=False):
        """Initialize a Loader.

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
        :param earliest_version: The oldest version to include.
        :type earliest_version: str
        :param ignore_cache: Do not load a cache file if it is present.
        :type ignore_cache: bool

        """
        self._reporoot = reporoot
        self._notesdir = notesdir
        self._branch = branch
        self._collapse_pre_releases = collapse_pre_releases
        self._earliest_version = earliest_version
        self._ignore_cache = ignore_cache

        self._cache = None
        self._scanner_output = None
        self._cache_filename = get_cache_filename(reporoot, notesdir)

        self._load_data()

    def _load_data(self):
        cache_file_exists = os.path.exists(self._cache_filename)

        if self._ignore_cache and cache_file_exists:
            LOG.debug('ignoring cache file %s', self._cache_filename)

        if (not self._ignore_cache) and cache_file_exists:
            with open(self._cache_filename, 'r') as f:
                self._cache = yaml.safe_load(f.read())
                # Save the cached scanner output to the same attribute
                # it would be in if we had loaded it "live". This
                # simplifies some of the logic in the other methods.
                self._scanner_output = {
                    n['version']: n['files']
                    for n in self._cache['notes']
                }
        else:
            self._scanner_output = scanner.get_notes_by_version(
                reporoot=self._reporoot,
                notesdir=self._notesdir,
                branch=self._branch,
                collapse_pre_releases=self._collapse_pre_releases,
                earliest_version=self._earliest_version,
            )

    @property
    def versions(self):
        "A list of all of the versions found."
        return list(self._scanner_output.keys())

    def __getitem__(self, version):
        "Return data about the files that should go into a given version."
        return self._scanner_output[version]

    def parse_note_file(self, filename, sha):
        """Return the data structure encoded in the note file.

        Emit warnings for content that does not look valid in some
        way, but return it anway for backwards-compatibility.

        """
        if self._cache:
            content = self._cache['file-contents'][filename]
        else:
            body = scanner.get_file_at_commit(self._reporoot, filename, sha)
            content = yaml.safe_load(body)

        for section_name, section_content in content.items():
            if section_name == 'prelude':
                if not isinstance(section_content, six.string_types):
                    LOG.warning(
                        ('The prelude section of %s '
                         'does not parse as a single string. '
                         'Is the YAML input escaped properly?') %
                        filename,
                    )
            else:
                if not isinstance(section_content, list):
                    LOG.warning(
                        ('The %s section of %s '
                         'does not parse as a list of strings. '
                         'Is the YAML input escaped properly?') % (
                             section_name, filename),
                    )
                else:
                    for item in section_content:
                        if not isinstance(item, six.string_types):
                            LOG.warning(
                                ('The item %r in the %s section of %s '
                                 'parses as a %s instead of a string. '
                                 'Is the YAML input escaped properly?'
                                 ) % (item, section_name,
                                      filename, type(item)),
                            )

        return content
