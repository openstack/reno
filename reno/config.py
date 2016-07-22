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

LOG = logging.getLogger(__name__)


class Config(object):

    _FILENAME = 'config.yaml'

    _OPTS = {
        # The root directory of the git repository to scan.
        'reporoot': '.',

        # The notes subdirectory within the relnotesdir where the
        # notes live.
        'notesdir': 'notes',

        # Should pre-release versions be merged into the final release
        # of the same number (1.0.0.0a1 notes appear under 1.0.0).
        'collapse_pre_releases': True,

        # The git branch to scan. Defaults to the "current" branch
        # checked out.
        'branch': None,

        # The earliest version to be included. This is usually the
        # lowest version number, and is meant to be the oldest
        # version.
        'earliest_version': None,
    }

    @classmethod
    def get_default(cls, opt):
        "Return the default for an option."
        try:
            return cls._OPTS[opt]
        except KeyError:
            raise ValueError('unknown option name %r' % (opt,))

    def __init__(self, relnotesdir):
        """Instantiate a Config object

        :param str relnotesdir:
            The directory containing release notes.

        """
        self.relnotesdir = relnotesdir
        # Initialize attributes from the defaults.
        self.override(**self._OPTS)

        self._filename = os.path.join(relnotesdir, self._FILENAME)
        self._contents = {}
        self._load_file()

    def _load_file(self):
        try:
            with open(self._filename, 'r') as fd:
                self._contents = yaml.safe_load(fd)
        except IOError as err:
            LOG.info('did not load config file %s: %s',
                     self._filename, err)
        else:
            self.override(**self._contents)

    def override(self, **kwds):
        """Set the values of the named configuration options.

        Take the values of the keyword arguments as the current value
        of the same option, regardless of whether a value is already
        present.

        """
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
