import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from .settings import DB_PATH
from .seed import ACCOUNTS, TICKETS, documents, telemetry, write_sources


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(path=DB_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path=DB_PATH):
    with connect(path) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, name TEXT, plan TEXT, region TEXT, product TEXT, entitlement INTEGER, concurrency_limit INTEGER, version INTEGER);
        CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, account_id TEXT REFERENCES accounts(id), subject TEXT, priority TEXT, scenario TEXT, body TEXT, status TEXT NOT NULL DEFAULT 'Open');
        CREATE TABLE IF NOT EXISTS telemetry(id TEXT PRIMARY KEY, account_id TEXT REFERENCES accounts(id), kind TEXT, timestamp TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY, region TEXT, started_at TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, kind TEXT, title TEXT, body TEXT);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, ticket_id TEXT, mode TEXT, status TEXT, created_at TEXT, result TEXT, trace TEXT);
        CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, run_id TEXT, account_id TEXT, old_value INTEGER, new_value INTEGER, expected_version INTEGER, reason TEXT, evidence TEXT, status TEXT, created_at TEXT, actor TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, action TEXT, proposal_id TEXT, payload TEXT);
        ''')
        if 'status' not in {row['name'] for row in c.execute('PRAGMA table_info(tickets)')}:
            c.execute("ALTER TABLE tickets ADD COLUMN status TEXT NOT NULL DEFAULT 'Open'")
            c.execute("UPDATE tickets SET status='Waiting on customer' WHERE id='INC-1044'")
            c.execute("UPDATE tickets SET status='In progress' WHERE id='INC-1045'")
        incident = dict(id='INCIDENT-021', region='eu-west-1', component='dashboard ingestion', status='investigating', started_at='2026-09-24T09:30:00Z', impact='Dashboard delayed by 15 minutes; Sync API job processing unaffected')
        c.execute('INSERT OR IGNORE INTO incidents VALUES(?,?,?,?)',(incident['id'],incident['region'],incident['started_at'],json.dumps(incident)))
        if c.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]:
            return
        c.executemany('INSERT INTO accounts VALUES(:id,:name,:plan,:region,:product,:entitlement,:concurrency_limit,:version)', ACCOUNTS)
        c.executemany('INSERT INTO tickets(id,account_id,subject,priority,scenario,body,status) VALUES(:id,:account_id,:subject,:priority,:scenario,:body,:status)', TICKETS)
        for row in telemetry():
            c.execute('INSERT INTO telemetry VALUES(?,?,?,?,?)', (row['id'],row['account_id'],row['kind'],row['timestamp'],json.dumps(row)))
        c.executemany('INSERT INTO documents VALUES(:id,:kind,:title,:body)',documents())
    write_sources()


def query(sql, args=(), path=DB_PATH):
    with connect(path) as c:
        return [dict(r) for r in c.execute(sql,args).fetchall()]


def ticket(ticket_id, path=DB_PATH):
    rows = query('SELECT * FROM tickets WHERE id=?',(ticket_id,),path)
    if not rows:
        raise ValueError('Unknown ticket')
    return rows[0]


def account(account_id, path=DB_PATH):
    rows = query('SELECT * FROM accounts WHERE id=?',(account_id,),path)
    if not rows:
        raise ValueError('Unknown account')
    return rows[0]


def start_run(ticket_id, mode, path=DB_PATH):
    run_id = str(uuid4())
    with connect(path) as c:
        c.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?)',(run_id,ticket_id,mode,'running',now(),None,'[]'))
    return run_id


def save_run(run_id, status, result, trace, path=DB_PATH):
    with connect(path) as c:
        c.execute('UPDATE runs SET status=?,result=?,trace=? WHERE id=?',(status,json.dumps(result),json.dumps(trace),run_id))


def audit(c, action, proposal_id, payload):
    cursor = c.execute('INSERT INTO audit(timestamp,action,proposal_id,payload) VALUES(?,?,?,?)',(now(),action,proposal_id,json.dumps(payload)))
    return cursor.lastrowid


def reset_northstar(path=DB_PATH):
    """Explicit demo reset; retain run/action audit history and invalidate approvals."""
    with connect(path) as c:
        c.execute('UPDATE accounts SET concurrency_limit=5,version=version+1 WHERE id=?',('ACC-001',))
        c.execute("UPDATE proposals SET status='expired' WHERE account_id='ACC-001' AND status='pending'")
        audit(c,'demo_reset',None,{'account_id':'ACC-001','limit':5})
