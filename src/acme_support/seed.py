"""Small, deliberately connected fictional dataset. No network access."""
import json
from .settings import CORPUS, ROOT

ACCOUNTS = [
    dict(id='ACC-001', name='Northstar Commerce', plan='Growth', region='us-east-1', product='Acme Sync API v2', entitlement=20, concurrency_limit=5, version=17),
    dict(id='ACC-002', name='Beacon Analytics', plan='Growth', region='us-east-1', product='Acme Sync API v2', entitlement=20, concurrency_limit=20, version=4),
    dict(id='ACC-003', name='Cedar Logistics', plan='Starter', region='us-east-1', product='Acme Sync API v2', entitlement=5, concurrency_limit=5, version=2),
    dict(id='ACC-004', name='Lumen Retail', plan='Growth', region='eu-west-1', product='Acme Sync API v2', entitlement=20, concurrency_limit=20, version=9),
    dict(id='ACC-005', name='Atlas Labs', plan='Enterprise', region='us-east-1', product='Acme Sync API v2', entitlement=50, concurrency_limit=50, version=12),
]
TICKETS = [
    dict(id='INC-1042', account_id='ACC-001', subject='429 errors after upgrading to Growth—order sync falling behind', priority='High', scenario='Primary · configuration recovery', body='We upgraded to Growth this morning and increased our sync workers from 5 to 12 at about 10:00 UTC. Since then, some requests to POST /v2/sync/jobs return HTTP 429 and our order sync backlog is growing. The usage dashboard shows we are well below our monthly allowance. Is there an outage, or did the upgrade not take effect? Example request ID: req_ns_1042_01.'),
    dict(id='INC-1043', account_id='ACC-002', subject='429 errors after Growth upgrade', priority='Medium', scenario='Misleading similarity', body='Our new import script gets 429 errors when it submits a batch. We upgraded last week. Can you increase our concurrency? Request req_beacon_01, today around 10:00 UTC.'),
    dict(id='INC-1044', account_id='ACC-003', subject='Intermittent sync failures last month', priority='Medium', scenario='Insufficient evidence', body='Some syncs failed last month. We did not save request IDs or exact times. Can you tell us why?'),
    dict(id='INC-1045', account_id='ACC-004', subject='Dashboard delayed although sync jobs complete', priority='Medium', scenario='Known incident', body='Our EU dashboard is about 15 minutes behind since 09:30 UTC today, but our API jobs seem successful. Should we retry them?'),
]
for ticket in TICKETS:
    ticket['status'] = {'INC-1044': 'Waiting on customer', 'INC-1045': 'In progress'}.get(ticket['id'], 'Open')

KB = [
 ('KB-001','Acme Sync API v2 overview','POST /v2/sync/jobs creates a data sync job. A request ID identifies each attempt. Job completion and dashboard refresh are separate operations. Collect region, timestamp, API error code, and request ID before diagnosing failures.'),
 ('KB-002','Safe retries and idempotency','For rejected 429 requests, honor Retry-After and use exponential backoff with jitter. Retrying accepted jobs can duplicate work unless an idempotency key is used. Do not promise that retries cure a persistent configuration mismatch.'),
 ('KB-003','Interpreting 429: concurrency, rate, and quota','CONCURRENCY_LIMIT_EXCEEDED means simultaneous admitted requests have reached the enforced account concurrency limit. REQUEST_RATE_EXCEEDED means arrivals exceeded requests-per-minute limits; adjust pacing, not concurrency. MONTHLY_QUOTA_EXCEEDED means monthly allowance exhaustion. HTTP 429 alone does not identify which condition applies. Check live error codes and usage. A low monthly usage percentage does not exclude concurrency rejection.'),
 ('KB-004','Request-rate bursts','Growth permits 600 request starts per minute. A burst over 600 can generate REQUEST_RATE_EXCEEDED even with low concurrent work and low monthly usage. Pace submissions, honor Retry-After, and use jitter. Raising concurrent request capacity is not a fix.'),
 ('KB-005','Collecting evidence for intermittent failures','Request IDs, UTC time window, region, endpoint, and response codes are required to establish a cause. Detailed demo telemetry retains seven days. When evidence has expired, request a fresh reproduction and avoid assigning a confirmed root cause.'),
 ('KB-006','Restore concurrency after failed plan propagation','Applies to Acme Sync API v2. Starter entitlement is 5; Growth is 20; Enterprise is 50. A failed plan entitlement propagation job can leave the previous enforced concurrency limit while billing reflects the new plan. Verify the active entitlement, current enforced limit, and failed event; confirm CONCURRENCY_LIMIT_EXCEEDED in current errors. With explicit support operator approval, restore enforced concurrency to the existing entitlement using update_concurrency_limit. Never exceed entitlement or change billing. Check configuration version before execution. Interim mitigation: cap client workers at the enforced limit. After execution, verify configuration and fresh errors before declaring service recovery.'),
 ('KB-007','Regional dashboard lag','A dashboard ingestion delay can occur while API jobs succeed. Check incident region, component, and time window. If only dashboard ingestion is affected, avoid resubmitting successful jobs. Communicate the incident status and verify dashboard freshness after resolution.'),
 ('KB-008','Authentication errors','HTTP 401 with INVALID_TOKEN is an authentication problem. Verify token expiry and scope without exposing credentials. Account concurrency changes cannot resolve authentication errors.'),
 ('KB-009','Configuration change controls','Support operators may restore concurrency to an existing purchased entitlement. Explicit approval must bind the exact account, old/new values, and configuration version. Stale proposals require re-investigation. Record proposal, approval, execution outcome, and before/after state. A successful configuration write is not proof of workload recovery.'),
]
HISTORY = [
 ('HIST-001','Expired token during scheduled sync','Atlas Labs','401 INVALID_TOKEN after an expired token. Rotating the credential restored access. No concurrency changes.'),
 ('HIST-002','Dashboard stale in EU','Lumen Retail','eu-west-1 dashboard ingestion incident; API jobs completed normally. Waited for incident recovery; did not replay successful jobs.'),
 ('HIST-003','Monthly quota exhausted','Cedar Logistics','MONTHLY_QUOTA_EXCEEDED at 100% monthly allowance. Billing entitlement review was required; pacing did not replenish allowance.'),
 ('HIST-004','429 from large import burst','Beacon Analytics','REQUEST_RATE_EXCEEDED at 900 starts/minute; concurrency below 20. Paced requests below 600/min and errors stopped.'),
 ('HIST-005','Timeout without request IDs','Cedar Logistics','Insufficient retained telemetry. Requested fresh reproduction with request ID and UTC timestamp. Cause remained unconfirmed.'),
 ('HIST-006','Duplicate jobs after manual retry','Northstar Commerce','A successful job was resubmitted without an idempotency key. Used stable keys for retries; not related to concurrency.'),
 ('HIST-007','Growth upgrade retained Starter concurrency','Atlas Labs','Acme Sync API v2, us-east-1. Growth entitlement 20 but enforced concurrency 5. Plan propagation failed. Errors were CONCURRENCY_LIMIT_EXCEEDED when 12 workers ran. An operator approved restoring 5 to 20; fresh requests succeeded afterward. This is a precedent, not evidence of another account’s current state.'),
 ('HIST-008','Client configured above Starter allowance','Cedar Logistics','Starter entitlement and enforcement both 5. Client used 8 workers. Reduced workers to 5; no authorized limit increase.'),
 ('HIST-009','403 from missing job scope','Atlas Labs','Valid token lacked jobs:write scope. Updated credentials through customer procedure. Limit changes would not help.'),
 ('HIST-010','Slow reporting with successful API calls','Lumen Retail','Dashboard refresh latency with normal job completion. Checked component-level incident rather than modifying API limits.'),
 ('HIST-011','429 after upgrade to Growth','Beacon Analytics','Similar title to a concurrency incident, but errors were REQUEST_RATE_EXCEEDED. Account enforcement correctly matched Growth at 20; requests burst above 600/min. Pacing and backoff fixed the issue. Increasing concurrency was not appropriate.'),
 ('HIST-012','Upgrade followed by successful sync','Northstar Commerce','Previous upgrade completed successfully; no errors. Plan changes alone do not demonstrate propagation failure.'),
 ('HIST-013','Temporary worker spike','Atlas Labs','50 concurrent requests admitted at Enterprise entitlement; client briefly launched 60. Bounded worker pool resolved CONCURRENCY_LIMIT_EXCEEDED.'),
 ('HIST-014','Old incident unrelated to new failure','Cedar Logistics','An older EU dashboard incident did not explain US API authentication errors. Region, component, time, and error code distinguished them.'),
]


def documents():
    docs = []
    for sid, title, body in KB:
        docs.append(dict(id=sid, kind='kb', title=title, body=body))
    for sid, title, customer, body in HISTORY:
        docs.append(dict(id=sid, kind='history', title=title, body=f'Historical customer: {customer}. Resolved before 2026-09-24. {body}'))
    return docs


def write_sources():
    CORPUS.mkdir(parents=True, exist_ok=True)
    for doc in documents():
        (CORPUS / f"{doc['id']}.md").write_text(f"# {doc['id']}: {doc['title']}\n\nSource type: {doc['kind']}\nProduct: Acme Sync API v2\n\n{doc['body']}\n")
    (ROOT / 'data/synthetic/accounts/accounts.json').write_text(json.dumps(ACCOUNTS, indent=2))
    (ROOT / 'data/synthetic/tickets/incoming.json').write_text(json.dumps(TICKETS, indent=2))


def telemetry():
    rows = []
    def add(sid, account, kind, body, ts='2026-09-24T10:15:00Z'):
        rows.append(dict(id=sid, account_id=account, kind=kind, timestamp=ts, **body))
    add('MET-001', 'ACC-001', 'usage', dict(window='09:30–09:59 UTC', attempted_peak=5, admitted_peak=5, error_429=0, monthly_usage_percent=18, peak_requests_per_minute=60, rate_limit_per_minute=600), '2026-09-24T09:59:00Z')
    add('MET-002', 'ACC-001', 'usage', dict(window='10:00–10:15 UTC', attempted_peak=12, admitted_peak=5, total_requests=800, error_429=240, monthly_usage_percent=18, peak_requests_per_minute=90, rate_limit_per_minute=600, backlog_jobs=320))
    add('ERR-001', 'ACC-001', 'errors', dict(code='CONCURRENCY_LIMIT_EXCEEDED', http_status=429, count=240, total_requests=800, enforced_limit=5, request_id='req_ns_1042_01', endpoint='POST /v2/sync/jobs'))
    add('EVT-001', 'ACC-001', 'events', dict(event='plan_upgraded', before='Starter', after='Growth', entitlement=20), '2026-09-24T09:45:00Z')
    add('EVT-002', 'ACC-001', 'events', dict(event='entitlement_propagation_failed', job='prop_ns_0924', retained_concurrency=5, configuration_version=17), '2026-09-24T09:46:00Z')
    add('EVT-003', 'ACC-001', 'events', dict(event='client_workers_changed', before=5, after=12, origin='customer integration event'), '2026-09-24T10:00:00Z')
    add('MET-003','ACC-002','usage',dict(attempted_peak=8, admitted_peak=8, peak_requests_per_minute=920, rate_limit_per_minute=600, monthly_usage_percent=12))
    add('ERR-002','ACC-002','errors',dict(code='REQUEST_RATE_EXCEEDED',http_status=429,count=180,request_id='req_beacon_01'))
    add('EVT-004','ACC-002','events',dict(event='entitlement_propagation_succeeded', enforced_concurrency=20),'2026-09-18T09:45:00Z')
    add('MET-004','ACC-004','usage',dict(attempted_peak=8,admitted_peak=8,error_429=0,successful_jobs=150,dashboard_lag_minutes=15))
    return rows
