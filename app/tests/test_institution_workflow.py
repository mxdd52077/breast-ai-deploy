import json
from app.backend import institution_workflow as w
from app.backend.db import Session, Audit
from src.evidence.pubmed_client import PubMedArticle

def post(c,path,body=None):
    return c.post('/api/institution'+path,json=body) if body is not None else c.post('/api/institution'+path)

def simulation(c,**extra):
    r=post(c,'/simulations',{'inputs':{},**extra})
    assert r.status_code==200,r.text
    return r.json()

def test_sample_proposal_and_source(demo):
    csv=demo.get('/api/institution/sample.csv')
    assert csv.status_code==200
    r=demo.post('/api/institution/data-check',files={'file':('sample.csv',csv.content,'text/csv')})
    assert r.status_code==200,r.text
    data=r.json();assert data['passed'] and data['proposals']['population_size']==200
    assert data['proposals']['current_screening_rate']==25
    s=simulation(demo,inputs=data['proposals'],sources={k:data['source_id'] for k in data['proposals']})
    assert s['analysis']['provenance']['population_size']['source_id']==data['source_id']
    assert post(demo,'/simulations',{'inputs':{'population_size':201},'sources':{'population_size':data['source_id']}}).status_code==400

def candidate(demo,monkeypatch):
    monkeypatch.setattr(w.PubMedClient,'search',lambda *a:[PubMedArticle(pmid='12345678',title='DBT trial',authors=('Test',),publication_year='2025',journal='Journal',abstract='DBT recall rate was 8.5 percent.')])
    article=post(demo,'/evidence/search',{'text':'DBT screening'}).json()[0]
    monkeypatch.setattr(w,'chat_json',lambda s,c,schema:schema.model_validate({'candidates':[{'parameter':'recall_rate','value':8.5,'unit':'percent','quote':'DBT recall rate was 8.5 percent.','applicability':'DBT screened women; applicability needs review.'}]}))
    r=post(demo,'/evidence/'+article['id']+'/extract');assert r.status_code==200,r.text
    return r.json()[0]

def test_evidence_approval_no_auto_compute_and_provenance(demo,monkeypatch):
    c=candidate(demo,monkeypatch)
    assert demo.get('/api/institution/simulations').json()==[]
    a=post(demo,'/candidates/'+c['id']+'/approve',{'note':'Reviewed applicability'}).json()
    s=simulation(demo,inputs={'recall_rate':8.5},approval_ids=[a['id']])
    assert s['analysis']['provenance']['recall_rate']['pmid']=='12345678'
    assert post(demo,'/simulations',{'inputs':{'recall_rate':9},'approval_ids':[a['id']]}).status_code==400
    r=demo.post('/api/auth/demo');demo.headers['X-CSRF-Token']=r.json()['csrf']
    assert post(demo,'/candidates/'+c['id']+'/approve',{'note':'Other account'}).status_code==404
    assert post(demo,'/simulations',{'inputs':{'recall_rate':8.5},'approval_ids':[a['id']]}).status_code==404

def test_bad_candidate_quote_is_not_saved(demo,monkeypatch):
    c=candidate(demo,monkeypatch)
    monkeypatch.setattr(w,'chat_json',lambda s,c,schema:schema.model_validate({'candidates':[{'parameter':'recall_rate','value':90,'unit':'percent','quote':'90 percent','applicability':'invalid'}]}))
    assert post(demo,'/evidence/'+c['article_id']+'/extract').status_code==503

def test_outreach_is_repeatable_and_hospital_uses_saved_inputs(demo):
    a=post(demo,'/outreach',{'population':100,'capacity':20,'seed':42})
    assert a.status_code==200,a.text
    assert a.json()==post(demo,'/outreach',{'population':100,'capacity':20,'seed':42}).json()
    assert post(demo,'/outreach',{'population':100,'capacity':101}).status_code==400
    s=simulation(demo,inputs={'mammography_cost':300})
    csv=demo.get('/api/institution/sample.csv').content
    data={'simulation_id':s['id'],'capacity':'20','assumptions_confirmed':'true'}
    r=demo.post('/api/institution/outreach/hospital',data=data,files={'file':('sample.csv',csv,'text/csv')})
    assert r.status_code==200,r.text
    assert r.json()['assumptions']['annualized_screening_cost']==150
    assert r.json()['eligible_count']==200
    assert len(r.json()['selected_rows'])==20
    assert all(set(x)=={'rank','source_row','priority_score'} for x in r.json()['selected_rows'])
    with Session() as db:
        assert 'selected_rows' not in db.get(Audit,r.json()['id']).detail
    data['assumptions_confirmed']='false'
    assert demo.post('/api/institution/outreach/hospital',data=data,files={'file':('sample.csv',csv,'text/csv')}).status_code==400

def test_report_locked_validated_approved(demo,monkeypatch):
    s=simulation(demo)
    data={'key_assumptions':['模型默认假设'],'limitations':['未本地校准'],'recommended_actions':['核验本院成本']}
    monkeypatch.setattr(w,'chat_json',lambda _s,c,schema:schema.model_validate(data))
    r=post(demo,'/simulations/'+s['id']+'/report');assert r.status_code==200,r.text
    assert r.json()['status']=='draft'
    a=post(demo,'/reports/'+r.json()['id']+'/approve',{'note':'Verified'});assert a.json()['status']=='approved'
    data['limitations']=['虚构的第999999999项限制']
    safe=post(demo,'/simulations/'+s['id']+'/report')
    assert safe.status_code==200
    assert '999999999' not in json.dumps(safe.json(),ensure_ascii=False)

def test_scenario_only_proposes(demo,monkeypatch):
    monkeypatch.setattr(w,'chat_json',lambda _s,c,schema:schema.model_validate({'target_screening_rate':70,'screening_modality':'DBT','missing_fields':['population_size'],'assumptions':[],'pubmed_query':'DBT screening'}))
    r=post(demo,'/scenario',{'text':'DBT target 70%'});assert r.status_code==200,r.text
    assert demo.get('/api/institution/simulations').json()==[]
    assert simulation(demo,inputs={'target_screening_rate':70},sources={'target_screening_rate':r.json()['id']})['inputs']['target_screening_rate']==70

def test_actual_labels_evaluation_and_invalid_scores(demo):
    r=demo.post('/api/institution/evaluation',data={'source_note':'Independent labels, fictional test','threshold':'.5'},files={'file':('labels.csv',b'label,score\n1,0.9\n0,0.8\n0,0.1\n1,0.2','text/csv')})
    assert r.status_code==200,r.text
    assert r.json()['metrics']['accuracy']==.5
    assert r.json()['metrics']['true_positive']==1
    bad=demo.post('/api/institution/evaluation',data={'source_note':'Invalid test'},files={'file':('labels.csv',b'label,score\n1,99','text/csv')})
    assert bad.status_code==400

def test_transient_model_failure_retries_once_without_duplicate_record(demo,monkeypatch):
    count=0
    def flaky(system,content,schema):
        nonlocal count
        count+=1
        if count==1:raise w.ServiceError('智能服务未返回可验证结果')
        return schema.model_validate({'target_screening_rate':70,'screening_modality':'DBT','missing_fields':[],'assumptions':[],'pubmed_query':'DBT screening'})
    monkeypatch.setattr(w,'chat_json',flaky)
    assert post(demo,'/scenario',{'text':'DBT target 70%'}).status_code==200
    assert count==2
    rows=demo.get('/api/institution/workflow').json()
    assert len([r for r in rows if r['kind']=='institution_scenario'])==1

def test_stream_only_returns_validated_result(demo,monkeypatch):
    monkeypatch.setattr(w,'chat_json',lambda _s,c,schema:schema.model_validate({'target_screening_rate':70,'screening_modality':'DBT','missing_fields':[],'assumptions':[],'pubmed_query':'DBT screening'}))
    r=post(demo,'/scenario-stream',{'text':'DBT target 70%'})
    events=[json.loads(x) for x in r.text.splitlines()]
    assert events[0]['type']=='status'
    assert events[-1]['type']=='result'
    assert events[-1]['data']['target_screening_rate']==70
    r=post(demo,'/simulations/not-owned/report-stream')
    events=[json.loads(x) for x in r.text.splitlines()]
    assert events[-1]['type']=='error' and events[-1]['status']==404
    assert not any(x['type']=='result' for x in events)
