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
import os

from reno import linter
from reno.tests import test_scanner


class TestLinter(test_scanner.Base):
    def setUp(self):
        super().setUp()
        self.repo.add_file('README.txt')
        self.notesdir = os.path.join(self.reporoot, 'releasenotes', 'notes')
        os.makedirs(self.notesdir, exist_ok=True)
        self.args = argparse.Namespace()

    def _create_note(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.notesdir, filename)
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def test_lint_clean(self):
        self._create_note(
            'note-0000000000000001.yaml',
            'features:\n  - Clean feature note.\n',
        )
        self.assertEqual(0, linter.lint_cmd(self.args, self.c))

    def test_lint_unrecognized_section(self):
        self._create_note(
            'note-0000000000000001.yaml',
            'invalid_section:\n  - Invalid section.\n',
        )
        self.assertEqual(1, linter.lint_cmd(self.args, self.c))

    def test_lint_uid_collision(self):
        self._create_note(
            'note1-a1b2c3d4e5f67890.yaml',
            'features:\n  - Feature note 1.\n',
        )
        self._create_note(
            'note2-a1b2c3d4e5f67890.yaml',
            'features:\n  - Feature note 2.\n',
        )
        self.assertEqual(1, linter.lint_cmd(self.args, self.c))

    def test_lint_uid_collision_resolved_with_override(self):
        self._create_note(
            'note1-a1b2c3d4e5f67890.yaml',
            'features:\n  - Feature note 1.\n',
        )
        self._create_note(
            'note2-a1b2c3d4e5f67890.yaml',
            'features:\n  - Feature note 2.\n',
        )
        self.c.override(
            uid_overrides={
                'note2-a1b2c3d4e5f67890.yaml': 'override01234567',
            }
        )
        self.assertEqual(0, linter.lint_cmd(self.args, self.c))
