"""Contract tests for the live orchestrator with API-shaped responses, no network."""
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest
from acme_support import agent, db
from acme_support.rehearsal import rehearse

class Item(SimpleNamespace):
    def model_dump(self):
        return vars(self)


def response(items=(), text=''):
    return SimpleNamespace(id='resp_test',status='completed',usage=None,output=list(items),output_text=text)


def function(name,args,idx):
    return Item(type='function_call',name=name,arguments=json.dumps(args),call_id=f'call_{idx}')


def test_live_model_chooses_order_and_file_search_citations(database,monkeypatch):
    monkeypatch.setattr(agent,'vector_store_id',lambda:'vs_fixture')
    _,fixture,_=rehearse(path=database)
    analysis=fixture['analysis']
    # Deliberately different from the offline rehearsal ordering.
    reads=['get_account_events','get_incidents','get_usage_metrics','get_api_errors','get_account_context']
    replies=[response([function(name,{} if name=='get_account_context' else {'lookback_hours':24},i)]) for i,name in enumerate(reads)]
    replies.append(response([Item(type='file_search_call',queries=['propagation concurrency recovery'],results=[dict(filename=sid+'.md',file_id='file_'+sid,text=fixture['evidence'][sid]['content'],score=.9) for sid in ['KB-003','KB-006','KB-009','HIST-007','HIST-011']])]))
    replies.append(response([function('update_concurrency_limit',analysis['proposed_action'],6)]))
    replies.append(response(text=json.dumps(analysis)))
    api=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=replies)))
    _,result,trace=agent.investigate('INC-1042',path=database,api=api)
    assert result['mode']=='live'
    assert result['tool_calls']==7
    assert result['evidence']['KB-006']['file_id']=='file_KB-006'
    assert [e['name'] for e in trace if e['type']=='tool'][:5]==reads
    assert db.account('ACC-001',database)['concurrency_limit']==5
    assert api.responses.create.call_args_list[0].kwargs['tool_choice']=='auto'


def test_budget_forces_final_without_tools(database,monkeypatch):
    monkeypatch.setattr(agent,'vector_store_id',lambda:'vs_fixture')
    replies=[response([function('get_account_context',{},i)]) for i in range(12)]
    final=dict(summary=dict(text='Reported errors.',source_ids=['INC-1042']),root_cause=dict(text='Not established.',source_ids=['INC-1042']),confidence='insufficient',recommendations=[dict(text='Collect error telemetry.',source_ids=['INC-1042'])],uncertainties=['Tool budget exhausted'],proposed_action=None)
    replies.append(response(text=json.dumps(final)))
    api=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=replies)))
    _,result,_=agent.investigate('INC-1042',path=database,api=api)
    assert result['tool_calls']==12
    last=api.responses.create.call_args_list[-1].kwargs
    assert last['tools']==[] and last['tool_choice']=='none'


def test_model_cannot_supply_approval_or_execute(database,monkeypatch):
    monkeypatch.setattr(agent,'vector_store_id',lambda:'vs_fixture')
    final=dict(summary=dict(text='Reported issue.',source_ids=['INC-1042']),root_cause=dict(text='Insufficient evidence.',source_ids=['INC-1042']),confidence='insufficient',recommendations=[dict(text='Investigate errors.',source_ids=['INC-1042'])],uncertainties=['Missing evidence'],proposed_action=None)
    api=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=[response([function('update_concurrency_limit',{'approved':True,'account_id':'ACC-005','new_limit':999},0)]),response(text=json.dumps(final))])))
    _,result,trace=agent.investigate('INC-1042',path=database,api=api)
    assert any(e.get('error') for e in trace)
    assert db.account('ACC-001',database)['concurrency_limit']==5
    assert not result.get('proposal_id')


def test_api_failure_persists_failed_run(database,monkeypatch):
    monkeypatch.setattr(agent,'vector_store_id',lambda:'vs_fixture')
    api=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=TimeoutError('network'))))
    with pytest.raises(TimeoutError):
        agent.investigate('INC-1042',path=database,api=api)
    assert db.query('SELECT status FROM runs',path=database)[0]['status']=='failed'


def test_redundant_proposal_rejected_before_final_answer(database,monkeypatch):
    monkeypatch.setattr(agent,'vector_store_id',lambda:'vs_fixture')
    with db.connect(database) as c:
        c.execute("UPDATE accounts SET concurrency_limit=20,version=18 WHERE id='ACC-001'")
    final=dict(summary=dict(text='Current configuration is corrected.',source_ids=['ACC-001']),root_cause=dict(text='Historical cause requires additional evidence.',source_ids=['INC-1042']),confidence='insufficient',recommendations=[dict(text='Collect fresh telemetry.',source_ids=['ACC-001'])],uncertainties=['No recovery measurement'],proposed_action=None)
    suggestion=dict(new_limit=20,expected_version=18,reason='Repeat restoration',source_ids=['ACC-001'])
    api=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=[response([function('get_account_context',{},0)]),response([function('update_concurrency_limit',suggestion,1)]),response(text=json.dumps(final))])))
    _,result,trace=agent.investigate('INC-1042',path=database,api=api)
    assert not result.get('proposal_id')
    assert any('current limit is 20' in e.get('error','') for e in trace)
    assert db.account('ACC-001',database)['version']==18
