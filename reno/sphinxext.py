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

import os.path

from reno import defaults
from reno import formatter
from reno import scanner

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles


class ReleaseNotesDirective(rst.Directive):

    has_content = True

    option_spec = {
        'branch': directives.unchanged,
        'reporoot': directives.unchanged,
        'relnotessubdir': directives.unchanged,
        'notesdir': directives.unchanged,
        'version': directives.unchanged,
    }

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        def info(msg):
            app.info('[reno] %s' % (msg,))

        title = ' '.join(self.content)
        branch = self.options.get('branch')
        reporoot_opt = self.options.get('reporoot', '.')
        reporoot = os.path.abspath(reporoot_opt)
        relnotessubdir = self.options.get('relnotessubdir',
                                          defaults.RELEASE_NOTES_SUBDIR)
        notessubdir = self.options.get('notesdir', defaults.NOTES_SUBDIR)
        version_opt = self.options.get('version')

        notesdir = os.path.join(relnotessubdir, notessubdir)
        info('scanning %s for %s release notes' %
             (os.path.join(reporoot, notesdir), branch or 'current branch'))

        notes = scanner.get_notes_by_version(reporoot, notesdir, branch)
        if version_opt is not None:
            versions = [
                v.strip()
                for v in version_opt.split(',')
            ]
        else:
            versions = notes.keys()
        text = formatter.format_report(
            reporoot,
            notes,
            versions,
            title=title,
        )
        source_name = '<' + __name__ + '>'
        result = ViewList()
        for line in text.splitlines():
            result.append(line, source_name)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.add_directive('release-notes', ReleaseNotesDirective)
