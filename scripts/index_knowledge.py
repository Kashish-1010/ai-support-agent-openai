from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from acme_support.indexing import index_knowledge
if __name__ == '__main__':
    print('Ready vector store:', index_knowledge(print))
