from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
DB_PATH = Path(os.getenv('ACME_DB_PATH', str(ROOT / 'data/local/acme.db')))
INDEX_PATH = ROOT / 'data/local/index.json'
CORPUS = ROOT / 'data/synthetic/knowledge'
DEMO_NOW = '2026-09-24T10:20:00Z'
MODEL = os.getenv('OPENAI_MODEL', 'gpt-6-luna')


def vector_store_id():
    import json
    configured = os.getenv('OPENAI_VECTOR_STORE_ID')
    if configured:
        return configured
    if INDEX_PATH.exists():
        manifest = json.loads(INDEX_PATH.read_text())
        return manifest.get('vector_store_id') if manifest.get('status') == 'completed' else None
    return None
