# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# oslosphinx uses reno and reno uses oslosphinx. Make oslosphinx for
# reno optional to break the build cycle
try:
    import openstackdocstheme  # noqa
except ImportError:
    has_theme = False
else:
    has_theme = True


# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'reno.sphinxext',
    'reno._exts.show_reno_config',
]

if has_theme:
    extensions.append('openstackdocstheme')

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'reno'
copyright = u'2013, OpenStack Foundation'

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# Do not warn about non-local image URI
suppress_warnings = ['image.nonlocal_uri']


# -- openstackdocstheme configuration -----------------------------------------

if has_theme:
    html_theme = 'openstackdocs'

repository_name = 'openstack/reno'
bug_project = '933'
bug_tag = 'docs'
