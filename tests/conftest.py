from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from acme_support.db import initialize

@pytest.fixture
def database(tmp_path):
    path=tmp_path/'test.db'
    initialize(path)
    return path
