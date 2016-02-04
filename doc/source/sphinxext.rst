==================
 Sphinx Extension
==================

In addition to the command line tool, reno includes a Sphinx extension
for incorporating release notes for a project in its documentation
automatically.

Enable the extension by adding ``'reno.sphinxext'`` to the
``extensions`` list in the Sphinx project ``conf.py`` file.

.. rst:directive:: release-notes

   The ``release-notes`` directive accepts the same inputs as the
   ``report`` subcommand, and inserts the report inline into the
   current document where Sphinx then processes it to create HTML,
   PDF, or other output formats.

   If the directive has a body, it is used to create a title entry
   with ``=`` over and under lines (the typical heading style for the
   top-level heading in a document).

   Options:

   *branch*

     The name of the branch to scan. Defaults to the current branch.

   *reporoot*

     The path to the repository root directory. Defaults to the
     directory where ``sphinx-build`` is being run.

   *relnotessubdir*

     The path under ``reporoot`` where the release notes are. Defaults
     to ``releasenotes``.

   *notesdir*

     The path under ``relnotessubdir`` where the release notes
     are. Defaults to ``notes``.

   *version*

     A comma separated list of versions to include in the notes. The
     default is to include all versions found on ``branch``.

   *collapse-pre-releases*

     A flag indicating that notes attached to pre-release versions
     should be incorporated into the notes for the final release,
     after the final release is tagged.

   *earliest-version*

     A string containing the version number of the earliest version to
     be included. For example, when scanning a branch, this is
     typically set to the version used to create the branch to limit
     the output to only versions on that branch.

Examples
========

The release notes for the "current" branch, with "Release Notes" as a
title.

::

    .. release-notes:: Release Notes

The release notes for the "stable/liberty" branch, with a separate
title.

::

   =======================
    Liberty Release Notes
   =======================

   .. release-notes::
      :branch: stable/liberty

The release notes for version "1.0.0".

::

   .. release-notes:: 1.0.0 Release Notes
      :version: 1.0.0
