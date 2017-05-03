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
import logging
import sys

from reno import cache
from reno import config
from reno import create
from reno import defaults
from reno import linter
from reno import lister
from reno import report

_query_args = [
    (('--version',),
     dict(default=[],
          action='append',
          help='the version(s) to include, defaults to all')),
    (('--branch',),
     dict(default=config.Config.get_default('branch'),
          help='the branch to scan, defaults to the current')),
    (('--collapse-pre-releases',),
     dict(action='store_true',
          default=config.Config.get_default('collapse_pre_releases'),
          help='combine pre-releases with their final release')),
    (('--no-collapse-pre-releases',),
     dict(action='store_false',
          dest='collapse_pre_releases',
          help='show pre-releases separately')),
    (('--earliest-version',),
     dict(default=None,
          help='stop when this version is reached in the history')),
    (('--ignore-cache',),
     dict(default=False,
          action='store_true',
          help='if there is a cache file present, do not use it')),
    (('--stop-at-branch-base',),
     dict(action='store_true',
          default=True,
          dest='stop_at_branch_base',
          help='stop scanning when the branch meets master')),
    (('--no-stop-at-branch-base',),
     dict(action='store_false',
          dest='stop_at_branch_base',
          help='do not stop scanning when the branch meets master')),
]


def _build_query_arg_group(parser):
    group = parser.add_argument_group('query')
    for args, kwds in _query_args:
        group.add_argument(*args, **kwds)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--verbose',
        dest='verbosity',
        default=logging.INFO,
        help='produce more output',
        action='store_const',
        const=logging.DEBUG,
    )
    parser.add_argument(
        '-q', '--quiet',
        dest='verbosity',
        action='store_const',
        const=logging.WARN,
        help='produce less output',
    )
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
        '--edit',
        action='store_true',
        help='Edit note after its creation (require EDITOR env variable)',
    )
    do_new.add_argument(
        'slug',
        help='descriptive title of note (keep it short)',
    )
    do_new.add_argument(
        'reporoot',
        default='.',
        nargs='?',
        help='root of the git repository',
    )
    do_new.set_defaults(func=create.create_cmd)

    do_list = subparsers.add_parser(
        'list',
        help='list notes files based on query arguments',
    )
    _build_query_arg_group(do_list)
    do_list.add_argument(
        'reporoot',
        default='.',
        nargs='?',
        help='root of the git repository',
    )
    do_list.set_defaults(func=lister.list_cmd)

    do_report = subparsers.add_parser(
        'report',
        help='generate release notes report',
    )
    do_report.add_argument(
        'reporoot',
        default='.',
        nargs='?',
        help='root of the git repository',
    )
    do_report.add_argument(
        '--output', '-o',
        default=None,
        help='output filename, defaults to stdout',
    )
    do_report.add_argument(
        '--no-show-source',
        dest='show_source',
        default=True,
        action='store_false',
        help='do not show the source for notes',
    )
    do_report.add_argument(
        '--title',
        default='Release Notes',
        help='set the main title of the generated report',
    )
    _build_query_arg_group(do_report)
    do_report.set_defaults(func=report.report_cmd)

    do_cache = subparsers.add_parser(
        'cache',
        help='generate release notes cache',
    )
    do_cache.add_argument(
        'reporoot',
        default='.',
        nargs='?',
        help='root of the git repository',
    )
    do_cache.add_argument(
        '--output', '-o',
        default=None,
        help=('output filename, '
              'defaults to the cache file within the notesdir, '
              'use "-" for stdout'),
    )
    _build_query_arg_group(do_cache)
    do_cache.set_defaults(func=cache.cache_cmd)

    do_linter = subparsers.add_parser(
        'lint',
        help='check some common mistakes',
    )
    do_linter.add_argument(
        'reporoot',
        default='.',
        nargs='?',
        help='root of the git repository',
    )
    do_linter.set_defaults(func=linter.lint_cmd)

    args = parser.parse_args(argv)
    conf = config.Config(args.reporoot, args.relnotesdir)
    conf.override_from_parsed_args(args)

    logging.basicConfig(
        level=args.verbosity,
        format='%(message)s',
    )

    return args.func(args, conf)
