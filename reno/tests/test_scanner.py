# -*- coding: utf-8 -*-

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

import itertools
import logging
import os.path
import re
import subprocess
import textwrap

from reno import create
from reno import scanner
from reno.tests import base
from reno import utils

import fixtures
import mock
from testtools.content import text_content


_SETUP_TEMPLATE = """
import setuptools
try:
    import multiprocessing  # noqa
except ImportError:
    pass

setuptools.setup(
    setup_requires=['pbr'],
    pbr=True)
"""

_CFG_TEMPLATE = """
[metadata]
name = testpkg
summary = Test Package

[files]
packages =
    testpkg
"""


class GPGKeyFixture(fixtures.Fixture):
    """Creates a GPG key for testing.

    It's recommended that this be used in concert with a unique home
    directory.
    """

    def setUp(self):
        super(GPGKeyFixture, self).setUp()
        tempdir = self.useFixture(fixtures.TempDir())
        gnupg_version_re = re.compile('^gpg\s.*\s([\d+])\.([\d+])\.([\d+])')
        gnupg_version = utils.check_output(['gpg', '--version'],
                                           cwd=tempdir.path)
        for line in gnupg_version.split('\n'):
            gnupg_version = gnupg_version_re.match(line)
            if gnupg_version:
                gnupg_version = (int(gnupg_version.group(1)),
                                 int(gnupg_version.group(2)),
                                 int(gnupg_version.group(3)))
                break
        else:
            if gnupg_version is None:
                gnupg_version = (0, 0, 0)
        config_file = tempdir.path + '/key-config'
        f = open(config_file, 'wt')
        try:
            if gnupg_version[0] == 2 and gnupg_version[1] >= 1:
                f.write("""
                %no-protection
                %transient-key
                """)
            f.write("""
            %no-ask-passphrase
            Key-Type: RSA
            Name-Real: Example Key
            Name-Comment: N/A
            Name-Email: example@example.com
            Expire-Date: 2d
            Preferences: (setpref)
            %commit
            """)
        finally:
            f.close()
        # Note that --quick-random (--debug-quick-random in GnuPG 2.x)
        # does not have a corresponding preferences file setting and
        # must be passed explicitly on the command line instead
        if gnupg_version[0] == 1:
            gnupg_random = '--quick-random'
        elif gnupg_version[0] >= 2:
            gnupg_random = '--debug-quick-random'
        else:
            gnupg_random = ''
        cmd = ['gpg', '--gen-key', '--batch']
        if gnupg_random:
            cmd.append(gnupg_random)
        cmd.append(config_file)
        subprocess.check_call(cmd, cwd=tempdir.path)


class Base(base.TestCase):

    def _run_git(self, *args):
        return utils.check_output(
            ['git'] + list(args),
            cwd=self.reporoot,
        )

    def _git_setup(self):
        os.makedirs(self.reporoot)
        self._run_git('init', '.')
        self._run_git('config', '--local', 'user.email', 'example@example.com')
        self._run_git('config', '--local', 'user.name', 'reno developer')
        self._run_git('config', '--local', 'user.signingkey',
                      'example@example.com')

    def _git_commit(self, message='commit message'):
        self._run_git('add', '.')
        self._run_git('commit', '-m', message)

    def _add_other_file(self, name):
        with open(os.path.join(self.reporoot, name), 'w') as f:
            f.write('adding %s\n' % name)
        self._git_commit('add %s' % name)

    def _add_notes_file(self, slug='slug', commit=True, legacy=False):
        n = self.get_note_num()
        if legacy:
            basename = '%016x-%s.yaml' % (n, slug)
        else:
            basename = '%s-%016x.yaml' % (slug, n)
        filename = os.path.join(self.reporoot, 'releasenotes', 'notes',
                                basename)
        create._make_note_file(filename)
        self._git_commit('add %s' % basename)
        return os.path.join('releasenotes', 'notes', basename)

    def _make_python_package(self):
        setup_name = os.path.join(self.reporoot, 'setup.py')
        with open(setup_name, 'w') as f:
            f.write(_SETUP_TEMPLATE)
        cfg_name = os.path.join(self.reporoot, 'setup.cfg')
        with open(cfg_name, 'w') as f:
            f.write(_CFG_TEMPLATE)
        pkgdir = os.path.join(self.reporoot, 'testpkg')
        os.makedirs(pkgdir)
        init = os.path.join(pkgdir, '__init__.py')
        with open(init, 'w') as f:
            f.write("Test package")
        self._git_commit('add test package')

    def setUp(self):
        super(Base, self).setUp()
        self.logger = self.useFixture(
            fixtures.FakeLogger(
                format='%(levelname)8s %(name)s %(message)s',
                level=logging.DEBUG,
                nuke_handlers=True,
            )
        )
        # Older git does not have config --local, so create a temporary home
        # directory to permit using git config --global without stepping on
        # developer configuration.
        self.useFixture(fixtures.TempHomeDir())
        self.useFixture(GPGKeyFixture())
        self.useFixture(fixtures.NestedTempfile())
        self.temp_dir = self.useFixture(fixtures.TempDir()).path
        self.reporoot = os.path.join(self.temp_dir, 'reporoot')
        self.notesdir = os.path.join(self.reporoot,
                                     'releasenotes',
                                     'notes',
                                     )
        self._git_setup()
        self._counter = itertools.count(1)
        self.get_note_num = lambda: next(self._counter)


class BasicTest(Base):

    def test_non_python_no_tags(self):
        filename = self._add_notes_file()
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'0.0.0': [filename]},
            results,
        )

    def test_python_no_tags(self):
        self._make_python_package()
        filename = self._add_notes_file()
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'0.0.0': [filename]},
            results,
        )

    def test_note_before_tag(self):
        filename = self._add_notes_file()
        self._add_other_file('not-a-release-note.txt')
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': [filename]},
            results,
        )

    def test_note_commit_tagged(self):
        filename = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': [filename]},
            results,
        )

    def test_note_commit_after_tag(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        filename = self._add_notes_file()
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0-1': [filename]},
            results,
        )

    def test_other_commit_after_tag(self):
        filename = self._add_notes_file()
        self._add_other_file('ignore-1.txt')
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        self._add_other_file('ignore-2.txt')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': [filename]},
            results,
        )

    def test_multiple_notes_after_tag(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file()
        f2 = self._add_notes_file()
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0-2': [f1, f2]},
            results,
        )

    def test_multiple_notes_within_tag(self):
        self._make_python_package()
        f1 = self._add_notes_file(commit=False)
        f2 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': [f1, f2]},
            results,
        )

    def test_multiple_tags(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        f2 = self._add_notes_file()
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f1],
             '2.0.0-1': [f2],
             },
            results,
        )

    def test_rename_file(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        f2 = f1.replace('slug1', 'slug2')
        self._run_git('mv', f1, f2)
        self._git_commit('rename note file')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f2],
             },
            results,
        )

    def test_rename_file_sort_earlier(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        f2 = f1.replace('slug1', 'slug0')
        self._run_git('mv', f1, f2)
        self._git_commit('rename note file')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f2],
             },
            results,
        )

    def test_edit_file(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        with open(os.path.join(self.reporoot, f1), 'w') as f:
            f.write('---\npreamble: new contents for file')
        self._git_commit('edit note file')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f1],
             },
            results,
        )

    def test_legacy_file(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file('slug1', legacy=True)
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        f2 = f1.replace('slug1', 'slug2')
        self._run_git('mv', f1, f2)
        self._git_commit('rename note file')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f2],
             },
            results,
        )

    def test_rename_legacy_file_to_new(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file('slug1', legacy=True)
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        # Rename the file with the new convention of placing the UUID
        # after the slug instead of before.
        f2 = f1.replace('0000000000000001-slug1',
                        'slug1-0000000000000001')
        self._run_git('mv', f1, f2)
        self._git_commit('rename note file')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f2],
             },
            results,
        )

    def test_limit_by_earliest_version(self):
        self._make_python_package()
        self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f2 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'middle tag', '2.0.0')
        f3 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'last tag', '3.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
            earliest_version='2.0.0',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f2],
             '3.0.0': [f3],
             },
            results,
        )

    def test_delete_file(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file('slug1')
        f2 = self._add_notes_file('slug2')
        self._run_git('rm', f1)
        self._git_commit('remove note file')
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f2],
             },
            results,
        )

    def test_rename_then_delete_file(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        f1 = self._add_notes_file('slug1')
        f2 = f1.replace('slug1', 'slug2')
        self._run_git('mv', f1, f2)
        self._git_commit('rename note file')
        self._run_git('rm', f2)
        self._git_commit('remove note file')
        f3 = self._add_notes_file('slug3')
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'2.0.0': [f3],
             },
            results,
        )


class PreReleaseTest(Base):

    def test_alpha(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0.0a1')
        f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0.0a2')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0.0a2': [f1],
             },
            results,
        )

    def test_beta(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0.0b1')
        f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0.0b2')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0.0b2': [f1],
             },
            results,
        )

    def test_release_candidate(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0.0rc1')
        f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0.0rc2')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0.0rc2': [f1],
             },
            results,
        )

    def test_collapse(self):
        files = []
        self._make_python_package()
        files.append(self._add_notes_file('slug1'))
        self._run_git('tag', '-s', '-m', 'alpha tag', '1.0.0.0a1')
        files.append(self._add_notes_file('slug2'))
        self._run_git('tag', '-s', '-m', 'beta tag', '1.0.0.0b1')
        files.append(self._add_notes_file('slug3'))
        self._run_git('tag', '-s', '-m', 'release candidate tag', '1.0.0.0rc1')
        files.append(self._add_notes_file('slug4'))
        self._run_git('tag', '-s', '-m', 'full release tag', '1.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
            collapse_pre_releases=True,
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': files,
             },
            results,
        )

    def test_collapse_without_full_release(self):
        self._make_python_package()
        f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'alpha tag', '1.0.0.0a1')
        f2 = self._add_notes_file('slug2')
        self._run_git('tag', '-s', '-m', 'beta tag', '1.0.0.0b1')
        f3 = self._add_notes_file('slug3')
        self._run_git('tag', '-s', '-m', 'release candidate tag', '1.0.0.0rc1')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
            collapse_pre_releases=True,
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0.0a1': [f1],
             '1.0.0.0b1': [f2],
             '1.0.0.0rc1': [f3],
             },
            results,
        )

    def test_collapse_without_notes(self):
        self._make_python_package()
        self._run_git('tag', '-s', '-m', 'earlier tag', '0.1.0')
        f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'alpha tag', '1.0.0.0a1')
        f2 = self._add_notes_file('slug2')
        self._run_git('tag', '-s', '-m', 'beta tag', '1.0.0.0b1')
        f3 = self._add_notes_file('slug3')
        self._run_git('tag', '-s', '-m', 'release candidate tag', '1.0.0.0rc1')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
            collapse_pre_releases=True,
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0.0a1': [f1],
             '1.0.0.0b1': [f2],
             '1.0.0.0rc1': [f3],
             },
            results,
        )


class MergeCommitTest(Base):

    def test_1(self):
        # Create changes on master and in the branch
        # in order so the history is "normal"
        n1 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        self._run_git('checkout', '-b', 'test_merge_commit')
        n2 = self._add_notes_file()
        self._run_git('checkout', 'master')
        self._add_other_file('ignore-1.txt')
        self._run_git('merge', '--no-ff', 'test_merge_commit')
        self._add_other_file('ignore-2.txt')
        self._run_git('tag', '-s', '-m', 'second tag', '2.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': [n1],
             '2.0.0': [n2]},
            results,
        )
        self.assertEqual(
            ['2.0.0', '1.0.0'],
            list(raw_results.keys()),
        )

    def test_2(self):
        # Create changes on the branch before the tag into which it is
        # actually merged.
        self._add_other_file('ignore-0.txt')
        self._run_git('checkout', '-b', 'test_merge_commit')
        n1 = self._add_notes_file()
        self._run_git('checkout', 'master')
        n2 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        self._add_other_file('ignore-1.txt')
        self._run_git('merge', '--no-ff', 'test_merge_commit')
        self._add_other_file('ignore-2.txt')
        self._run_git('tag', '-s', '-m', 'second tag', '2.0.0')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': [n2],
             '2.0.0': [n1]},
            results,
        )
        self.assertEqual(
            ['2.0.0', '1.0.0'],
            list(raw_results.keys()),
        )

    def test_3(self):
        # Create changes on the branch before the tag into which it is
        # actually merged, with another tag in between the time of the
        # commit and the time of the merge. This should reflect the
        # order of events described in bug #1522153.
        self._add_other_file('ignore-0.txt')
        self._run_git('checkout', '-b', 'test_merge_commit')
        n1 = self._add_notes_file()
        self._run_git('checkout', 'master')
        n2 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        self._add_other_file('ignore-1.txt')
        self._run_git('tag', '-s', '-m', 'second tag', '1.1.0')
        self._run_git('merge', '--no-ff', 'test_merge_commit')
        self._add_other_file('ignore-2.txt')
        self._run_git('tag', '-s', '-m', 'third tag', '2.0.0')
        self._add_other_file('ignore-3.txt')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        # Since the 1.1.0 tag has no notes files, it does not appear
        # in the output. It's only there to trigger the bug as it was
        # originally reported.
        self.assertEqual(
            {'1.0.0': [n2],
             '2.0.0': [n1]},
            results,
        )
        self.assertEqual(
            ['2.0.0', '1.0.0'],
            list(raw_results.keys()),
        )

    def test_4(self):
        # Create changes on the branch before the tag into which it is
        # actually merged, with another tag in between the time of the
        # commit and the time of the merge. This should reflect the
        # order of events described in bug #1522153.
        self._add_other_file('ignore-0.txt')
        self._run_git('checkout', '-b', 'test_merge_commit')
        n1 = self._add_notes_file()
        self._run_git('checkout', 'master')
        n2 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        self._add_other_file('ignore-1.txt')
        n3 = self._add_notes_file()
        self._run_git('tag', '-s', '-m', 'second tag', '1.1.0')
        self._run_git('merge', '--no-ff', 'test_merge_commit')
        self._add_other_file('ignore-2.txt')
        self._run_git('tag', '-s', '-m', 'third tag', '2.0.0')
        self._add_other_file('ignore-3.txt')
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {'1.0.0': [n2],
             '1.1.0': [n3],
             '2.0.0': [n1]},
            results,
        )
        self.assertEqual(
            ['2.0.0', '1.1.0', '1.0.0'],
            list(raw_results.keys()),
        )


class UniqueIdTest(Base):

    def test_legacy(self):
        uid = scanner._get_unique_id(
            'releasenotes/notes/0000000000000001-slug1.yaml'
        )
        self.assertEqual('0000000000000001', uid)

    def test_modern(self):
        uid = scanner._get_unique_id(
            'releasenotes/notes/slug1-0000000000000001.yaml'
        )
        self.assertEqual('0000000000000001', uid)


class BranchTest(Base):

    def setUp(self):
        super(BranchTest, self).setUp()
        self._make_python_package()
        self.f1 = self._add_notes_file('slug1')
        self._run_git('tag', '-s', '-m', 'first tag', '1.0.0')
        self.f2 = self._add_notes_file('slug2')
        self._run_git('tag', '-s', '-m', 'first tag', '2.0.0')
        self._add_notes_file('slug3')
        self._run_git('tag', '-s', '-m', 'first tag', '3.0.0')

    def test_files_current_branch(self):
        self._run_git('checkout', '2.0.0')
        self._run_git('checkout', '-b', 'stable/2')
        f21 = self._add_notes_file('slug21')
        log_text = self._run_git('log')
        self.addDetail('git log', text_content(log_text))
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {
                '1.0.0': [self.f1],
                '2.0.0': [self.f2],
                '2.0.0-1': [f21],
            },
            results,
        )

    def test_files_stable_from_master(self):
        self._run_git('checkout', '2.0.0')
        self._run_git('checkout', '-b', 'stable/2')
        f21 = self._add_notes_file('slug21')
        self._run_git('checkout', 'master')
        log_text = self._run_git('log', '--pretty=%x00%H %d', '--name-only',
                                 'stable/2')
        self.addDetail('git log', text_content(log_text))
        raw_results = scanner.get_notes_by_version(
            self.reporoot,
            'releasenotes/notes',
            'stable/2',
        )
        results = {
            k: [f for (f, n) in v]
            for (k, v) in raw_results.items()
        }
        self.assertEqual(
            {
                '1.0.0': [self.f1],
                '2.0.0': [self.f2],
                '2.0.0-1': [f21],
            },
            results,
        )


class GetTagsParseTest(base.TestCase):

    EXPECTED = [
        '2.0.0',
        '1.8.1',
        '1.8.0',
        '1.7.1',
        '1.7.0',
        '1.6.0',
        '1.5.0',
        '1.4.0',
        '1.3.0',
        '1.2.0',
        '1.1.0',
        '1.0.0',
        '0.11.2',
        '0.11.1',
        '0.11.0',
        '0.10.1',
        '0.10.0',
        '0.9.0',
        '0.8.0',
        '0.7.1',
        '0.7.0',
        '0.6.0',
        '0.5.1',
        '0.5.0',
        '0.4.2',
        '0.4.1',
        '0.4.0',
        '0.3.2',
        '0.3.1',
        '0.3.0',
        '0.2.5',
        '0.2.4',
        '0.2.3',
        '0.2.2',
        '0.2.1',
        '0.2.0',
        '0.1.3',
        '0.1.2',
        '0.1.1',
        '0.1.0',
    ]

    def test_keystoneclient_ubuntu_1_9_1(self):
        # git 1.9.1 as it produces output on ubuntu for python-keystoneclient
        # git log --simplify-by-decoration --pretty="%d"
        tag_list_output = textwrap.dedent("""
         (HEAD, origin/master, origin/HEAD, gerrit/master, master)
         (apu/master)
         (tag: 2.0.0)
         (tag: 1.8.1)
         (tag: 1.8.0)
         (tag: 1.7.1)
         (tag: 1.7.0)
         (tag: 1.6.0)
         (tag: 1.5.0)
         (tag: 1.4.0)
         (uncap-requirements)
         (tag: 1.3.0)
         (tag: 1.2.0)
         (tag: 1.1.0)
         (tag: 1.0.0)
         (tag: 0.11.2)
         (tag: 0.11.1)
         (tag: 0.11.0)
         (tag: 0.10.1)
         (tag: 0.10.0)
         (tag: 0.9.0)
         (tag: 0.8.0)
         (tag: 0.7.1)
         (tag: 0.7.0)
         (tag: 0.6.0)
         (tag: 0.5.1)
         (tag: 0.5.0)
         (tag: 0.4.2)
         (tag: 0.4.1)
         (tag: 0.4.0)
         (tag: 0.3.2)
         (tag: 0.3.1)
         (tag: 0.3.0)
         (tag: 0.2.5)
         (tag: 0.2.4)
         (tag: 0.2.3)
         (tag: 0.2.2)
         (tag: 0.2.1)
         (tag: 0.2.0)

         (origin/feature/keystone-v3, gerrit/feature/keystone-v3)
         (tag: 0.1.3)
         (tag: 0.1.2)
         (tag: 0.1.1)
         (tag: 0.1.0)
         (tag: folsom-1)
         (tag: essex-rc1)
         (tag: essex-4)
         (tag: essex-3)
        """)
        with mock.patch('reno.utils.check_output') as co:
            co.return_value = tag_list_output
            actual = scanner._get_version_tags_on_branch('reporoot',
                                                         branch=None)
        self.assertEqual(self.EXPECTED, actual)

    def test_keystoneclient_rhel_1_7_1(self):
        # git 1.7.1 as it produces output on RHEL 6 for python-keystoneclient
        # git log --simplify-by-decoration --pretty="%d"
        tag_list_output = textwrap.dedent("""
         (HEAD, origin/master, origin/HEAD, master)
         (tag: 2.0.0)
         (tag: 1.8.1)
         (tag: 1.8.0)
         (tag: 1.7.1)
         (tag: 1.7.0)
         (tag: 1.6.0)
         (tag: 1.5.0)
         (tag: 1.4.0)
         (tag: 1.3.0)
         (tag: 1.2.0)
         (tag: 1.1.0)
         (tag: 1.0.0)
         (tag: 0.11.2)
         (tag: 0.11.1)
         (tag: 0.11.0)
         (tag: 0.10.1)
         (tag: 0.10.0)
         (tag: 0.9.0)
         (tag: 0.8.0)
         (tag: 0.7.1)
         (tag: 0.7.0)
         (tag: 0.6.0)
         (tag: 0.5.1)
         (tag: 0.5.0)
         (tag: 0.4.2)
         (tag: 0.4.1)
         (tag: 0.4.0)
         (tag: 0.3.2)
         (tag: 0.3.1)
         (tag: 0.3.0)
         (tag: 0.2.5)
         (tag: 0.2.4)
         (tag: 0.2.3)
         (tag: 0.2.2)
         (tag: 0.2.1)
         (tag: 0.2.0)
         (tag: 0.1.3)
         (0.1.2)
         (tag: 0.1.1)
         (0.1.0)
         (tag: folsom-1)
         (tag: essex-rc1)
         (essex-4)
         (essex-3)
        """)
        with mock.patch('reno.utils.check_output') as co:
            co.return_value = tag_list_output
            actual = scanner._get_version_tags_on_branch('reporoot',
                                                         branch=None)
        self.assertEqual(self.EXPECTED, actual)
