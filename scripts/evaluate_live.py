"""Small live smoke evaluation. Does not approve or execute any proposed change."""
from pathlib import Path
import json
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from acme_support.agent import investigate
from acme_support.db import initialize
from acme_support.settings import ROOT

if __name__ == '__main__':
    temporary = tempfile.TemporaryDirectory(prefix='live-eval-',dir=ROOT/'data/local')
    database = Path(temporary.name)/'evaluation.db'
    initialize(database)
    report=[]
    for ticket in ['INC-1042','INC-1043','INC-1044','INC-1045']:
        try:
            run,result,_=investigate(ticket,on_progress=print,path=database)
            expected_action=ticket=='INC-1042'
            checks={'action_presence_matches_expected':bool(result.get('proposal_id'))==expected_action}
            if expected_action:
                checks['primary_evidence_retrieved']={'ACC-001','ERR-001','EVT-002','KB-006'} <= set(result['evidence'])
            report.append(dict(ticket=ticket,run_id=run,checks=checks,analysis=result['analysis']))
        except Exception as exc:
            report.append(dict(ticket=ticket,error_type=type(exc).__name__))
    output=ROOT/'data/local/live-evaluation.json'
    output.write_text(json.dumps(report,indent=2))
    temporary.cleanup()
    print(f'Report: {output}. Review answers manually. No writes approved; main app database unchanged.')
    if any('error_type' in r or not all(r['checks'].values()) for r in report):
        sys.exit(1)
