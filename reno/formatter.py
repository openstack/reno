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


def _indent_for_list(text, prefix='  '):
    """Indent some text to make it work as a list entry.

    Indent all lines except the first with the prefix.
    """
    lines = text.splitlines()
    return '\n'.join([lines[0]] + [
        prefix + l
        for l in lines[1:]
    ]) + '\n'


def _anchor(version_title, title, branch):
    title = title or 'relnotes'
    return '.. _{title}_{version_title}{branch}:'.format(
        title=title,
        version_title=version_title,
        branch=('_' + branch.replace('/', '_') if branch else ''),
    )


def _section_anchor(section_title, version_title, title, branch):
    # Get the title and remove the trailing :
    title = _anchor(version_title, title, branch)[:-1]
    return "{title}_{section_title}:".format(
        title=title,
        section_title=section_title,
    )


def format_report(loader, config, versions_to_include, title=None,
                  show_source=True, branch=None):
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
        if '-' in version:
            # This looks like an "unreleased version".
            version_title = config.unreleased_version_title or version
        else:
            version_title = version
        report.append(_anchor(version_title, title, branch))
        report.append('')
        report.append(version_title)
        report.append('=' * len(version_title))
        report.append('')

        if config.add_release_date:
            report.append('Release Date: ' + loader.get_version_date(version))
            report.append('')

        # Add the preludes.
        notefiles = loader[version]
        prelude_name = config.prelude_section_name
        notefiles_with_prelude = [(n, sha) for n, sha in notefiles
                                  if prelude_name in file_contents[n]]
        if notefiles_with_prelude:
            prelude_title = prelude_name.replace('_', ' ').title()
            report.append(_section_anchor(
                prelude_title, version_title, title, branch))
            report.append('')
            report.append(prelude_title)
            report.append('-' * len(prelude_name))
            report.append('')

        for n, sha in notefiles_with_prelude:
            if show_source:
                report.append('.. %s @ %s\n' % (n, sha))
            report.append(file_contents[n][prelude_name])
            report.append('')

        # Add other sections.
        for section_name, section_title in config.sections:
            notes = [
                (n, fn, sha)
                for fn, sha in notefiles
                if file_contents[fn].get(section_name)
                for n in file_contents[fn].get(section_name, [])
            ]
            if notes:
                report.append(_section_anchor(
                    section_title, version_title, title, branch))
                report.append('')
                report.append(section_title)
                report.append('-' * len(section_title))
                report.append('')
                for n, fn, sha in notes:
                    if show_source:
                        report.append('.. %s @ %s\n' % (fn, sha))
                    report.append('- %s' % _indent_for_list(n))
                report.append('')

    return '\n'.join(report)
