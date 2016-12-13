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

import os
import sys

import yaml

from reno import loader
from reno import scanner


def build_cache_db(conf, versions_to_include):
    s = scanner.Scanner(conf)
    notes = s.get_notes_by_version()

    # Default to including all versions returned by the scanner.
    if not versions_to_include:
        versions_to_include = list(notes.keys())

    # Build a cache data structure including the file contents as well
    # as the basic data returned by the scanner.
    file_contents = {}
    for version in versions_to_include:
        for filename, sha in notes[version]:
            body = s.get_file_at_commit(filename, sha)
            # We want to save the contents of the file, which is YAML,
            # inside another YAML file. That looks terribly ugly with
            # all of the escapes needed to format it properly as
            # embedded YAML, so parse the input and convert it to a
            # data structure that can be serialized cleanly.
            y = yaml.safe_load(body)
            file_contents[filename] = y

    cache = {
        'notes': [
            {'version': k, 'files': v}
            for k, v in notes.items()
        ],
        'file-contents': file_contents,
    }
    return cache


def write_cache_db(conf, versions_to_include,
                   outfilename=None):
    """Create a cache database file for the release notes data.

    Build the cache database from scanning the project history and
    write it to a file within the project.

    By default, the data is written to the same file the scanner will
    try to read when it cannot look at the git history. If outfilename
    is given and is '-' the data is written to stdout
    instead. Otherwise, if outfilename is given, the data overwrites
    the named file.

    Return the name of the file created, if any.

    """
    if outfilename == '-':
        stream = sys.stdout
        close_stream = False
    elif outfilename:
        stream = open(outfilename, 'w')
        close_stream = True
    else:
        outfilename = loader.get_cache_filename(conf.reporoot, conf.notespath)
        if not os.path.exists(os.path.dirname(outfilename)):
            os.makedirs(os.path.dirname(outfilename))
        stream = open(outfilename, 'w')
        close_stream = True
    try:
        cache = build_cache_db(
            conf,
            versions_to_include=versions_to_include,
        )
        yaml.safe_dump(
            cache,
            stream,
            allow_unicode=True,
            explicit_start=True,
            encoding='utf-8',
        )
    finally:
        if close_stream:
            stream.close()
    return outfilename


def cache_cmd(args, conf):
    "Generates a release notes cache"
    write_cache_db(
        conf=conf,
        versions_to_include=args.version,
        outfilename=args.output,
    )
    return
