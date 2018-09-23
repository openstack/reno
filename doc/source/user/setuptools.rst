==============================
 Python Packaging Integration
==============================

*reno* supports integration with `setuptools`_ and *setuptools* derivatives
like *pbr* through a custom command - ``build_reno``.

.. _pbr: https://docs.openstack.org/pbr/latest/
.. _setuptools: https://setuptools.readthedocs.io/en/latest/

Using setuptools integration
----------------------------

To enable the ``build_reno`` command, you simply need to install *reno*. Once
done, simply run:

.. code-block:: shell

   python setup.py build_reno

You can configure the command in ``setup.py`` or ``setup.cfg``. To configure it
from ``setup.py``, add a ``build_reno`` section to ``command_options`` like so:

.. code-block:: python

   from setuptools import setup

   setup(
       name='mypackage',
       version='0.1',
       ...
       command_options={
           'build_reno': {
               'output_file': ('setup.py', 'RELEASENOTES.txt'),
           },
       },
   )

To configure the command from ``setup.cfg``, add a ``build_reno`` section. For
example:

.. code-block:: ini

   [build_reno]
   output-file = RELEASENOTES.txt

Options for setuptools integration
----------------------------------

These options related to the *setuptools* integration only. For general
configuration of *reno*, refer to :ref:`configuration`.

``repo-root``
  The root directory of the Git repository; defaults to ``.``

``rel-notes-dir``
  The parent directory; defaults to ``releasenotes``

``output-file``
  The filename of the release notes file; defaults to ``RELEASENOTES.rst``
