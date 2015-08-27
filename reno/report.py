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

from __future__ import print_function

from reno import scanner
from reno import utils

import yaml


_SECTION_ORDER = [
    ('features', 'New Features'),
    ('issues', 'Known Issues'),
    ('upgrade', 'Upgrade Notes'),
    ('critical', 'Critical Issues'),
    ('security', 'Security Issues'),
    ('fixes', 'Bug Fixes'),
    ('other', 'Other Notes'),
]


def format_report(scanner_output, versions_to_include):
    report = []
    report.append('=============')
    report.append('Release Notes')
    report.append('=============')
    report.append('')

    # Read all of the notes files.
    file_contents = {}
    for version in versions_to_include:
        for filename in scanner_output[version]:
            with open(filename, 'r') as f:
                y = yaml.safe_load(f)
                file_contents[filename] = y

    for version in versions_to_include:
        report.append(version)
        report.append('=' * len(version))
        report.append('')

        # Add the preludes.
        notefiles = scanner_output[version]
        for n in notefiles:
            if 'prelude' in file_contents[n]:
                report.append(file_contents[n]['prelude'])
                report.append('')

        for section_name, section_title in _SECTION_ORDER:
            notes = [
                n
                for fn in notefiles
                for n in file_contents[fn].get(section_name, [])
            ]
            if notes:
                report.append(section_title)
                report.append('-' * len(section_title))
                report.append('')
                for n in notes:
                    report.append('- %s' % n)
                report.append('')

    return '\n'.join(report)


def report_cmd(args):
    "Generates a release notes report"
    reporoot = args.reporoot.rstrip('/') + '/'
    notesdir = utils.get_notes_dir(args)
    notes = scanner.get_notes_by_version(reporoot, notesdir)
    if args.version:
        versions = args.version
    else:
        versions = notes.keys()
    text = format_report(notes, versions)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(text)
    else:
        print(text)
    return
