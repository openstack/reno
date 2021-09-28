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
from datetime import datetime
import logging
import os.path

import yaml

from reno import scanner

LOG = logging.getLogger(__name__)


def get_cache_filename(conf):
    return os.path.normpath(os.path.join(
        conf.reporoot, conf.notespath, 'reno.cache'))


class Loader(object):
    "Load the release notes for a given repository."

    def __init__(self, conf, ignore_cache=False):
        """Initialize a Loader.

        The versions are presented in reverse chronological order.

        Notes files are associated with the earliest version for which
        they were available, regardless of whether they changed later.

        :param conf: Parsed configuration from file
        :type conf: reno.config.Config
        :param ignore_cache: Do not load a cache file if it is present.
        :type ignore_cache: bool
        """
        self._config = conf
        self._ignore_cache = ignore_cache

        self._reporoot = conf.reporoot
        self._notespath = conf.notespath
        self._branch = conf.branch
        self._collapse_pre_releases = conf.collapse_pre_releases
        self._earliest_version = conf.earliest_version

        self._cache = None
        self._scanner = None
        self._scanner_output = None
        self._tags_to_dates = None
        self._cache_filename = get_cache_filename(conf)
        self._encoding = conf.options['encoding']

        self._load_data()

    def _load_data(self):
        cache_file_exists = os.path.exists(self._cache_filename)

        if self._ignore_cache and cache_file_exists:
            LOG.debug('ignoring cache file %s', self._cache_filename)

        if (not self._ignore_cache) and cache_file_exists:
            LOG.debug('loading cache file %s', self._cache_filename)

            with open(self._cache_filename, 'r', encoding=self._encoding) as f:
                self._cache = yaml.safe_load(f.read())

            # Save the cached scanner output to the same attribute
            # it would be in if we had loaded it "live". This
            # simplifies some of the logic in the other methods.
            self._scanner_output = collections.OrderedDict(
                (n['version'], n['files'])
                for n in self._cache['notes']
            )
            self._tags_to_dates = collections.OrderedDict(
                (n['version'], n['date'])
                for n in self._cache['dates']
            )
        else:
            self._scanner = scanner.Scanner(self._config)
            self._scanner_output = self._scanner.get_notes_by_version()
            self._tags_to_dates = self._scanner.get_version_dates()

    def close(self):
        """Close any files opened by this loader."""
        if self._scanner is not None:
            self._scanner.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def versions(self):
        "A list of all of the versions found."
        return list(self._scanner_output.keys())

    def __getitem__(self, version):
        "Return data about the files that should go into a given version."
        return self._scanner_output[version]

    def get_version_date(self, version):
        "Return release data for a version."
        if version in self._tags_to_dates.keys():
            date = datetime.fromtimestamp(self._tags_to_dates[version])
            return date.strftime("%Y-%m-%d")
        return "Unknown"

    def parse_note_file(self, filename, sha):
        """Return the data structure encoded in the note file.

        Emit warnings for content that does not look valid in some
        way, but return it anyway for backwards-compatibility.

        """
        if self._cache:
            content = self._cache['file-contents'][filename]
        else:
            body = self._scanner.get_file_at_commit(filename, sha)
            content = yaml.safe_load(body)

        cleaned_content = {}

        if not isinstance(content, dict):
            LOG.warning(
                '%s does not appear to be structured as a YAML mapping. '
                'Did you forget a top-level key?',
                filename,
            )
            raise ValueError(
                f'{filename} does not appear to be structured as a YAML '
                f'mapping. Did you forget a top-level key?'
            )

        for section_name, section_content in content.items():
            if section_name == self._config.prelude_section_name:
                if not isinstance(section_content, str):
                    LOG.warning(
                        'The %s section of %s does not parse as a single '
                        'string. Is the YAML input escaped properly?',
                        section_name, filename,
                    )
            else:
                if section_name not in dict(self._config.sections):
                    # TODO(stephenfin): Make this an error in a future release
                    LOG.warning(
                        'The %s section of %s is not a recognized section. '
                        'It should be one of: %s. '
                        'This will be an error in a future release.',
                        section_name, filename,
                        ', '.join(dict(self._config.sections)),
                    )
                if isinstance(section_content, str):
                    # A single string is OK, but wrap it with a list
                    # so the rest of the code can treat the data model
                    # consistently.
                    section_content = [section_content]
                elif not isinstance(section_content, list):
                    LOG.warning(
                        'The %s section of %s does not parse as a string or '
                        'list of strings. Is the YAML input escaped properly?',
                        section_name, filename,
                    )
                else:
                    for item in section_content:
                        if not isinstance(item, str):
                            LOG.warning(
                                'The item %r in the %s section of %s parses '
                                'as a %s instead of a string. '
                                'Is the YAML input escaped properly?',
                                item, section_name, filename, type(item),
                            )

            cleaned_content[section_name] = section_content

        return cleaned_content
