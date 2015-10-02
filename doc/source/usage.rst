========
 Usage
========

Creating New Release Notes
==========================

The ``reno`` command line tool is used to create a new release note
file in the correct format and with a unique name.  The ``create``
subcommand combines a random suffix with a "slug" value to make the
new file with a unique name that is easy to identify again later.

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

        releasenotes/notes/95915aaedd3c48d8-slug-goes-here.yaml

By default the new note is created under ``./releasenotes/notes``. Use
the ``--rel-notes-dir`` to change the parent directory (the ``notes``
subdirectory is always appended).

Editing a Release Note
======================

The note file is a YAML file with several sections. All of the text is
interpreted as having reStructuredText formatting.

prelude

  General comments about the release. The prelude from all notes in a
  section are combined, in note order, to produce a single prelude
  introducing that release.

features

  A list of new major features in the release.

issues

  A list of known issues in the release. For example, if a new driver
  is experimental or known to not work in some cases, it should be
  mentioned here.

upgrade

  A list of upgrade notes in the release. For example, if a database
  schema alteration is needed.

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
   critical:
     - Add critical notes here, or remove this section.
   security:
     - Add security notes here, or remove this section.
   fixes:
     - Add normal bug fixes here, or remove this section.
   other:
     - Add other notes here, or remove this section.


Generating a Report
===================

Run ``reno report <path-to-git-repository>`` to generate a report
containing the release notes. The ``--branch`` argument can be used to
generate a report for a specific branch (the default is the branch
that is checked out). To limit the report to a subset of the available
versions on the branch, use the ``--version`` option (it can be
repeated).

Notes are output in the order they are found by ``git log`` looking
over the history of the branch. This is deterministic, but not
necessarily predictable or mutable.
