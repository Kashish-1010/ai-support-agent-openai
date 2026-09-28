"""Explicitly scripted offline walkthrough, never presented as live model output."""
from . import db
from .actions import propose
from .agent import validate_analysis
from .models import Analysis
from .settings import DB_PATH
from .tools import read_tool


def rehearse(ticket_id='INC-1042', on_progress=lambda message: None, path=DB_PATH):
    if ticket_id != 'INC-1042':
        raise ValueError('Offline rehearsal is available for Northstar only. Use Live AI for secondary scenarios.')
    run_id = db.start_run(ticket_id,'rehearsal',path)
    ticket = db.ticket(ticket_id,path)
    evidence = {ticket_id:dict(source_id=ticket_id,title=ticket['subject'],content=ticket['body'],clock='customer report')}
    trace = []
    for name in ['get_account_context','get_api_errors','get_usage_metrics','get_account_events','get_incidents']:
        args = {} if name == 'get_account_context' else dict(lookback_hours=24)
        rows = read_tool(name,args,ticket_id,path)
        evidence.update({r['source_id']:r for r in rows})
        trace.append(dict(type='tool',name=name,arguments=args,source_ids=[r['source_id'] for r in rows]))
        on_progress(f'Rehearsal · {name}')
    ids = ['KB-003','KB-006','KB-009','HIST-007','HIST-011']
    for sid in ids:
        doc = db.query('SELECT * FROM documents WHERE id=?',(sid,),path)[0]
        evidence[sid] = dict(source_id=sid,title=doc['title'],content=doc['body'],clock='local rehearsal document')
    trace.append(dict(type='fixture',name='Local document fixtures (not File Search)',source_ids=ids))
    a = db.account('ACC-001',path)
    changed = a['concurrency_limit'] == a['entitlement']
    def finding(text,*ids):
        return dict(text=text,source_ids=list(ids))
    action = None if changed else dict(new_limit=20,expected_version=a['version'],reason='Restore Northstar’s existing Growth entitlement after failed plan propagation.',source_ids=['ACC-001','ERR-001','EVT-002','KB-006'])
    analysis = Analysis.model_validate(dict(
        summary=finding('Northstar’s order sync hit 240 concurrency rejections out of 800 requests after workers increased from 5 to 12. Monthly quota and request rate were not exhausted.','INC-1042','ERR-001','MET-002'),
        root_cause=finding('The Growth upgrade propagation failed at 09:46 UTC, retaining the Starter concurrency limit of 5 instead of the entitled 20. The error code and admitted-concurrency plateau connect that mismatch to the failures.' + (' The current configuration has since been restored to 20; the telemetry still reflects the pre-change snapshot.' if changed else ''),'ACC-001','EVT-001','EVT-002','ERR-001','MET-002','KB-003'),
        confidence='high',
        recommendations=[
            finding('The configuration is now at the entitled 20. Collect fresh telemetry before declaring recovery.' if changed else 'Restore Northstar’s concurrency limit from 5 → 20, matching its existing Growth entitlement. This changes configuration only, not billing.','ACC-001','KB-006','KB-009'),
            finding('Until corrected, cap workers at 5. After the change, verify configuration, run fresh requests, and check concurrency errors and backlog before declaring recovery.','KB-006'),
            finding('HIST-007 corroborates the recovery procedure. HIST-011 involved REQUEST_RATE_EXCEEDED and is a misleading match; its pacing fix alone does not address this account’s stale limit.','HIST-007','HIST-011','ERR-001'),
        ],
        uncertainties=['Telemetry is a frozen synthetic snapshot; no post-change workload recovery has been measured.','No matching regional incident is recorded; this does not rule out an unreported incident.'],proposed_action=action))
    validate_analysis(analysis,evidence)
    result = dict(analysis=analysis.model_dump(),evidence=evidence,mode='rehearsal',tool_calls=5,elapsed_seconds=0)
    db.save_run(run_id,'completed',result,trace,path)
    if action:
        result['proposal_id'] = propose(run_id,analysis.proposed_action,evidence,path)
    db.save_run(run_id,'completed',result,trace,path)
    return run_id,result,trace
