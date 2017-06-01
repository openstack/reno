========
 Usage
========

Creating New Release Notes
==========================

The ``reno`` command line tool is used to create a new release note
file in the correct format and with a unique name.  The ``new``
subcommand combines a random suffix with a "slug" value to create
the file with a unique name that is easy to identify again later.

::

    $ reno new slug-goes-here
    Created new notes file in releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml

Within OpenStack projects, ``reno`` is often run via tox instead of
being installed globally. For example

::

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

::

    $ reno new slug-goes-here --edit
    ... Opens the editor set in the EDITOR environment variable, editing the new file ...
    Created new notes file in releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml


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

  General comments about the release. The prelude from all notes in a
  section are combined, in note order, to produce a single prelude
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

::

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

.. include:: ../../examples/notes/add-complex-example-6b5927c246456896.yaml
   :literal:

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

Configuring Reno
================

Reno looks for an optional ``config.yaml`` file in the release notes
directory.  If the values in the configuration file do not apply to
the command being run, they are ignored. For example, some reno
commands take inputs controlling the branch, earliest revision, and
other common parameters that control which notes are included in the
output.  Because they are commonly set options, a configuration file
may be the most convenient way to manage the values consistently.

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
    template: |
              <template-used-to-create-new-notes>
              ...

Many of the settings in the configuration file can be overridden by
using command-line switches. For example:

- ``--branch``
- ``--earliest-version``
- ``--collapse-pre-releases``/``--no-collapse-pre-releases``
- ``--ignore-cache``
- ``--stop-at-branch-base``/``--no-stop-at-branch-base``

The following options are configurable:

`notesdir`

  The notes subdirectory within the `relnotesdir` where the notes live.

  Defaults to ``notes``.

`collapse_pre_releases`

  Should pre-release versions be merged into the final release of the same
  number (`1.0.0.0a1` notes appear under `1.0.0`).

  Defaults to ``True``.

`stop_at_branch_base`

  Should the scanner stop at the base of a branch (True) or go ahead and scan
  the entire history (False)?

  Defaults to ``True``.

`branch`

  The git branch to scan. If a stable branch is specified but does not exist,
  reno attempts to automatically convert that to an "end-of-life" tag. For
  example, ``origin/stable/liberty`` would be converted to ``liberty-eol``.

  Defaults to the "current" branch checked out.

`earliest_version`

  The earliest version to be included. This is usually the lowest version
  number, and is meant to be the oldest version. If unset, all versions will be
  scanned.

  Defaults to ``None``.

`template`

  The template used by reno new to create a note.

`release_tag_re`

  The regex pattern used to match the repo tags representing a valid release
  version. The pattern is compiled with the verbose and unicode flags enabled.

  Defaults to ``((?:[\d.ab]|rc)+)``.

`pre_release_tag_re`

  The regex pattern used to check if a valid release version tag is also a
  valid pre-release version. The pattern is compiled with the verbose and
  unicode flags enabled. The pattern must define a group called `pre_release`
  that matches the pre-release part of the tag and any separator, e.g for
  pre-release version `12.0.0.0rc1` the default RE pattern will identify
  `.0rc1` as the value of the group 'pre_release'.

  Defaults to ``(?P<pre_release>\.\d+(?:[ab]|rc)+\d*)$``.

`branch_name_re`

  The pattern for names for branches that are relevant when scanning history to
  determine where to stop, to find the "base" of a branch. Other branches are
  ignored.

  Defaults to ``stable/.+``.

`sections`

  The identifiers and names of permitted sections in the release notes, in the
  order in which the final report will be generated. A prelude section will
  always be automatically inserted before the first element of this list.

Debugging
=========

The true location of formatting errors in release notes may be masked
because of the way release notes are included into sphinx documents.
To generate the release notes manually, so that they can be put into a
sphinx document directly for debugging, use the ``report`` command.

.. code-block:: console

    $ reno report .

Within OpenStack
================

The OpenStack project maintains separate instructions for configuring
the CI jobs and other project-specific settings used for reno. Refer
to the `Managing Release Notes
<http://docs.openstack.org/project-team-guide/release-management.html#managing-release-notes>`__
section of the Project Team Guide for details.
