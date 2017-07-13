=========================================
 reno: A New Way to Manage Release Notes
=========================================

Reno is a release notes manager designed with high throughput in mind,
supporting fast distributed development teams without introducing
additional development processes.  Our goal is to encourage detailed
and accurate release notes for every release.

Reno uses git to store its data, along side the code being
described. This means release notes can be written when the code
changes are fresh, so no details are forgotten. It also means that
release notes can go through the same review process used for managing
code and other documentation changes.

Reno stores each release note in a separate file to enable a large
number of developers to work on multiple patches simultaneously, all
targeting the same branch, without worrying about merge
conflicts. This cuts down on the need to rebase or otherwise manually
resolve conflicts, and keeps a development team moving quickly.

Reno also supports multiple branches, allowing release notes to be
back-ported from master to maintenance branches together with the
code for bug fixes.

Reno organizes notes into logical groups based on whether they
describe new features, bug fixes, known issues, or other topics of
interest to the user. Contributors categorize individual notes as they
are added, and reno combines them before publishing.

Notes can be styled using reStructuredText directives, and reno's
Sphinx integration makes it easy to incorporate release notes into
automated documentation builds.

Notes are automatically associated with the release version based on
the git tags applied to the repository, so it is not necessary to
track changes manually using a bug tracker or other tool, or to worry
that an important change will be missed when the release notes are
written by hand all at one time, just before a release.

Modifications to notes are incorporated when the notes are shown in
their original location in the history. This feature makes it possible
to correct typos or otherwise fix a published release note after a
release is made, but have the new note content associated with the
original version number. Notes also can be deleted, eliminating them
from future documentation builds.

Project Meta-data
=================

.. .. image:: https://governance.openstack.org/badges/reno.svg
    :target: https://governance.openstack.org/reference/tags/index.html

* Free software: Apache license
* Documentation: https://docs.openstack.org/reno/latest/
* Source: https://git.openstack.org/cgit/openstack/reno
* Bugs: https://bugs.launchpad.net/reno
* IRC: #openstack-release on freenode
