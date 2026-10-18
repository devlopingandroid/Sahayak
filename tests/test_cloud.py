import importlib.util
import json
import sqlite3
import sys
import tarfile
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sahayak_cloud'))
from app import create_app
from store import Store,now


def test_cloud_requires_preconfigured_caretaker_and_never_starts_server_audio(tmp_path,monkeypatch):
    monkeypatch.setenv('SAHAYAK_CLOUD','1')
    with pytest.raises(RuntimeError,match='Cloud setup requires'):
        create_app(tmp_path/'empty',False)
    monkeypatch.setenv('SAHAYAK_PASSWORD_HASH',generate_password_hash('test-cloud-password'))
    monkeypatch.setenv('SAHAYAK_DEVICE_TOKEN','test-cloud-device')
    monkeypatch.setenv('SAHAYAK_ALLOWED_ORIGINS','https://dashboard.example')
    import app as module
    monkeypatch.setattr(module,'Audio',lambda:pytest.fail('Cloud must not open server audio devices'))
    app=create_app(tmp_path/'cloud',False)
    c=app.test_client()
    origin={'Origin':'https://dashboard.example'}
    result=c.post('/api/auth',json={'password':'test-cloud-password'},headers=origin,base_url='https://backend.example')
    assert result.status_code==200
    assert 'Secure;' in result.headers['Set-Cookie']
    status=c.get('/api/status',base_url='https://backend.example').json
    assert status['cloud'] is True and status['local_audio'] is False
    assert c.post('/api/audio/listen',json={},headers=origin,base_url='https://backend.example').status_code==403
    assert c.patch('/api/settings',json={'room':'Wrong'},headers={'Origin':'https://evil.example'},base_url='https://backend.example').status_code==403
    assert c.post('/upload',data=b'wrong',base_url='https://backend.example').status_code==401


def test_migration_keeps_private_credentials_and_remaps_image_paths_without_modifying_source(tmp_path):
    spec=importlib.util.spec_from_file_location('cloud_export',Path(__file__).resolve().parents[1]/'deploy/export_cloud_data.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source=tmp_path/'source'
    source.mkdir()
    store=Store(source/'sahayak.sqlite3')
    image=source/'face.jpg'
    image.write_bytes(b'test-image')
    store.set('gemini_api_key','test-only-secret')
    store.set('allow_legacy_upload',True)
    store.execute('INSERT INTO people(id,name,created) VALUES(?,?,?)',('p','Tanish',now()))
    store.execute('INSERT INTO samples VALUES(?,?,?,?,1,?)',('s','p',str(image),'[1,0]',now()))
    output=tmp_path/'private.tar.gz'
    result=module.export_data(source,output)
    assert result['images']==1
    with tarfile.open(output) as archive:
        assert len(archive.getnames())==2
        assert all(not name.startswith('/') and '..' not in name for name in archive.getnames())
        migrated=tmp_path/'check.sqlite3'
        migrated.write_bytes(archive.extractfile('sahayak.sqlite3').read())
    backup=Store(migrated)
    path=backup.rows('SELECT path FROM samples')[0]['path']
    assert path.startswith('/data/images/') and path.endswith('.jpg')
    assert backup.get('gemini_api_key')=='test-only-secret'
    assert backup.get('allow_legacy_upload') is False
    assert store.get('allow_legacy_upload') is True
    assert store.rows('SELECT path FROM samples')[0]['path']==str(image)
    with pytest.raises(ValueError,match='already exists'):
        module.export_data(source,output)
