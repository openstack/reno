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

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils import statemachine
from dulwich import repo
from sphinx.util import logging
from sphinx.util.nodes import nested_parse_with_titles

import reno
from reno import config
from reno import defaults
from reno import formatter
from reno import loader

LOG = logging.getLogger(__name__)


class ReleaseNotesDirective(rst.Directive):

    has_content = True

    # FIXME(dhellmann): We should be able to build this information
    # from the configuration options so we don't have to edit it
    # manually when we add new options.
    option_spec = {
        'branch': directives.unchanged,
        'reporoot': directives.unchanged,
        'relnotessubdir': directives.unchanged,
        'notesdir': directives.unchanged,
        'version': directives.unchanged,
        'collapse-pre-releases': directives.flag,
        'earliest-version': directives.unchanged,
        'stop-at-branch-base': directives.flag,
        'ignore-notes': directives.unchanged,
        'unreleased-version-title': directives.unchanged,
    }

    def _find_reporoot(self, reporoot_opt, relnotessubdir_opt):
        """Find root directory of project."""
        reporoot = os.path.abspath(reporoot_opt)
        # When building on RTD.org the root directory may not be
        # the current directory, so look for it.
        try:
            return repo.Repo.discover(reporoot).path
        except Exception:
            pass

        for root in ('.', '..', '../..'):
            if os.path.exists(os.path.join(root, relnotessubdir_opt)):
                return root

        raise Exception(
            'Could not discover root directory; tried: %s' % ', '.join([
                os.path.abspath(root) for root in ('.', '..', '../..')
            ])
        )

    def run(self):
        title = ' '.join(self.content)
        branch = self.options.get('branch')
        relnotessubdir = self.options.get(
            'relnotessubdir', defaults.RELEASE_NOTES_SUBDIR,
        )
        reporoot = self._find_reporoot(
            self.options.get('reporoot', '.'), relnotessubdir,
        )
        ignore_notes = [
            name.strip()
            for name in self.options.get('ignore-notes', '').split(',')
        ]
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
        if 'unreleased-version-title' in self.options:
            opt_overrides['unreleased_version_title'] = self.options.get(
                'unreleased-version-title')

        if branch:
            opt_overrides['branch'] = branch
        if ignore_notes:
            opt_overrides['ignore_notes'] = ignore_notes
        conf.override(**opt_overrides)

        notesdir = os.path.join(relnotessubdir, conf.notesdir)
        LOG.info('scanning %s for %s release notes' % (
                 os.path.join(conf.reporoot, notesdir),
                 branch or 'current branch'))

        ldr = loader.Loader(conf)
        if version_opt is not None:
            versions = [
                v.strip()
                for v in version_opt.split(',')
            ]
        else:
            versions = ldr.versions
        LOG.info('got versions %s' % (versions,))
        text = formatter.format_report(
            ldr,
            conf,
            versions,
            title=title,
            branch=branch,
        )
        source_name = '<%s %s>' % (__name__, branch or 'current branch')
        result = statemachine.ViewList()
        for line_num, line in enumerate(text.splitlines(), 1):
            LOG.debug('%4d: %s', line_num, line)
            result.append(line, source_name, line_num)

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.add_directive('release-notes', ReleaseNotesDirective)
    metadata_dict = {
        'version': reno.__version__,
        'parallel_read_safe': True
    }
    return metadata_dict
