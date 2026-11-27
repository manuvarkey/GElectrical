"""persistence.gepro (M2 step 8): load/save round trip without GTK."""

import glob
import json
import os
import zipfile

import pytest

from gelectrical import persistence, undo
from gelectrical.core.constants import PROJECT_FILE_VER
from gelectrical.model.project import ProjectModel

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECTS = sorted(glob.glob(os.path.join(ROOT, 'sample_files', '**', '*.gepro'), recursive=True)) + \
    sorted(glob.glob(os.path.join(ROOT, 'tests', 'projects', 'cov_*.gepro')))


def _load(filename):
    project = ProjectModel(stack=undo.Stack())
    persistence.load_project(project, filename)
    return project


def _members(filename):
    with zipfile.ZipFile(filename) as z:
        return [(info.filename, z.read(info.filename)) for info in z.infolist()]


@pytest.mark.parametrize('filename', PROJECTS, ids=os.path.basename)
def test_save_load_save_is_stable(filename, tmp_path):
    first = tmp_path / 'first.gepro'
    second = tmp_path / 'second.gepro'
    project = _load(filename)
    model = project.get_model()
    persistence.save_project(project, str(first))
    reloaded = _load(str(first))
    assert json.dumps(reloaded.get_model(), sort_keys=True) == json.dumps(model, sort_keys=True)
    persistence.save_project(reloaded, str(second))
    assert _members(str(first)) == _members(str(second))


def test_file_layout(tmp_path):
    project = _load(PROJECTS[0])
    target = tmp_path / 'out.gepro'
    persistence.save_project(project, str(target))
    members = _members(str(target))
    names = [name for name, _ in members]
    assert names[-1] == 'document.json'
    document = json.loads(members[-1][1])
    assert list(document)[:2] == ['_file_version', '_files']
    assert document['_file_version'] == PROJECT_FILE_VER
    assert document['_files'] == names[:-1]
    assert names[-2] == 'proj_loadprofiles.json'
    # Same JSON formatting as the legacy writer
    assert members[-1][1].decode('utf-8') == json.dumps(document, indent=2)


def test_wrong_version_rejected(tmp_path):
    bad = tmp_path / 'bad.gepro'
    with zipfile.ZipFile(bad, 'w') as z:
        z.writestr('document.json', json.dumps({'_file_version': 'OTHER', '_files': []}))
    with pytest.raises(persistence.ProjectFileError, match='Wrong file type'):
        persistence.read_gepro(str(bad))


def test_not_a_zip_rejected(tmp_path):
    bad = tmp_path / 'bad.gepro'
    bad.write_text('not a project', encoding='utf-8')
    with pytest.raises(persistence.ProjectFileError):
        persistence.read_gepro(str(bad))


def test_projects_do_not_share_defaults():
    """D4: editing one project leaves new projects untouched"""
    a = ProjectModel()
    a.fields['Information']['project_name']['value'] = 'CHANGED'
    a.loadprofiles['load_prof_1'][0] = 'CHANGED'
    b = ProjectModel()
    assert b.fields['Information']['project_name']['value'] == 'PROJECT'
    assert b.loadprofiles['load_prof_1'][0] == 'Flat'
