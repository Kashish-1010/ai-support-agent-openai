from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'src'))

import json
import streamlit as st
from acme_support import db
from acme_support.actions import decide
from acme_support.agent import configured, investigate
from acme_support.indexing import index_knowledge
from acme_support.rehearsal import rehearse
from acme_support.findings_view import diagnosis_sentence, signal_cards, human_sources, source_label, humanize_source_ids
from acme_support.settings import MODEL, vector_store_id

st.set_page_config(page_title='Acme · Support intelligence', page_icon='◈', layout='wide')
db.initialize()
st.markdown('''<style>
.block-container {max-width:1320px;padding-top:2rem;padding-bottom:3rem}
h1 {letter-spacing:-1.5px;font-size:2.5rem!important} h2 {letter-spacing:-.5px}
[data-testid="stSidebar"] {border-right:1px solid #e1e6f0}
[data-testid="stMetric"] {background:white;border:1px solid #e1e6f0;border-radius:14px;padding:16px}
[data-testid="stMetricLabel"] {color:#64748b}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px}
.brand {font-size:23px;font-weight:800;letter-spacing:-.8px;color:#203153;margin-bottom:0}
.eyebrow {font-size:11px;font-weight:700;letter-spacing:2px;color:#64748b;text-transform:uppercase}
.pill {display:inline-block;background:#e8edff;color:#315cf5;padding:5px 10px;border-radius:30px;font-size:12px;font-weight:600}
</style>''',unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<p class="brand">◈ acme</p><p class="eyebrow">Support intelligence</p>',unsafe_allow_html=True)
    st.divider()
    st.markdown('**Support workspace**')
    st.caption('Acme Sync · Customer support')
    st.caption('Review tickets, investigate issues, and approve the next step.')
    st.divider()
    with st.expander('Demo settings', expanded=False):
        mode = st.radio('Investigation mode',['Live AI','Offline rehearsal'],key='investigation_mode',help='Offline rehearsal is a scripted Northstar walkthrough for development.')
        st.caption('Synthetic workspace · September 24, 2026')
        st.caption('Operator: demo-support-operator')
        st.write('API key: ' + ('Configured' if configured() else 'Not configured'))
        st.write('Model: ' + MODEL)
        st.write('File Search: ' + ('Index configured' if vector_store_id() else 'Not indexed'))
        st.caption('Upload only the 23 synthetic KB and history documents. Requires your API key; API/storage charges may apply.')
        if st.button('Prepare File Search',disabled=not configured(),width='stretch'):
            try:
                with st.status('Preparing knowledge index…',expanded=True) as status:
                    index_knowledge(st.write)
                    status.update(label='Knowledge index ready',state='complete')
                st.rerun()
            except Exception as exc:
                st.error(f'Index setup failed ({type(exc).__name__}). Check your API key, network and OpenAI project access, then retry.')
        st.caption('Set OPENAI_API_KEY in .env, then restart Streamlit.')
        st.divider()
        st.caption('Restart the Northstar walkthrough. Prior audit records remain; pending proposals expire.')
        if st.button('Reset Northstar scenario',width='stretch'):
            db.reset_northstar()
            st.session_state.pop('result_INC-1042',None)
            st.rerun()
        with st.expander('Recent investigation runs'):
            runs = db.query('SELECT id,ticket_id,mode,status,created_at FROM runs ORDER BY created_at DESC LIMIT 10')
            if runs:
                st.dataframe(runs,hide_index=True,width='stretch')
            else:
                st.caption('No investigations yet.')
    st.caption('Evidence-led support. Human-approved actions.')

st.markdown('<span class="eyebrow">Acme Sync / Support workspace</span>',unsafe_allow_html=True)
st.title('From ticket to resolution.')
st.caption('Investigate the signals. Review the evidence. Approve the next step.')
tickets = db.query('SELECT t.*,a.name FROM tickets t JOIN accounts a ON a.id=t.account_id ORDER BY t.id')
selected = st.session_state.get('selected_ticket')
if selected not in {ticket['id'] for ticket in tickets}:
    st.subheader('Support inbox')
    st.caption('Select a ticket to review the conversation and start an investigation.')
    filters = st.session_state.get('saved_inbox_filters', {'status':'All statuses','customer':''})
    statuses = ['All statuses','Open','In progress','Waiting on customer','Resolved']
    status_col, customer_col = st.columns([1,2])
    with status_col:
        status_filter = st.selectbox('Status', statuses,index=statuses.index(filters['status']),key='inbox_status')
    with customer_col:
        customer_filter = st.text_input('Customer or account',value=filters['customer'],placeholder='Search customer name or account ID',key='inbox_customer').strip().casefold()
    st.session_state['saved_inbox_filters'] = {'status':status_filter,'customer':customer_filter}
    filtered = [ticket for ticket in tickets if
        (status_filter=='All statuses' or ticket['status']==status_filter) and
        (not customer_filter or customer_filter in ticket['name'].casefold() or customer_filter in ticket['account_id'].casefold())]
    st.caption(f"{len(filtered)} of {len(tickets)} tickets")
    for item in filtered:
        with st.container(border=True):
            content_col, status_col, priority_col = st.columns([5,1.8,1])
            with content_col:
                st.caption(f"{item['id']} · {item['name']} · {item['account_id']}")
                if st.button(item['subject'],key='open_'+item['id'],type='tertiary',width='stretch'):
                    st.session_state['selected_ticket'] = item['id']
                    st.rerun()
            with status_col:
                st.caption('Status')
                st.write(item['status'])
            with priority_col:
                st.caption('Priority')
                st.write(item['priority'])
    if not filtered:
        st.info('No tickets match these filters. Try another status or customer.')
    st.stop()

if st.button('← Back to inbox',type='tertiary'):
    st.session_state.pop('selected_ticket',None)
    st.rerun()
ticket = next(ticket for ticket in tickets if ticket['id']==selected)
a = db.account(ticket['account_id'])
left,right = st.columns([2.2,1],gap='large')
with left:
    with st.container(border=True):
        st.markdown(f"**{ticket['id']}** · {ticket['priority']} priority · {ticket['status']}")
        st.subheader(ticket['subject'])
        st.markdown(ticket['body'])
        st.caption(f"{a['name']} · {a['product']} · {a['region']} · Received 10:20 UTC")
with right:
    with st.container(border=True):
        st.markdown('**Account at a glance**')
        st.write(f"{a['name']} · {a['plan']}")
        st.caption(f"Account ID · {a['id']}")
        st.write(a['product'])
        st.caption(f"Region · {a['region']}")

if mode == 'Offline rehearsal':
    st.caption('Development rehearsal · Scripted analysis, not live AI.')

unavailable = (mode=='Offline rehearsal' and selected!='INC-1042') or (mode=='Live AI' and (not configured() or not vector_store_id()))
requested = st.button('Analyze with AI' if mode=='Live AI' else 'Run Northstar rehearsal',type='primary',disabled=unavailable,key='analyze_ticket')
if requested:
    try:
        with st.status('Gathering evidence…',expanded=True) as status:
            handler = investigate if mode=='Live AI' else rehearse
            def show_progress(message):
                labels = {
                    'get_account_context': 'Reviewed account context',
                    'get_usage_metrics': 'Reviewed usage patterns',
                    'get_api_errors': 'Reviewed API error evidence',
                    'get_incidents': 'Checked relevant service incidents',
                    'get_account_events': 'Reviewed recent account events',
                }
                if message.startswith('Investigating'):
                    return
                if message.startswith('File Search'):
                    st.write('Retrieved supporting documents')
                    return
                for tool, label in labels.items():
                    if tool in message:
                        st.write(label)
                        return
                st.write(message)
            run_id,result,trace = handler(selected,on_progress=show_progress)
            st.session_state['result_'+selected] = (run_id,result,trace)
            status.update(label='Investigation complete · review findings below',state='complete',expanded=False)
    except Exception as exc:
        st.error(f'Investigation failed ({type(exc).__name__}). No configuration change was made. Verify setup or retry; partial evidence is available in the run log.')
if unavailable:
    st.caption('Analysis is unavailable. Check Demo settings.' if mode=='Live AI' else 'Select Northstar to run the development rehearsal.')

saved = st.session_state.get('result_'+selected)
if saved:
    run_id,result,trace = saved
    analysis = result['analysis']
    st.divider()
    st.subheader('Investigation findings')
    st.caption(f"{'Scripted rehearsal · ' if result['mode']=='rehearsal' else ''}{len(result['evidence'])} sources reviewed · Confidence: {analysis['confidence']}")
    confidence = analysis['confidence']
    banner_title = {
        'high': 'Root cause identified · High confidence',
        'medium': 'Likely root cause · Medium confidence',
        'insufficient': 'More evidence needed · Root cause unconfirmed',
    }[confidence]
    banner = st.success if confidence=='high' else st.warning if confidence=='insufficient' else st.info
    banner(f"**{banner_title}**\n\n{humanize_source_ids(diagnosis_sentence(analysis['root_cause']['text']))}")
    cards = signal_cards(result['evidence'])
    if cards:
        st.caption('Key evidence · Snapshot captured during this investigation')
        for column, (label, value, detail, source_id) in zip(st.columns(len(cards)), cards):
            with column:
                with st.container(border=True):
                    st.caption(label)
                    st.markdown(f'**{value}**')
                    st.caption(detail)
                    with st.popover(label):
                        st.markdown('**'+label+'**')
                        st.caption('Full source record and technical ID are in the Evidence Library.')
    finding_tab,evidence_tab,activity_tab = st.tabs(['Analysis & action','Evidence library','Activity & audit'])
    def show_finding(finding):
        st.write(humanize_source_ids(finding['text']))
        with st.popover('Sources · ' + ' · '.join(human_sources(finding['source_ids'],result['evidence']))):
            for source_id in finding['source_ids']:
                source = result['evidence'][source_id]
                st.markdown('**'+source_label(source_id,source)+'**')
                st.caption('Full source record and technical ID are in the Evidence Library.')
    with finding_tab:
        c1,c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown('**01 / Issue summary**')
                show_finding(analysis['summary'])
        with c2:
            with st.container(border=True):
                st.markdown('**02 / Root cause assessment**')
                show_finding(analysis['root_cause'])
        with st.container(border=True):
            st.markdown('**03 / Recommended solution**')
            for i,finding in enumerate(analysis['recommendations'],1):
                st.markdown(f'**Step {i}**')
                display_finding = finding
                if i == 1 and result.get('proposal_id'):
                    pending_proposal = db.query('SELECT * FROM proposals WHERE id=?',(result['proposal_id'],))[0]
                    if pending_proposal['status'] == 'pending':
                        display_finding = dict(finding)
                        display_finding['text'] = f"Restore {a['name']}’s concurrency limit from {pending_proposal['old_value']} → {pending_proposal['new_value']}, matching its existing {a['plan']} entitlement."
                show_finding(display_finding)
        if analysis['uncertainties']:
            with st.expander('Limitations & verification needed'):
                for item in analysis['uncertainties']:
                    st.write('• '+humanize_source_ids(item))
        if result.get('action_blocked'):
            st.warning('Action proposal blocked: '+result['action_blocked'])
        if result.get('proposal_id'):
            proposal = db.query('SELECT * FROM proposals WHERE id=?',(result['proposal_id'],))[0]
            with st.container(border=True):
                st.markdown('**Human approval required**' if proposal['status']=='pending' else '**Configuration action**')
                st.markdown('### Restore concurrency entitlement' if proposal['status']=='pending' else '### Concurrency entitlement restored' if proposal['status']=='executed' else '### Update concurrency limit')
                st.caption(f"{a['name']} · Account configuration action")
                b1,b2,b3 = st.columns(3)
                b1.metric('Proposed from',proposal['old_value'])
                b2.metric('Proposed to',proposal['new_value'])
                b3.metric('Status',proposal['status'].upper())
                st.write(humanize_source_ids(proposal['reason']))
                st.caption(f"Version {proposal['expected_version']} · Supporting evidence: {', '.join(human_sources(json.loads(proposal['evidence']),result['evidence']))}")
                st.caption('Effect: permit more parallel requests within the purchased entitlement. Risk: higher simultaneous load. No billing change; recovery must be verified with fresh telemetry.')
                if proposal['status']=='pending':
                    acknowledge = st.checkbox(f"I approve changing {a['name']} from {proposal['old_value']} to {proposal['new_value']} concurrent requests.",key='ack_'+proposal['id'])
                    approve_col,reject_col = st.columns(2)
                    with approve_col:
                        if st.button('Approve and execute',type='primary',disabled=not acknowledge,key='approve_'+proposal['id'],width='stretch'):
                            outcome = decide(proposal['id'],approve=True,actor='demo-support-operator')
                            st.session_state['action_message'] = outcome['message']
                            st.rerun()
                    with reject_col:
                        if st.button('Reject proposal',key='reject_'+proposal['id'],width='stretch'):
                            outcome = decide(proposal['id'],approve=False,actor='demo-support-operator')
                            st.session_state['action_message'] = outcome['message']
                            st.rerun()
                elif proposal['status']=='executed':
                    executed = db.query("SELECT id,payload FROM audit WHERE proposal_id=? AND action='executed' ORDER BY id DESC LIMIT 1",(proposal['id'],))
                    if executed:
                        audit_payload = json.loads(executed[0]['payload'])
                        st.success('✓ Change executed')
                        st.markdown(f"Concurrency limit updated **{audit_payload['before']} → {audit_payload['after']}**")
                        st.markdown(f"Configuration version **{audit_payload.get('before_version',proposal['expected_version'])} → {audit_payload['version']}**")
                        st.caption(f"Audit record created · #{executed[0]['id']}")
                    else:
                        st.success('✓ Change executed and audited')
                    st.warning('Verification required: Fresh telemetry is needed before declaring the customer issue resolved.')
        if 'action_message' in st.session_state:
            st.info(st.session_state.pop('action_message'))
    with evidence_tab:
        st.caption('These are the sources actually made available during this run. Telemetry is frozen at September 24, 10:20 UTC; account configuration is read live.')
        filter_text = st.text_input('Find evidence by ID or text',placeholder='Try ERR-001, propagation, or HIST-011')
        for sid,source in result['evidence'].items():
            if filter_text.lower() not in json.dumps(source).lower():
                continue
            with st.expander(f"{sid} · {source['title']}"):
                st.caption(source.get('clock','') + (' · '+source['timestamp'] if source.get('timestamp') else ''))
                if isinstance(source['content'],str):
                    st.write(source['content'])
                else:
                    st.json(source['content'])
                if source.get('file_id'):
                    st.caption(f"File Search source: {source['file_id']} · score {source.get('score')}")
    with activity_tab:
        st.caption(f"Run {run_id[:8]} · {result['tool_calls']} tool calls · {result['elapsed_seconds']}s")
        st.caption('Tool activity and evidence references, not private model reasoning.')
        for event in trace:
            if event['type']=='response':
                with st.expander('Responses API · '+event['response_id']):
                    st.json(event)
            else:
                with st.expander(event.get('name','Tool activity')):
                    st.json(event)
        audit = db.query('SELECT * FROM audit WHERE proposal_id IN (SELECT id FROM proposals WHERE run_id=?) ORDER BY id',(run_id,))
        st.markdown('**Action audit trail**')
        if not audit:
            st.caption('No action events for this run.')
        for event in audit:
            with st.expander(event['action'].upper()+' · '+event['timestamp']):
                st.json(json.loads(event['payload']))
        st.download_button('Download run evidence & audit',json.dumps(dict(run_id=run_id,result=result,trace=trace,audit=audit),indent=2),file_name=f'{selected}-{run_id[:8]}.json',mime='application/json')
else:
    st.divider()
    st.markdown('**Ready to investigate**')
    st.caption('Start an investigation to see the issue summary, likely cause, supporting evidence, and recommended next steps.')
