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

import argparse
import sys

from reno import create
from reno import defaults
from reno import lister
from reno import report


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--rel-notes-dir', '-d',
        dest='relnotesdir',
        default=defaults.RELEASE_NOTES_SUBDIR,
        help='location of release notes YAML files',
    )
    subparsers = parser.add_subparsers(
        title='commands',
    )

    do_new = subparsers.add_parser(
        'new',
        help='create a new note',
    )
    do_new.add_argument(
        'slug',
        help='descriptive title of note (keep it short)',
    )
    do_new.set_defaults(func=create.create_cmd)

    do_list = subparsers.add_parser(
        'list',
        help='list notes files based on query arguments',
    )
    do_list.add_argument(
        'reporoot',
        help='root of the git repository',
    )
    do_list.add_argument(
        '--version',
        default=[],
        action='append',
        help='the version(s) to include, defaults to all',
    )
    do_list.add_argument(
        '--branch',
        default=None,
        help='the branch to scan, defaults to the current',
    )
    do_list.set_defaults(func=lister.list_cmd)

    do_report = subparsers.add_parser(
        'report',
        help='generate release notes report',
    )
    do_report.add_argument(
        'reporoot',
        help='root of the git repository',
    )
    do_report.add_argument(
        '--output', '-o',
        default=None,
        help='output filename, defaults to stdout',
    )
    do_report.add_argument(
        '--branch',
        default=None,
        help='the branch to scan, defaults to the current',
    )
    do_report.add_argument(
        '--version',
        default=[],
        action='append',
        help='the version(s) to include, defaults to all',
    )
    do_report.set_defaults(func=report.report_cmd)

    args = parser.parse_args()
    return args.func(args)
