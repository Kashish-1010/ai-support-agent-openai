"""Approval is a UI/backend decision. No approval capability is exposed to the model."""
import json
from uuid import uuid4
from . import db
from .settings import DB_PATH


def propose(run_id, suggestion, evidence, path=DB_PATH):
    if suggestion is None:
        return None
    with db.connect(path) as c:
        run = c.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        if not run or run['status'] != 'completed':
            raise ValueError('A completed investigation is required')
        ticket = c.execute('SELECT * FROM tickets WHERE id=?',(run['ticket_id'],)).fetchone()
        account = c.execute('SELECT * FROM accounts WHERE id=?',(ticket['account_id'],)).fetchone()
        if not suggestion.source_ids or not set(suggestion.source_ids) <= set(evidence):
            raise ValueError('Action references unavailable evidence')
        # Recovery-only capability: cannot create new entitlements or choose arbitrary capacity.
        if suggestion.new_limit != account['entitlement'] or account['concurrency_limit'] >= suggestion.new_limit:
            raise ValueError('Only restoration to the existing higher entitlement is allowed')
        if suggestion.expected_version != account['version']:
            raise ValueError('Account configuration changed; investigate again')
        if account['id'] not in suggestion.source_ids:
            raise ValueError('Action must cite the current account record')
        pid = str(uuid4())
        c.execute('INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?,?,?)',(pid,run_id,account['id'],account['concurrency_limit'],suggestion.new_limit,account['version'],suggestion.reason,json.dumps(suggestion.source_ids),'pending',db.now(),None))
        db.audit(c,'proposed',pid,dict(run_id=run_id,account_id=account['id'],old_value=account['concurrency_limit'],new_value=suggestion.new_limit,expected_version=account['version'],reason=suggestion.reason,source_ids=suggestion.source_ids))
    return pid


def decide(proposal_id, *, approve, actor, path=DB_PATH):
    if actor != 'demo-support-operator':
        raise PermissionError('Only the local demo support operator can approve changes')
    with db.connect(path) as c:
        c.execute('BEGIN IMMEDIATE')
        proposal = c.execute('SELECT * FROM proposals WHERE id=?',(proposal_id,)).fetchone()
        if not proposal:
            raise ValueError('Unknown proposal')
        if proposal['status'] != 'pending':
            return dict(status=proposal['status'],message='Already handled; no additional write performed.')
        if not approve:
            c.execute("UPDATE proposals SET status='rejected',actor=? WHERE id=?",(actor,proposal_id))
            db.audit(c,'rejected',proposal_id,dict(actor=actor))
            return dict(status='rejected',message='Rejected. Account configuration unchanged.')
        account = c.execute('SELECT * FROM accounts WHERE id=?',(proposal['account_id'],)).fetchone()
        if account['version'] != proposal['expected_version'] or account['concurrency_limit'] != proposal['old_value'] or account['entitlement'] != proposal['new_value']:
            c.execute("UPDATE proposals SET status='expired',actor=? WHERE id=?",(actor,proposal_id))
            db.audit(c,'execution_blocked',proposal_id,dict(actor=actor,reason='Stale configuration or entitlement'))
            return dict(status='expired',message='Configuration changed. Run a fresh investigation and approve a new proposal.')
        db.audit(c,'approved',proposal_id,dict(actor=actor,new_value=proposal['new_value']))
        c.execute('UPDATE accounts SET concurrency_limit=?,version=version+1 WHERE id=?',(proposal['new_value'],proposal['account_id']))
        c.execute("UPDATE proposals SET status='executed',actor=? WHERE id=?",(actor,proposal_id))
        audit_id = db.audit(c,'executed',proposal_id,dict(actor=actor,tool='update_concurrency_limit',account_id=proposal['account_id'],before=proposal['old_value'],after=proposal['new_value'],before_version=account['version'],version=account['version']+1))
        return dict(status='executed',message=f"Concurrency limit updated from {proposal['old_value']} to {proposal['new_value']}. Fresh telemetry is required to verify customer recovery.",before_value=proposal['old_value'],after_value=proposal['new_value'],before_version=account['version'],after_version=account['version']+1,audit_record_id=audit_id)
