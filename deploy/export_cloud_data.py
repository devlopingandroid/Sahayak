"""Make a private, consistent migration archive; never publish it with source."""
import argparse
import hashlib
import sqlite3
import tarfile
import tempfile
from contextlib import closing
from pathlib import Path


def export_data(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not (source/'sahayak.sqlite3').is_file():
        raise ValueError('The source directory must contain sahayak.sqlite3.')
    if output.exists():
        raise ValueError('Choose a new output filename; an archive already exists there.')
    with tempfile.TemporaryDirectory(prefix='sahayak-cloud-export-') as folder:
        target = Path(folder)/'sahayak.sqlite3'
        with closing(sqlite3.connect(source/'sahayak.sqlite3')) as original, closing(sqlite3.connect(target)) as backup:
            original.backup(backup)
        files = {}
        missing = 0
        with closing(sqlite3.connect(target)) as db, db:
            for table, column in (('events','image'),('devices','image'),('samples','path')):
                values=db.execute(f'SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL').fetchall()
                for (value,) in values:
                    path=Path(value)
                    if not path.is_file():
                        missing+=1
                        # Preserve the record but don't retain Windows-only paths.
                        replacement='/data/images/missing_'+hashlib.sha256(value.encode()).hexdigest()+'.jpg' if column=='path' else None
                        db.execute(f'UPDATE {table} SET {column}=? WHERE {column}=?',(replacement,value))
                        continue
                    name=hashlib.sha256(str(path.resolve()).encode()).hexdigest()+path.suffix.lower()
                    files[name]=path
                    db.execute(f'UPDATE {table} SET {column}=? WHERE {column}=?',('/data/images/'+name,value))
            # Cloud camera requests must be authenticated even for migrated setups.
            db.execute("INSERT INTO settings VALUES('allow_legacy_upload','false') ON CONFLICT(key) DO UPDATE SET value='false'")
            db.execute("UPDATE notifications SET status='failed',error='Migration interrupted unconfirmed delivery; resend if needed.' WHERE status='queued'")
        output.parent.mkdir(parents=True,exist_ok=True)
        try:
            with tarfile.open(output,'w:gz') as archive:
                archive.add(target,arcname='sahayak.sqlite3')
                for name,path in files.items():
                    archive.add(path,arcname='images/'+name)
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return {'images':len(files),'missing_images':missing,'archive':str(output)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=export_data(args.source,args.output)
    print('Private archive created: '+result['archive'])
    print(f"Images included: {result['images']}; missing historical image references: {result['missing_images']}")
    print('This archive contains private photos, credentials and memory records. Transfer only to your private backend storage.')
