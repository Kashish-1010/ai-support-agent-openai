# Live validation — September 27, 2026

Model: `gpt-6-luna` (low reasoning effort). Real Responses API calls and hosted File Search; no scripted substitute. The key remains in ignored `.env` and is not included in reports.

## Results

- All 23 synthetic knowledge documents successfully indexed.
- Northstar: diagnosed failed entitlement propagation; retrieved account, errors, events, usage and KB evidence; proposed 5 → 20 at version 17.
- Beacon: distinguished request-rate bursts from concurrency; no write proposal.
- Cedar: reported insufficient evidence and requested fresh diagnostic details; no write proposal.
- Lumen: identified the EU dashboard incident while distinguishing successful API jobs; no write proposal.
- Isolated live Streamlit UI test: proposal displayed, execution disabled before approval, account stayed at 5, simulated operator approved, limit became 20, proposed/approved/executed audit records verified.
- Post-change live investigation: current limit 20 acknowledged and no final redundant proposal. The backend rejected an attempted redundant tool request and returned the current state to the model.
- Regression suite: 15 passed.

The live UI's initial Northstar investigation took 13.4 seconds and 7 tool calls; post-change re-analysis took 11.8 seconds and 7 calls. These are single-run observations, not performance guarantees.

## Issue found and corrected

An initial evaluation used the existing app database, where the operator had already changed the limit to 20. The model incorrectly treated the historical limit of 5 as current. Existing execution validation blocked the redundant action. The prompt now explicitly prioritizes current account context over frozen telemetry, and the proposal tool rejects already-aligned limits before the final answer so the model can correct its recommendation. Evaluations now use fresh isolated databases and preserve the user's main app state.

## Evidence

Ignored local reports: `data/local/live-evaluation.json` (four scenario answers and checks) and `data/local/live-ui-validation.json` (before/after live findings, checks, and action audit). Main app live runs remain in SQLite. Reports contain fictional support data, not API credentials.

These checks validate a small demo, not production readiness. Source presence is checked automatically; the recorded diagnoses were also reviewed against the scenario contract. Telemetry remains synthetic and frozen; a successful configuration update does not establish real workload recovery. Source-withholding and broader adversarial evaluation remain follow-ups.
