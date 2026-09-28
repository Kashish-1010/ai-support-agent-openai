"""Narrow, account-bound read operations. The model never supplies account IDs."""
import json
from datetime import datetime, timedelta
from . import db
from .models import NoArgs, Window
from .settings import DB_PATH, DEMO_NOW

READS = {
    'get_account_context': ('Read current account plan, entitlement, enforced concurrency, region, product and configuration version.', NoArgs),
    'get_usage_metrics': ('Read synthetic usage samples: attempted/admitted concurrency, rate, quota and backlog. Historical samples do not change after a config write.', Window),
    'get_api_errors': ('Read API error codes, counts and sample request IDs for the selected account.', Window),
    'get_incidents': ('Read known incidents relevant to the selected account region and Acme components. Empty results do not rule out unknown incidents.', Window),
    'get_account_events': ('Read recent plan/configuration events for the selected account.', Window),
}


def definitions():
    return [dict(type='function',name=name,description=description,parameters=model.model_json_schema(),strict=True) for name,(description,model) in READS.items()]


def read_tool(name, arguments, ticket_id, path=DB_PATH):
    if name not in READS:
        raise ValueError('Tool not allowed')
    validated = READS[name][1].model_validate(arguments, strict=True)
    selected = db.ticket(ticket_id,path)
    account = db.account(selected['account_id'],path)
    if name == 'get_account_context':
        return [dict(source_id=account['id'], title=f"{account['name']} account configuration", content=account, timestamp=db.now(), clock='current configuration')]
    since = (datetime.fromisoformat(DEMO_NOW.replace('Z','+00:00')) - timedelta(hours=validated.lookback_hours)).isoformat().replace('+00:00','Z')
    if name == 'get_incidents':
        content = dict(region=account['region'], window_start=since, window_end=DEMO_NOW, service='Acme Sync API v2', matching_incidents=[])
        rows = db.query('SELECT payload FROM incidents WHERE region=? AND started_at<=? LIMIT 20',(account['region'],DEMO_NOW),path)
        content['matching_incidents'] = [json.loads(row['payload']) for row in rows]
        return [dict(source_id=f"INCIDENTS-{account['id']}",title='Regional incident lookup',content=content,timestamp=DEMO_NOW,clock='synthetic snapshot')]
    kind = {'get_usage_metrics':'usage','get_api_errors':'errors','get_account_events':'events'}[name]
    rows = db.query('SELECT payload FROM telemetry WHERE account_id=? AND kind=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp LIMIT 50',(account['id'],kind,since,DEMO_NOW),path)
    results = [dict(source_id=(p:=json.loads(r['payload']))['id'],title=f"{kind.title()} · {p['timestamp']}",content=p,timestamp=p['timestamp'],clock='synthetic snapshot') for r in rows]
    if not results:
        results = [dict(source_id=f"EMPTY-{kind}-{account['id']}",title=f'No retained {kind}',content=dict(note='No records in requested window. This is missing evidence, not proof of no failures.',window_start=since,window_end=DEMO_NOW),timestamp=DEMO_NOW,clock='synthetic snapshot')]
    return results
