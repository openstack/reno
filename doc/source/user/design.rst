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
