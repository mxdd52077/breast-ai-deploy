"""Production smoke test with a disposable fictional demo account."""
import json
import httpx

with httpx.Client(base_url='https://apex-care-tan.vercel.app', timeout=150) as client:
    login=client.post('/api/auth/demo'); login.raise_for_status()
    client.headers['X-CSRF-Token']=login.json()['csrf']
    try:
        raw='虚构测试资料：请于2030年9月10日上午9点到乳腺外科复诊。'
        uploaded=client.post('/api/documents',files={'file':('schedule-smoke.txt',raw.encode(),'text/plain')})
        uploaded.raise_for_status()
        key=uploaded.json()['id']
        workspace=client.get('/api/workspace').json()
        extracted=[f for f in workspace['facts'] if f['document_id']==key]
        assert any(f['scheduled_date']=='2030-09-10' for f in extracted), 'Kimi schedule extraction failed'
        items=[{'id':f['id'],'version':f['version']} for f in workspace['facts'] if f['status']=='pending' and not f['conflict']]
        # A date conflict must be individually reviewed; confirm the uploaded fact with a note if flagged.
        for f in extracted:
            if f['conflict']:
                r=client.patch('/api/facts/'+f['id'],json={'status':'confirmed','version':f['version'],'note':'虚构测试：已对照原文'})
                r.raise_for_status()
        response=client.post('/api/facts/confirm-batch',json={'items':items}); response.raise_for_status()
        final=client.get('/api/workspace').json()
        assert all(f['status']=='confirmed' for f in final['facts'] if f['id'] in {i['id'] for i in items})
        assert any(t['due_date']=='2030-09-10' for t in final['tasks'])
        repeated=client.post('/api/facts/confirm-batch',json={'items':items})
        assert repeated.status_code==409
        print(json.dumps({'kimi_schedule_extracted':True,'batch_confirmed':len(items),'repeat_rejected':True,'tasks':len(final['tasks'])}))
    finally:
        removed=client.delete('/api/account')
        removed.raise_for_status()
