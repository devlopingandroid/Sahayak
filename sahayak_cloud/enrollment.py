"""Capture first, name later face enrollment. Temporary photos stay local."""
import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np


class FaceRecording:
    def __init__(self, store, vision, save_image):
        self.store, self.vision, self.save_image = store, vision, save_image
        self.lock = threading.RLock()
        self.session = None

    def status(self):
        with self.lock:
            s = self.session
            if not s:
                return None
            if s['state'] == 'capturing' and time.monotonic() > s['deadline']:
                s['state'] = 'awaiting_name' if len(s['photos']) >= 7 else 'timed_out'
                s['guidance'] = ('What name should I give this person?' if len(s['photos']) >= 7
                    else 'Not enough clear, varied photos. Cancel and try again with better light.')
            return {'id': s['id'], 'device_id': s['device_id'], 'state': s['state'],
                'captured': len(s['photos']), 'target': 8, 'guidance': s['guidance'],
                'person_id': s.get('person_id')}

    def active(self):
        status = self.status()
        return bool(status and status['state'] in ('capturing', 'awaiting_name', 'timed_out'))

    def protected_paths(self):
        with self.lock:
            return {p['path'] for p in self.session['photos']} if self.session else set()

    def start(self, device, image, stamp):
        with self.lock:
            if self.active():
                raise ValueError('A person recording is already open. Finish or cancel it first.')
            self.session = {'id': uuid.uuid4().hex, 'device_id': device, 'state': 'capturing',
                'photos': [], 'last_stamp': None, 'deadline': time.monotonic() + 150,
                'guidance': 'Keep one person in view. Slowly look left, right, up and straight ahead.'}
            self.feed(device, image, stamp)
            return self.status()

    def feed(self, device, image, stamp):
        with self.lock:
            self.status()
            s = self.session
            if not s or s['state'] != 'capturing' or device != s['device_id']:
                return
            if s['last_stamp'] and (datetime.fromisoformat(stamp) - datetime.fromisoformat(s['last_stamp'])).total_seconds() < 1:
                return
            try:
                candidate = self.vision.enrollment_candidate(image)
                if s['photos']:
                    if float(np.dot(candidate['feature'], s['photos'][0]['feature'])) < .45:
                        raise ValueError('Keep the same person in view throughout this recording.')
                    if any(np.count_nonzero(candidate['hash'] != p['hash']) < 5 for p in s['photos']):
                        raise ValueError('Photo looks too similar. Slowly change your face angle or expression.')
                path = self.save_image(image)
                s['photos'].append(candidate | {'path': path})
                s['last_stamp'] = stamp
                s['guidance'] = 'Good photo saved. Slowly change your face angle for the next photo.'
                if len(s['photos']) == 8:
                    s.update(state='awaiting_name', guidance='What name should I give this person?')
            except ValueError as exc:
                s['guidance'] = str(exc)

    def image(self, ident, index):
        with self.lock:
            if not self.session or self.session['id'] != ident or not 0 <= index < len(self.session['photos']):
                return None
            return self.session['photos'][index]['path']

    def finish(self, ident, name, relationship=''):
        name, relationship = name.strip(), relationship.strip()
        if not name or len(name) > 80 or len(relationship) > 120:
            raise ValueError('Enter a name up to 80 characters and a relationship up to 120 characters.')
        with self.lock:
            s = self.session
            if not s or s['id'] != ident:
                raise ValueError('This recording is no longer available.')
            if s['state'] == 'saved':
                return {'id': s['person_id'], 'name': s['name'], 'samples': len(s['photos'])}
            self.status()
            if s['state'] != 'awaiting_name' or len(s['photos']) < 7:
                raise ValueError('Wait for at least seven clear photos before saving.')
            if not all(Path(p['path']).is_file() for p in s['photos']):
                raise ValueError('A captured photo is no longer available. Cancel and record this person again.')
            person = uuid.uuid4().hex
            stamp = datetime.now().astimezone().isoformat()
            with self.store.connect() as db:
                db.execute('INSERT INTO people(id,name,relationship,introduction,created) VALUES(?,?,?,?,?)',
                    (person, name, relationship, '', stamp))
                for photo in s['photos']:
                    db.execute('INSERT INTO samples VALUES(?,?,?,?,1,?)',
                        (uuid.uuid4().hex, person, photo['path'], json.dumps(photo['feature'].tolist()), stamp))
            s.update(state='saved', person_id=person, name=name, guidance='Saved on this laptop and ready for recognition.')
            return {'id': person, 'name': name, 'samples': len(s['photos'])}

    def cancel(self, ident):
        with self.lock:
            s = self.session
            if not s or s['id'] != ident:
                raise ValueError('This recording is no longer available.')
            if s['state'] != 'saved':
                for photo in s['photos']:
                    Path(photo['path']).unlink(missing_ok=True)
            self.session = None
