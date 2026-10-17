"""Local SQLite storage. Existing JSON files are imported, never overwritten."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS people(id TEXT PRIMARY KEY,name TEXT NOT NULL,relationship TEXT,
              introduction TEXT,created TEXT NOT NULL,deleted INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS samples(id TEXT PRIMARY KEY,person_id TEXT NOT NULL,path TEXT NOT NULL,
              embedding TEXT,approved INTEGER DEFAULT 0,created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,patient_id TEXT NOT NULL,device_id TEXT,
              first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,location TEXT,location_source TEXT,
              people TEXT NOT NULL,objects TEXT NOT NULL,detections TEXT NOT NULL,image TEXT,
              verified INTEGER DEFAULT 0,source TEXT,deleted INTEGER DEFAULT 0,frames INTEGER DEFAULT 1);
            CREATE INDEX IF NOT EXISTS events_patient_time ON events(patient_id,last_seen);
            CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,last_seen TEXT,image TEXT,location TEXT,
              frames INTEGER DEFAULT 0,error TEXT);
            CREATE TABLE IF NOT EXISTS routines(id TEXT PRIMARY KEY,title TEXT NOT NULL,time TEXT NOT NULL,
              steps TEXT NOT NULL,enabled INTEGER DEFAULT 1,deleted INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS progress(routine_id TEXT,day TEXT,step INTEGER DEFAULT 0,
              completed TEXT,PRIMARY KEY(routine_id,day));
            CREATE TABLE IF NOT EXISTS answers(id TEXT PRIMARY KEY,question TEXT NOT NULL,answer TEXT NOT NULL,
              expires TEXT,deleted INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS help(id TEXT PRIMARY KEY,message TEXT,created TEXT,status TEXT,
              acknowledged TEXT,notification TEXT);
            CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY,created TEXT,status TEXT,error TEXT);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def rows(self, sql, args=()):
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args).fetchall()]

    def execute(self, sql, args=()):
        with self.connect() as db:
            db.execute(sql, args)

    def get(self, key, default=None):
        rows = self.rows('SELECT value FROM settings WHERE key=?', (key,))
        return json.loads(rows[0]['value']) if rows else default

    def set(self, key, value):
        self.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                     (key, json.dumps(value)))

    def events(self, patient, limit=100):
        rows = self.rows('SELECT * FROM events WHERE patient_id=? AND deleted=0 ORDER BY last_seen DESC LIMIT ?',
                         (patient, limit))
        for row in rows:
            for key in ('people', 'objects', 'detections'):
                row[key] = json.loads(row[key])
        return rows

    def record_observation(self, patient, device, stamp, room, path, objects, people, detections):
        """Group matching encounters, preserving caretaker-confirmed records."""
        previous=self.events(patient,1)
        latest=previous[0] if previous else None
        same=(latest and not latest['verified'] and latest['source']=='camera'
            and latest['device_id']==device and latest['location']==(room or None)
            and latest['objects']==objects
            and sorted(p['id'] for p in latest['people'])==sorted(p['id'] for p in people)
            and 0<=(datetime.fromisoformat(stamp)-datetime.fromisoformat(latest['last_seen'])).total_seconds()<60)
        if same:
            self.execute('UPDATE events SET last_seen=?,image=?,detections=?,people=?,frames=frames+1 WHERE id=?',
                (stamp,path,json.dumps(detections),json.dumps(people),latest['id']))
            return latest['id']
        ident=uuid.uuid4().hex
        self.execute('''INSERT INTO events(id,patient_id,device_id,first_seen,last_seen,location,location_source,people,objects,detections,image,source)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(ident,patient,device,stamp,stamp,room or None,
            'configured camera' if room else 'unknown',json.dumps(people),json.dumps(objects),json.dumps(detections),path,'camera'))
        return ident

    def import_legacy(self, root, patient):
        if self.get('legacy_imported', False):
            return
        import hashlib
        for file in (root / 'memory_db.json', root / 'sahayak_cloud/memory_db.json'):
            if not file.exists():
                continue
            try:
                entries = json.loads(file.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                continue
            for entry in entries:
                ident = 'legacy-' + hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()[:24]
                who = entry.get('Who', 'Unknown')
                stamp = entry.get('When', now())
                if not datetime.fromisoformat(stamp).tzinfo:
                    # Legacy server used laptop local time; preserve it with its local UTC offset.
                    stamp = datetime.fromisoformat(stamp).astimezone().isoformat()
                evidence = entry.get('Evidence', '')
                candidates = [file.parent / evidence, root / evidence]
                image = next((str(p.resolve()) for p in candidates if p.is_file()), None)
                self.execute('''INSERT OR IGNORE INTO events
                    (id,patient_id,device_id,first_seen,last_seen,location,location_source,people,objects,detections,image,source)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (ident, patient, 'legacy', stamp, stamp, None, 'unknown',
                     json.dumps([{'name': who, 'id': None}] if who != 'Unknown' else []),
                     json.dumps(entry.get('What', [])), '[]', image, 'legacy import'))
        self.set('legacy_imported', True)
