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

import yaml

from reno import defaults

LOG = logging.getLogger(__name__)


class Config(object):

    _OPTS = {
        # The notes subdirectory within the relnotesdir where the
        # notes live.
        'notesdir': defaults.NOTES_SUBDIR,

        # Should pre-release versions be merged into the final release
        # of the same number (1.0.0.0a1 notes appear under 1.0.0).
        'collapse_pre_releases': True,

        # Should the scanner stop at the base of a branch (True) or go
        # ahead and scan the entire history (False)?
        'stop_at_branch_base': True,

        # The git branch to scan. Defaults to the "current" branch
        # checked out.
        'branch': None,

        # The earliest version to be included. This is usually the
        # lowest version number, and is meant to be the oldest
        # version.
        'earliest_version': None,

        # The template used by reno new to create a note.
        'template': defaults.TEMPLATE.format(defaults.PRELUDE_SECTION_NAME),

        # The RE pattern used to match the repo tags representing a valid
        # release version. The pattern is compiled with the verbose and unicode
        # flags enabled.
        'release_tag_re': '''
            ((?:[\d.ab]|rc)+)  # digits, a, b, and rc cover regular and
                               # pre-releases
        ''',

        # The RE pattern used to check if a valid release version tag is also a
        # valid pre-release version. The pattern is compiled with the verbose
        # and unicode flags enabled. The pattern must define a group called
        # 'pre_release' that matches the pre-release part of the tag and any
        # separator, e.g for pre-release version '12.0.0.0rc1' the default RE
        # pattern will identify '.0rc1' as the value of the group
        # 'pre_release'.
        'pre_release_tag_re': '''
            (?P<pre_release>\.\d+(?:[ab]|rc)+\d*)$
        ''',

        # The pattern for names for branches that are relevant when
        # scanning history to determine where to stop, to find the
        # "base" of a branch. Other branches are ignored.
        'branch_name_re': 'stable/.+',

        # The identifiers and names of permitted sections in the
        # release notes, in the order in which the final report will
        # be generated. A prelude section will always be automatically
        # inserted before the first element of this list.
        'sections': [
            ['features', 'New Features'],
            ['issues', 'Known Issues'],
            ['upgrade', 'Upgrade Notes'],
            ['deprecations', 'Deprecation Notes'],
            ['critical', 'Critical Issues'],
            ['security', 'Security Issues'],
            ['fixes', 'Bug Fixes'],
            ['other', 'Other Notes'],
        ],

        # The name of the prelude section in the note template. This
        # allows users to rename the section to, for example,
        # 'release_summary' or 'project_wide_general_announcements',
        # which is displayed in titlecase in the report after
        # replacing underscores with spaces.
        'prelude_section_name': defaults.PRELUDE_SECTION_NAME,

        # When this option is set to True, any merge commits with no
        # changes and in which the second or later parent is tagged
        # are considered "null-merges" that bring the tag information
        # into the current branch but nothing else.
        #
        # OpenStack used to use null-merges to bring final release
        # tags from stable branches back into the master branch. This
        # confuses the regular traversal because it makes that stable
        # branch appear to be part of master and/or the later stable
        # branch. This option allows us to ignore those.
        'ignore_null_merges': True,

        # Note files to be ignored. It's useful to be able to ignore a
        # file if it is edited on the wrong branch. Notes should be
        # specified by their filename or UID. Setting the value in the
        # configuration file makes it apply to all branches.
        'ignore_notes': [],
    }

    @classmethod
    def get_default(cls, opt):
        "Return the default for an option."
        try:
            return cls._OPTS[opt]
        except KeyError:
            raise ValueError('unknown option name %r' % (opt,))

    def __init__(self, reporoot, relnotesdir=None):
        """Instantiate a Config object

        :param str reporoot:
            The root directory of the repository.
        :param str relnotesdir:
            The directory containing release notes. Defaults to
            'releasenotes'.
        """
        self.reporoot = reporoot
        if relnotesdir is None:
            relnotesdir = defaults.RELEASE_NOTES_SUBDIR
        self.relnotesdir = relnotesdir
        # Initialize attributes from the defaults.
        self.override(**self._OPTS)

        self._contents = {}
        self._load_file()

    def _load_file(self):
        filenames = [
            os.path.join(self.reporoot, self.relnotesdir, 'config.yaml'),
            os.path.join(self.reporoot, 'reno.yaml')]

        for filename in filenames:
            if os.path.isfile(filename):
                break
        else:
            LOG.info('no configuration file in: %s', ', '.join(filenames))
            return

        try:
            with open(filename, 'r') as fd:
                self._contents = yaml.safe_load(fd)
        except IOError as err:
            LOG.warning('did not load config file %s: %s', filename, err)
        else:
            self.override(**self._contents)

    def _rename_prelude_section(self, **kwargs):
        key = 'prelude_section_name'
        if key in kwargs and kwargs[key] != self._OPTS[key]:
            new_prelude_name = kwargs[key]

            self.template = defaults.TEMPLATE.format(new_prelude_name)

    def override(self, **kwds):
        """Set the values of the named configuration options.

        Take the values of the keyword arguments as the current value
        of the same option, regardless of whether a value is already
        present.

        """
        # Replace prelude section name if it has been changed.
        self._rename_prelude_section(**kwds)

        for n, v in kwds.items():
            if n not in self._OPTS:
                LOG.warning('ignoring unknown configuration value %r = %r',
                            n, v)
            else:
                setattr(self, n, v)

    def override_from_parsed_args(self, parsed_args):
        """Set the values of the configuration options from parsed CLI args.

        This method assumes that the DEST values for the command line
        arguments are named the same as the configuration options.

        """
        arg_values = {
            o: getattr(parsed_args, o)
            for o in self._OPTS.keys()
            if hasattr(parsed_args, o)
        }
        self.override(**arg_values)

    @property
    def reporoot(self):
        return self._reporoot

    # Ensure that the 'reporoot' value always only ends in one '/'.
    @reporoot.setter
    def reporoot(self, value):
        self._reporoot = value.rstrip('/') + '/'

    @property
    def notespath(self):
        """The path in the repo where notes are kept.

        .. important::

           This does not take ``reporoot`` into account. You need to add this
           manually if required.
        """
        return os.path.join(self.relnotesdir, self.notesdir)

    @property
    def options(self):
        """Get all configuration options as a dict.

        Returns the actual configuration options after overrides.
        """
        options = {o: getattr(self, o) for o in self._OPTS}
        return options

# def parse_config_into(parsed_arguments):

#         """Parse the user config onto the namespace arguments.

#     :param parsed_arguments:
#         The result of calling :meth:`argparse.ArgumentParser.parse_args`.
#     :type parsed_arguments:
#         argparse.Namespace
#     """
#     config_path = get_config_path(parsed_arguments.relnotesdir)
#     config_values = read_config(config_path)

#     for key in config_values.keys():
#         try:
#             getattr(parsed_arguments, key)
#         except AttributeError:
#             LOG.info('Option "%s" does not apply to this particular command.'
#                      '. Ignoring...', key)
#             continue
#         setattr(parsed_arguments, key, config_values[key])

#     parsed_arguments._config = config_values
