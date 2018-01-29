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
import logging
import os.path
import textwrap

import yaml

from reno import defaults

LOG = logging.getLogger(__name__)


Opt = collections.namedtuple('Opt', 'name default help')

_OPTIONS = [
    Opt('notesdir', defaults.NOTES_SUBDIR,
        textwrap.dedent("""\
        The notes subdirectory within the relnotesdir where the
        notes live.
        """)),

    Opt('collapse_pre_releases', True,
        textwrap.dedent("""\
        Should pre-release versions be merged into the final release
        of the same number (1.0.0.0a1 notes appear under 1.0.0).
        """)),

    Opt('stop_at_branch_base', True,
        textwrap.dedent("""\
        Should the scanner stop at the base of a branch (True) or go
        ahead and scan the entire history (False)?
        """)),

    Opt('branch', None,
        textwrap.dedent("""\
        The git branch to scan. Defaults to the "current" branch
        checked out. If a stable branch is specified but does not
        exist, reno attempts to automatically convert that to an
        "end-of-life" tag. For example, ``origin/stable/liberty``
        would be converted to ``liberty-eol``.
        """)),

    Opt('earliest_version', None,
        textwrap.dedent("""\
        The earliest version to be included. This is usually the
        lowest version number, and is meant to be the oldest
        version. If unset, all versions will be scanned.
        """)),

    Opt('template', defaults.TEMPLATE.format(defaults.PRELUDE_SECTION_NAME),
        textwrap.dedent("""\
        The template used by reno new to create a note.
        """)),

    Opt('release_tag_re',
        textwrap.dedent('''\
        ((?:[\d.ab]|rc)+)  # digits, a, b, and rc cover regular and
                           # pre-releases
        '''),
        textwrap.dedent("""\
        The regex pattern used to match the repo tags representing a
        valid release version. The pattern is compiled with the
        verbose and unicode flags enabled.
        """)),

    Opt('pre_release_tag_re',
        textwrap.dedent('''\
        (?P<pre_release>\.\d+(?:[ab]|rc)+\d*)$
        '''),
        textwrap.dedent("""\
        The regex pattern used to check if a valid release version tag
        is also a valid pre-release version. The pattern is compiled
        with the verbose and unicode flags enabled. The pattern must
        define a group called 'pre_release' that matches the
        pre-release part of the tag and any separator, e.g for
        pre-release version '12.0.0.0rc1' the default pattern will
        identify '.0rc1' as the value of the group 'pre_release'.
        """)),

    Opt('branch_name_re', 'stable/.+',
        textwrap.dedent("""\
        The pattern for names for branches that are relevant when
        scanning history to determine where to stop, to find the
        "base" of a branch. Other branches are ignored.
        """)),

    Opt('closed_branch_tag_re', '(.+)-eol',
        textwrap.dedent("""\
        The pattern for names for tags that replace closed
        branches that are relevant when scanning history to
        determine where to stop, to find the "base" of a
        branch. Other tags are ignored.
        """)),

    Opt('branch_name_prefix', 'stable/',
        textwrap.dedent("""\
        The prefix to add to tags for closed branches
        to restore the old branch name to allow sorting
        to place the tag in the proper place in history.
        For example, OpenStack turns "mitaka-eol" into
        "stable/mitaka" by removing the "-eol" suffix
        via closed_branch_tag_re and setting the prefix
        to "stable/".
        """)),

    Opt('sections',
        [
            ['features', 'New Features'],
            ['issues', 'Known Issues'],
            ['upgrade', 'Upgrade Notes'],
            ['deprecations', 'Deprecation Notes'],
            ['critical', 'Critical Issues'],
            ['security', 'Security Issues'],
            ['fixes', 'Bug Fixes'],
            ['other', 'Other Notes'],
        ],
        textwrap.dedent("""\
        The identifiers and names of permitted sections in the
        release notes, in the order in which the final report will
        be generated. A prelude section will always be automatically
        inserted before the first element of this list.
        """)),

    Opt('prelude_section_name', defaults.PRELUDE_SECTION_NAME,
        textwrap.dedent("""\
        The name of the prelude section in the note template. This
        allows users to rename the section to, for example,
        'release_summary' or 'project_wide_general_announcements',
        which is displayed in titlecase in the report after
        replacing underscores with spaces.
        """)),

    Opt('ignore_null_merges', True,
        textwrap.dedent("""\
        When this option is set to True, any merge commits with no
        changes and in which the second or later parent is tagged
        are considered "null-merges" that bring the tag information
        into the current branch but nothing else.

        OpenStack used to use null-merges to bring final release
        tags from stable branches back into the master branch. This
        confuses the regular traversal because it makes that stable
        branch appear to be part of master and/or the later stable
        branch. This option allows us to ignore those.
        """)),

    Opt('ignore_notes', [],
        textwrap.dedent("""\
        Note files to be ignored. It's useful to be able to ignore a
        file if it is edited on the wrong branch. Notes should be
        specified by their filename or UID.

        Setting the option in the main configuration file makes it
        apply to all branches. To ignore a note in the HTML build, use
        the ``ignore-notes`` parameter to the ``release-notes`` sphinx
        directive.
        """)),
]


class Config(object):

    _OPTS = {o.name: o for o in _OPTIONS}

    @classmethod
    def get_default(cls, opt):
        "Return the default for an option."
        try:
            return cls._OPTS[opt].default
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
        self.override(**{o.name: o.default for o in _OPTIONS})

        self._contents = {}
        self._load_file()

    def _load_file(self):
        filenames = [
            os.path.join(self.reporoot, self.relnotesdir, 'config.yaml'),
            os.path.join(self.reporoot, 'reno.yaml')]

        for filename in filenames:
            LOG.debug('looking for configuration file %s', filename)
            if os.path.isfile(filename):
                break
        else:
            LOG.info('no configuration file in: %s', ', '.join(filenames))
            return

        try:
            with open(filename, 'r') as fd:
                self._contents = yaml.safe_load(fd)
            LOG.info('loaded configuration file %s', filename)
        except IOError as err:
            LOG.warning('did not load config file %s: %s', filename, err)
        else:
            self.override(**self._contents)

    def _rename_prelude_section(self, **kwargs):
        key = 'prelude_section_name'
        if key in kwargs and kwargs[key] != self._OPTS[key].default:
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
            o.name: getattr(parsed_args, o.name)
            for o in _OPTIONS
            if hasattr(parsed_args, o.name)
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
        options = {
            o.name: getattr(self, o.name)
            for o in _OPTIONS
        }
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
