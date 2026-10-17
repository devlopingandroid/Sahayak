import base64
import json
import sys
from pathlib import Path
import cv2
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sahayak_cloud'))
from app import create_app, PATIENT, discard_empty_frame
from store import now

@pytest.fixture
def setup(tmp_path):
    app=create_app(tmp_path,False)
    app.config['TESTING']=True
    client=app.test_client()
    client.post('/api/auth',json={'password':'testonly-password'})
    return app,client,app.extensions['store']

def event(store,ident,people,objects):
    stamp=now()
    store.execute('''INSERT INTO events(id,patient_id,device_id,first_seen,last_seen,location_source,people,objects,detections,source)
        VALUES(?,?,?,?,?,?,?,?,?,?)''',(ident,PATIENT,'esp32',stamp,stamp,'unknown',json.dumps(people),json.dumps(objects),'[]','camera'))

def test_auth_and_origin(setup):
    app,c,s=setup
    assert app.test_client().get('/api/events').status_code==401
    assert c.patch('/api/settings',json={'room':'wrong'},headers={'Origin':'https://evil.example'}).status_code==403
    assert s.get('room') is None


def test_tunnel_visitors_are_not_local_even_when_forwarded_over_loopback(setup):
    _,c,s=setup
    auth=c.get('/api/auth',headers={'Cf-Connecting-IP':'203.0.113.10'})
    assert auth.json['local'] is False
    response=c.post('/api/audio/listen',json={},headers={'Cf-Connecting-IP':'203.0.113.10'})
    assert response.status_code==403


def test_only_configured_hosted_origin_can_write(setup,tmp_path,monkeypatch):
    _,c,s=setup
    import app as module
    monkeypatch.setattr(module,'BASE',tmp_path)
    folder=tmp_path/'.codex_artifacts';folder.mkdir(exist_ok=True)
    (folder/'remote-access.json').write_text(json.dumps({'allowed_origins':['https://sahayak.example']}))
    assert c.patch('/api/settings',json={'room':'Living room'},headers={'Origin':'https://sahayak.example'}).status_code==200
    assert c.patch('/api/settings',json={'room':'Wrong'},headers={'Origin':'https://other.example'}).status_code==403
    assert s.get('room')=='Living room'


def test_remote_signin_is_rate_limited(setup):
    app,_,_=setup
    c=app.test_client()
    headers={'Cf-Connecting-IP':'203.0.113.15'}
    for _ in range(8):
        assert c.post('/api/auth',json={'password':'incorrect'},headers=headers).status_code==401
    assert c.post('/api/auth',json={'password':'incorrect'},headers=headers).status_code==429

def test_invalid_image_and_device_token(setup):
    app,c,s=setup
    assert c.post('/upload',json={'image':'not base64'}).status_code==400
    s.set('allow_legacy_upload',False)
    assert c.post('/upload',json={}).status_code==401
    _,raw=cv2.imencode('.jpg',np.zeros((100,100,3),np.uint8))
    response=c.post('/upload',data=raw.tobytes(),content_type='image/jpeg',headers={'X-Device-Token':s.get('device_token')})
    assert response.status_code==202
    assert app.extensions['frames'].qsize()==1


def test_wifi_setup_link_uses_private_camera_address(setup):
    app,c,s=setup
    _,raw=cv2.imencode('.jpg',np.zeros((100,100,3),np.uint8))
    headers={'X-Device-Token':s.get('device_token'),'X-Wifi-Setup':'1','X-Device-Id':'camera-wifi'}
    uploaded=c.post('/upload',data=raw.tobytes(),content_type='image/jpeg',headers=headers,
        environ_overrides={'REMOTE_ADDR':'192.168.1.52'})
    assert uploaded.status_code==202
    assert c.get('/api/status').json['devices'][0]['wifi_setup_url']=='http://192.168.1.52/'
    # Forwarded headers and public client addresses must not produce arbitrary links.
    headers['X-Device-Id']='public-client'
    headers['X-Forwarded-For']='192.168.1.99'
    c.post('/upload',data=raw.tobytes(),content_type='image/jpeg',headers=headers,
        environ_overrides={'REMOTE_ADDR':'8.8.8.8'})
    public=next(d for d in c.get('/api/status').json['devices'] if d['id']=='public-client')
    assert public['wifi_setup_url'] is None

def test_query_must_match_person_and_object(setup):
    app,c,s=setup
    c.post('/api/people',json={'name':'Tanish'})
    event(s,'phone',[{'id':'a','name':'Tanish'}],['cell phone'])
    event(s,'bottle',[{'id':'a','name':'Tanish'}],['bottle'])
    response=c.post('/api/query',json={'text':'Did you see Tanish and my phone?'}).json
    assert response['event']['id']=='phone'
    assert 'ownership' in response['response']
    assert 'place was not confirmed' in response['response']
    assert c.post('/api/query',json={'text':'Have you seen my glasses?'}).json['status']=='not_found'

def test_medication_never_inferred_and_expired_answer_ignored(setup):
    _,c,s=setup
    c.post('/api/answers',json={'question':'Did I take medicine?','answer':'Take another dose'})
    assert c.post('/api/query',json={'text':'Did I take medicine?'}).json['status']=='unconfirmed'
    c.post('/api/answers',json={'question':'When will Tanish visit?','answer':'At six','expires':'2000-01-01T00:00:00Z'})
    assert c.post('/api/query',json={'text':'When will Tanish visit?'}).json['status']!='approved'

def test_routine_progress_bounded_and_help_honest(setup):
    _,c,s=setup
    ident=c.post('/api/routines',json={'title':'Morning','time':'09:00','steps':['Sit','Breakfast']}).json['id']
    for _ in range(4):
        assert c.patch('/api/routines/'+ident,json={'action':'done'}).status_code==200
    assert c.get('/api/routines').json[0]['step']==2
    request=c.post('/api/help',json={'message':'Please help'}).json
    assert 'not configured' in request['delivery']
    assert c.get('/api/help').json[0]['status']=='requested'
    c.patch('/api/help/'+request['id'],json={})
    assert c.get('/api/help').json[0]['status']=='acknowledged'


def test_ask_help_queues_alert_and_includes_schedule(setup):
    _,c,s=setup
    s.set('telegram_enabled',True)
    s.set('telegram_token','test-only-token')
    s.set('telegram_chat','test-only-chat')
    c.post('/api/routines',json={'title':'Breakfast','time':'09:00','steps':['Sit at the table']})
    answer=c.post('/api/query',json={'text':'Sahayak help'}).json
    assert answer['status']=='help'
    assert answer['help']['delivery']=='queued'
    assert 'Delivery is not confirmed yet' in answer['response']
    assert 'Breakfast' in answer['response']
    assert '9:00 AM' in answer['response']
    assert c.get('/api/help').json[0]['message']=='Sahayak help'
    assert s.rows('SELECT status FROM notifications')[0]['status']=='queued'


def test_ask_help_without_telegram_reports_failure(setup):
    _,c,s=setup
    answer=c.post('/api/query',json={'text':'Help!'}).json
    assert answer['status']=='help'
    assert 'could not be queued' in answer['response']
    assert 'no activities scheduled yet' in answer['response']
    assert len(c.get('/api/help').json)==1
    assert not s.rows('SELECT * FROM notifications')


def test_schedule_shows_order_progress_and_omits_disabled(setup):
    _,c,s=setup
    late=c.post('/api/routines',json={'title':'Walk','time':'17:00','steps':['Shoes','Walk with caretaker']}).json['id']
    early=c.post('/api/routines',json={'title':'Breakfast','time':'09:00','steps':['Eat breakfast']}).json['id']
    disabled=c.post('/api/routines',json={'title':'Unused','time':'08:00','steps':['Unused']}).json['id']
    c.patch('/api/routines/'+late,json={'action':'done'})
    c.patch('/api/routines/'+early,json={'action':'done'})
    c.patch('/api/routines/'+disabled,json={'enabled':False})
    answer=c.post('/api/query',json={'text':'What is my schedule?'}).json
    assert answer['status']=='schedule'
    assert [r['title'] for r in answer['routines']]==['Breakfast','Walk']
    assert 'completed' in answer['response'] and 'next step: Walk with caretaker' in answer['response']
    assert 'Unused' not in answer['response']
    assert not s.rows('SELECT * FROM help')


def test_consecutive_voice_questions_return_answers_not_transcripts(setup):
    app,c,s=setup
    class FakeAudio:
        def __init__(self):
            self.questions=iter(['What is my schedule?','What should I do next?'])
        def listen(self,language):return next(self.questions)
    # Exercise the same voice endpoint used by the dashboard without microphone input.
    import app as app_module
    from unittest.mock import patch
    # The audio service is captured by create_app, so inject it during construction.
    with patch.object(app_module,'Audio',FakeAudio):
        # Avoid starting model/network workers for this isolated voice test.
        with patch.object(app_module.threading.Thread,'start',lambda self:None):
            voice_app=app_module.create_app(s.path.parent/'voice',True)
    client=voice_app.test_client()
    client.post('/api/auth',json={'password':'voice-test-password'})
    client.post('/api/routines',json={'title':'Walk','time':'17:00','steps':['Wear your shoes']})
    first=client.post('/api/audio/listen',json={})
    second=client.post('/api/audio/listen',json={})
    assert first.status_code==second.status_code==200
    assert first.json['text']=='What is my schedule?'
    assert first.json['response']!=first.json['text']
    assert 'Walk' in first.json['response']
    assert 'Wear your shoes' in second.json['response']

def test_reviewed_samples_only_and_unknown_person(setup):
    _,c,s=setup
    person=c.post('/api/people',json={'name':'Tanish'}).json['id']
    s.execute('INSERT INTO samples VALUES(?,?,?,?,0,?)',('sample',person,'not-a-file','[1,0]',now()))
    assert c.get('/api/people').json[0]['approved_samples']==0
    c.patch('/api/samples/sample',json={'approved':True})
    assert c.get('/api/people').json[0]['approved_samples']==1
    assert c.post('/api/people/missing/samples',json={}).status_code==404

def test_deleted_events_hidden_and_image_protected(setup):
    app,c,s=setup
    event(s,'sample',[],['chair'])
    c.delete('/api/events/sample')
    assert c.get('/api/events').json==[]
    assert app.test_client().get('/api/events/sample/image').status_code==401
    assert c.get('/api/events/sample/image').status_code==404

def test_recap_excludes_unverified_observations(setup):
    _,c,s=setup
    event(s,'unverified',[],['chair'])
    event(s,'confirmed',[],['bottle'])
    c.patch('/api/events/confirmed',json={'verified':True})
    assert [e['id'] for e in c.get('/api/recap').json['events']]==['confirmed']

def test_pause_and_settings_are_validated_before_write(setup):
    _,c,s=setup
    assert c.patch('/api/settings',json={'room':'Wrong','face_threshold':1.2}).status_code==400
    assert s.get('room') is None
    c.patch('/api/settings',json={'capture_enabled':False})
    assert c.post('/upload',json={}).json['status']=='paused'

def test_person_only_sighting_is_searchable(setup):
    _,c,s=setup
    c.post('/api/people',json={'name':'Tanish'})
    event(s,'person-only',[{'id':'a','name':'Tanish'}],[])
    response=c.post('/api/query',json={'text':'Where is Tanish?'}).json
    assert response['status']=='found'
    assert response['event']['id']=='person-only'


def test_relationship_identity_and_last_sighting_use_enrollment(setup):
    _,c,s=setup
    daughter=c.post('/api/people',json={'name':'Ananya','relationship':'Daughter','introduction':'She visits you on Sundays.'}).json['id']
    identity=c.post('/api/query',json={'text':'Who is my daughter?'}).json
    assert identity['status']=='approved'
    assert 'Ananya is your daughter' in identity['response']
    assert 'visits you on Sundays' in identity['response']
    missing=c.post('/api/query',json={'text':'Where is my daughter?'}).json
    assert missing['status']=='not_found' and 'recorded sighting' in missing['response']
    event(s,'daughter-sighting',[{'id':daughter,'name':'Ananya'}],[])
    s.execute('UPDATE events SET location=?,location_source=? WHERE id=?',('Living room','configured camera','daughter-sighting'))
    location=c.post('/api/query',json={'text':'Where is my daughter?'}).json
    assert location['event']['id']=='daughter-sighting'
    assert 'Ananya, your daughter' in location['response']
    assert 'Living room' in location['response']
    assert 'not a confirmed current location' in location['response']
    named=c.post('/api/query',json={'text':'Who is Ananya?'}).json
    assert 'Ananya is your daughter' in named['response']


def test_relationship_ambiguity_missing_and_deleted_profiles(setup):
    _,c,s=setup
    assert c.post('/api/query',json={'text':'Who is my daughter?'}).json['status']=='not_found'
    first=c.post('/api/people',json={'name':'Ananya','relationship':'Daughter'}).json['id']
    second=c.post('/api/people',json={'name':'Riya','relationship':'daughter'}).json['id']
    identity=c.post('/api/query',json={'text':'Who is my daughter?'}).json
    assert 'Ananya' in identity['response'] and 'Riya' in identity['response']
    assert c.post('/api/query',json={'text':'Where is my daughter?'}).json['status']=='clarify'
    event(s,'riya',[{'id':second,'name':'Riya'}],[])
    assert c.post('/api/query',json={'text':'Where is Riya?'}).json['event']['id']=='riya'
    c.delete('/api/people/'+first)
    assert c.post('/api/query',json={'text':'Who is my daughter?'}).json['people'][0]['name']=='Riya'
    c.delete('/api/people/'+second)
    assert c.post('/api/query',json={'text':'Where is my daughter?'}).json['status']=='not_found'


def test_relationship_aliases_and_name_word_boundaries(setup):
    _,c,s=setup
    c.post('/api/people',json={'name':'Ann','relationship':'Mother'})
    assert 'Ann is your mother' in c.post('/api/query',json={'text':'Who is my mom?'}).json['response']
    # A short name must not match inside unrelated words.
    assert c.post('/api/query',json={'text':'Where is my anniversary gift?'}).json['status']=='not_found'

def test_encounter_merge_keeps_latest_photo_and_preserves_confirmed_memory(setup):
    _,c,s=setup
    first=s.record_observation(PATIENT,'esp32','2026-10-17T10:00:00+00:00','Living room','first.jpg',['chair'],[],[])
    second=s.record_observation(PATIENT,'esp32','2026-10-17T10:00:10+00:00','Living room','latest.jpg',['chair'],[],[])
    assert first==second
    merged=s.events(PATIENT)[0]
    assert merged['frames']==2 and merged['image']=='latest.jpg'
    assert merged['first_seen']=='2026-10-17T10:00:00+00:00'
    c.patch('/api/events/'+first,json={'verified':True})
    third=s.record_observation(PATIENT,'esp32','2026-10-17T10:00:20+00:00','Living room','new.jpg',['chair'],[],[])
    assert third!=first
    confirmed=next(e for e in s.events(PATIENT) if e['id']==first)
    assert confirmed['image']=='latest.jpg' and confirmed['last_seen']=='2026-10-17T10:00:10+00:00'

def test_editing_steps_requires_new_completion_confirmation(setup):
    _,c,s=setup
    ident=c.post('/api/routines',json={'title':'Morning','time':'09:00','steps':['Sit']}).json['id']
    c.patch('/api/routines/'+ident,json={'action':'done'})
    c.patch('/api/routines/'+ident,json={'steps':['Sit','Ask for breakfast'],'time':'10:00'})
    changed=c.get('/api/routines').json[0]
    assert changed['step']==0 and changed['time']=='10:00' and len(changed['steps'])==2

def test_camera_rotation_and_empty_frame_cleanup_keep_live_preview(setup):
    app,c,s=setup
    image=np.zeros((100,100,3),np.uint8)
    image[:50,:]=(0,0,255)
    image[50:,:]=(255,0,0)
    _,encoded=cv2.imencode('.jpg',image)
    assert c.post('/upload',data=encoded.tobytes(),content_type='image/jpeg').status_code==202
    device,path,room,stamp=app.extensions['frames'].get_nowait()
    corrected=cv2.imread(path)
    assert corrected[10,10,0]>240 and corrected[90,10,2]>240
    assert discard_empty_frame(s,Path(path).parent,path)
    assert not Path(path).exists()
    assert s.rows('SELECT image FROM devices')[0]['image'] is None
    assert c.get('/api/status').json['devices'][0]['image_url']
    assert c.get('/api/devices/'+device+'/image').status_code==200

def test_cleanup_preserves_evidence_samples_and_other_directories(setup,tmp_path):
    app,c,s=setup
    folder=tmp_path/'images'
    evidence=folder/'evidence.jpg'; evidence.write_bytes(b'evidence')
    event(s,'saved',[],['chair'])
    s.execute('UPDATE events SET image=? WHERE id=?',(str(evidence),'saved'))
    assert not discard_empty_frame(s,folder,evidence)
    sample=folder/'sample.jpg';sample.write_bytes(b'face')
    s.execute('INSERT INTO samples VALUES(?,?,?,?,0,?)',('pending','person',str(sample),'[1,0]',now()))
    assert not discard_empty_frame(s,folder,sample)
    outside=tmp_path/'original.jpg';outside.write_bytes(b'original')
    assert not discard_empty_frame(s,folder,outside)
    assert evidence.exists() and sample.exists() and outside.exists()

def test_rotation_can_be_disabled(setup):
    app,c,s=setup
    assert c.patch('/api/settings',json={'camera_rotation':90}).status_code==400
    c.patch('/api/settings',json={'camera_rotation':0})
    image=np.zeros((100,100,3),np.uint8);image[:50,:]=(0,0,255)
    _,encoded=cv2.imencode('.jpg',image)
    c.post('/upload',data=encoded.tobytes(),content_type='image/jpeg')
    _,path,_,_=app.extensions['frames'].get_nowait()
    assert cv2.imread(path)[10,10,2]>240

def upload_then_remove_empty_frame(app,c,s):
    _,encoded=cv2.imencode('.jpg',np.zeros((100,100,3),np.uint8))
    assert c.post('/upload',data=encoded.tobytes(),content_type='image/jpeg').status_code==202
    device,path,_,_=app.extensions['frames'].get_nowait()
    assert discard_empty_frame(s,Path(path).parent,path)
    return device

def test_manual_enrollment_uses_ram_after_empty_disk_frame_deleted(setup,monkeypatch):
    app,c,s=setup
    person=c.post('/api/people',json={'name':'Ayush'}).json['id']
    device=upload_then_remove_empty_frame(app,c,s)
    monkeypatch.setattr(app.extensions['vision'],'enrollment',lambda image:[1.0,0.0])
    result=c.post('/api/people/'+person+'/samples',json={'device_id':device})
    assert result.status_code==201 and result.is_json
    sample=s.rows('SELECT * FROM samples WHERE id=?',(result.json['id'],))[0]
    assert Path(sample['path']).exists() and sample['approved']==0

def test_guided_enrollment_starts_immediately_from_ram_and_uses_fast_interval(setup,monkeypatch):
    app,c,s=setup
    person=c.post('/api/people',json={'name':'Ayush'}).json['id']
    device=upload_then_remove_empty_frame(app,c,s)
    v=app.extensions['vision'];v.ready=True
    monkeypatch.setattr(v,'enrollment',lambda image:[1.0,0.0])
    result=c.post('/api/people/'+person+'/capture',json={'device_id':device})
    assert result.status_code==200 and result.json['captured']==1
    assert result.json['state']=='capturing'
    assert s.rows('SELECT count(*) n FROM samples')[0]['n']==1
    config=c.get('/api/device-config',headers={'X-Device-Token':s.get('device_token')})
    assert config.json['capture_interval']==1
    c.post('/api/people/'+person+'/capture',json={'stop':True})
    assert c.get('/api/device-config',headers={'X-Device-Token':s.get('device_token')}).json['capture_interval']==10

def test_capture_quality_feedback_and_unexpected_errors_are_json(setup,monkeypatch):
    app,c,s=setup
    person=c.post('/api/people',json={'name':'Ayush'}).json['id']
    device=upload_then_remove_empty_frame(app,c,s)
    v=app.extensions['vision'];v.ready=True
    def no_face(image):raise ValueError('Use a clear photo containing exactly one face.')
    monkeypatch.setattr(v,'enrollment',no_face)
    session=c.post('/api/people/'+person+'/capture',json={'device_id':device})
    assert session.status_code==200 and session.json['state']=='waiting_for_face'
    manual=c.post('/api/people/'+person+'/samples',json={'device_id':device})
    assert manual.status_code==400 and 'one face' in manual.json['error']
    def crash(image):raise RuntimeError('Simulated model failure')
    monkeypatch.setattr(v,'enrollment',crash)
    result=c.post('/api/people/'+person+'/samples',json={'device_id':device})
    assert result.status_code==500 and result.is_json and '<html' not in result.text

def test_guided_capture_rejects_offline_camera(setup):
    app,c,s=setup
    app.extensions['vision'].ready=True
    person=c.post('/api/people',json={'name':'Ayush'}).json['id']
    result=c.post('/api/people/'+person+'/capture',json={'device_id':'offline'})
    assert result.status_code==400 and result.is_json
