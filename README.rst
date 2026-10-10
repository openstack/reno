======
 reno
======

Reno is a release notes manager designed with high throughput in mind,
supporting fast distributed development teams without introducing
additional development processes.  Our goal is to encourage detailed
and accurate release notes for every release.

Overview
--------

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

Quick Start
-----------

Getting Started with reno
~~~~~~~~~~~~~~~~~~~~~~~~~

You can use ``uvx`` (from `uv <https://docs.astral.sh/uv/>`_) to run ``reno``
without needing to install it into your local environment:

.. code-block:: shell

    $ uvx reno new my-first-note

By default, this creates a new YAML file under ``releasenotes/notes/`` with a
unique random identifier (for example,
``releasenotes/notes/my-first-note-0123456789abcdef.yaml``).

Edit the generated file to populate the relevant sections (such as
``features``, ``fixes``, ``upgrade``, or ``deprecations``) using
reStructuredText formatting, and remove any unused sections:

.. code-block:: yaml

    ---
    features:
      - |
        Added awesome new feature X that improves performance by 50%.
    fixes:
      - |
        Fixed an issue where widget processing failed unexpectedly.

Commit the new file alongside your code changes in git.

.. note::

   Both the directory where notes are stored and the default sections
   are customizable. See `Configuring reno`_ for details.

Including Release Notes in Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To include the generated release notes in your Sphinx documentation:

1. Add ``reno`` to your documentation dependencies (e.g., in
   ``doc/requirements.txt`` or ``pyproject.toml``).

2. Enable the Sphinx extension by adding ``'reno.sphinxext'`` to the
   ``extensions`` list in your Sphinx ``conf.py``:

   .. code-block:: python

       extensions = [
           ...,
           'reno.sphinxext',
       ]

3. Add the ``release-notes`` directive to an ``.rst`` document in your
   Sphinx documentation (such as ``releasenotes.rst`` or
   ``doc/source/releasenotes.rst``):

   .. code-block:: rst

       ====================
        Release Notes
       ====================

       .. release-notes::

When Sphinx builds your documentation, reno scans the repository's git
tags and commit history to automatically collate notes and group them by
release version.

Configuring reno
----------------

Reno supports configuration through an optional configuration file. It
searches for configuration in the following order:

1. ``releasenotes/config.yaml`` (or ``<rel-notes-dir>/config.yaml``)
2. ``reno.yaml`` in the root directory of the repository
3. A ``[tool.reno]`` table in ``pyproject.toml``

Custom Sections
~~~~~~~~~~~~~~~

By default, reno includes sections for features, bug fixes, known issues,
upgrade notes, deprecations, critical fixes, and security issues. You can
define your own custom set of sections using the ``sections`` option:

.. code-block:: toml

    # pyproject.toml
    [tool.reno]
    sections = [
      ["features", "New Features"],
      ["fixes", "Bug Fixes"],
      ["deprecations", "Deprecations"],
      ["api", "API Changes"],
    ]

Or in YAML (``reno.yaml``):

.. code-block:: yaml

    sections:
      - [features, New Features]
      - [fixes, Bug Fixes]
      - [deprecations, Deprecations]
      - [api, API Changes]

A ``prelude`` section (for general release announcements) is always
included automatically at the top of the generated release report.

Customizing Note Paths
~~~~~~~~~~~~~~~~~~~~~~

By default, release notes are placed in ``releasenotes/notes/``. You can
control both parts of this path:

* **Notes subdirectory:** Configure ``notesdir`` in your configuration file
  to change the subdirectory within the release notes folder:

  .. code-block:: toml

      # pyproject.toml
      [tool.reno]
      notesdir = "fragments"

* **Parent release notes directory:** Use the ``--rel-notes-dir`` (or ``-d``)
  command-line option to point reno to a different base directory:

  .. code-block:: shell

      $ uvx reno --rel-notes-dir docs/releasenotes new my-note

  When using Sphinx, configure the corresponding options on the
  ``release-notes`` directive:

  .. code-block:: rst

      .. release-notes::
         :relnotessubdir: docs/releasenotes
         :notesdir: fragments

Comparison to towncrier
-----------------------

`towncrier <https://towncrier.readthedocs.io/>`_ is another popular tool
for managing release notes from per-change fragments. While both tools
solve the problem of merge conflicts on a single changelog file by having
developers write separate fragment files, they differ fundamentally in how
release notes are associated with releases and published.

* **towncrier** relies on a manual, commit-time process. At release time, a
  maintainer runs ``towncrier build``, which gathers all pending fragments,
  concatenates them into a monolithic file (like ``NEWS.rst`` or
  ``CHANGELOG.md``), and deletes the individual fragment files. The
  modified changelog and fragment deletions must then be committed back to
  git prior to tagging the release.

* **reno** relies on git metadata (commit history and tags) to dynamically
  discover and associate notes with releases. Individual note files are
  kept in the repository permanently. At documentation build time, reno
  traverses git history to determine which notes belong to which release
  based on tags.

Pros of reno:

* **Zero manual action at release time:** Reno requires no release-time
  build step. Releases can be tagged directly without needing to assemble a
  changelog, delete fragments, or manage dedicated release pull requests.

* **Post-release corrections:** Because notes remain as individual files
  and are mapped to releases based on git history, you can edit notes, fix
  typos, or retroactively add or remove notes even after a release has been
  tagged. The changes will automatically be reflected in the proper
  historical release section.

* **Branch and backport friendly:** Release notes are committed alongside
  code changes. When backporting a bug fix commit to a stable branch, the
  associated release note is backported with it naturally, without merge
  conflicts on a single shared changelog file.

Cons of reno:

* **Requires git history and tags:** Because reno relies on git metadata to
  determine release versions, it requires access to the repository's git
  history and tags. Shallow git clones (such as ``git clone --depth 1``
  often used by default in CI systems or container builds) or source
  tarballs lack this history and will fail to associate notes properly
  unless unshallowed or pre-compiled into a cache using ``reno cache``.

* **Performance on very large repositories:** Reno's git traversal can
  become slower on repositories with deep git histories and thousands of
  tags and commits, unlike towncrier's simple file-system concatenation.

* **Tightly coupled to git:** Unlike towncrier which produces a standalone
  static changelog file, reno cannot generate notes outside of a git
  repository unless a pre-built cache is distributed with the source.

Presentations
-------------

.. image:: https://img.youtube.com/vi/tEOGJ_h0Lx0/0.jpg
   :target: https://www.youtube.com/watch?v=tEOGJ_h0Lx0
   :alt: EuroPython 2018 Presentation

Project Metadata
----------------

.. .. image:: https://governance.openstack.org/tc/badges/reno.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

* Free software: Apache license
* Documentation: https://docs.openstack.org/reno/latest/
* Source: https://opendev.org/openstack/reno/
* Bugs: https://storyboard.openstack.org/#!/project/933
* IRC: #openstack-release on OFTC
