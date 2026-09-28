from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from acme_support.db import initialize
from acme_support.seed import write_sources
if __name__ == '__main__':
    initialize()
    write_sources()
    print('Synthetic database and knowledge documents ready.')
