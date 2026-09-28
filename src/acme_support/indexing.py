"""Explicit corpus upload; never uploads operational data or user prompt logs."""
import hashlib
import json
from contextlib import ExitStack
from openai import NotFoundError
from .agent import client
from .seed import write_sources
from .settings import CORPUS, INDEX_PATH


def index_knowledge(on_progress=lambda message: None):
    api = client()
    write_sources()
    paths = sorted(CORPUS.glob('*.md'))
    digest = hashlib.sha256(b''.join(p.name.encode()+p.read_bytes() for p in paths)).hexdigest()
    if INDEX_PATH.exists():
        old = json.loads(INDEX_PATH.read_text())
        if old.get('sha256') == digest and old.get('status') == 'completed':
            try:
                store = api.vector_stores.retrieve(old['vector_store_id'])
            except NotFoundError:
                store = None
            if store and store.status == 'completed' and store.file_counts.completed == len(paths):
                on_progress('Existing knowledge index is ready.')
                return old['vector_store_id']
    store = api.vector_stores.create(name='Acme Support demo · 9 KB + 14 historical tickets',expires_after={'anchor':'last_active_at','days':7})
    manifest = dict(vector_store_id=store.id,sha256=digest,status='indexing',files=[p.name for p in paths])
    INDEX_PATH.parent.mkdir(parents=True,exist_ok=True)
    INDEX_PATH.write_text(json.dumps(manifest,indent=2))
    on_progress(f'Uploading {len(paths)} synthetic documents…')
    with ExitStack() as stack:
        files = [stack.enter_context(p.open('rb')) for p in paths]
        batch = api.vector_stores.file_batches.upload_and_poll(store.id,files=files,max_concurrency=3)
    if batch.status != 'completed' or batch.file_counts.failed or batch.file_counts.completed != len(paths):
        manifest['status']='failed'
        INDEX_PATH.write_text(json.dumps(manifest,indent=2))
        raise ValueError('Indexing did not complete for every document. Retry setup; inspect the vector store if needed.')
    manifest['status']='completed'
    INDEX_PATH.write_text(json.dumps(manifest,indent=2))
    on_progress('Knowledge index ready.')
    return store.id
