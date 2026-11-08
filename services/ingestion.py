"""Append-only file ingestion with gated, atomic manifest publication.
Readers see the prior complete manifest until the new batch has passed validation.
"""
import hashlib,json,os,shutil,uuid
from pathlib import Path
from sql.data_engine import DataEngine
from services.monitoring import monitor

def publish_batch(source, directory, thresholds=None, max_age_hours=None):
    source=Path(source).resolve();root=Path(directory).resolve();root.mkdir(parents=True,exist_ok=True)
    lock=root/'.publish.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise RuntimeError('Another publisher holds the ingestion lock')
    os.close(fd)
    candidate=None;temporary=None
    try:
        digest=hashlib.sha256()
        with source.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        sha=digest.hexdigest();manifest=root/'manifest.json'
        previous=json.loads(manifest.read_text()) if manifest.exists() else {'version':0,'files':[],'digests':[]}
        if sha in previous['digests']:
            return {'status':'already_ingested','version':previous['version'],'manifest':str(manifest)}
        candidate=root/f'{sha}.parquet'
        if not candidate.exists():
            temporary=root/f'.{uuid.uuid4().hex}.parquet'
            shutil.copyfile(source,temporary)
            with temporary.open('rb') as f:os.fsync(f.fileno())
            os.replace(temporary,candidate)
        files=previous['files']+[str(candidate)]
        with DataEngine(files) as engine:
            report=monitor(engine,thresholds,max_age_hours)
        if not report['passed']:
            raise ValueError('Quality gate failed: '+json.dumps(report))
        payload={'version':previous['version']+1,'files':files,'digests':previous['digests']+[sha],
                 'events':report['events'],'latest_event':report['latest_event']}
        temporary=root/f'.manifest-{uuid.uuid4().hex}.json'
        with temporary.open('w') as f:
            json.dump(payload,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temporary,manifest)
        return {'status':'published','version':payload['version'],'manifest':str(manifest),'events':payload['events']}
    finally:
        if temporary and temporary.exists():temporary.unlink()
        lock.unlink(missing_ok=True)
