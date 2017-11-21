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

from docutils import nodes
from docutils.parsers import rst
from docutils.statemachine import ViewList

from sphinx.util.nodes import nested_parse_with_titles

from reno import config
import six


def _multi_line_string(s, indent=''):
    output_lines = s.splitlines()
    if not output_lines[0].strip():
        output_lines = output_lines[1:]
    for l in output_lines:
        yield indent + l


def _format_option_help(options):
    "Produce RST lines for the configuration options."
    for opt in options:
        yield '``{}``'.format(opt.name)
        for l in _multi_line_string(opt.help, '  '):
            yield l
        yield ''
        if isinstance(opt.default, six.string_types) and '\n' in opt.default:
            # Multi-line string
            yield '  Defaults to'
            yield ''
            yield '  ::'
            yield ''
            for l in _multi_line_string(opt.default, '    '):
                yield l
        else:
            yield '  Defaults to ``{!r}``'.format(opt.default)
        yield ''


class ShowConfigDirective(rst.Directive):

    option_spec = {}

    has_content = True

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        result = ViewList()
        source_name = '<' + __name__ + '>'
        for line in _format_option_help(config._OPTIONS):
            app.info(line)
            result.append(line, source_name)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)

        return node.children


def setup(app):
    app.add_directive('show-reno-config', ShowConfigDirective)
