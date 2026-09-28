"""Paid live integration check in an isolated SQLite database, including simulated operator approval."""
from pathlib import Path
import os
import json
import tempfile
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='live-ui-',dir=ROOT/'data/local') as directory:
    os.environ['ACME_DB_PATH']=str(Path(directory)/'test.db')
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=180).run()
    app.radio[0].set_value('Live AI').run()
    app.button(key='open_INC-1042').click().run()
    analyze=next(b for b in app.button if b.label=='Analyze with AI')
    assert not analyze.disabled, 'Live mode not configured'
    print('Live UI: starting Northstar investigation',flush=True)
    analyze.click().run()
    assert not app.exception, 'UI exception'
    from acme_support import db
    rows=db.query("SELECT * FROM runs WHERE mode='live' ORDER BY created_at DESC")
    assert rows and rows[0]['status']=='completed', f'Live investigation failed: {[r["status"] for r in rows]}'
    result=json.loads(rows[0]['result'])
    assert result.get('proposal_id'), result.get('action_blocked','No proposal generated')
    assert {'ACC-001','ERR-001','EVT-002','KB-006'} <= set(result['evidence'])
    assert db.account('ACC-001')['concurrency_limit']==5
    approve=next(b for b in app.button if b.label=='Approve and execute')
    assert approve.disabled
    print('Live UI: evidence valid; account unchanged before approval',flush=True)
    app.checkbox[0].check().run()
    next(b for b in app.button if b.label=='Approve and execute').click().run()
    assert not app.exception
    assert db.account('ACC-001')['concurrency_limit']==20
    events=db.query('SELECT action,payload FROM audit ORDER BY id')
    assert [e['action'] for e in events]==['proposed','approved','executed']
    assert any('committed and audited' in e.value for e in app.success)
    print('Live UI: approved 5 -> 20; execution and audit verified',flush=True)
    next(b for b in app.button if b.label=='Analyze with AI').click().run()
    latest=db.query("SELECT * FROM runs ORDER BY created_at DESC LIMIT 1")[0]
    assert latest['status']=='completed'
    after=json.loads(latest['result'])
    assert after['analysis']['proposed_action'] is None, 'Redundant change suggested'
    assert not after.get('proposal_id')
    report=dict(model=os.getenv('OPENAI_MODEL'),checks=dict(live_investigation=True,file_search=True,approval_required=True,configuration_changed=True,audit_verified=True,no_redundant_change=True),before=result,after=after,audit=events)
    (ROOT/'data/local/live-ui-validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: live UI flow, approval gate, write, audit, and post-change re-analysis. Main app database untouched.',flush=True)
