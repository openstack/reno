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


def _indent_for_list(text, prefix='  '):
    """Indent some text to make it work as a list entry.

    Indent all lines except the first with the prefix.
    """
    lines = text.splitlines()
    return '\n'.join([lines[0]] + [
        prefix + l
        for l in lines[1:]
    ]) + '\n'


def format_report(loader, config, versions_to_include, title=None,
                  show_source=True):
    report = []
    if title:
        report.append('=' * len(title))
        report.append(title)
        report.append('=' * len(title))
        report.append('')

    # Read all of the notes files.
    file_contents = {}
    for version in versions_to_include:
        for filename, sha in loader[version]:
            body = loader.parse_note_file(filename, sha)
            file_contents[filename] = body

    for version in versions_to_include:
        report.append(version)
        report.append('=' * len(version))
        report.append('')

        # Add the preludes.
        notefiles = loader[version]
        for n, sha in notefiles:
            if 'prelude' in file_contents[n]:
                if show_source:
                    report.append('.. %s @ %s\n' % (n, sha))
                report.append(file_contents[n]['prelude'])
                report.append('')

        for section_name, section_title in config.sections:
            notes = [
                (n, fn, sha)
                for fn, sha in notefiles
                if file_contents[fn].get(section_name)
                for n in file_contents[fn].get(section_name, [])
            ]
            if notes:
                report.append(section_title)
                report.append('-' * len(section_title))
                report.append('')
                for n, fn, sha in notes:
                    if show_source:
                        report.append('.. %s @ %s\n' % (fn, sha))
                    report.append('- %s' % _indent_for_list(n))
                report.append('')

    return '\n'.join(report)
