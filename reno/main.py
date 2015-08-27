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
from reno import lister


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--rel-notes-dir', '-d',
        dest='relnotesdir',
        default='releasenotes',
        help='location of release notes YAML files',
    )
    subparsers = parser.add_subparsers(
        title='commands',
    )

    new_ = subparsers.add_parser(
        'new',
        help='create a new note',
    )
    new_.add_argument(
        'slug',
        help='descriptive title of note (keep it short)',
    )
    new_.set_defaults(func=create.create_cmd)

    list_ = subparsers.add_parser(
        'list',
        help='list notes files based on query arguments',
    )
    list_.add_argument(
        'reporoot',
        help='root of the git repository',
    )
    list_.add_argument(
        '--branch',
        help=('the branch of the git repository to scan, ',
              'defaults to the checked out repo'),
    )
    list_.add_argument(
        '--version',
        default=[],
        action='append',
        help='the version(s) to include, defaults to all',
    )
    list_.set_defaults(func=lister.list_cmd)

    args = parser.parse_args()
    return args.func(args)
