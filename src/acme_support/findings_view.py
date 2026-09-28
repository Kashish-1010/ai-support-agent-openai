"""Presentation-only summaries of evidence already available to an investigation."""
import re


def humanize_source_ids(text):
    """Keep model prose while rendering internal source keys as reader-facing names."""
    patterns = [
        (r'INCIDENTS-[A-Z0-9-]+', 'Active incidents'),
        (r'INCIDENT-\d+', 'Active incidents'),
        (r'MET-\d+', 'Usage telemetry'),
        (r'ERR-\d+', 'API error logs'),
        (r'ACC-\d+', 'Account configuration'),
        (r'EVT-\d+', 'Account events'),
        (r'KB-\d+', 'Product KB'),
        (r'HIST-\d+', 'Similar resolved tickets'),
        (r'INC-\d+', 'Customer ticket'),
    ]
    for pattern, label in patterns:
        text=re.sub(pattern,label,text,flags=re.IGNORECASE)
    return text


def source_label(source_id, source=None):
    """Stable reader-facing category; raw identifiers stay in Evidence Library."""
    sid=source_id.upper()
    if sid.startswith('INCIDENTS-') or sid.startswith('INCIDENT-'):
        return 'Active incidents'
    if sid.startswith(('MET-', 'ERR-')):
        return 'Usage telemetry' if sid.startswith('MET-') else 'API error logs'
    if sid.startswith(('EVT-', 'ACC-')) or (source and isinstance(source.get('content'),dict) and 'concurrency_limit' in source['content']):
        return 'Account configuration' if sid.startswith('ACC-') else 'Account events'
    if sid.startswith('KB-'):
        return 'Product KB'
    if sid.startswith('HIST-'):
        return 'Similar resolved tickets'
    if sid.startswith('EMPTY-'):
        return 'Evidence gap'
    return 'Customer ticket' if sid.startswith('INC-') else 'Supporting evidence'


def human_sources(source_ids, evidence):
    labels=[]
    for sid in source_ids:
        label=source_label(sid,evidence.get(sid))
        if label not in labels:
            labels.append(label)
    return labels


def public_excerpt(content):
    """Keep evidence preview readable while reserving record IDs for provenance."""
    if isinstance(content,dict):
        return {key:public_excerpt(value) for key,value in content.items() if key not in {'id','source_id'}}
    if isinstance(content,list):
        return [public_excerpt(value) for value in content]
    return content


def diagnosis_sentence(text):
    text = ' '.join(text.split())
    return re.split(r'(?<=[.!?])\s+(?=[A-Z])', text, maxsplit=1)[0]


def signal_cards(evidence):
    records = [(sid, source['content']) for sid, source in evidence.items() if isinstance(source.get('content'), dict)]
    account = next(((sid,c) for sid,c in records if 'concurrency_limit' in c and 'entitlement' in c), None)
    usage = [(sid,c) for sid,c in records if c.get('kind')=='usage']
    usage.sort(key=lambda row: row[1].get('timestamp',''))
    errors = next(((sid,c) for sid,c in records if c.get('kind')=='errors'),None)
    incidents = next(((sid,c) for sid,c in records if 'matching_incidents' in c),None)
    cards=[]
    if incidents:
        sid,c=incidents
        matches=c['matching_incidents']
        cards.append(('Active incidents',f'{len(matches)} known incident' + ('s' if len(matches)!=1 else '') if matches else 'No known match',c.get('region','') + ' · checked window',sid))
    if errors:
        sid,c=errors
        cards.append(('API errors',f"{c.get('http_status','API')} · {c.get('count','—')} errors",c.get('code','Error sample'),sid))
    if usage:
        sid,c=usage[-1]
        if 'attempted_peak' in c and 'admitted_peak' in c:
            value=f"{c['attempted_peak']} attempted / {c['admitted_peak']} admitted"
            detail='Peak concurrent requests'
            if 'peak_requests_per_minute' in c:
                detail+=f" · {c['peak_requests_per_minute']} requests/min"
        else:
            value='Usage sample available'
            detail=c.get('window','Recorded telemetry')
        cards.append(('Usage telemetry',value,detail,sid))
    if account:
        sid,c=account
        cards.append(('Account configuration',f"{c['concurrency_limit']} enforced / {c['entitlement']} entitled",f"{c.get('region','')} · version {c.get('version','—')}",sid))
    # Missing evidence is explicit; never turn absence into a healthy signal.
    if len(cards)<3:
        for sid,c in records:
            if sid.startswith('EMPTY-'):
                cards.append(('Evidence gap','No retained records',c.get('note','Additional evidence needed'),sid))
                if len(cards)>=3:
                    break
    return cards[:4]
