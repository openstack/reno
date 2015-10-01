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
import os.path
import re
import subprocess

from reno import create
from reno import scanner
from reno.tests import base
from reno import utils

import fixtures
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
        for line in gnupg_version[0].split('\n'):
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
        # if gnupg_version[0] == 1:
        #     gnupg_random = '--quick-random'
        # elif gnupg_version[0] >= 2:
        #     gnupg_random = '--debug-quick-random'
        # else:
        #     gnupg_random = ''
        subprocess.check_call(
            ['gpg', '--gen-key', '--batch',
             # gnupg_random,
             config_file],
            cwd=tempdir.path)


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
             '2.0.0-1': [],
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
             '2.0.0-1': [],
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
             '2.0.0-1': [],
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
             '2.0.0-1': [],
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
             '2.0.0-1': [],
             },
            results,
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
