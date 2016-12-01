========
 Usage
========

Creating New Release Notes
==========================

The ``reno`` command line tool is used to create a new release note
file in the correct format and with a unique name.  The ``new``
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

        releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml

The ``--edit`` option enables to edit the note just after its creation.

::

    $ reno new slug-goes-here --edit
    ... Open your editor (defined with EDITOR environment variable) ...
    Created new notes file in releasenotes/notes/slug-goes-here-95915aaedd3c48d8.yaml


By default the new note is created under ``./releasenotes/notes``. Use
the ``--rel-notes-dir`` to change the parent directory (the ``notes``
subdirectory is always appended). It's also possible to set a custom
template to create notes (see `Configuring Reno`_ ).

Editing a Release Note
======================

The note file is a YAML file with several sections. All of the text is
interpreted as having `reStructuredText`_ formatting.

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

Formatting
----------

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

Notes are output in the order they are found by ``git log`` looking
over the history of the branch. This is deterministic, but not
necessarily predictable or mutable.

Configuring Reno
================

Reno looks for an optional ``config.yml`` file in your release notes
directory.  This file may contain optional flags that you might use with a
command. If the values do not apply to the command, they are ignored in the
configuration file. For example, a couple reno commands allow you to specify

- ``--branch``
- ``--earliest-version``
- ``--collapse-pre-releases``/``--no-collapse-pre-releases``
- ``--ignore-cache``
- ``--stop-at-branch-base``/``--no-stop-at-branch-base``

So you might write a config file (if you use these often) like:

.. code-block:: yaml

    ---
    branch: master
    earliest_version: 12.0.0
    collapse_pre_releases: false
    stop_at_branch_base: true
    template: |
              <template-used-to-create-new-notes>
              ...

These will be parsed first and then the CLI options will be applied after
the config files.

Debugging
=========

The way release notes are included into sphinx documents may mask where
formatting errors occur. To generate the release notes manually, so that
they can be put into a sphinx document directly for debugging, run:

.. code-block:: console

    $ reno report .

Within OpenStack
================

The OpenStack project maintains separate instructions for configuring
the CI jobs and other project-specific settings used for reno. Refer
to the `Managing Release Notes
<http://docs.openstack.org/project-team-guide/release-management.html#managing-release-notes>`__
section of the Project Team Guide for details.
