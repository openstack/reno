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
import glob
import logging
import os.path
import warnings

from reno import config as reno_config
from reno import loader

LOG = logging.getLogger(__name__)


def lint_cmd(args: argparse.Namespace, conf: reno_config.Config) -> int:
    """Check some common mistakes"""
    warnings.warn(
        "The 'reno lint' command is deprecated and will be removed in a "
        "future release. Note validation is now performed automatically by "
        "the loader.",
        DeprecationWarning,
        stacklevel=2,
    )
    LOG.warning(
        "The 'reno lint' command is deprecated and will be removed in a "
        "future release. Note validation is now performed automatically by "
        "the loader."
    )
    LOG.debug('starting lint')
    conf.override(strict=True)
    notesdir = os.path.join(conf.reporoot, conf.notespath)
    notes = glob.glob(os.path.join(notesdir, '*.yaml'))

    error = 0
    allowed_section_names = [conf.prelude_section_name] + [
        s.name for s in conf.sections
    ]

    try:
        with loader.Loader(conf, ignore_cache=True) as ldr:
            for f in notes:
                LOG.debug('examining %s', f)
                try:
                    content = ldr.parse_note_file(f, None)
                except ValueError as e:
                    LOG.warning('%s', e)
                    error = 1
                    continue

                for section_name in content.keys():
                    if section_name not in allowed_section_names:
                        LOG.warning(
                            'unrecognized section name %s in %s',
                            section_name,
                            f,
                        )
                        error = 1
    except ValueError as e:
        LOG.warning('%s', e)
        error = 1

    return error
