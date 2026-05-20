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

import collections.abc

from docutils import nodes
from docutils.parsers import rst
from docutils.statemachine import ViewList
import sphinx.application
from sphinx.util import logging
from sphinx.util.nodes import nested_parse_with_titles

from reno import config

LOG = logging.getLogger(__name__)


def _multi_line_string(
    s: str, indent: str = ''
) -> collections.abc.Generator[str, None, None]:
    output_lines = s.splitlines()
    if not output_lines[0].strip():
        output_lines = output_lines[1:]
    for x in output_lines:
        yield indent + x


def _format_option_help(
    options: list[config.Opt],
) -> collections.abc.Generator[str, None, None]:
    "Produce RST lines for the configuration options."
    for opt in sorted(options, key=lambda opt: opt.name):
        yield f'``{opt.name}``'
        for x in _multi_line_string(opt.help, '  '):
            yield x
        yield ''
        if isinstance(opt.default, str) and '\n' in opt.default:
            # Multi-line string
            yield '  Defaults to'
            yield ''
            yield '  ::'
            yield ''
            for x in _multi_line_string(opt.default, '    '):
                yield x
        else:
            yield f'  Defaults to ``{opt.default!r}``'
        yield ''


class ShowConfigDirective(rst.Directive):
    option_spec = {}
    has_content = True

    def run(self) -> list[nodes.Node]:
        result: ViewList[str] = ViewList()
        source_name = '<' + __name__ + '>'
        for line in _format_option_help(config._OPTIONS):
            LOG.info(line)
            result.append(line, source_name)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)

        return node.children


def setup(app: sphinx.application.Sphinx) -> None:
    app.add_directive('show-reno-config', ShowConfigDirective)
