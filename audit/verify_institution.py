"""Exercise live providers using only a disposable fictional account."""
import json
import os
import sys
import tempfile
from pathlib import Path
import httpx

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
if '--local' in sys.argv:
    from dotenv import load_dotenv
    load_dotenv(root/'app/.env')
    directory=tempfile.mkdtemp(prefix='apex-live-institution-')
    os.environ['DATABASE_URL']='sqlite:///'+str(Path(directory)/'test.db')
    os.environ['APEX_DATA_DIR']=directory
    os.environ['APEX_WORKER']='false'
    os.environ['APEX_AUTO_CREATE_DB']='true'
    from fastapi.testclient import TestClient
    from app.backend.main import app
    from app.backend import institution_workflow as w
    validator=w.validate_executive_report
    def diagnose(*args):
        try:return validator(*args)
        except Exception as exc:
            print('Fictional report validation: '+str(exc),flush=True)
            raise
    w.validate_executive_report=diagnose
    client=TestClient(app)
else:
    client=httpx.Client(base_url='https://apex-care-tan.vercel.app',timeout=240)

def checked(r):
    if r.status_code!=200:raise RuntimeError(f'{r.request.url.path}: {r.status_code}: {r.text[:300]}')
    return r.json()

def streamed(path,body=None):
    with client.stream('POST',path,json=body) as response:
        assert response.status_code==200,response.status_code
        for line in response.iter_lines():
            if not line:continue
            event=json.loads(line)
            if event['type']=='result':return event['data']
            if event['type']=='error':raise RuntimeError(event['message'])
    raise RuntimeError('Stream closed without result')

with client:
    login=checked(client.post('/api/auth/demo'))
    client.headers['X-CSRF-Token']=login['csrf']
    try:
        scenario=streamed('/api/institution/scenario-stream',{'text':'虚构医院DBT场景：1000名40至74岁女性，平均55岁，当前筛查率50%，目标70%。'})
        assert scenario['population_size']==1000 and scenario['target_screening_rate']==70
        print('Live Kimi scenario verified',flush=True)
        sample=client.get('/api/institution/sample.csv');sample.raise_for_status()
        quality=checked(client.post('/api/institution/data-check',files={'file':('synthetic.csv',sample.content,'text/csv')}))
        assert quality['passed']
        simulation=checked(client.post('/api/institution/simulations',json={'name':'Fictional live verification','inputs':{**quality['proposals'],'target_screening_rate':70},'sources':{k:quality['source_id'] for k in quality['proposals']}}))
        outreach=checked(client.post('/api/institution/outreach/hospital',data={'simulation_id':simulation['id'],'capacity':'20','assumptions_confirmed':'true'},files={'file':('synthetic.csv',sample.content,'text/csv')}))
        assert outreach['eligible_count']==200
        print('CSV, source, deterministic ROI and hospital outreach verified',flush=True)
        papers=checked(client.post('/api/institution/evidence/search',json={'text':'digital breast tomosynthesis screening recall rate'}))
        assert papers and all(p['pmid'].isdigit() for p in papers)
        print('Live PubMed verified: '+str(len(papers))+' articles',flush=True)
        paper=next(p for p in papers if p['abstract'])
        candidates=streamed('/api/institution/evidence/'+paper['id']+'/extract-stream')
        print('Live Kimi evidence extraction verified: '+str(len(candidates))+' candidates',flush=True)
        if candidates:
            candidate=candidates[0]
            approval=checked(client.post('/api/institution/candidates/'+candidate['id']+'/approve',json={'note':'Fictional verification only: reviewed source excerpt.'}))
            simulation=checked(client.post('/api/institution/simulations',json={'inputs':{**quality['proposals'],'target_screening_rate':70,candidate['parameter']:candidate['value']},'approval_ids':[approval['id']]}))
        report=streamed('/api/institution/simulations/'+simulation['id']+'/report-stream')
        assert report['report']['simulation_snapshot']==simulation['results']
        approved=checked(client.post('/api/institution/reports/'+report['id']+'/approve',json={'note':'Fictional verification: checked locked snapshot and draft.'}))
        assert approved['status']=='approved'
        assert any(x['id']==approved['id'] for x in checked(client.get('/api/institution/workflow')))
        print('Live Kimi report, validation, approval and persistence verified',flush=True)
    finally:
        client.delete('/api/account').raise_for_status()
