import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from acme_support import indexing, settings


def test_successful_index_is_reused(tmp_path,monkeypatch):
    manifest=tmp_path/'index.json'
    monkeypatch.setattr(indexing,'INDEX_PATH',manifest)
    store=SimpleNamespace(id='vs_test',status='completed',file_counts=SimpleNamespace(completed=23))
    batch=SimpleNamespace(status='completed',file_counts=SimpleNamespace(completed=23,failed=0))
    api=SimpleNamespace(vector_stores=SimpleNamespace(create=Mock(return_value=store),retrieve=Mock(return_value=store),file_batches=SimpleNamespace(upload_and_poll=Mock(return_value=batch))))
    monkeypatch.setattr(indexing,'client',lambda:api)
    assert indexing.index_knowledge()=='vs_test'
    assert len(json.loads(manifest.read_text())['files'])==23
    assert indexing.index_knowledge()=='vs_test'
    assert api.vector_stores.create.call_count==1
    assert api.vector_stores.file_batches.upload_and_poll.call_count==1


def test_failed_index_not_offered_to_agent(tmp_path,monkeypatch):
    manifest=tmp_path/'index.json'
    monkeypatch.setattr(indexing,'INDEX_PATH',manifest)
    monkeypatch.setattr(settings,'INDEX_PATH',manifest)
    monkeypatch.delenv('OPENAI_VECTOR_STORE_ID',raising=False)
    batch=SimpleNamespace(status='completed',file_counts=SimpleNamespace(completed=22,failed=1))
    api=SimpleNamespace(vector_stores=SimpleNamespace(create=Mock(return_value=SimpleNamespace(id='vs_failed')),file_batches=SimpleNamespace(upload_and_poll=Mock(return_value=batch))))
    monkeypatch.setattr(indexing,'client',lambda:api)
    with pytest.raises(ValueError):
        indexing.index_knowledge()
    assert settings.vector_store_id() is None
