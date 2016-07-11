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


def get_config_path(relnotesdir):
    """Generate the path to the config file.

    :param str relnotesdir:
        The directory containing release notes.
    :returns:
        The path to the config file in the release notes directory.
    :rtype:
        str
    """
    return os.path.join(relnotesdir, defaults.RELEASE_NOTES_CONFIG_FILENAME)


def read_config(config_file):
    """Read and parse the config file.

    :param str config_file:
        The path to the config file to parse.
    :returns:
        The YAML parsed into a dictionary, otherwise, or an empty dictionary
        if the path does not exist.
    :rtype:
        dict
    """
    if not os.path.exists(config_file):
        return {}

    with open(config_file, 'r') as fd:
        return yaml.safe_load(fd)


def parse_config_into(parsed_arguments):
    """Parse the user config onto the namespace arguments.

    :param parsed_arguments:
        The result of calling :meth:`argparse.ArgumentParser.parse_args`.
    :type parsed_arguments:
        argparse.Namespace
    """
    config_path = get_config_path(parsed_arguments.relnotesdir)
    config_values = read_config(config_path)

    for key in config_values.keys():
        try:
            getattr(parsed_arguments, key)
        except AttributeError:
            LOG.info('Option "%s" does not apply to this particular command.'
                     '. Ignoring...', key)
            continue
        setattr(parsed_arguments, key, config_values[key])

    parsed_arguments._config = config_values
