from pathlib import Path
import os
import tempfile
from streamlit.testing.v1 import AppTest
with tempfile.TemporaryDirectory() as directory:
    os.environ['ACME_DB_PATH']=str(Path(directory)/'ui.db')
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception, app.exception
    assert not app.metric, 'Landing screen exposes configuration metrics'
    assert not any('configuration recovery' in c.value.lower() or 'Purchased entitlement' in c.value for c in app.caption)
    assert any(e.label=='Demo settings' for e in app.expander)
    assert not any(b.label=='Analyze with AI' for b in app.button)
    assert len([b for b in app.button if b.key and b.key.startswith('open_')])==4
    app.selectbox(key='inbox_status').set_value('Waiting on customer').run()
    assert [b.key for b in app.button if b.key and b.key.startswith('open_')]==['open_INC-1044']
    app.text_input(key='inbox_customer').set_value('northstar').run()
    assert not [b for b in app.button if b.key and b.key.startswith('open_')]
    app.selectbox(key='inbox_status').set_value('All statuses').run()
    assert [b.key for b in app.button if b.key and b.key.startswith('open_')]==['open_INC-1042']
    app.button(key='open_INC-1042').click().run()
    assert any(b.label=='Analyze with AI' for b in app.button)
    next(b for b in app.button if b.label=='← Back to inbox').click().run()
    assert app.text_input(key='inbox_customer').value=='northstar'
    app.button(key='open_INC-1042').click().run()
    app.radio[0].set_value('Offline rehearsal').run()
    next(b for b in app.button if b.label=='Run Northstar rehearsal').click().run()
    assert not app.exception, app.exception
    assert any('Root cause' in m.value for m in app.markdown)
    assert any('Root cause identified · High confidence' in e.value for e in app.success)
    assert any('5 enforced / 20 entitled' in e.value for e in app.markdown)
    assert any('12 attempted / 5 admitted' in e.value for e in app.markdown)
    assert any('Active incidents' in m.value for m in app.caption)
    assert any('Usage telemetry' in m.value for m in app.caption)
    assert any('Account configuration' in m.value for m in app.caption)
    assert any('Product KB' in m.value for m in app.caption)
    assert any('Similar resolved tickets' in m.value for m in app.caption)
    assert not any('INCIDENTS-ACC-' in p.value or 'MET-00' in p.value or 'KB-00' in p.value for p in app.popover)
    approve=next(b for b in app.button if b.label=='Approve and execute')
    assert approve.disabled
    app.checkbox[0].check().run()
    next(b for b in app.button if b.label=='Approve and execute').click().run()
    assert not app.exception, app.exception
    assert any('committed and audited' in m.value for m in app.success)
    # A new browser session must not automatically reveal persisted findings.
    fresh=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not any('Root cause assessment' in m.value for m in fresh.markdown)
    assert not fresh.metric
    next(b for b in app.button if b.label=='Reset Northstar scenario').click().run()
    assert not app.exception, app.exception
    print('UI passed: load, rehearsal, approval gate, execution, verified state, reset.')
