========
 Usage
========

Creating New Release Notes
==========================

The ``reno`` command line tool is used to create a new release note
file in the correct format and with a unique name.  The ``new``
subcommand combines a random suffix with a "slug" value to create
the file with a unique name that is easy to identify again later.

.. code-block:: shell

    $ reno new slug-goes-here
    Created new notes file in releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml

Within OpenStack projects, ``reno`` is often run via tox instead of
being installed globally. For example

.. code-block:: shell

    $ tox -e venv -- reno new slug-goes-here
    venv develop-inst-nodeps: /mnt/projects/release-notes-generation/reno
    venv runtests: commands[0] | reno new slug-goes-here
    Created new notes file in releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml
      venv: commands succeeded
      congratulations :)
    $ git status
    Untracked files:
      (use "git add <file>..." to include in what will be committed)

        releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml

The ``--edit`` option opens the new note in a text editor.

.. code-block:: shell

    $ reno new slug-goes-here --edit
    ... Opens the editor set in the EDITOR environment variable, editing the new file ...
    Created new notes file in releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml

The ``--from-template`` option allows you to use a pre-defined file and use
that as the release note.

.. code-block:: shell

    $ reno new slug-goes-here --from-template my-file.yaml
    ... Creates a release note using the provided file my-file.yaml ...
    Created new notes file in releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml

.. note::

    You can also combine the flags ``--edit`` and ``--from-template``
    to create a release note from a specified file and immediately start an
    editor to modify the new file.

By default, the new note is created under ``./releasenotes/notes``.
The ``--rel-notes-dir`` command-line flag changes the parent directory
(the ``notes`` subdirectory is always appended). It's also possible to
set a custom template to create notes (see `Configuring Reno`_ ).

Editing a Release Note
======================

The note file is a YAML file with several sections. All of the text is
interpreted as having `reStructuredText`_ formatting. The permitted
sections are configurable (see below) but default to the following
list:

prelude
  General comments about the release. Prelude sections from all notes in a
  release are combined, in note order, to produce a single prelude
  introducing that release. This section is always included, regardless
  of what sections are configured.

features
  A list of new major features in the release.

issues
  A list of known issues in the release. For example, if a new driver
  is experimental or known to not work in some cases, it should be
  mentioned here.

upgrade
  A list of upgrade notes in the release. For example, if a database
  schema alteration is needed.

deprecations
  A list of features, APIs, configuration options to be deprecated in the
  release. Deprecations should not be used for something that is removed in the
  release, use upgrade section instead. Deprecation should allow time for users
  to make necessary changes for the removal to happen in a future release.

critical
  A list of *fixed* critical bugs.

security
  A list of *fixed* security issues.

fixes
  A list of other *fixed* bugs.

other
  Other notes that are important but do not fall into any of the given
  categories.

Any sections that would be blank should be left out of the note file
entirely.

.. code-block:: yaml

   ---
   prelude: >
       Replace this text with content to appear at the
       top of the section for this release.
   features:
     - List new features here, or remove this section.
   issues:
     - List known issues here, or remove this section.
   upgrade:
     - List upgrade notes here, or remove this section.
   deprecations:
     - List deprecation notes here, or remove this section
   critical:
     - Add critical notes here, or remove this section.
   security:
     - Add security notes here, or remove this section.
   fixes:
     - Add normal bug fixes here, or remove this section.
   other:
     - Add other notes here, or remove this section.

Note File Syntax
----------------

Release notes may include embedded `reStructuredText`_, including simple
inline markup like emphasis and pre-formatted text as well as complex
body structures such as nested lists and tables. To use these
formatting features, the note must be escaped from the YAML parser.

The default template sets up the ``prelude`` section to use ``>`` so
that line breaks in the text are removed. This escaping mechanism is
not needed for the bullet items in the other sections of the template.

To escape the text of any section and *retain* the newlines, prefix
the value with ``|``. For example:

.. literalinclude:: ../../../examples/notes/add-complex-example-6b5927c246456896.yaml
   :language: yaml

See :doc:`examples` for the rendered version of the note.

.. _reStructuredText: http://www.sphinx-doc.org/en/stable/rest.html

Generating a Report
===================

Run ``reno report <path-to-git-repository>`` to generate a report
containing the release notes. The ``--branch`` argument can be used to
generate a report for a specific branch (the default is the branch
that is checked out). To limit the report to a subset of the available
versions on the branch, use the ``--version`` option (it can be
repeated).

Notes are output in the order they are found when scanning the git
history of the branch using topological ordering. This is
deterministic, but not necessarily predictable or mutable.

Checking Notes
==============

Run ``reno lint <path-to-git-repository>`` to test the existing
release notes files against some rules for catching common
mistakes. The command exits with an error code if there are any
mistakes, so it can be used in a build pipeline to force some
correctness.

Computing Next Release Version
==============================

Run ``reno -q semver-next`` to compute the next SemVer_ version number
based on the types of release notes found since the last release.

.. _SemVer: https://semver.org

.. _configuration:

Configuring Reno
================

Reno looks for an optional config file, either ``config.yaml`` in the release
notes directory or ``reno.yaml`` in the root directory. If the values in the
configuration file do not apply to the command being run, they are ignored. For
example, some reno commands take inputs controlling the branch, earliest
revision, and other common parameters that control which notes are included in
the output. Because they are commonly set options, a configuration file may be
the most convenient way to manage the values consistently.

.. code-block:: yaml

    ---
    branch: master
    earliest_version: 12.0.0
    collapse_pre_releases: false
    stop_at_branch_base: true
    sections:
      # The prelude section is implicitly included.
      - [features, New Features]
      - [issues, Known Issues]
      - [upgrade, Upgrade Notes]
      - [api, API Changes]
      - [security, Security Issues]
      - [fixes, Bug Fixes]
    # Change prelude_section_name to 'release_summary' from default value
    # 'prelude'.
    prelude_section_name: release_summary
    template: |
              <template-used-to-create-new-notes>
              ...
    encoding: utf8

Many of the settings in the configuration file can be overridden by
using command-line switches. For example:

- ``--branch``
- ``--earliest-version``
- ``--collapse-pre-releases``/``--no-collapse-pre-releases``
- ``--ignore-cache``
- ``--stop-at-branch-base``/``--no-stop-at-branch-base``

The following options are configurable:

.. show-reno-config::

Debugging
=========

The true location of formatting errors in release notes may be masked
because of the way release notes are included into sphinx documents.
To generate the release notes manually, so that they can be put into a
sphinx document directly for debugging, use the ``report`` command.

.. code-block:: console

    $ reno report .

Fixing Release Notes
====================

Occasionally it is necessary to update release notes due to typos, URLs
changing, or errors such as invalid section names not being noticed until
after they have been committed or released.

Reno identifies each release note by the unique identifier (a 16-character
hexadecimal SHA) embedded in its filename (for example,
``my-note-95915aaedd3c48d8.yaml``). This identifier allows reno to track a
release note across Git commits, modifications, and renames.

To fix an existing release note, edit the existing file in place and commit
the changes. The process is exactly the same regardless of what you are
fixing:

* Fixing typos, grammatical mistakes, or broken links in the note text.
* Correcting an invalid or unrecognized section header (for example,
  changing ``feature:`` to ``features:``).
* Adding or removing content from sections.

Because reno tracks notes by their unique ID, when you modify an existing note
in a new commit, reno pulls the updated contents from the newest commit while
retaining the note's association with the release where it was first introduced.

.. versionchanged:: 2.6.0

   Modifying an existing release note file in Git associates the note with
   the release where it was originally introduced while using the updated
   content from the newest commit. In earlier versions, modifying a note
   could cause it to be attributed to a newer release.

Past Releases and Stable Branches
---------------------------------

If an update is needed for a release note that was already included in a past
release on a stable branch, the fix should be proposed directly to the stable
branch where the note was introduced (or cherry-picked to that branch). Because
Git branches diverge at the branch point, commits made only on the main
development branch are not in the Git history of the stable branch and will
therefore not appear in documentation built from that stable branch.

Excluding Notes
---------------

If a release note was added by mistake and should be removed entirely from the
rendered output, the ``ignore-notes`` option can be used in Sphinx (or
``ignore_notes`` in the configuration file) to exclude specific notes by
filename or unique ID:

.. code-block:: rest

      ===========================
       Pike Series Release Notes
      ===========================

      .. release-notes::
         :branch: stable/pike
         :ignore-notes:
           mistake-note-1-ee6274467572906b.yaml,
           mistake-note-2-dd6274467572906b.yaml

Within OpenStack
================

The OpenStack project maintains separate instructions for configuring
the CI jobs and other project-specific settings used for reno. Refer
to the `Managing Release Notes
<https://docs.openstack.org/project-team-guide/release-management.html#managing-release-notes>`__
section of the Project Team Guide for details.

Within Travis CI
================

The `Travis CI <https://travis-ci.org/>`_ uses shallow git clones,
and detached head, which prevents reno from accessing the repo data
it needs.
You'll see an error message like the one mentioned in
`Launchpad bug 1703603 <https://bugs.launchpad.net/reno/+bug/1703603>`_.

To use reno within a Travis CI job, the cloned repository needs to be
unshallowed and checked out in the right branch from your ``.travis.yml``,
like in the following example:

.. code-block:: yaml

   ---
   language: python

   python:
     - 3.5

   install:
     - |
        # Force unshallow and checkout the current branch
        # https://docs.openstack.org/reno/latest/user/usage.html#within-travis-ci
        git config remote.origin.fetch +refs/heads/*:refs/remotes/origin/*
        git fetch --unshallow --tags
        git symbolic-ref --short HEAD || git checkout -b ${TRAVIS_BRANCH}-test $TRAVIS_BRANCH
        # Ref: https://stackoverflow.com/questions/32580821/how-can-i-customize-override-the-git-clone-step-in-travis-ci

   script:
     - reno report .
