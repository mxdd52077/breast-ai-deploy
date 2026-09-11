"""Online report stream and approval check with disposable fictional inputs."""
import httpx
import json
with httpx.Client(base_url='https://apex-care-tan.vercel.app',timeout=60) as c:
    login=c.post('/api/auth/demo');login.raise_for_status()
    c.headers['X-CSRF-Token']=login.json()['csrf']
    try:
        r=c.post('/api/institution/simulations',json={'name':'Fictional report stream test','inputs':{}});r.raise_for_status();simulation=r.json()
        report=None
        with c.stream('POST','/api/institution/simulations/'+simulation['id']+'/report-stream') as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:continue
                event=json.loads(line)
                if event['type']=='status':print('Report stream progress received',flush=True)
                if event['type']=='error':raise RuntimeError(event['message'])
                if event['type']=='result':report=event['data']
        assert report and report['report']['simulation_snapshot']==simulation['results']
        approved=c.post('/api/institution/reports/'+report['id']+'/approve',json={'note':'Fictional verification of locked results and report.'});approved.raise_for_status()
        assert approved.json()['status']=='approved'
        history=c.get('/api/institution/workflow');history.raise_for_status()
        assert any(r['id']==approved.json()['id'] for r in history.json())
        print('Production streamed Kimi report, exact snapshot, approval and persistence PASS',flush=True)
    finally:c.delete('/api/account').raise_for_status()
