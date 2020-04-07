# Copyright 2017, Red Hat, Inc.
#
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

"""Custom distutils command.

For more information, refer to the distutils and setuptools source:

- https://github.com/python/cpython/blob/3.6/Lib/distutils/cmd.py
- https://github.com/pypa/setuptools/blob/v36.0.0/setuptools/command/sdist.py
"""

import typing

from distutils import cmd
from distutils import errors
from distutils import log


from reno import cache
from reno import config
from reno import defaults
from reno import formatter
from reno import loader

COMMAND_NAME = 'build_reno'  # duplicates what's found in setup.cfg


def load_config(distribution):
    """Utility method to parse distutils/setuptools configuration.

    This is for use by other libraries to extract the command configuration.

    :param distribution: A :class:`distutils.dist.Distribution` object
    :returns: A tuple of a :class:`reno.config.Config` object, the output path
        of the human-readable release notes file, and the output file of the
        reno cache file
    """
    option_dict = distribution.get_option_dict(COMMAND_NAME)

    if option_dict.get('repo_root') is not None:
        repo_root = option_dict.get('repo_root')[1]
    else:
        repo_root = defaults.REPO_ROOT

    if option_dict.get('rel_notes_dir') is not None:
        rel_notes_dir = option_dict.get('rel_notes_dir')[1]
    else:
        rel_notes_dir = defaults.RELEASE_NOTES_SUBDIR

    if option_dict.get('output_file') is not None:
        output_file = option_dict.get('output_file')[1]
    else:
        output_file = defaults.RELEASE_NOTES_FILENAME

    conf = config.Config(repo_root, rel_notes_dir)
    cache_file = loader.get_cache_filename(conf)

    return (conf, output_file, cache_file)


class BuildReno(cmd.Command):
    """Distutils command to build reno release notes.

    The release note build can be triggered from distutils, and some
    configuration can be included in ``setup.py`` or ``setup.cfg`` instead of
    being specified from the command-line.
    """
    description = 'Build reno release notes'
    user_options = [
        ('repo-root=', None, 'the root directory of the Git repository; '
         'defaults to "."'),
        ('rel-notes-dir=', None, 'the parent directory; defaults to '
         '"releasenotes"'),
        ('output-file=', None, 'the filename of the release notes file'),
    ]

    def initialize_options(self):
        self.repo_root = None
        self.rel_notes_dir = None
        self.output_file = None

    def finalize_options(self):
        if self.repo_root is None:
            self.repo_root = defaults.REPO_ROOT

        if self.rel_notes_dir is None:
            self.rel_notes_dir = defaults.RELEASE_NOTES_SUBDIR

        if self.output_file is None:
            self.output_file = defaults.RELEASE_NOTES_FILENAME

    # Overriding distutils' Command._ensure_stringlike which doesn't support
    # unicode, causing finalize_options to fail if invoked again. Workaround
    # for http://bugs.python.org/issue19570
    def _ensure_stringlike(self, option, what, default=None):
        # type: (typing.unicode, typing.unicode, typing.Any) -> typing.Any
        val = getattr(self, option)
        if val is None:
            setattr(self, option, default)
            return default
        elif not isinstance(val, str):
            raise errors.DistutilsOptionError("'%s' must be a %s (got `%s`)"
                                              % (option, what, val))
        return val

    def run(self):
        conf = config.Config(self.repo_root, self.rel_notes_dir)

        # Generate the cache using the configuration options found
        # in the release notes directory and the default output
        # filename.
        cache_filename = cache.write_cache_db(
            conf=conf,
            versions_to_include=[],  # include all versions
            outfilename=None,  # generate the default name
        )
        log.info('wrote cache file to %s', cache_filename)

        ldr = loader.Loader(conf)
        text = formatter.format_report(
            ldr,
            conf,
            ldr.versions,
            title=self.distribution.metadata.name,
        )
        with open(self.output_file, 'w') as f:
            f.write(text)
        log.info('wrote release notes to %s', self.output_file)
