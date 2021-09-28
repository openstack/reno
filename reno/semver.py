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

from packaging import version

from reno import loader

LOG = logging.getLogger(__name__)


def compute_next_version(conf):
    "Compute the next semantic version based on the available release notes."
    LOG.debug('starting semver-next')
    with loader.Loader(conf, ignore_cache=True) as ldr:
        LOG.debug('known versions: %s', ldr.versions)

        # We want to include any notes in the local working directory or
        # in any commits that came after the last tag. We should never end
        # up with more than 2 entries in to_include.
        to_include = []
        for to_consider in ldr.versions:
            if to_consider == '*working-copy*':
                to_include.append(to_consider)
                continue

            # This check relies on PEP 440 versioning
            parsed = version.Version(to_consider)
            if parsed.post:
                to_include.append(to_consider)
                continue

            break

        # If we found no commits then we're sitting on a real tag and
        # there is nothing to do to update the version.
        if not to_include:
            LOG.debug('found no staged notes and no post-release commits')
            return ldr.versions[0]

        LOG.debug('including notes from %s', to_include)

        candidate_bases = to_include[:]
        if candidate_bases[0] == '*working-copy*':
            candidate_bases = candidate_bases[1:]

        if not candidate_bases:
            # We have a real tag and some locally modified files. Use the
            # real tag as the basis of the next version.
            base_version = version.Version(ldr.versions[1])
        else:
            base_version = version.Version(candidate_bases[0])

        LOG.debug('base version %s', base_version)

        inc_minor = False
        inc_patch = False

        for ver in to_include:
            for filename, sha in ldr[ver]:
                notes = ldr.parse_note_file(filename, sha)

                for section in conf.semver_major:
                    if notes.get(section, []):
                        LOG.debug('found breaking change in %r section of %s',
                                  section, filename)
                        return '{}.0.0'.format(base_version.major + 1)

                for section in conf.semver_minor:
                    if notes.get(section, []):
                        LOG.debug('found feature in %r section of %s',
                                  section, filename)
                        inc_minor = True
                        break

                for section in conf.semver_patch:
                    if notes.get(section, []):
                        LOG.debug('found bugfix in %r section of %s',
                                  section, filename)
                        inc_patch = True
                        break

    major = base_version.major
    minor = base_version.minor
    patch = base_version.micro

    if inc_patch:
        patch += 1

    if inc_minor:
        minor += 1
        patch = 0

    return '{}.{}.{}'.format(major, minor, patch)


def semver_next_cmd(args, conf):
    "Calculate next semantic version number"
    print(compute_next_version(conf))
    return 0
