import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sahayak_cloud'))
from app import create_app
from store import Store
from enrollment import FaceRecording
from vision import Vision


class Candidates:
    ready=True
    count=0
    def enrollment_candidate(self,image):
        self.count+=1
        bits=np.zeros(64,dtype=bool)
        bits[(self.count-1)*8:self.count*8]=True
        return {'feature':np.array([1.,0.]),'hash':bits}


@pytest.fixture
def recording(tmp_path):
    store=Store(tmp_path/'test.sqlite3')
    def save(image):
        path=tmp_path/(str(len(list(tmp_path.glob('*.jpg'))))+'.jpg')
        cv2.imwrite(str(path),image)
        return str(path)
    recorder=FaceRecording(store,Candidates(),save)
    image=np.zeros((80,80,3),np.uint8)
    stamp=datetime.now(timezone.utc)
    recorder.start('camera',image,stamp.isoformat())
    return recorder,store,image,stamp


def complete(recorder,image,stamp):
    for i in range(1,8):
        recorder.feed(recorder.status()['device_id'],image,(stamp+timedelta(seconds=i*2)).isoformat())


def test_capture_first_name_later_atomically_saves_eight_approved_photos(recording):
    recorder,store,image,stamp=recording
    assert not store.rows('SELECT * FROM people')
    assert not store.rows('SELECT * FROM samples')
    complete(recorder,image,stamp)
    status=recorder.status()
    assert status['state']=='awaiting_name' and status['captured']==8
    assert 'photos' not in status and 'path' not in str(status)
    assert len(recorder.protected_paths())==8
    result=recorder.finish(status['id'],'Ayush','Brother')
    assert result['samples']==8
    assert store.rows('SELECT name,relationship FROM people')==[{'name':'Ayush','relationship':'Brother'}]
    assert len(store.rows('SELECT * FROM samples WHERE approved=1'))==8
    # A repeated submit must not create a second profile or duplicate samples.
    assert recorder.finish(status['id'],'Ayush')['id']==result['id']
    assert len(store.rows('SELECT * FROM people'))==1
    assert all(Path(p['path']).is_file() for p in store.rows('SELECT path FROM samples'))


def test_rejects_duplicate_wrong_person_and_repeated_timestamp(recording):
    recorder,store,image,stamp=recording
    recorder.feed('camera',image,stamp.isoformat())
    assert recorder.status()['captured']==1
    first=recorder.session['photos'][0]
    recorder.vision.enrollment_candidate=lambda _: {'feature':first['feature'],'hash':first['hash']}
    recorder.feed('camera',image,(stamp+timedelta(seconds=2)).isoformat())
    assert recorder.status()['captured']==1
    assert 'similar' in recorder.status()['guidance']
    recorder.vision.enrollment_candidate=lambda _: {'feature':np.array([0.,1.]),'hash':~first['hash']}
    recorder.feed('camera',image,(stamp+timedelta(seconds=4)).isoformat())
    assert recorder.status()['captured']==1
    assert 'same person' in recorder.status()['guidance']
    assert not store.rows('SELECT * FROM people')


def test_cancel_removes_only_temporary_photos_and_incomplete_save_fails(recording):
    recorder,store,image,stamp=recording
    ident=recorder.status()['id']
    path=Path(recorder.image(ident,0))
    with pytest.raises(ValueError,match='seven'):
        recorder.finish(ident,'Test')
    with pytest.raises(ValueError,match='already open'):
        recorder.start('camera',image,stamp.isoformat())
    recorder.cancel(ident)
    assert not path.exists() and recorder.status() is None
    assert not store.rows('SELECT * FROM people')
    assert recorder.image(ident,0) is None


def test_seven_good_photos_can_finish_after_timeout(recording):
    recorder,_,image,stamp=recording
    for i in range(1,7):
        recorder.feed('camera',image,(stamp+timedelta(seconds=i*2)).isoformat())
    recorder.session['deadline']=0
    assert recorder.status()['state']=='awaiting_name'
    assert recorder.finish(recorder.status()['id'],'Asha')['samples']==7


def test_too_few_photos_timeout_without_creating_profile(recording):
    recorder,store,_,_=recording
    recorder.session['deadline']=0
    assert recorder.status()['state']=='timed_out'
    assert not store.rows('SELECT * FROM people')


def test_routes_and_voice_command_start_real_recording_workflow(tmp_path,monkeypatch):
    app=create_app(tmp_path,False)
    app.config['TESTING']=True
    c=app.test_client()
    c.post('/api/auth',json={'password':'test-only-password'})
    store=app.extensions['store']
    vision=app.extensions['vision']
    vision.ready=True
    monkeypatch.setattr(vision,'enrollment_candidate',Candidates().enrollment_candidate)
    image=np.zeros((80,80,3),np.uint8)
    _,raw=cv2.imencode('.jpg',image)
    stamp=datetime.now(timezone.utc)
    store.execute('INSERT INTO devices(id,last_seen) VALUES(?,?)',('my-camera',stamp.isoformat()))
    app.extensions['previews']['my-camera']=raw.tobytes()
    result=c.post('/api/query',json={'text':'Record a person'}).json
    assert result['status']=='recording'
    ident=result['recording']['id']
    photo_url=f'/api/enrollment/{ident}/photos/0'
    assert app.test_client().get(photo_url).status_code==401
    assert c.get(photo_url).status_code==200
    complete(app.extensions['recorder'],image,stamp)
    assert c.get('/api/status').json['recording']['state']=='awaiting_name'
    assert c.post(f'/api/enrollment/{ident}/finish',json={'name':'Ayush'}).status_code==201
    assert c.get('/api/people').json[0]['approved_samples']==8
    assert c.delete(f'/api/enrollment/{ident}').status_code==200
    assert len(store.rows('SELECT * FROM samples'))==8


def test_offline_camera_cannot_create_empty_profile(tmp_path):
    app=create_app(tmp_path,False)
    c=app.test_client()
    c.post('/api/auth',json={'password':'test-only-password'})
    app.extensions['vision'].ready=True
    assert c.post('/api/enrollment/start',json={}).status_code==400
    assert not app.extensions['store'].rows('SELECT * FROM people')


def test_quality_gates_reject_multiple_faces_blur_and_bad_light(tmp_path,monkeypatch):
    vision=Vision(tmp_path,None)
    vision.ready=True
    face=np.array([50.,50.,100.,100.]+[0.]*11)
    feature=np.array([1.,0.])
    monkeypatch.setattr(vision,'faces',lambda image:[(face,feature),(face,feature)])
    image=np.full((320,320,3),100,np.uint8)
    with pytest.raises(ValueError,match='exactly one'):
        vision.enrollment_candidate(image)
    monkeypatch.setattr(vision,'faces',lambda image:[(face,feature)])
    with pytest.raises(ValueError,match='blurred'):
        vision.enrollment_candidate(image)
    with pytest.raises(ValueError,match='lighting'):
        vision.enrollment_candidate(np.zeros_like(image))


def test_spoken_name_is_transcribed_without_querying_or_creating_help(tmp_path,monkeypatch):
    import app as module
    class FakeAudio:
        def listen(self,language,short_phrase=False):
            assert short_phrase is True
            return 'Tanish'
    monkeypatch.setattr(module,'Audio',FakeAudio)
    monkeypatch.setattr(module.threading.Thread,'start',lambda self:None)
    app=create_app(tmp_path,True)
    c=app.test_client()
    c.post('/api/auth',json={'password':'test-only-password'})
    result=c.post('/api/audio/listen',json={'purpose':'person_name'})
    assert result.json=={'text':'Tanish'}
    assert not app.extensions['store'].rows('SELECT * FROM help')


def test_short_name_audio_keeps_first_spoken_chunks(monkeypatch):
    import audio as module
    import speech_recognition as sr
    import threading
    import itertools
    class Recognizer:
        energy_threshold=300
        def adjust_for_ambient_noise(self,*args,**kwargs):
            pytest.fail('Single names must not be swallowed by noise calibration')
        def recognize_google(self,audio,language):
            assert np.max(np.frombuffer(audio.frame_data,dtype=np.int16))==1200
            return 'Tanish'
    class Microphone:
        CHUNK=1600
        SAMPLE_RATE=16000
        SAMPLE_WIDTH=2
        count=0
        def __enter__(self):
            self.stream=self
            return self
        def __exit__(self,*args):pass
        def read(self,size):
            self.count+=1
            return np.full(size,1200 if self.count<=3 else 0,dtype=np.int16).tobytes()
    monkeypatch.setattr(sr,'Recognizer',Recognizer)
    monkeypatch.setattr(sr,'Microphone',Microphone)
    ticks=itertools.count(0,.1)
    monkeypatch.setattr(module.time,'monotonic',lambda:next(ticks))
    audio=module.Audio.__new__(module.Audio)
    audio.lock=threading.Lock()
    audio.cancel_event=threading.Event()
    assert audio.listen(short_phrase=True)=='Tanish'
