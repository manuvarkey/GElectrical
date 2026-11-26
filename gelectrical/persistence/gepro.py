#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# gepro
#
#  Copyright 2014 Manu Varkey <manuvarkey@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

"""``.gepro`` project files (moved from ``MainWindow.open_project/on_save``, M2).

A ``.gepro`` file is a ZIP archive with ``document.json`` (file version,
member list, project fields) and one JSON member per drawing sheet plus
``proj_loadprofiles.json`` (docs/architecture/project-format.md). The bytes
written are the same as before M2: members in sheet order, JSON with
``indent=2``, ``document.json`` last. The write is not atomic yet (D6, M4).
"""

import json, logging
from zipfile import ZipFile

from ..core.constants import PROJECT_FILE_VER

# Get logger object
log = logging.getLogger(__name__)


class ProjectFileError(Exception):
    """The file is not a GElectrical project or cannot be parsed"""


def read_gepro(filename):
    """Return (document, pages) of a project file; ``pages`` keeps the member
    order of ``document['_files']``. Raises ProjectFileError."""
    try:
        with ZipFile(filename, 'r') as projzip:
            with projzip.open('document.json') as document_file:
                document = json.load(document_file)  # load data structure
            if document.get('_file_version') != PROJECT_FILE_VER:
                raise ProjectFileError('Wrong file type selected')
            pages = dict()
            for file_name in document['_files']:
                with projzip.open(file_name) as file_file:
                    pages[file_name] = json.load(file_file)  # load data structure
    except ProjectFileError:
        raise
    except Exception as e:
        raise ProjectFileError('Error opening file: ' + repr(e)) from e
    return document, pages


def build_document(proj_settings, proj_pages):
    """Return (document, [(member, data), ...]) for ``ProjectModel.get_model()``"""
    document = dict()
    document['_file_version'] = PROJECT_FILE_VER
    document['_files'] = [page_name for page_name, page in proj_pages]
    document.update(proj_settings)
    return document, list(proj_pages)


def write_gepro(filename, proj_settings, proj_pages):
    """Write a project file from the storage model of ``ProjectModel.get_model()``"""
    document, pages = build_document(proj_settings, proj_pages)
    with ZipFile(filename, 'w') as projzip:
        for page_name, page in pages:
            projzip.writestr(page_name, json.dumps(page, indent=2))
        projzip.writestr('document.json', json.dumps(document, indent=2))


def load_project(project, filename):
    """Read ``filename`` into ``project`` (``ProjectModel.set_model``)"""
    document, pages = read_gepro(filename)
    if project.set_model(document, pages) is False:
        raise ProjectFileError('Project data incomplete')
    log.info('load_project - Project opened - ' + str(filename))


def save_project(project, filename):
    """Write ``project`` to ``filename``"""
    proj_settings, proj_pages = project.get_model()
    write_gepro(filename, proj_settings, proj_pages)
    log.info('save_project - Project saved - ' + str(filename))
