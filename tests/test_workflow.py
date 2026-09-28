import json
import pytest
from acme_support import db
from acme_support.actions import decide
from acme_support.rehearsal import rehearse
from acme_support.tools import read_tool
from acme_support.agent import validate_analysis
from acme_support.models import Analysis


def test_rehearsal_requires_human_approval(database):
    run,result,_=rehearse(path=database)
    assert db.account('ACC-001',database)['concurrency_limit']==5
    assert result['analysis']['proposed_action']['new_limit']==20
    assert {'ACC-001','ERR-001','EVT-002','KB-006','HIST-011'} <= set(result['evidence'])
    pid=result['proposal_id']
    outcome=decide(pid,approve=True,actor='demo-support-operator',path=database)
    assert outcome['status']=='executed'
    assert db.account('ACC-001',database)['concurrency_limit']==20
    decide(pid,approve=True,actor='demo-support-operator',path=database)
    assert db.account('ACC-001',database)['version']==18
    assert [r['action'] for r in db.query('SELECT * FROM audit',path=database)]==['proposed','approved','executed']
    _,after,_=rehearse(path=database)
    assert after['analysis']['proposed_action'] is None


def test_rejection_never_writes(database):
    _,result,_=rehearse(path=database)
    pid=result['proposal_id']
    decide(pid,approve=False,actor='demo-support-operator',path=database)
    assert decide(pid,approve=True,actor='demo-support-operator',path=database)['status']=='rejected'
    assert db.account('ACC-001',database)['concurrency_limit']==5


def test_stale_proposal_blocked(database):
    _,result,_=rehearse(path=database)
    with db.connect(database) as c:
        c.execute("UPDATE accounts SET version=18 WHERE id='ACC-001'")
    assert decide(result['proposal_id'],approve=True,actor='demo-support-operator',path=database)['status']=='expired'
    assert db.account('ACC-001',database)['concurrency_limit']==5


def test_entitlement_change_blocks_execution(database):
    _,result,_=rehearse(path=database)
    with db.connect(database) as c:
        c.execute("UPDATE accounts SET entitlement=5 WHERE id='ACC-001'")
    assert decide(result['proposal_id'],approve=True,actor='demo-support-operator',path=database)['status']=='expired'


def test_actor_and_scope_restrictions(database):
    _,result,_=rehearse(path=database)
    with pytest.raises(PermissionError):
        decide(result['proposal_id'],approve=True,actor='model',path=database)
    with pytest.raises(ValueError):
        read_tool('get_account_context',{'account_id':'ACC-005'},'INC-1042',database)
    with pytest.raises(ValueError):
        read_tool('get_api_errors',{'lookback_hours':169},'INC-1042',database)
    rows=read_tool('get_api_errors',{'lookback_hours':24},'INC-1043',database)
    assert rows[0]['content']['code']=='REQUEST_RATE_EXCEEDED'
    assert all(r['content'].get('account_id')!='ACC-001' for r in rows)


def test_missing_evidence_and_citations(database):
    rows=read_tool('get_api_errors',{'lookback_hours':168},'INC-1044',database)
    assert 'missing evidence' in rows[0]['content']['note']
    _,result,_=rehearse(path=database)
    parsed=Analysis.model_validate(result['analysis'])
    parsed.root_cause.source_ids.append('INVENTED')
    with pytest.raises(ValueError):
        validate_analysis(parsed,result['evidence'])


def test_reset_invalidates_pending_and_preserves_audit(database):
    _,result,_=rehearse(path=database)
    db.reset_northstar(database)
    assert decide(result['proposal_id'],approve=True,actor='demo-support-operator',path=database)['status']=='expired'
    assert len(db.query('SELECT * FROM audit',path=database))==2


def test_incidents_are_region_scoped(database):
    us=read_tool('get_incidents',{'lookback_hours':24},'INC-1042',database)
    eu=read_tool('get_incidents',{'lookback_hours':24},'INC-1045',database)
    assert us[0]['content']['matching_incidents']==[]
    assert eu[0]['content']['matching_incidents'][0]['id']=='INCIDENT-021'
