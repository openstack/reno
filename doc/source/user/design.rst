=====================================
 Design Constraints and Requirements
=====================================

Managing release notes for a complex project over a long period of
time with many releases can be time consuming and error prone. Reno
helps automate the hard parts by devising a way to store the notes
inside the git repository where they can be tagged as part of the
release.

We had several design inputs:

* Release notes should be part of the git history, so as fixes in
  master are back-ported to older branches the notes can go with the
  code change.
* Release notes may need to change over time, as typos are found,
  logical errors or confusing language needs to be fixed, or as more
  information becomes available (CVE numbers, etc.).
* Release notes should be peer-reviewed, as with other documentation
  and code changes.
* Notes are mutable in that a clone today vs a clone tomorrow might
  have different release notes about the same change.
* Notes are immutable in that for a given git hash/tag the release
  notes will be the same. Tagging a commit will change the version
  description but that is all.
* We want to avoid merge issues when shepherding in a lot of
  release-note-worthy changes, which we expect to happen on stable
  branches always, and at release times on master branches.
* We want writing a release note to be straight-forward.
* We do not want release notes to be custom ordered within a release,
  but we do want the ordering to be predictable and consistent.
* We must be able to entirely remove a release note.
* We must not make things progressively slow down to a crawl over
  years of usage.
* Release note authors shouldn't need to know any special values for
  naming their notes files (i.e., no change id or SHA value that has
  special meaning).
* It would be nice if it was somewhat easy to identify the file
  containing a release note on a particular topic.
* Release notes should be grouped by type in the output document.

  1. New features
  2. Known issues
  3. Upgrade notes
  4. Security fixes
  5. Bugs fixes
  6. Other

We want to eventually provide the ability to create a release notes
file for a given release and add it to the source distribution for the
project. As a first step, we are going to settle for publishing
release notes in the documentation for a project.

Assumptions
-----------

Based on the above, *reno* makes a couple of assumptions about the release
policy used for a given project. *reno* expects all development, including bug
fixes, to take place on a single branch, ``master``. If *stable* or *release*
branches are used to support an older release then development should not take
place on these branches. Instead, bug fixes should be backported or
cherry-picked from ``master`` to the given *stable* branch. This is commonly
referred to as a `trunk-based`_ development workflow.

.. code-block:: none
   :caption: Trunk-based development. This is what *reno* expects.

    * bc823f0 (HEAD -> master) Fix a bug
    |
    | * 9723350 (tag: 1.0.1, stable/1.0) Fix a bug
    | * 49e2158 (tag: 1.0.0) Release 1.0
    * | ad13f52 Fix a bug on master
    * | 81b6b41 doc: Handle multiple branches in release notes
    |/
    * 0faba45 Integrate reno
    * a7beb14 (tag: 0.1.0) Add documentation
    * e23b0c8 Add gitignore
    * ff980c7 Initial commit

(where ``9723350`` is the backported version of ``bc823f0``).

By comparison, *reno* does not currently support projects where development is
spread across multiple active branches. In these situations, bug fixes are
developed on the offending *stable* or *release* branch and this branch is
later merged back into ``master``. This is commonly referred to as a
`git-flow-based`_ development workflow.

.. code-block:: none
   :caption: git-flow-based development. This is not compatible with *reno*.

    * 7df1078 (HEAD -> master) Merge branch 'stable/1.0'
    |\
    | * 9723350 (tag: 1.0.1, stable/1.0) Fix a bug on stable
    | * 49e2158 (tag: 1.0.0) Release 1.0
    * | ad13f52 Fix a bug on master
    * | 81b6b41 doc: Handle multiple branches in release notes
    |/
    * 0faba45 Integrate reno
    * a7beb14 (tag: 0.1.0) Add documentation
    * e23b0c8 Add gitignore
    * ff980c7 Initial commit

When this happens, *reno* has no way to distinguish between changes that apply
to the given *stable* branch and those that apply to ``master``. This is
because *reno* is *branch-based*, rather than *release-based*. If your project
uses this workflow, *reno* might not be for you.

More information is available  `here`_.

.. _trunk-based: https://trunkbaseddevelopment.com/
.. _git-flow-based: http://nvie.com/posts/a-successful-git-branching-model/
.. _here: https://storyboard.openstack.org/#!/story/1588309
