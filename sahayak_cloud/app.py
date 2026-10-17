"""Local SAHAYAK API and worker services."""
import base64
import functools
import hashlib
import ipaddress
import json
import logging
import os
import queue
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import cv2
import numpy as np
import requests
from flask import Flask, request, jsonify, session, send_file, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from store import Store, now
from vision import Vision
from audio import Audio

BASE = Path(__file__).resolve().parents[1]
PATIENT = 'patient_001'


def uid():
    return uuid.uuid4().hex


def discard_empty_frame(store, image_dir, path):
    """Discard a processed empty frame, never evidence or enrollment samples."""
    target=Path(path).resolve()
    if target.parent!=Path(image_dir).resolve() or target.suffix.lower()!='.jpg':
        return False
    if store.rows('SELECT id FROM events WHERE image=? LIMIT 1',(str(target),)) or store.rows('SELECT id FROM samples WHERE path=? LIMIT 1',(str(target),)):
        return False
    store.execute('UPDATE devices SET image=NULL WHERE image=?',(str(target),))
    target.unlink(missing_ok=True)
    return True


def create_app(data_dir=None, start_workers=True):
    app = Flask(__name__, static_folder=None)
    data = Path(data_dir or os.environ.get('SAHAYAK_DATA', BASE / 'sahayak_cloud/data')).resolve()
    data.mkdir(parents=True, exist_ok=True)
    images = data / 'images'
    images.mkdir(exist_ok=True)
    store = Store(data / 'sahayak.sqlite3')
    store.execute("UPDATE notifications SET status='failed',error='Application restarted before delivery was confirmed. Please resend.' WHERE status='queued'")
    for key in ('session_key','device_token'):
        if not store.get(key):
            store.set(key,secrets.token_urlsafe(32))
    app.secret_key = store.get('session_key')
    app.config.update(MAX_CONTENT_LENGTH=6*1024*1024, SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict', PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        SESSION_COOKIE_NAME='sahayak_'+hashlib.sha256(str(data).encode()).hexdigest()[:8])
    if data_dir is None:
        store.import_legacy(BASE, PATIENT)
    frames, notifications = queue.Queue(maxsize=3), queue.Queue(maxsize=30)
    previews={}
    device_setup_urls={}
    vision = Vision(BASE, store)
    audio = Audio() if start_workers else None
    runtime = {'processed':0,'last_error':None,'last_processing_ms':0,'last_queue_ms':0,'listening':False,
        'enrollment':None}
    enrollment_lock=threading.RLock()
    login_attempts={}
    login_lock=threading.Lock()
    app.extensions.update(store=store,vision=vision,frames=frames,runtime=runtime,previews=previews)

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value,dict):
            raise ValueError('Expected a JSON object.')
        return value

    def auth(fn):
        @functools.wraps(fn)
        def wrapped(*args,**kwargs):
            if not session.get('caretaker'):
                return jsonify(error='Please sign in on the laptop.'),401
            return fn(*args,**kwargs)
        return wrapped

    def local():
        # A tunnel connects from loopback but its visitor is still remote.
        return request.remote_addr in ('127.0.0.1','::1') and not request.headers.get('Cf-Connecting-IP')

    @app.before_request
    def origins():
        from urllib.parse import urlparse
        origin=request.headers.get('Origin')
        allowed=[]
        remote_config=BASE/'.codex_artifacts/remote-access.json'
        try:
            allowed=json.loads(remote_config.read_text(encoding='utf-8')).get('allowed_origins',[])
        except (OSError,ValueError):
            pass
        if origin and request.method not in ('GET','HEAD','OPTIONS') and urlparse(origin).hostname!=request.host.split(':')[0] and origin not in allowed:
            return jsonify(error='Cross-origin write rejected.'),403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        if request.path.startswith('/api'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(ValueError)
    def validation(exc):
        return jsonify(error=str(exc)),400

    @app.errorhandler(413)
    def too_large(exc):
        return jsonify(error='Maximum request size is 6 MB.'),413

    @app.errorhandler(HTTPException)
    def http_error(exc):
        if request.path.startswith('/api/') or request.path=='/upload':
            return jsonify(error=exc.description),exc.code
        return exc

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        logging.exception('Unhandled application error on %s',request.path)
        return jsonify(error='The server could not complete this request. Please retry; details were logged on the laptop.'),500

    def read_image(raw):
        if not raw or len(raw)>4*1024*1024:
            raise ValueError('Provide a JPEG or PNG under 4 MB.')
        image=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
        if image is None or image.shape[0]*image.shape[1]>16000000:
            raise ValueError('Unreadable image or image dimensions too large.')
        return image

    def save_image(image):
        path=images/(uid()+'.jpg')
        if not cv2.imwrite(str(path),image):
            raise ValueError('Could not save image.')
        return str(path)

    def recent_camera_frame(device_id):
        rows=store.rows('SELECT image,last_seen FROM devices WHERE id=?',(device_id,))
        if not rows or (datetime.now(timezone.utc)-datetime.fromisoformat(rows[0]['last_seen'])).total_seconds()>30:
            raise ValueError('No recent camera frame. Connect the ESP32 and wait for a new image.')
        raw=previews.get(device_id)
        if raw is None:
            path=rows[0]['image']
            if not path or not Path(path).is_file():
                raise ValueError('The last preview is no longer available. Wait for the next camera image.')
            raw=Path(path).read_bytes()
        return read_image(raw),rows[0]['last_seen']

    def collect_enrollment_frame(enrollment,image,stamp,path=None):
        with enrollment_lock:
            if runtime['enrollment'] is not enrollment or enrollment['captured']>=enrollment['target']:
                return
            if (datetime.now(timezone.utc)-datetime.fromisoformat(enrollment['started'])).total_seconds()>120:
                enrollment.update(state='timed_out',error='Capture timed out. Review available samples or start again.')
                return
            if enrollment['last_sample'] and datetime.fromisoformat(stamp)<=datetime.fromisoformat(enrollment['last_sample']):
                return
            try:
                feature=vision.enrollment(image)
                sample_path=path or save_image(image)
                store.execute('INSERT INTO samples VALUES(?,?,?,?,0,?)',(uid(),enrollment['person_id'],sample_path,json.dumps(feature),now()))
                enrollment['captured']+=1
                enrollment.update(last_sample=stamp,error=None,state='complete' if enrollment['captured']>=enrollment['target'] else 'capturing')
            except ValueError as exc:
                enrollment.update(state='waiting_for_face',error=str(exc))

    def serve_image(path):
        if not path or not Path(path).is_file():
            return jsonify(error='Evidence image unavailable.'),404
        resolved=Path(path).resolve()
        if not (resolved.is_relative_to(BASE) or resolved.is_relative_to(data)):
            return jsonify(error='Image outside this installation.'),403
        return send_file(resolved,mimetype='image/jpeg',max_age=0)

    def event_json(row):
        result=dict(row)
        result['image_url']='/api/events/'+row['id']+'/image' if row.get('image') else None
        result.pop('image',None)
        return result

    defaults={'patient_name':'Your loved one','room':'','capture_interval':10,'capture_enabled':True,'camera_rotation':180,
        'language':'en-IN','face_threshold':.5,'retention_days':30,'telegram_enabled':False,
        'telegram_chat':'','allow_legacy_upload':True,'patient_introduction':''}

    def settings_public():
        return {k:store.get(k,v) for k,v in defaults.items()} | {
            'telegram_configured':bool(store.get('telegram_token')),'device_token':store.get('device_token')}

    @app.route('/api/auth',methods=['GET','POST','DELETE'])
    def authentication():
        configured=bool(store.get('password_hash'))
        if request.method=='GET':
            return jsonify(configured=configured,authenticated=bool(session.get('caretaker')),local=local())
        if request.method=='DELETE':
            session.clear()
            return jsonify(ok=True)
        password=str(body().get('password',''))
        if configured:
            visitor=request.headers.get('Cf-Connecting-IP') or request.remote_addr
            with login_lock:
                current=time.monotonic()
                # Bound both guessing frequency and memory use for the public tunnel.
                for key in list(login_attempts):
                    login_attempts[key]=[t for t in login_attempts[key] if current-t<60]
                    if not login_attempts[key]:del login_attempts[key]
                attempts=login_attempts.setdefault(visitor,[])
                if len(attempts)>=8 or len(login_attempts)>1000:
                    return jsonify(error='Too many sign-in attempts. Wait one minute and try again.'),429
                attempts.append(current)
        if not configured:
            if not local():
                return jsonify(error='Create the caretaker password from localhost on the laptop.'),403
            if len(password)<10:
                raise ValueError('Use at least 10 characters.')
            store.set('password_hash',generate_password_hash(password))
        elif not check_password_hash(store.get('password_hash'),password):
            time.sleep(.5)
            return jsonify(error='Incorrect password.'),401
        session.clear()
        with login_lock:
            login_attempts.pop(request.headers.get('Cf-Connecting-IP') or request.remote_addr,None)
        session['caretaker']=True
        session.permanent=True
        return jsonify(ok=True)

    @app.get('/api/status')
    @auth
    def status():
        devices=store.rows('SELECT * FROM devices')
        for d in devices:
            d['frame_age_ms']=round(max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(d['last_seen'])).total_seconds()*1000))
            d['online']=d['frame_age_ms']<max(45,store.get('capture_interval',10)*3)*1000
            d['image_url']='/api/devices/'+d['id']+'/image' if d['image'] or d['id'] in previews else None
            d['wifi_setup_url']=device_setup_urls.get(d['id'])
            d.pop('image',None)
        events=store.events(PATIENT,500)
        return jsonify(devices=devices,vision={'ready':vision.ready,'error':vision.error,'labels':vision.labels},
            queue=frames.qsize(),**runtime,today_events=sum(datetime.fromisoformat(e['last_seen']).astimezone().date()==datetime.now().date() for e in events),
            people_count=store.rows('SELECT count(*) n FROM people WHERE deleted=0')[0]['n'],
            event_count=store.rows('SELECT count(*) n FROM events WHERE deleted=0 AND patient_id=?',(PATIENT,))[0]['n'],
            notifications=store.rows('SELECT * FROM notifications ORDER BY created DESC LIMIT 5'),
            audio_error=audio.error if audio else None,local_audio=local(),capture_enabled=store.get('capture_enabled',True))

    @app.route('/api/settings',methods=['GET','PATCH'])
    @auth
    def settings():
        if request.method=='PATCH':
            value=body()
            # Validate the whole update before writing any settings.
            clean={}
            for key,item in value.items():
                if key not in defaults and key!='telegram_token':
                    continue
                if key in ('capture_interval','retention_days'):
                    item=int(item)
                    if not 1<=item<=(60 if key=='capture_interval' else 3650):
                        raise ValueError('Capture interval: 1–60 seconds. Retention: 1–3650 days.')
                if key=='face_threshold':
                    item=float(item)
                    if not .35<=item<=.9:
                        raise ValueError('Face threshold must be 0.35–0.90.')
                if key=='camera_rotation':
                    item=int(item)
                    if item not in (0,180):
                        raise ValueError('Camera rotation must be 0 or 180 degrees.')
                if key in ('capture_enabled','telegram_enabled','allow_legacy_upload') and not isinstance(item,bool):
                    raise ValueError('Switch values must be true or false.')
                if key=='telegram_token' and not item:
                    continue
                clean[key]=item
            for key,item in clean.items():
                store.set(key,item)
        return jsonify(settings_public())

    @app.post('/upload')
    def upload():
        if request.headers.get('X-Device-Token','')!=store.get('device_token') and not store.get('allow_legacy_upload',True):
            return jsonify(error='Device token required.'),401
        if not store.get('capture_enabled',True):
            return jsonify(status='paused',capture_interval=store.get('capture_interval',10))
        value=body() if request.is_json else {}
        if value.get('patient_id',PATIENT) not in (PATIENT,'P001'):
            raise ValueError('This installation is configured for patient_001.')
        try:
            raw=base64.b64decode(value.get('image',''),validate=True) if request.is_json else request.get_data()
        except Exception:
            raise ValueError('Invalid Base64 image.')
        image=read_image(raw)
        # Rotate camera uploads before preview, recognition and evidence storage.
        # Uploaded reference photos are already upright and are not transformed.
        if store.get('camera_rotation',180)==180:
            image=cv2.rotate(image,cv2.ROTATE_180)
        if frames.full():
            return jsonify(error='Processing queue busy; retry next frame.'),429
        ident=str(value.get('device_id',request.headers.get('X-Device-Id','esp32-cam')))
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',ident):
            raise ValueError('Invalid device identifier.')
        if request.headers.get('X-Wifi-Setup')=='1':
            try:
                camera_ip=ipaddress.IPv4Address(request.remote_addr)
                if camera_ip.is_private and not camera_ip.is_loopback and not camera_ip.is_unspecified:
                    device_setup_urls[ident]='http://'+str(camera_ip)+'/'
            except ipaddress.AddressValueError:
                pass
        path=save_image(image)
        previews[ident]=Path(path).read_bytes()
        stamp=now()
        room=str(store.get('room','')).strip()
        store.execute('''INSERT INTO devices(id,last_seen,image,location,frames) VALUES(?,?,?,?,1)
            ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,image=excluded.image,
            location=excluded.location,frames=devices.frames+1,error=NULL''',(ident,stamp,path,room))
        try:
            frames.put_nowait((ident,path,room,stamp))
        except queue.Full:
            return jsonify(error='Queue busy; image received but not processed.'),429
        return jsonify(status='queued',capture_interval=store.get('capture_interval',10)),202

    @app.get('/api/device-config')
    def device_config():
        if not secrets.compare_digest(request.headers.get('X-Device-Token',''),store.get('device_token')):
            return jsonify(error='Device token required.'),401
        enrollment=runtime['enrollment']
        collecting=bool(enrollment and enrollment['state'] not in ('complete','timed_out') and
            (datetime.now(timezone.utc)-datetime.fromisoformat(enrollment['started'])).total_seconds()<120)
        return jsonify(capture_interval=1 if collecting else store.get('capture_interval',10),capture_enabled=store.get('capture_enabled',True))

    @app.get('/api/devices/<ident>/image')
    @auth
    def device_image(ident):
        if ident in previews:
            return app.response_class(previews[ident],mimetype='image/jpeg')
        rows=store.rows('SELECT image FROM devices WHERE id=?',(ident,))
        return serve_image(rows[0]['image'] if rows else None)

    @app.get('/api/events')
    @auth
    def events():
        values=store.events(PATIENT,500)
        search=request.args.get('q','').lower()
        if search:
            values=[e for e in values if search in (' '.join(e['objects'])+' '+' '.join(p['name'] for p in e['people'])+' '+(e['location'] or '')).lower()]
        return jsonify([event_json(e) for e in values])

    @app.get('/api/events/<ident>/image')
    @auth
    def event_image(ident):
        rows=store.rows('SELECT image,detections FROM events WHERE id=? AND patient_id=? AND deleted=0',(ident,PATIENT))
        if rows and request.args.get('annotated')=='1' and rows[0]['image']:
            path=Path(rows[0]['image']).resolve()
            if path.is_file() and (path.is_relative_to(BASE) or path.is_relative_to(data)):
                image=cv2.imread(str(path))
                if image is not None:
                    for detection in json.loads(rows[0]['detections']):
                        x1,y1,x2,y2=[int(v) for v in detection['box']]
                        cv2.rectangle(image,(x1,y1),(x2,y2),(125,80,200),2)
                        cv2.putText(image,detection['label'],(x1,max(18,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.55,(125,80,200),2)
                    ok,encoded=cv2.imencode('.jpg',image)
                    if ok:
                        return app.response_class(encoded.tobytes(),mimetype='image/jpeg')
        return serve_image(rows[0]['image'] if rows else None)

    @app.route('/api/events/<ident>',methods=['PATCH','DELETE'])
    @auth
    def edit_event(ident):
        if not store.rows('SELECT id FROM events WHERE id=? AND patient_id=?',(ident,PATIENT)):
            return jsonify(error='Event not found.'),404
        if request.method=='DELETE':
            store.execute('UPDATE events SET deleted=1 WHERE id=?',(ident,))
        else:
            value=body()
            if 'location' in value:
                store.execute('UPDATE events SET location=?,location_source=? WHERE id=?',(str(value['location'])[:120],'caretaker',ident))
            if 'verified' in value:
                store.execute('UPDATE events SET verified=? WHERE id=?',(bool(value['verified']),ident))
            if 'objects' in value:
                if not isinstance(value['objects'],list) or not all(isinstance(o,str) for o in value['objects']):
                    raise ValueError('Objects must be a list of labels.')
                store.execute('UPDATE events SET objects=?,verified=1 WHERE id=?',(json.dumps(value['objects']),ident))
            if 'person_ids' in value:
                selected=[]
                for person_id in value['person_ids']:
                    rows=store.rows('SELECT id,name,relationship,introduction FROM people WHERE id=? AND deleted=0',(person_id,))
                    if not rows:
                        raise ValueError('Select an existing person.')
                    selected.append(rows[0])
                store.execute('UPDATE events SET people=?,verified=1 WHERE id=?',(json.dumps(selected),ident))
        return jsonify(ok=True)

    @app.route('/api/people',methods=['GET','POST'])
    @auth
    def people():
        if request.method=='POST':
            value=body()
            name=str(value.get('name','')).strip()
            if not name or len(name)>80:
                raise ValueError('Enter a name up to 80 characters.')
            ident=uid()
            store.execute('INSERT INTO people(id,name,relationship,introduction,created) VALUES(?,?,?,?,?)',
                (ident,name,str(value.get('relationship',''))[:120],str(value.get('introduction',''))[:500],now()))
            return jsonify(id=ident),201
        result=store.rows('SELECT * FROM people WHERE deleted=0 ORDER BY name')
        for person in result:
            samples=store.rows('SELECT id,approved FROM samples WHERE person_id=?',(person['id'],))
            person.update(samples=samples,approved_samples=sum(s['approved'] for s in samples),
                photo_url='/api/samples/'+samples[0]['id']+'/image' if samples else None)
        return jsonify(result)

    @app.route('/api/people/<ident>',methods=['PATCH','DELETE'])
    @auth
    def edit_person(ident):
        if request.method=='DELETE':
            store.execute('UPDATE people SET deleted=1 WHERE id=?',(ident,))
        else:
            value=body()
            for key in ('name','relationship','introduction'):
                if key in value:
                    if key=='name' and not str(value[key]).strip():
                        raise ValueError('Name cannot be empty.')
                    store.execute(f'UPDATE people SET {key}=? WHERE id=?',(str(value[key])[:500],ident))
        return jsonify(ok=True)

    @app.post('/api/people/<ident>/samples')
    @auth
    def add_sample(ident):
        if not store.rows('SELECT id FROM people WHERE id=? AND deleted=0',(ident,)):
            return jsonify(error='Person not found.'),404
        if request.is_json:
            image,_=recent_camera_frame(body().get('device_id','esp32-cam'))
        else:
            file=request.files.get('image')
            if not file:
                raise ValueError('Choose a photo.')
            image=read_image(file.read())
        feature=vision.enrollment(image)
        ident_sample=uid()
        store.execute('INSERT INTO samples VALUES(?,?,?,?,0,?)',(ident_sample,ident,save_image(image),json.dumps(feature),now()))
        return jsonify(id=ident_sample,approved=False),201

    @app.post('/api/people/<ident>/capture')
    @auth
    def capture_session(ident):
        value=body()
        if value.get('stop'):
            runtime['enrollment']=None
            return jsonify(ok=True)
        if not store.rows('SELECT id FROM people WHERE id=? AND deleted=0',(ident,)):
            return jsonify(error='Person not found.'),404
        if not vision.ready:
            raise ValueError('Wait until face recognition models are ready.')
        device_id=value.get('device_id','esp32-cam')
        image,stamp=recent_camera_frame(device_id)
        runtime['enrollment']={'person_id':ident,'device_id':value.get('device_id','esp32-cam'),
            'captured':0,'target':6,'started':now(),'last_sample':None,'error':None,'state':'capturing'}
        collect_enrollment_frame(runtime['enrollment'],image,stamp)
        return jsonify(runtime['enrollment'])

    @app.route('/api/samples/<ident>',methods=['PATCH','DELETE'])
    @auth
    def sample_review(ident):
        if request.method=='DELETE':
            store.execute('DELETE FROM samples WHERE id=?',(ident,))
        else:
            store.execute('UPDATE samples SET approved=? WHERE id=?',(bool(body().get('approved')),ident))
        return jsonify(ok=True)

    @app.get('/api/samples/<ident>/image')
    @auth
    def sample_image(ident):
        rows=store.rows('SELECT path FROM samples WHERE id=?',(ident,))
        return serve_image(rows[0]['path'] if rows else None)

    def routine_list():
        rows=store.rows('''SELECT r.*,COALESCE(p.step,0) step FROM routines r LEFT JOIN progress p
            ON p.routine_id=r.id AND p.day=? WHERE r.deleted=0 ORDER BY time''',(datetime.now().date().isoformat(),))
        for row in rows:
            row['steps']=json.loads(row['steps'])
        return rows

    def schedule_summary():
        routines=[r for r in routine_list() if r['enabled']]
        if not routines:
            return routines,'You have no activities scheduled yet. Your caretaker can add them in Daily routines.'
        parts=[]
        for routine in routines:
            clock=datetime.strptime(routine['time'],'%H:%M').strftime('%I:%M %p').lstrip('0')
            progress=('completed' if routine['step']>=len(routine['steps']) else
                'next step: '+routine['steps'][routine['step']])
            parts.append(f"At {clock}, {routine['title']}; {progress}.")
        return routines,"Here is your schedule for today. "+' '.join(parts)

    def request_help(message):
        ident,notification=uid(),None
        try:
            notification=notify('SAHAYAK assistance requested: '+message)
            state='queued'
        except ValueError as exc:
            state=('failed; saved on this laptop' if 'queue full' in str(exc).lower()
                else 'not configured; saved on this laptop')
        store.execute('INSERT INTO help VALUES(?,?,?,?,?,?)',(ident,message,now(),'requested',None,notification))
        return {'id':ident,'status':'requested','delivery':state,'notification':notification}

    def answer_query(value):
        text=str(value.get('text','')).strip()
        lower=text.lower()
        if not text and not (value.get('object') or value.get('person')):
            raise ValueError('Ask about a person, object or your next activity.')
        if any(k in lower for k in ('medicine','medication','dose','dawai','दवा')):
            return {'status':'unconfirmed','response':'I cannot confirm a medicine dose from camera images. Please check with your caretaker before taking medicine.'}
        if any(k in lower for k in ('who am i','mera naam','मेरा नाम')):
            introduction=store.get('patient_introduction','')
            return {'status':'approved' if introduction else 'not_found',
                'response':introduction or 'Your caretaker has not added a personal introduction yet. Shall we ask them for help?'}
        if re.search(r'\bhelp\b',lower) or any(k in lower for k in ('madad','मदद')):
            result=request_help(text[:500])
            routines,summary=schedule_summary()
            confirmation=('I have saved your help request. I am sending your caretaker a Telegram alert. Delivery is not confirmed yet.'
                if result['delivery']=='queued' else
                'I have saved your help request, but the Telegram alert could not be queued. Please call your caretaker directly.')
            return {'status':'help','help':result,'routines':routines,'response':confirmation+' '+summary}
        if any(k in lower for k in ('schedule','routines','routine today','today\u2019s routine',"today's routine",'daily routine','my routine')):
            routines,summary=schedule_summary()
            return {'status':'schedule','routines':routines,'response':summary}
        if any(k in lower for k in ('what next','what should i do','next activity','ab kya','अब क्या')):
            pending=[r for r in routine_list() if r['enabled'] and r['step']<len(r['steps'])]
            due=[r for r in pending if r['time']<=datetime.now().strftime('%H:%M')]
            target=due[-1] if due else (pending[0] if pending else None)
            return {'status':'routine','routine':target,'response':f"{target['title']}: {target['steps'][target['step']]}"} if target else {'status':'not_found','response':'There are no unfinished approved routines for today.'}
        for a in store.rows('SELECT * FROM answers WHERE deleted=0'):
            if a['expires'] and datetime.fromisoformat(a['expires'].replace('Z','+00:00')).astimezone(timezone.utc)<datetime.now(timezone.utc):
                continue
            if a['question'].lower().strip(' ?')==lower.strip(' ?'):
                return {'status':'approved','response':a['answer']}
        if any(k in lower for k in ('who is this','who is in front','yeh kaun','ये कौन')):
            latest=next((e for e in store.events(PATIENT,20) if e['source']=='camera'),None)
            if latest and (datetime.now(timezone.utc)-datetime.fromisoformat(latest['last_seen'])).total_seconds()<30 and latest['people']:
                return {'status':'found','response':'. '.join(p.get('introduction') or f"This is {p['name']}"+(f", your {p['relationship']}" if p.get('relationship') else '') for p in latest['people']),'event':event_json(latest)}
            return {'status':'not_found','response':'I do not have a recent, reliable person identification. Please ask your caretaker.'}
        names=store.rows('SELECT id,name,relationship,introduction FROM people WHERE deleted=0 ORDER BY name')
        def mentioned(phrase):
            return bool(phrase and re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',lower))
        relationship_aliases={'mom':'mother','mum':'mother','mummy':'mother','dad':'father','daddy':'father',
            'grandma':'grandmother','granny':'grandmother','grandpa':'grandfather'}
        def relation_key(value):
            key=re.sub(r'^(my|your)\s+','',str(value or '').strip().lower())
            return relationship_aliases.get(key,key)
        relationships={relation_key(p['relationship']) for p in names if p['relationship']}
        relationships.update(('daughter','son','mother','father','brother','sister','wife','husband',
            'grandmother','grandfather','granddaughter','grandson','friend','caretaker','caregiver'))
        terms={term:term for term in relationships}
        terms.update(relationship_aliases)
        relation=next((terms[term] for term in sorted(terms,key=len,reverse=True) if mentioned(term)),None)
        person=str(value.get('person','')).strip().lower() or next((p['name'].lower() for p in sorted(names,key=lambda p:len(p['name']),reverse=True) if mentioned(p['name'].lower())),None)
        profile=next((p for p in names if p['name'].lower()==person),None)
        identity=bool(re.search(r'\bwho\s+(?:is|are)\b|\btell me about\b|\bwhat\b.*\bname\b',lower)) and not re.search(r'\bwhere\b|\blast seen\b',lower)
        if not person and relation:
            relatives=[p for p in names if relation_key(p['relationship'])==relation]
            if not relatives:
                return {'status':'not_found','response':f"Your caretaker has not enrolled anyone as your {relation}. Please ask them to add this relationship in People."}
            if identity:
                response=' '.join(f"{p['name']} is your {relation}."+(f" {p['introduction']}" if p['introduction'] else '') for p in relatives)
                return {'status':'approved','response':response,'people':relatives}
            if len(relatives)>1:
                choices=', '.join(p['name'] for p in relatives)
                return {'status':'clarify','response':f"I have more than one person enrolled as your {relation}: {choices}. Whose last sighting would you like? Please ask using their name."}
            profile=relatives[0]
            person=profile['name'].lower()
        if identity and profile:
            relationship=f"your {relation_key(profile['relationship'])}" if profile['relationship'] else 'an enrolled person'
            return {'status':'approved','response':f"{profile['name']} is {relationship}."+(f" {profile['introduction']}" if profile['introduction'] else ''),'people':[profile]}
        aliases={'phone':'cell phone','mobile':'cell phone','mobile phone':'cell phone','फोन':'cell phone','chair':'chair','कुर्सी':'chair','bottle':'bottle','बोतल':'bottle','laptop':'laptop','remote':'remote','book':'book','keys':'keys','glasses':'glasses'}
        obj=value.get('object')
        if obj:
            obj=aliases.get(str(obj).lower(),str(obj).lower())
        else:
            for word in sorted(set(vision.labels+list(aliases)),key=len,reverse=True):
                if re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',lower):
                    obj=aliases.get(word,word)
                    break
        if not person and not obj:
            return {'status':'not_found','response':'Ask about an enrolled person or supported object, such as “Have you seen my phone?”'}
        matching=[e for e in store.events(PATIENT,2000) if (not person or any(p['name'].lower()==person for p in e['people'])) and (not obj or obj in [o.lower() for o in e['objects']])]
        if not matching:
            return {'status':'not_found','response':f"I do not have a recorded sighting of {person or obj}. Please ask your caretaker."}
        event=matching[0]
        when=datetime.fromisoformat(event['last_seen']).astimezone().strftime('%d %b %Y at %I:%M %p')
        person_label=(profile['name']+(f", your {relation_key(profile['relationship'])}," if profile['relationship'] else '')) if profile else person
        subject=' and '.join(x for x in (person_label,obj) if x)
        location=f" by the {event['location']} camera" if event['location'] and event['location_source']=='configured camera' else (f" in {event['location']}" if event['location'] else '; the place was not confirmed')
        response=f"{subject[0].upper()+subject[1:]} was last recorded{location} on {when}. This is a past sighting, not a confirmed current location."
        if obj and any(k in lower for k in ('my ','mera','मेरे','मेरा')):
            response+=' I cannot confirm ownership from generic object detection.'
        return {'status':'found','response':response,'event':event_json(event)}

    @app.post('/api/query')
    @app.post('/query')
    @auth
    def query():
        return jsonify(answer_query(body()))

    @app.route('/api/routines',methods=['GET','POST'])
    @auth
    def routines():
        if request.method=='GET':
            return jsonify(routine_list())
        value=body()
        steps=value.get('steps',[])
        if not value.get('title') or not isinstance(steps,list) or not steps or not all(isinstance(s,str) and s.strip() for s in steps):
            raise ValueError('Enter a name and at least one nonempty step.')
        if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',value.get('time','')):
            raise ValueError('Choose a valid time.')
        ident=uid()
        store.execute('INSERT INTO routines(id,title,time,steps) VALUES(?,?,?,?)',(ident,str(value['title'])[:120],value['time'],json.dumps(steps)))
        return jsonify(id=ident),201

    @app.route('/api/routines/<ident>',methods=['PATCH','DELETE'])
    @auth
    def routine_progress(ident):
        if request.method=='DELETE':
            store.execute('UPDATE routines SET deleted=1 WHERE id=?',(ident,))
            return jsonify(ok=True)
        value=body()
        routine=next((r for r in routine_list() if r['id']==ident),None)
        if not routine:
            return jsonify(error='Routine not found.'),404
        if any(key in value for key in ('title','time','steps')):
            title=str(value.get('title',routine['title'])).strip()
            schedule=value.get('time',routine['time'])
            steps=value.get('steps',routine['steps'])
            if not title or not isinstance(steps,list) or not steps or not all(isinstance(s,str) and s.strip() for s in steps):
                raise ValueError('Enter a name and at least one nonempty step.')
            if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',schedule):
                raise ValueError('Choose a valid time.')
            store.execute('UPDATE routines SET title=?,time=?,steps=? WHERE id=?',(title[:120],schedule,json.dumps(steps),ident))
            if steps!=routine['steps']:
                store.execute('DELETE FROM progress WHERE routine_id=? AND day=?',(ident,datetime.now().date().isoformat()))
        if 'enabled' in value:
            store.execute('UPDATE routines SET enabled=? WHERE id=?',(bool(value['enabled']),ident))
        if value.get('action') in ('done','reset'):
            step=0 if value['action']=='reset' else min(routine['step']+1,len(routine['steps']))
            store.execute('INSERT INTO progress VALUES(?,?,?,?) ON CONFLICT(routine_id,day) DO UPDATE SET step=excluded.step,completed=excluded.completed',
                (ident,datetime.now().date().isoformat(),step,now()))
        return jsonify(ok=True)

    @app.route('/api/answers',methods=['GET','POST'])
    @auth
    def approved_answers():
        if request.method=='GET':
            return jsonify(store.rows('SELECT * FROM answers WHERE deleted=0'))
        value=body()
        if not str(value.get('question','')).strip() or not str(value.get('answer','')).strip():
            raise ValueError('Enter a question and approved answer.')
        expiry=value.get('expires') or None
        if expiry:
            datetime.fromisoformat(expiry.replace('Z','+00:00'))
        ident=uid()
        store.execute('INSERT INTO answers(id,question,answer,expires) VALUES(?,?,?,?)',(ident,value['question'],value['answer'],expiry))
        return jsonify(id=ident),201

    @app.delete('/api/answers/<ident>')
    @auth
    def delete_answer(ident):
        store.execute('UPDATE answers SET deleted=1 WHERE id=?',(ident,))
        return jsonify(ok=True)

    @app.get('/api/recap')
    @auth
    def daily_recap():
        today=datetime.now().date()
        records=[e for e in store.events(PATIENT,2000) if e['verified'] and datetime.fromisoformat(e['last_seen']).astimezone().date()==today]
        completed=[r for r in routine_list() if r['step']==len(r['steps'])]
        return jsonify(date=today.isoformat(),events=[event_json(e) for e in records],routines=[r['title'] for r in completed])

    def notify(text,image=None):
        if not store.get('telegram_enabled') or not store.get('telegram_token') or not store.get('telegram_chat'):
            raise ValueError('Configure and enable Telegram in Settings first.')
        ident=uid()
        store.execute('INSERT INTO notifications VALUES(?,?,?,NULL)',(ident,now(),'queued'))
        try:
            notifications.put_nowait((ident,text,image))
        except queue.Full:
            store.execute('UPDATE notifications SET status=?,error=? WHERE id=?',('failed','Queue full',ident))
            raise ValueError('Notification queue full. Retry later.')
        return ident

    @app.post('/api/telegram')
    @auth
    def telegram():
        value=body()
        if value.get('event_id'):
            event=next((e for e in store.events(PATIENT,2000) if e['id']==value['event_id']),None)
            if not event or not event['image'] or not Path(event['image']).exists():
                raise ValueError('No evidence photo available.')
            text=f"SAHAYAK last recorded sighting\n{', '.join(p['name'] for p in event['people'])}\n{', '.join(event['objects'])}\n{event['last_seen']}\nPlace: {event['location'] or 'unconfirmed'}"
            ident=notify(text,event['image'])
        else:
            ident=notify('SAHAYAK connection test. Caretaker notifications are connected.')
        return jsonify(id=ident,status='queued'),202

    @app.route('/api/help',methods=['GET','POST'])
    @auth
    def help_requests():
        if request.method=='GET':
            return jsonify(store.rows('''SELECT h.*,n.status delivery,n.error delivery_error FROM help h
                LEFT JOIN notifications n ON h.notification=n.id ORDER BY h.created DESC LIMIT 50'''))
        message=str(body().get('message','Please help me.'))[:500]
        return jsonify(request_help(message)),201

    @app.patch('/api/help/<ident>')
    @auth
    def acknowledge(ident):
        store.execute('UPDATE help SET status=?,acknowledged=? WHERE id=?',('acknowledged',now(),ident))
        return jsonify(ok=True)

    @app.post('/api/audio/listen')
    @auth
    def listen():
        if not local():
            return jsonify(error='Control the laptop microphone from localhost.'),403
        if not audio:
            raise ValueError('Audio service unavailable.')
        if runtime['listening']:
            raise ValueError('Already listening.')
        runtime['listening']=True
        try:
            transcript=audio.listen(store.get('language','en-IN'))
            return jsonify(text=transcript,**answer_query({'text':transcript}))
        finally:
            runtime['listening']=False

    @app.post('/api/audio/speak')
    @auth
    def speak():
        if not local():
            return jsonify(error='Control the laptop speaker from localhost.'),403
        if not audio:
            raise ValueError('Audio service unavailable.')
        audio.speak(str(body().get('text','')))
        return jsonify(status='queued')

    @app.post('/api/audio/cancel')
    @auth
    def cancel_listening():
        if not local():
            return jsonify(error='Control the laptop microphone from localhost.'),403
        if audio:
            audio.cancel()
        return jsonify(status='cancelling')

    def processor():
        vision.load()
        # Existing reference photos are offered for review, never automatically approved.
        if vision.ready and not store.get('reference_photos_imported'):
            try:
                for path in sorted((BASE/'sahayak_cloud/known_faces').glob('*')):
                    if path.suffix.lower() not in ('.jpg','.jpeg','.png'):
                        continue
                    name=path.stem.split('_')[0]
                    rows=store.rows('SELECT id FROM people WHERE name=? AND deleted=0',(name,))
                    ident=rows[0]['id'] if rows else uid()
                    if not rows:
                        store.execute('INSERT INTO people(id,name,relationship,introduction,created) VALUES(?,?,?,?,?)',(ident,name,'','',now()))
                    try:
                        feature=vision.enrollment(cv2.imread(str(path)))
                        store.execute('INSERT INTO samples VALUES(?,?,?,?,0,?)',(uid(),ident,str(path.resolve()),json.dumps(feature),now()))
                    except ValueError:
                        continue
                store.set('reference_photos_imported',True)
            except Exception:
                logging.exception('Reference photo import failed')
        while True:
            device,path,room,stamp=frames.get()
            started=time.perf_counter()
            runtime['last_queue_ms']=round(max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds()*1000))
            try:
                image=cv2.imread(path)
                enrollment=runtime['enrollment']
                if enrollment and enrollment['device_id']==device:
                    collect_enrollment_frame(enrollment,image,stamp,path)
                detections,people=vision.infer(image)
                objects=sorted(set(d['label'] for d in detections))
                if people or objects:
                    store.record_observation(PATIENT,device,stamp,room,path,objects,people,detections)
                else:
                    discard_empty_frame(store,images,path)
                runtime['processed']+=1
                runtime['last_error']=None
            except Exception as exc:
                logging.exception('Frame processing failed')
                runtime['last_error']=str(exc)
                store.execute('UPDATE devices SET error=? WHERE id=?',(str(exc),device))
            finally:
                runtime['last_processing_ms']=round((time.perf_counter()-started)*1000)
                frames.task_done()

    def notifier():
        while True:
            ident,text,image=notifications.get()
            error=None
            for attempt in range(3):
                try:
                    url='https://api.telegram.org/bot'+store.get('telegram_token')
                    payload={'chat_id':store.get('telegram_chat')}
                    if image:
                        with open(image,'rb') as photo:
                            response=requests.post(url+'/sendPhoto',data=payload|{'caption':text[:1000]},files={'photo':photo},timeout=20)
                    else:
                        response=requests.post(url+'/sendMessage',json=payload|{'text':text},timeout=20)
                    if not response.ok or not response.json().get('ok'):
                        raise ValueError('Telegram rejected the request.')
                    error=None
                    break
                except Exception:
                    error='Delivery failed. Check Telegram credentials, bot access and internet.'
                    time.sleep(attempt+1)
            store.execute('UPDATE notifications SET status=?,error=? WHERE id=?',('failed' if error else 'sent',error,ident))
            notifications.task_done()

    def maintenance():
        while True:
            try:
                cutoff=(datetime.now(timezone.utc)-timedelta(days=store.get('retention_days',30))).isoformat()
                store.execute('UPDATE events SET deleted=1 WHERE source=? AND last_seen<?',('camera',cutoff))
                refs={r['image'] for r in store.rows('SELECT image FROM events WHERE deleted=0') if r['image']}
                refs|={r['image'] for r in store.rows('SELECT image FROM devices') if r['image']}
                refs|={r['path'] for r in store.rows('SELECT path FROM samples')}
                for path in images.glob('*.jpg'):
                    if str(path) not in refs and time.time()-path.stat().st_mtime>3600:
                        path.unlink(missing_ok=True)
            except Exception:
                logging.exception('Maintenance failed')
            time.sleep(300)

    dist=BASE/'Web Interface/dist'

    @app.get('/api/health')
    def health():
        return jsonify(status='running',service='SAHAYAK')

    @app.route('/',defaults={'path':''})
    @app.route('/<path:path>')
    def frontend(path):
        if path.startswith('api/'):
            return jsonify(error='Endpoint not found.'),404
        if not dist.exists():
            return jsonify(status='Backend ready. Build frontend or run Vite on port 8080.')
        target=(dist/path).resolve()
        if path and target.is_relative_to(dist.resolve()) and target.is_file():
            return send_from_directory(dist,path)
        return send_from_directory(dist,'index.html')

    if start_workers:
        for target in (processor,notifier,maintenance):
            threading.Thread(target=target,daemon=True).start()
    return app
