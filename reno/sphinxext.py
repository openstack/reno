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

import logging
import os.path

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils import statemachine
from sphinx.util.nodes import nested_parse_with_titles

from dulwich import repo
from reno import config
from reno import defaults
from reno import formatter
from reno import loader


class ReleaseNotesDirective(rst.Directive):

    has_content = True

    option_spec = {
        'branch': directives.unchanged,
        'reporoot': directives.unchanged,
        'relnotessubdir': directives.unchanged,
        'notesdir': directives.unchanged,
        'version': directives.unchanged,
        'collapse-pre-releases': directives.flag,
        'earliest-version': directives.unchanged,
        'stop-at-branch-base': directives.flag,
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
        # When building on RTD.org the root directory may not be
        # the current directory, so look for it.
        reporoot = repo.Repo.discover(reporoot).path
        relnotessubdir = self.options.get('relnotessubdir',
                                          defaults.RELEASE_NOTES_SUBDIR)
        conf = config.Config(reporoot, relnotessubdir)
        opt_overrides = {}
        if 'notesdir' in self.options:
            opt_overrides['notesdir'] = self.options.get('notesdir')
        version_opt = self.options.get('version')
        # FIXME(dhellmann): Force these flags True for now and figure
        # out how Sphinx passes a "false" flag later.
        # 'collapse-pre-releases' in self.options
        opt_overrides['collapse_pre_releases'] = True
        # Only stop at the branch base if we have not been told
        # explicitly which versions to include.
        opt_overrides['stop_at_branch_base'] = (version_opt is None)
        if 'earliest-version' in self.options:
            opt_overrides['earliest_version'] = self.options.get(
                'earliest-version')
        if branch:
            opt_overrides['branch'] = branch
        conf.override(**opt_overrides)

        notesdir = os.path.join(relnotessubdir, conf.notesdir)
        info('scanning %s for %s release notes' %
             (os.path.join(conf.reporoot, notesdir),
              branch or 'current branch'))

        ldr = loader.Loader(conf)
        if version_opt is not None:
            versions = [
                v.strip()
                for v in version_opt.split(',')
            ]
        else:
            versions = ldr.versions
        info('got versions %s' % (versions,))
        text = formatter.format_report(
            ldr,
            conf,
            versions,
            title=title,
        )
        source_name = '<%s %s>' % (__name__, branch or 'current branch')
        result = statemachine.ViewList()
        for line in text.splitlines():
            result.append(line, source_name)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.add_directive('release-notes', ReleaseNotesDirective)

    logging.basicConfig(
        level=logging.INFO,
        format='[%(name)s] %(message)s',
    )
