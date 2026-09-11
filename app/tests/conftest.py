import os
import tempfile
from pathlib import Path

# Isolated disposable fixtures; never use the user's local app database or keys.
os.environ['APEX_DATA_DIR']=tempfile.mkdtemp(prefix='apex-tests-')
os.environ['DATABASE_URL']='sqlite:///'+str(Path(os.environ['APEX_DATA_DIR'])/'test.db')
os.environ['APEX_WORKER']='false'
os.environ['APEX_ALLOW_REAL_UPLOADS']='false'
os.environ['APEX_LLM_API_KEY']=''
os.environ['PADDLEOCR_ACCESS_TOKEN']=''
os.environ['BAIDU_OCR_API_KEY']=''
os.environ['BAIDU_OCR_SECRET_KEY']=''
os.environ['APEX_OCR_PROVIDER']='paddle'
os.environ['LANGSMITH_TRACING']='false'
os.environ['LANGCHAIN_TRACING_V2']='false'

import pytest
from fastapi.testclient import TestClient
from app.backend.main import app
from app.backend.security import limits

@pytest.fixture
def client():
    limits.clear()
    with TestClient(app) as c:
        yield c

@pytest.fixture
def demo(client):
    r=client.post('/api/auth/demo')
    assert r.status_code==200,r.text
    client.headers['X-CSRF-Token']=r.json()['csrf']
    return client
